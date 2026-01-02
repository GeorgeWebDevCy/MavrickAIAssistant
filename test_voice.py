import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engine.voice import VoiceEngine

def test_voice():
    load_dotenv()
    print("Initializing VoiceEngine...")
    try:
        engine = VoiceEngine()
        print("Attempting to speak...")
        engine.speak("Testing high quality voice system. Can you hear me, Sir?")
        print("Voice command completed.")
    except Exception as e:
        print(f"CRITICAL FAIL: {repr(e)}")

if __name__ == "__main__":
    test_voice()
