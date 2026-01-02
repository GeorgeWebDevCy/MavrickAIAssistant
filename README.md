# Mavrick AI Assistant (Jarvis-like)

Mavrick is a sophisticated, voice-controlled AI assistant with a futuristic HUD-style interface. Inspired by JARVIS (Iron Man), it uses GPT-4o for its brain and integrated system tools for automation.

## Features
- **Futuristic HUD**: Transparent, borderless UI with a pulsing core animation.
- **Voice Controlled**: Speech-to-text (Google Recognition) and Text-to-speech (pyttsx3).
- **AI Brain**: Powered by OpenAI GPT-4o with tool-calling capabilities.
- **System Automation**:
  - Get Time/Date/System Stats.
  - Open applications (Chrome, Notepad, Code, etc.).
  - Search the web.

## Setup Instructions

1. **Prerequisites**:
   - Python 3.10+
   - PyAudio (requires `pip install pipwin` then `pipwin install pyaudio` on some Windows setups if standard pip fails).

2. **Installation**:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   pip install customtkinter openai pyttsx3 speechrecognition pyaudio python-dotenv psutil
   ```

3. **Configuration**:
   - Rename `.env` or create one with your OpenAI API key:
     ```env
     OPENAI_API_KEY=your_actual_key_here
     USER_NAME=Sir
     ```

4. **Run**:
   ```bash
   python main.py
   ```

## Key Commands
- "Mavrick, what's the time?"
- "Mavrick, open Chrome."
- "Mavrick, search for latest space news."
- "Mavrick, how are my system stats?"