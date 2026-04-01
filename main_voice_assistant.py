import os
import re
import queue
import threading
import requests
import subprocess
import time
from dotenv import load_dotenv
import google.generativeai as genai
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions, Microphone

# Load environment variables
load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini Brain
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')
# We use start_chat() instead of generate_content() so it remembers the conversation history!
chat_session = model.start_chat(history=[])

# State variables for managing audio interruptions
tts_queue = queue.Queue()
current_mpv_process = None
is_ai_speaking = False
# A lock to prevent the AI from generating multiple conflicting responses at the same time
thinking_lock = threading.Lock()

def deepgram_tts_worker():
    """Background Mouth thread: takes sentences from the queue and plays them."""
    global current_mpv_process, is_ai_speaking
    url = "https://api.deepgram.com/v1/speak?model=aura-asteria-en"
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    while True:
        text = tts_queue.get()
        if text is None:
            break
            
        payload = {"text": text}
        try:
            is_ai_speaking = True
            with requests.post(url, headers=headers, json=payload, stream=True) as response:
                if response.status_code == 200:
                    current_mpv_process = subprocess.Popen(
                        ['mpv', '--no-cache', '--no-terminal', '--', '-'], 
                        stdin=subprocess.PIPE
                    )
                    # Stream chunks to the player
                    for chunk in response.iter_content(chunk_size=4096):
                        if chunk and current_mpv_process.poll() is None: # check if process was killed by interruption
                            try:
                                current_mpv_process.stdin.write(chunk)
                            except BrokenPipeError:
                                break
                    
                    if current_mpv_process.poll() is None:
                        current_mpv_process.stdin.close()
                        current_mpv_process.wait()
        except Exception as e:
            print(f"TTS Error: {e}")
        finally:
            is_ai_speaking = False
            tts_queue.task_done()

def stop_ai_speaking():
    """Interrupts the AI: Clears the text queue and kills the audio player."""
    global current_mpv_process
    
    # 1. Clear all upcoming sentences from the queue
    with tts_queue.mutex:
        tts_queue.queue.clear()
        
    # 2. Kill the currently playing audio
    if current_mpv_process and current_mpv_process.poll() is None:
        current_mpv_process.kill()

def process_user_input(text):
    """The core pipeline: Send text to Brain, stream response to Mouth."""
    if not thinking_lock.acquire(blocking=False):
        return # If it's already processing a request, ignore overlapping audio triggers
        
    try:
        print(f"\n🎙️ You: {text}")
        print("🤖 Asteria: ", end="", flush=True)
        
        # Send text to Gemini and request a streaming response
        response_stream = chat_session.send_message(text, stream=True)
        buffer = ""
        
        for chunk in response_stream:
            text_chunk = chunk.text
            if not text_chunk:
                continue
                
            print(text_chunk, end="", flush=True)
            buffer += text_chunk
            
            # Split sentences and send them to the audio queue instantly
            match = re.search(r'(?<=[.!?])\s+', buffer)
            if match:
                sentence = buffer[:match.end()].strip()
                if sentence:
                    tts_queue.put(sentence)
                buffer = buffer[match.end():]
                
        # Flush the remainder
        if buffer.strip():
            tts_queue.put(buffer.strip())
            
    except Exception as e:
        print(f"\n[Gemini Error: {e}]")
    finally:
        thinking_lock.release()

def main():
    print("\n" + "="*60)
    print("Phase 4: The Full Voice Assistant (Ear + Brain + Mouth)")
    print("="*60)

    # 1. Start the Mouth
    tts_thread = threading.Thread(target=deepgram_tts_worker, daemon=True)
    tts_thread.start()

    # 2. Initialize the Ear
    client = DeepgramClient(DEEPGRAM_API_KEY)
    connection = client.listen.live.v("1")

    # Buffer to hold transcript chunks until the user stops talking
    user_speech_buffer = []

    def on_message(self, result, **kwargs):
        transcript = result.channel.alternatives[0].transcript
        
        if len(transcript) > 0:
            # INTERRUPT FEATURE: If the AI is talking, and you speak, it stops talking immediately!
            if is_ai_speaking:
                print("\n[Barge-in detected! Stopping AI...]")
                stop_ai_speaking()
                
            user_speech_buffer.append(transcript)
            
            # is_final means Deepgram detected a pause (endpointing threshold reached)
            if result.is_final:
                full_sentence = " ".join(user_speech_buffer).strip()
                user_speech_buffer.clear()
                
                if full_sentence:
                    # Fire the brain in a background thread so we can keep listening
                    threading.Thread(target=process_user_input, args=(full_sentence,), daemon=True).start()

    def on_error(self, error, **kwargs):
        print(f"\n[Deepgram Error: {error}]")

    connection.on(LiveTranscriptionEvents.Transcript, on_message)
    connection.on(LiveTranscriptionEvents.Error, on_error)

    # 800ms of silence = End of the user's turn
    options = LiveOptions(
        model="nova-2",
        language="en-US",
        smart_format=True,
        encoding="linear16",
        channels=1,
        sample_rate=16000,
        endpointing=800 
    )

    if not connection.start(options):
        print("Failed to connect to Deepgram.")
        return

    # Start sending mic audio to Deepgram
    microphone = Microphone(connection.send)
    microphone.start()

    print("\n✅ System is LIVE. Start talking to Asteria! (Press Ctrl+C to stop)")
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nShutting down safely...")
    finally:
        microphone.finish()
        connection.finish()
        tts_queue.put(None)
        tts_thread.join()

if __name__ == "__main__":
    main()