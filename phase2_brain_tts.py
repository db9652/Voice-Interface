import os
import re
import queue
import threading
import requests
import subprocess
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_key_here":
    raise ValueError("GEMINI_API_KEY is not set in the .env file.")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
# We use gemini-2.5-flash because it is built for blazing fast, low-latency responses
model = genai.GenerativeModel('gemini-2.5-flash')

# A queue to hold sentences that are ready to be spoken
tts_queue = queue.Queue()

def deepgram_tts_worker():
    """Background thread that takes sentences from the queue and plays them sequentially."""
    url = "https://api.deepgram.com/v1/speak?model=aura-asteria-en"
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    while True:
        text = tts_queue.get()
        if text is None:  # Sentinel value to shut down the thread
            break
            
        payload = {"text": text}
        try:
            with requests.post(url, headers=headers, json=payload, stream=True) as response:
                if response.status_code == 200:
                    process = subprocess.Popen(
                        ['mpv', '--no-cache', '--no-terminal', '--', '-'], 
                        stdin=subprocess.PIPE
                    )
                    for chunk in response.iter_content(chunk_size=4096):
                        if chunk:
                            process.stdin.write(chunk)
                    process.stdin.close()
                    process.wait()
                else:
                    print(f"\n[TTS Error: {response.status_code} - {response.text}]")
        except Exception as e:
            print(f"\n[Playback Error: {e}]")
        finally:
            tts_queue.task_done()

def main():
    # Start the "Mouth" (TTS) in a background thread so it doesn't block the "Brain" (Gemini)
    tts_thread = threading.Thread(target=deepgram_tts_worker, daemon=True)
    tts_thread.start()

    print("\n" + "="*50)
    print("Phase 2: The Brain (Gemini -> Deepgram Streaming)")
    print("="*50)
    
    # Text-based chat loop
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ['exit', 'quit']:
            break
            
        print("Asteria: ", end="", flush=True)
        
        # Ask Gemini to stream the response back token-by-token
        response_stream = model.generate_content(user_input, stream=True)
        
        buffer = ""
        for chunk in response_stream:
            text_chunk = chunk.text
            if not text_chunk:
                continue
                
            print(text_chunk, end="", flush=True)
            buffer += text_chunk
            
            # Look for sentence boundaries (., !, or ? followed by a space)
            # This is the "secret sauce" for zero lag. We don't wait for the whole paragraph!
            match = re.search(r'(?<=[.!?])\s+', buffer)
            if match:
                sentence = buffer[:match.end()].strip()
                if sentence:
                    tts_queue.put(sentence) # Send the completed sentence to the Mouth
                buffer = buffer[match.end():] # Keep the incomplete remainder in the buffer
                
        # Flush any leftover text that didn't end in punctuation
        if buffer.strip():
            tts_queue.put(buffer.strip())
            
        print("\n[Waiting for audio to finish playing...]")
        # Wait for the worker queue to clear before allowing the next input
        tts_queue.join() 

    # Clean shutdown
    tts_queue.put(None)
    tts_thread.join()

if __name__ == "__main__":
    main()