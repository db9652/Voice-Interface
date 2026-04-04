# Voice Interface Project Plan

## Overview
A real-time, low-latency conversational AI agent. The system listens to user input via the microphone, processes the intent using Google's Gemini Pro, and responds with a highly expressive voice using ElevenLabs.

## Architecture & Workflow

The pipeline consists of four main stages running sequentially (and partially concurrently via streaming):

1. **The Trigger & The Ear (VAD + STT)**
   - **VAD (Voice Activity Detection):** Continuously monitors the microphone. It detects when you start speaking and cuts the recording when you stop (e.g., after 1 second of silence).
   - **STT (Speech-to-Text):** The recorded audio is instantly sent to an STT provider (like Deepgram or OpenAI Whisper) to be converted into text.

2. **The Brain (LLM - Gemini Pro)**
   - The transcribed text is sent to Gemini Pro along with the conversation history.
   - **Crucial Optimization:** We request Gemini to *stream* its response back to us chunk by chunk, rather than waiting for the entire response to finish generating.

3. **The Mouth (TTS - ElevenLabs)**
   - As Gemini streams text back (e.g., as soon as a full sentence or phrase is formed), we immediately pipe that text into the ElevenLabs Streaming API.
   - ElevenLabs begins synthesizing the audio and streams it back to our speakers before Gemini has even finished writing the rest of the paragraph.

4. **The Loop**
   - The system plays the audio through PyAudio. Once the AI finishes speaking, it immediately goes back to listening for your next input.

## Tech Stack
- **Language:** Python 3
- **Audio I/O:** `pyaudio`, `sounddevice`
- **Speech-to-Text (Ear):** Deepgram (Cloud) / Vosk (Local Wake Word)
- **LLM (Brain):** Google Gemini Pro / OpenClaw Gateway
- **Text-to-Speech (Mouth):** Deepgram Aura TTS

## Implementation Phases

### Phase 1: The Voice (TTS Proof of Concept)
- Authenticate with ElevenLabs/Deepgram.
- Write a script to stream generated audio to the speakers.

### Phase 2: The Brain (LLM + TTS Streaming)
- Authenticate with Gemini Pro.
- Create a text-based chat loop with Gemini and stream to TTS.

### Phase 3: The Ear (Mic + STT)
- Implement microphone recording and STT.

### Phase 4: Full Pipeline & Barge-in
- Connect all phases (Mic -> STT -> LLM -> TTS).
- Implement "Barge-in" (Interruption): Stop playing audio when the user starts speaking.

### Phase 5: Privacy & Wake Word (Vosk)
- Integrated a local, offline wake word engine using **Vosk**.
- Mic stays 100% local until the word "White" is heard.
- Once triggered, it activates the cloud-based Deepgram + OpenClaw pipeline.
- Automatically goes back to "Sleep Mode" after 5 seconds of silence.
- Goal: Save API credits and ensure privacy.

### Phase 6: Client/Server Architecture & WebUI
- **Server:** Converted the core pipeline into a WebSocket server (`server.py`) running on port 8765. It handles Deepgram STT, OpenClaw LLM, and Deepgram TTS.
- **Client (WebUI):** Created a sleek HTML/JS frontend (`index.html`) that uses the browser's native `getUserMedia` API to capture mic audio and stream it to the server.
- **Deployment:** The setup is routed through Cloudflare Tunnels for `white.chintuladdu.online` providing automatic HTTPS and secure WebSocket connections (WSS) via `white-ws.chintuladdu.online`.
- **Security:** Integrated Cloudflare Access (Zero Trust) to protect the interface with an email-based PIN login.
