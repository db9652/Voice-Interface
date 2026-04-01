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
- **Audio I/O:** `pyaudio` (for capturing microphone and playing speaker output)
- **Speech-to-Text (Ear):** Deepgram (Recommended for <300ms latency) or OpenAI Whisper API.
- **LLM (Brain):** `google-generativeai` (Gemini Pro)
- **Text-to-Speech (Mouth):** `elevenlabs` Python SDK (Streaming mode)

## Implementation Phases

### Phase 1: The Voice (TTS Proof of Concept)
- Authenticate with ElevenLabs.
- Write a script to take a hardcoded string and stream the generated audio to the speakers.
- Goal: Verify API keys and audio playback latency.

### Phase 2: The Brain (LLM + TTS Streaming)
- Authenticate with Gemini Pro.
- Create a text-based chat loop with Gemini.
- Pipe Gemini's streaming text output directly into ElevenLabs.
- Goal: Ensure text chunks are smoothly converted to continuous audio without stuttering.

### Phase 3: The Ear (Mic + STT)
- Implement PyAudio to record from the microphone.
- Send the audio buffer to the STT provider and get the transcript.
- Goal: Complete the pipeline (Mic -> STT -> Print text).

### Phase 4: Full Pipeline & Optimization (VAD + Interruptions)
- Connect all three phases (Mic -> STT -> LLM -> TTS).
- Implement Voice Activity Detection (VAD) so no manual "Enter" key is needed; you just speak naturally.
- Implement "Barge-in" (Interruption): If the AI is speaking and you start talking, it should immediately stop playing audio and listen to you.