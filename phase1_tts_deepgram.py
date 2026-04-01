import os
import requests
import subprocess
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")
if not deepgram_api_key or deepgram_api_key == "your_deepgram_key_here":
    raise ValueError("DEEPGRAM_API_KEY is not set properly in the .env file. Please add it.")

# Deepgram Aura TTS API Endpoint (Asteria is a great conversational female voice)
url = "https://api.deepgram.com/v1/speak?model=aura-asteria-en"
headers = {
    "Authorization": f"Token {deepgram_api_key}",
    "Content-Type": "application/json"
}

payload = {
    "text": "Hello there! I am Asteria, an AI voice powered by Deepgram Aura. "
            "I'm completely free for you to test, and my latency is incredibly low. "
            "If you can hear me right now, then Phase 1 is an absolute success! "
            "Let's move on to the brain."
}

try:
    print("Connecting to Deepgram Aura TTS...")
    
    # We use stream=True so we start receiving audio bytes immediately, before the whole file is generated.
    with requests.post(url, headers=headers, json=payload, stream=True) as response:
        if response.status_code == 200:
            print("Streaming audio playback...")
            
            # Pipe the audio stream directly to mpv (a fast media player) for instant playback
            process = subprocess.Popen(
                ['mpv', '--no-cache', '--no-terminal', '--', '-'], 
                stdin=subprocess.PIPE
            )
            
            # Write chunks directly to the player as soon as we get them
            for chunk in response.iter_content(chunk_size=4096):
                if chunk:
                    process.stdin.write(chunk)
            
            # Close the stream and wait for playback to finish
            process.stdin.close()
            process.wait()
            print("\nPlayback complete!")
            
        else:
            print(f"Deepgram Error: {response.status_code} - {response.text}")

except FileNotFoundError:
    print("\nError: The 'mpv' player is not installed.")
    print("You need a media player to stream the audio directly.")
    print("Install it by running: sudo apt install mpv (Linux) or brew install mpv (Mac)")
except Exception as e:
    print(f"\nUnexpected Error: {e}")
