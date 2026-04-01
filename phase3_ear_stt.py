import os
from dotenv import load_dotenv
from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
    Microphone
)

# Load environment variables
load_dotenv()
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

if not DEEPGRAM_API_KEY or DEEPGRAM_API_KEY == "your_deepgram_key_here":
    raise ValueError("DEEPGRAM_API_KEY is not set.")

def main():
    print("\n" + "="*50)
    print("Phase 3: The Ear (Deepgram Streaming STT)")
    print("="*50)
    print("Initializing microphone and connecting to Deepgram...")

    try:
        # Initialize the Deepgram Client
        client = DeepgramClient(DEEPGRAM_API_KEY)
        
        # Create a websocket connection for live listening
        connection = client.listen.live.v("1")

        # Define what happens when we receive a transcript from Deepgram
        def on_message(self, result, **kwargs):
            # Extract the actual words from the JSON result
            transcript = result.channel.alternatives[0].transcript
            
            # The 'is_final' flag means Deepgram has detected a pause and finalized the sentence
            if len(transcript) > 0 and result.is_final:
                print(f"🎙️ You: {transcript}")

        def on_error(self, error, **kwargs):
            print(f"\n[Deepgram Error: {error}]")

        # Bind our functions to the connection events
        connection.on(LiveTranscriptionEvents.Transcript, on_message)
        connection.on(LiveTranscriptionEvents.Error, on_error)

        # Configure the live stream options
        options = LiveOptions(
            model="nova-2",      # Deepgram's fastest, most accurate model
            language="en-US",    # Language
            smart_format=True,   # Automatically add punctuation and capitalization
            encoding="linear16", # Raw audio format
            channels=1,
            sample_rate=16000,
            interim_results=False, # Set to True if you want to see words as they are being spoken
            endpointing=300        # Trigger "is_final" after 300ms of silence
        )

        # Start the connection
        if not connection.start(options):
            print("Failed to connect to Deepgram.")
            return

        # Start the microphone and stream the audio data directly into the connection
        microphone = Microphone(connection.send)
        microphone.start()

        print("\n✅ Microphone is LIVE. Start speaking!")
        input("Press Enter to stop the recording...\n\n")

        # Clean shutdown
        microphone.finish()
        connection.finish()
        print("Finished recording.")

    except Exception as e:
        print(f"\nError: {e}")
        print("If you see an audio error, ensure PyAudio is installed correctly and your microphone is not blocked.")

if __name__ == "__main__":
    main()