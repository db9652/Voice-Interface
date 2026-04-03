# Voice Interface Project

A real-time, low-latency conversational AI agent. 

The system listens to user input via the microphone, processes the intent using **Google's Gemini Pro** or **OpenClaw Gateway**, and responds with a highly expressive voice using **Deepgram Aura TTS**.

## Features
- **Real-time Streaming:** Processes audio and text concurrently for minimal latency.
- **Barge-in (Interruptions):** Stop the AI's response mid-sentence by just speaking.
- **Privacy & Wake Word:** Listen for "Hey White" locally without streaming audio to the cloud until triggered.
- **OpenClaw Integration:** Talk directly to the OpenClaw assistant and give it system commands via voice.
- **Remote Access (WebUI):** Client/Server architecture allows you to talk to the assistant from any smartphone or browser via WebSockets.

## Installation & Setup

1.  **Clone the Repository:**
    ```bash
    git clone git@github.com:db9652/Voice-Interface.git
    cd Voice-Interface
    ```

2.  **Create a Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    pip install vosk sounddevice
    ```

4.  **Set up API Keys:**
    Create a `.env` file and add your keys:
    ```
    DEEPGRAM_API_KEY=your_deepgram_key
    GEMINI_API_KEY=your_gemini_key
    ```

5.  **Download the Vosk Model (for Wake Word):**
    ```bash
    wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
    unzip vosk-model-small-en-us-0.15.zip
    mv vosk-model-small-en-us-0.15 model
    rm vosk-model-small-en-us-0.15.zip
    ```

6.  **Run the Project:**
    - To talk to raw Gemini locally: `python main_voice_assistant.py`
    - To talk to OpenClaw locally: `python openclaw_voice_client.py`
    - To talk to OpenClaw (with wake word): `python openclaw_voice_client_wakeword.py`

7.  **Run Remotely via WebUI (Client/Server):**
    - Start the WebSocket Server: `python server.py`
    - Start a local web server for the UI: `python -m http.server 8080`
    - Open your browser to `http://127.0.0.1:8080` (or setup a Cloudflare Tunnel for secure remote HTTPS access on your smartphone).

## Notes
- Formatting Constraint: Do not use asterisks (*) or double asterisks (**) in OpenClaw responses. The voice interface (Deepgram Aura) may read them aloud as "asterisks," which disrupts the conversational flow. Using a different TTS model might resolve this, but for now, avoid markdown emphasis.
