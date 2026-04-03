import asyncio
import websockets
import pyaudio
import json
import subprocess
import threading
import sys

# Change this to your Server's IP address when running remotely
SERVER_URI = "ws://127.0.0.1:8765"

# Audio Recording Config (Match Deepgram settings)
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024

current_mpv_process = None

def play_audio_stream(audio_queue):
    """Pulls bytes from the queue and pipes them to MPV to play"""
    global current_mpv_process
    while True:
        chunk = audio_queue.get()
        if chunk is None:
            break
            
        if isinstance(chunk, dict) and chunk.get("type") == "tts_start":
            # Start a new MPV process for this sentence
            current_mpv_process = subprocess.Popen(
                ['mpv', '--no-cache', '--no-terminal', '--', '-'], 
                stdin=subprocess.PIPE
            )
            continue
            
        if isinstance(chunk, dict) and chunk.get("type") == "tts_end":
            # Close stream to finish playing
            if current_mpv_process and current_mpv_process.poll() is None:
                current_mpv_process.stdin.close()
                current_mpv_process.wait()
            continue

        # Otherwise it's audio bytes
        if current_mpv_process and current_mpv_process.poll() is None:
            try:
                current_mpv_process.stdin.write(chunk)
            except BrokenPipeError:
                pass

async def microphone_client():
    audio_queue = asyncio.Queue()
    play_queue = queue.Queue() # Regular queue for the threading worker
    
    # Start playback worker
    threading.Thread(target=play_audio_stream, args=(play_queue,), daemon=True).start()

    print(f"Connecting to {SERVER_URI}...")
    try:
        async with websockets.connect(SERVER_URI) as websocket:
            print("✅ Connected! Start talking...")

            # 1. Thread for capturing microphone and putting in async queue
            def mic_callback(in_data, frame_count, time_info, status):
                # We could add energy detection here to trigger barge-in event
                asyncio.run_coroutine_threadsafe(audio_queue.put(in_data), loop)
                return (None, pyaudio.paContinue)

            p = pyaudio.PyAudio()
            stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, 
                            input=True, frames_per_buffer=CHUNK, 
                            stream_callback=mic_callback)
            stream.start_stream()
            loop = asyncio.get_running_loop()

            # 2. Async task for sending Mic bytes to Server
            async def send_audio():
                while True:
                    data = await audio_queue.get()
                    await websocket.send(data)

            # 3. Async task for receiving TTS bytes from Server
            async def receive_audio():
                while True:
                    try:
                        message = await websocket.recv()
                        if isinstance(message, bytes):
                            play_queue.put(message)
                        else:
                            data = json.loads(message)
                            play_queue.put(data)
                    except websockets.exceptions.ConnectionClosed:
                        print("Server disconnected.")
                        break

            # Run both tasks concurrently
            await asyncio.gather(send_audio(), receive_audio())
            
    except ConnectionRefusedError:
        print(f"❌ Could not connect to {SERVER_URI}. Is the server running?")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Shutting down client...")
        try:
            stream.stop_stream()
            stream.close()
            p.terminate()
        except:
            pass

if __name__ == "__main__":
    # We need queue for python threads
    import queue 
    asyncio.run(microphone_client())