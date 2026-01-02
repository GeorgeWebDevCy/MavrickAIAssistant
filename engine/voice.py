import os
import speech_recognition as sr
from openai import OpenAI
from dotenv import load_dotenv
import pygame
import tempfile
import threading
import time

load_dotenv(override=True)

class VoiceEngine:
    def __init__(self):
        self.stop_listening = None
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or "your_actual_key_here" in api_key:
            print("WARNING: OpenAI API Key not detected or still using placeholder.")
        else:
            print("OpenAI API Key detected.")
            
        self.client = OpenAI(api_key=api_key)
        self.user_name = os.getenv("USER_NAME", "Sir")
        self.voice = "onyx"  # Options: alloy, echo, fable, onyx, nova, shimmer
        self.total_chars = 0
        self.total_cost = 0.0
        self.debug_mode = os.getenv("DEBUG_MODE", "False") == "True"

        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 400
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        
        # Initialize pygame mixer
        try:
            pygame.mixer.quit() # Reset if needed
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception as e:
            print(f"Mixer Init Error: {e}")
            pygame.mixer.init()

        # Load UI sounds
        self.ui_sounds = {}
        sound_files = ["wake", "think", "listen"]
        for s in sound_files:
            path = f"assets/{s}.wav"
            if os.path.exists(path):
                self.ui_sounds[s] = pygame.mixer.Sound(path)

    def log_debug(self, msg):
        if self.debug_mode:
            print(f" [DEBUG] [VOICE]: {msg}")

    def set_persona(self, persona):
        # Map personas to specific OpenAI voices
        voices = {
            "mavrick": "onyx",
            "jarvis": "fable",
            "friday": "shimmer"
        }
        self.voice = voices.get(persona.lower(), "onyx")
        self.log_debug(f"Voice persona shifted to: {persona} (OpenAI: {self.voice})")
        return f"Personality matrix updated to {persona.upper()}."

    def play_ui_sound(self, name):
        if name in self.ui_sounds:
            self.ui_sounds[name].play()

    def speak(self, text):
        print(f"Mavrick: {text}")
        self.total_chars += len(text)
        # OpenAI TTS costs $0.015 per 1,000 characters
        self.total_cost += (len(text) / 1000) * 0.015
        try:
            # Generate speech using OpenAI TTS
            response = self.client.audio.speech.create(
                model="tts-1",
                voice=self.voice,
                input=text
            )
            
            # Save to temp file and play
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                temp_path = f.name
            
            response.write_to_file(temp_path)
            
            # Validate file
            file_size = os.path.getsize(temp_path)
            if file_size < 100:
                raise Exception(f"Generated audio file is too small or empty ({file_size} bytes).")
                
            print(f"Audio file generated ({file_size} bytes): {temp_path}")
            
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.set_volume(1.0)
            print("Playing audio...")
            pygame.mixer.music.play()
            
            # Wait for playback to finish
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            
            # Cleanup
            pygame.mixer.music.unload()
            os.remove(temp_path)
            
        except Exception as e:
            print(f"TTS Error: {repr(e)}")
            # Fallback to local TTS if needed or just print
            print(f"Mavrick (Text Only): {text}")

    def listen(self):
        with sr.Microphone() as source:
            print("Listening for command...")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
            except sr.WaitTimeoutError:
                return "None"

        try:
            print("Recognizing command...")
            query = self.recognizer.recognize_google(audio, language='en-in')
            print(f"User said: {query}\n")
            return query
        except Exception:
            return "None"

    def start_background_listening(self, callback_func, check_active_func):
        self.is_listening = True
        self.bg_callback = callback_func
        self.check_active = check_active_func
        self.bg_thread = threading.Thread(target=self._background_loop, daemon=True)
        self.bg_thread.start()
        print("Manual background listener thread started.")

    def _background_loop(self):
        bg_recognizer = sr.Recognizer()
        bg_recognizer.energy_threshold = 150
        bg_recognizer.dynamic_energy_threshold = False
        
        self.log_debug("Background awareness loop initiated.")
        iteration = 0
        
        while self.is_listening:
            iteration += 1
            is_active = self.check_active()
            
            if iteration % 20 == 0:
                self.log_debug(f"Awareness Beat {iteration}. Assistant active: {is_active}")
                
            if is_active:
                time.sleep(1.0) 
                continue
                
            try:
                with sr.Microphone() as source:
                    if bg_recognizer.energy_threshold == 150:
                         self.log_debug("Calibrating ambient noise floor...")
                         bg_recognizer.adjust_for_ambient_noise(source, duration=0.8)
                         self.log_debug(f"Noise floor set. Energy threshold: {bg_recognizer.energy_threshold:.2f}")
                    
                    try:
                        # self.log_debug("Datalink open. Monitoring frequencies...")
                        audio = bg_recognizer.listen(source, timeout=1, phrase_time_limit=2)
                        
                        if self.check_active(): continue
                        
                        text = bg_recognizer.recognize_google(audio, language='en-in').lower()
                        self.log_debug(f"Heard (Low Confidence): '{text}'")
                        
                        wake_words = ["computer", "hey computer", "mavrick", "maverick"]
                        if any(word in text for word in wake_words):
                            self.log_debug(f"MATCH DETECTED: '{text}'. Triggering wake protocol.")
                            self.bg_callback()
                            time.sleep(2.0)
                            
                    except sr.WaitTimeoutError:
                        continue
                    except sr.UnknownValueError:
                        continue
                    except Exception as e:
                        self.log_debug(f"Recognition anomaly: {type(e).__name__}")
            except Exception as e:
                self.log_debug(f"Microphone link lost: {type(e).__name__}. Retrying in 2.0s.")
                time.sleep(2.0) 

    def stop_background_listening(self):
        self.is_listening = False
        print("Background listener stopping...")

if __name__ == "__main__":
    v = VoiceEngine()
    v.speak("Systems are online and ready, Sir. This is the new neural voice engine.")
