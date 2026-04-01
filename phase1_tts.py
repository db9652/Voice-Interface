import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import stream

# Load environment variables from .env file
load_dotenv()

elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
if not elevenlabs_api_key:
    raise ValueError("ELEVENLABS_API_KEY is not set in the .env file. Please add it.")

# Initialize the ElevenLabs client
client = ElevenLabs(api_key=elevenlabs_api_key)

print("Connecting to ElevenLabs...")

# We use a Python generator to simulate how Gemini will send us text chunk-by-chunk.
# This proves that ElevenLabs can start speaking before the whole paragraph is finished.
def text_streamer():
    yield "Hello there! "
    yield "This is a test of the ElevenLabs streaming capability. "
    yield "If you can hear me talking without much of a delay, "
    yield "then Phase 1 is an absolute success! Let's get to work on the brain."

try:
    print("Generating and streaming audio...")
    
    # Rachel's default voice ID. In the new SDK, we must use the exact ID.
    rachel_voice_id = "21m00Tcm4TlvDq8ikWAM"
    
    # Generate audio stream using the turbo model for lowest latency
    # The convert_realtime method is explicitly built for text streaming (like from an LLM)
    audio_stream = client.text_to_speech.convert_realtime(
        text=text_streamer(),
        voice_id=rachel_voice_id,
        model_id="eleven_turbo_v2_5", # The turbo model is specifically optimized for conversational AI
        output_format="mp3_44100_128",
        voice_settings=None # Workaround for a bug in ElevenLabs Python SDK v2+ defaults
    )
    
    # Play the audio stream directly to the speakers
    stream(audio_stream)
    print("\nPlayback complete!")
    
except Exception as e:
    print(f"\nError: {e}")
    print("If you get an mpv or ffplay error, you might need to install them (e.g., 'sudo apt install mpv' or 'brew install mpv').")
