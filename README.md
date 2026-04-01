# Voice Interface Project

A modular, real-time voice conversational AI built in Python. This system acts as a fully voice-driven assistant that listens, thinks, and speaks back with extremely low latency. It is built by chaining state-of-the-art APIs for Speech-to-Text (STT), Large Language Models (LLM), and Text-to-Speech (TTS).

## Features
- **Real-time Listening:** The microphone is always hot. It uses a Voice Activity Detector (VAD) to understand exactly when you stop speaking.
- **Low-Latency Streaming:** Responses from the LLM stream directly into the TTS engine sentence-by-sentence, drastically reducing the pause before the AI speaks.
- **Barge-In (Interruptions):** If you interrupt the AI while it's speaking, it instantly stops talking and listens to you instead.

## Tech Stack
- **The Ear (STT):** [Deepgram Live Streaming API](https://deepgram.com/) - Converts spoken words to text with sub-300ms latency.
- **The Brain (LLM):** [Google Gemini 2.5 Flash](https://ai.google.dev/) - A blazing-fast generative model built for real-time applications.
- **The Mouth (TTS):** [Deepgram Aura](https://deepgram.com/) - A high-quality, ultra-low latency text-to-speech engine optimized for conversational AI.

## Project Structure
We built this iteratively in phases to test each component's latency and stability:
- `phase1_tts_deepgram.py`: Tests the TTS functionality and audio streaming.
- `phase2_brain_tts.py`: Tests connecting the LLM streaming directly into the TTS engine to eliminate generation wait times.
- `phase3_ear_stt.py`: Tests the physical microphone connection and Deepgram real-time transcription.
- `main_voice_assistant.py`: The final, complete conversational loop connecting all components with interruption handling.

## Setup Instructions

### Prerequisites
1. **Python 3.10+** installed on your system.
2. A **media player** to output the streaming audio directly. You need either `mpv` or `ffplay` installed globally:
   - **Linux:** `sudo apt install mpv`
   - **MacOS:** `brew install mpv`
   - **Windows:** Download [mpv](https://mpv.io/installation/) and add it to your system PATH.
3. API Keys from [Deepgram](https://console.deepgram.com) and [Google AI Studio](https://aistudio.google.com).

### Installation
1. Clone the repository:
   ```bash
   git clone git@github.com:db9652/Voice-Interface.git
   cd Voice-Interface
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the root directory and add your API keys:
   ```env
   GEMINI_API_KEY=your_gemini_key_here
   DEEPGRAM_API_KEY=your_deepgram_key_here
   ```

### Usage
To run the full voice assistant, simply execute:
```bash
python main_voice_assistant.py
```
Wait for the terminal to display `✅ System is LIVE`, and then speak naturally into your microphone!