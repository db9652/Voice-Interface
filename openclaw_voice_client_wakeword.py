import os
import re
import json
import queue
import threading
import requests
import subprocess
import time
import sys
from dotenv import load_dotenv
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions, Microphone
from vosk import Model, KaldiRecognizer
import sounddevice as sd

# Load environment variables
load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

# OpenClaw Gateway Config
OPENCLAW_GATEWAY_URL = "http://127.0.0.1:18789/v1/chat/completions"
OPENCLAW_TOKEN = "9f768d1ad23e7a4fc3cb0ebf871ab6c644878d871fa20713"

# State variables
tts_queue = queue.Queue()
current_mpv_process = None
is_ai_speaking = False
is_active = False # True when wake word is triggered
thinking_lock = threading.Lock()

# Vosk Model for Wake Word
VOSK_MODEL_PATH = "model"
if not os.path.exists(VOSK_MODEL_PATH):
    print("Vosk model not found. Run the setup command first.")
    sys.exit(1)
model = Model(VOSK_MODEL_PATH)
recognizer = KaldiRecognizer(model, 16000)

def play_chime(type="start"):
    """Play a short chime to indicate listening or ending."""
    # Using simple beep frequencies or a tiny wav if available.
    # For now, we'll use a simple print but can be upgraded to play a .wav.
    if type == "start":
        print("\n🔔 [Listening...]")
    else:
        print("\n🔕 [Idle]")

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
                    for chunk in response.iter_content(chunk_size=4096):
                        if chunk and current_mpv_process.poll() is None:
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
    with tts_queue.mutex:
        tts_queue.queue.clear()
    if current_mpv_process and current_mpv_process.poll() is None:
        current_mpv_process.kill()

def process_with_openclaw(text):
    """Send text to OpenClaw, stream response to Mouth."""
    if not thinking_lock.acquire(blocking=False):
        return
        
    try:
        print(f"\n🎙️ You: {text}")
        print("🤖 White: ", end="", flush=True)
        
        headers = {
            "Authorization": f"Bearer {OPENCLAW_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "openclaw/default",
            "messages": [{"role": "user", "content": text}],
            "stream": True,
            "user": "voice-client-blue"
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
    finally:
        thinking_lock.release()

def start_conversation():
    """Main Conversation Loop (Deepgram + OpenClaw). Runs until idle timeout."""
    global is_active
    play_chime("start")
    is_active = True
    
    client = DeepgramClient(DEEPGRAM_API_KEY)
    connection = client.listen.websocket.v("1")
    user_speech_buffer = []
    last_speech_time = time.time()
    IDLE_TIMEOUT = 5.0 # Seconds of silence before going back to wake word mode

    def on_message(self, result, **kwargs):
        nonlocal last_speech_time
        transcript = result.channel.alternatives[0].transcript
        if len(transcript) > 0:
            last_speech_time = time.time()
            if is_ai_speaking:
                stop_ai_speaking()
                
            user_speech_buffer.append(transcript)
            
            if result.is_final:
                full_sentence = " ".join(user_speech_buffer).strip()
                user_speech_buffer.clear()
                if full_sentence:
                    threading.Thread(target=process_with_openclaw, args=(full_sentence,), daemon=True).start()

    connection.on(LiveTranscriptionEvents.Transcript, on_message)

    options = LiveOptions(
        model="nova-2", language="en-US", smart_format=True,
        encoding="linear16", channels=1, sample_rate=16000, endpointing=800
    )

    if not connection.start(options):
        print("Failed to connect to Deepgram.")
        is_active = False
        return

    microphone = Microphone(connection.send)
    microphone.start()

    try:
        while is_active:
            # Check for timeout (if not speaking and AI not talking)
            if time.time() - last_speech_time > IDLE_TIMEOUT and not is_ai_speaking:
                is_active = False
            time.sleep(0.1)
    finally:
        microphone.finish()
        connection.finish()
        play_chime("stop")

def wake_word_callback(indata, frames, time_info, status):
    """Vosk Audio Callback."""
    global is_active
    if is_active: return # Don't listen for wake word if already active
    
    if recognizer.AcceptWaveform(bytes(indata)):
        result = json.loads(recognizer.Result())
        text = result.get("text", "")
        if "white" in text:
            print(f"\n[Wake word detected: {text}]")
            # We can't start the loop here because it's a callback. 
            # We'll set a flag to be picked up by the main loop.
            is_active = "triggered" 

def main():
    global is_active
    print("\n" + "="*60)
    print("OpenClaw Voice Interface (Wake Word: 'White')")
    print("="*60)
    print("Listening locally for 'White'...")

    tts_thread = threading.Thread(target=deepgram_tts_worker, daemon=True)
    tts_thread.start()

    with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                           channels=1, callback=wake_word_callback):
        while True:
            if is_active == "triggered":
                start_conversation()
                print("\nListening locally for 'White'...")
            time.sleep(0.1)

if __name__ == "__main__":
    main()
