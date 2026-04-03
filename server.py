import os
import re
import json
import queue
import threading
import requests
import asyncio
import websockets
from dotenv import load_dotenv
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions

load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
OPENCLAW_GATEWAY_URL = "http://127.0.0.1:18789/v1/chat/completions"
OPENCLAW_TOKEN = "9f768d1ad23e7a4fc3cb0ebf871ab6c644878d871fa20713"

# Keep track of connected clients
active_connections = set()

async def deepgram_tts_worker(tts_queue, websocket):
    """Takes sentences from the queue, gets TTS audio, and sends it to the client via WebSocket."""
    url = "https://api.deepgram.com/v1/speak?model=aura-asteria-en"
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    while True:
        text = await asyncio.to_thread(tts_queue.get)
        if text is None:
            break
            
        payload = {"text": text}
        try:
            # We notify the client that TTS is starting so it can clear its buffers if needed
            await websocket.send(json.dumps({"type": "tts_start"}))
            
            response = requests.post(url, headers=headers, json=payload, stream=True)
            if response.status_code == 200:
                for chunk in response.iter_content(chunk_size=4096):
                    if chunk:
                        # Send binary audio chunk to client
                        await websocket.send(chunk)
            
            # Notify client that this TTS segment is done
            await websocket.send(json.dumps({"type": "tts_end"}))
        except Exception as e:
            print(f"TTS Error: {e}")
        finally:
            tts_queue.task_done()

def process_user_input(text, tts_queue):
    """Send text to OpenClaw, stream response chunks to TTS queue."""
    try:
        print(f"\n🎙️ Client: {text}")
        print("🤖 White: ", end="", flush=True)
        
        headers = {
            "Authorization": f"Bearer {OPENCLAW_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "openclaw/default",
            "messages": [{"role": "user", "content": text}],
            "stream": True,
            "user": "voice-client-remote"
        }
        
        buffer = ""
        with requests.post(OPENCLAW_GATEWAY_URL, headers=headers, json=payload, stream=True) as response:
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith("data: "):
                        data_content = line_str[6:]
                        if data_content == "[DONE]":
                            break
                        try:
                            data = json.loads(data_content)
                            content = data['choices'][0]['delta'].get('content', '')
                            if content:
                                print(content, end="", flush=True)
                                buffer += content
                                match = re.search(r'(?<=[.!?])\s+', buffer)
                                if match:
                                    sentence = buffer[:match.end()].strip()
                                    if sentence:
                                        tts_queue.put(sentence)
                                    buffer = buffer[match.end():]
                        except:
                            pass
                            
        if buffer.strip():
            tts_queue.put(buffer.strip())
            
    except Exception as e:
        print(f"\n[OpenClaw Gateway Error: {e}]")


async def handle_client(websocket, path):
    print(f"New client connected: {websocket.remote_address}")
    active_connections.add(websocket)
    
    tts_queue = queue.Queue()
    is_ai_speaking = False
    
    # Start TTS worker for this specific client
    tts_task = asyncio.create_task(deepgram_tts_worker(tts_queue, websocket))

    # Initialize Deepgram Ear
    deepgram_client = DeepgramClient(DEEPGRAM_API_KEY)
    connection = deepgram_client.listen.websocket.v("1")
    user_speech_buffer = []

    def on_message(self, result, **kwargs):
        transcript = result.channel.alternatives[0].transcript
        if len(transcript) > 0:
            user_speech_buffer.append(transcript)
            if result.is_final:
                full_sentence = " ".join(user_speech_buffer).strip()
                user_speech_buffer.clear()
                if full_sentence:
                    # Fire Brain processing in background thread
                    threading.Thread(target=process_user_input, args=(full_sentence, tts_queue), daemon=True).start()

    def on_error(self, error, **kwargs):
        print(f"\n[Deepgram Error: {error}]")

    connection.on(LiveTranscriptionEvents.Transcript, on_message)
    connection.on(LiveTranscriptionEvents.Error, on_error)

    options = LiveOptions(
        model="nova-2",
        language="en-US",
        smart_format=True,
        # encoding="linear16", # Commented out to allow Web browser WebM streaming
        # sample_rate=16000,   # Commented out
        channels=1,
        endpointing=3000
    )

    if not connection.start(options):
        print("Failed to connect to Deepgram STT.")
        return

    try:
        async for message in websocket:
            if isinstance(message, bytes):
                # Incoming audio from client microphone -> send to Deepgram
                connection.send(message)
            else:
                # Text/JSON commands from client (e.g. barge-in)
                data = json.loads(message)
                if data.get("type") == "barge_in":
                    print("\n[Barge-in detected by client! Stopping TTS queue...]")
                    with tts_queue.mutex:
                        tts_queue.queue.clear()
                    
    except websockets.exceptions.ConnectionClosed:
        print(f"Client disconnected: {websocket.remote_address}")
    finally:
        active_connections.remove(websocket)
        connection.finish()
        tts_queue.put(None)
        await tts_task

async def main():
    print("Starting Voice Server on ws://0.0.0.0:8765")
    async with websockets.serve(handle_client, "0.0.0.0", 8765):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())