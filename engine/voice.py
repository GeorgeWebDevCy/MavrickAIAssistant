import os
import speech_recognition as sr
from openai import OpenAI
from dotenv import load_dotenv
import pygame
import tempfile
import threading
import time
import json
import sys

try:
    import pyttsx3
except Exception:
    pyttsx3 = None

try:
    import vosk
except Exception:
    vosk = None

load_dotenv(override=True)

class VoiceEngine:
    def __init__(self, user_name=None, voice=None, persona=None, wake_words=None):
        self.stop_listening = None
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or "your_actual_key_here" in api_key:
            print("WARNING: OpenAI API Key not detected or still using placeholder.")
        else:
            print("OpenAI API Key detected.")
            
        self.client = OpenAI(api_key=api_key)
        self.user_name = user_name or os.getenv("USER_NAME", "Sir")
        self.persona = (persona or "mavrick").lower()
        self.voice = voice or self._voice_for_persona(self.persona)
        self.total_chars = 0
        self.total_cost = 0.0
        self.debug_mode = os.getenv("DEBUG_MODE", "False") == "True"
        self.muted = False
        self.wake_words = self._normalize_wake_words(wake_words)
        self.offline_tts = os.getenv("OFFLINE_TTS", "False").lower() == "true"
        self.offline_stt = os.getenv("OFFLINE_STT", "False").lower() == "true"
        self._tts_engine = None
        self._vosk_model = None
        self._vosk_model_path = self._resolve_vosk_path()
        if self._vosk_model_path:
            self.offline_stt = True

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

    def _asset_base_dir(self):
        return getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

    def _resolve_vosk_path(self):
        env_path = os.getenv("VOSK_MODEL_PATH", "").strip()
        if env_path and os.path.isdir(env_path):
            return env_path
        candidate = os.path.join(self._asset_base_dir(), "data", "vosk")
        if os.path.isdir(candidate):
            return candidate
        return ""

    def _ensure_vosk_model(self):
        if self._vosk_model or not self._vosk_model_path or not vosk:
            return self._vosk_model is not None
        try:
            self._vosk_model = vosk.Model(self._vosk_model_path)
            return True
        except Exception as exc:
            self.log_debug(f"Vosk model load failed: {exc}")
            self._vosk_model = None
            return False

    def _voice_for_persona(self, persona):
        voices = {
            "mavrick": "onyx",
            "jarvis": "fable",
            "friday": "shimmer"
        }
        return voices.get(persona.lower(), "onyx")

    def _normalize_wake_words(self, wake_words):
        default_words = ["computer", "hey computer", "mavrick", "maverick"]
        if not isinstance(wake_words, list):
            return default_words
        cleaned = [str(word).strip().lower() for word in wake_words if str(word).strip()]
        return cleaned if cleaned else default_words

    def set_persona(self, persona):
        # Map personas to specific OpenAI voices
        self.persona = persona.lower()
        self.voice = self._voice_for_persona(self.persona)
        self.log_debug(f"Voice persona shifted to: {persona} (OpenAI: {self.voice})")
        return f"Personality matrix updated to {persona.upper()}."

    def set_voice(self, voice):
        voice = str(voice).strip().lower()
        if not voice:
            self.voice = self._voice_for_persona(self.persona)
        else:
            self.voice = voice
        self.log_debug(f"Voice override set to: {self.voice}")
        return self.voice

    def set_wake_words(self, wake_words):
        self.wake_words = self._normalize_wake_words(wake_words)
        self.log_debug(f"Wake words updated: {self.wake_words}")
        return self.wake_words

    def set_muted(self, muted):
        self.muted = bool(muted)
        state = "MUTED" if self.muted else "UNMUTED"
        self.log_debug(f"Voice output {state}.")
        return self.muted

    def toggle_mute(self):
        return self.set_muted(not self.muted)

    def play_ui_sound(self, name):
        if self.muted:
            return
        if name in self.ui_sounds:
            self.ui_sounds[name].play()

    def _ensure_tts_engine(self):
        if self._tts_engine or not pyttsx3:
            return self._tts_engine is not None
        try:
            self._tts_engine = pyttsx3.init()
            self._tts_engine.setProperty("rate", 180)
            return True
        except Exception as exc:
            self.log_debug(f"pyttsx3 init failed: {exc}")
            self._tts_engine = None
            return False

    def _speak_offline(self, text):
        if not self._ensure_tts_engine():
            return False
        try:
            self._tts_engine.say(text)
            self._tts_engine.runAndWait()
            return True
        except Exception as exc:
            self.log_debug(f"Offline TTS failed: {exc}")
            return False

    def speak(self, text):
        print(f"Mavrick: {text}")
        if self.muted:
            return
        self.total_chars += len(text)
        # OpenAI TTS costs $0.015 per 1,000 characters
        self.total_cost += (len(text) / 1000) * 0.015
        if self.offline_tts:
            if self._speak_offline(text):
                return
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
            if not self._speak_offline(text):
                print(f"Mavrick (Text Only): {text}")

    def _recognize_audio(self, recognizer, audio):
        if self.offline_stt and self._ensure_vosk_model():
            try:
                if hasattr(recognizer, "recognize_vosk"):
                    result = recognizer.recognize_vosk(audio, model=self._vosk_model)
                else:
                    result = recognizer.recognize_google(audio, language="en-in")
                if isinstance(result, str) and result.strip().startswith("{"):
                    data = json.loads(result)
                    return data.get("text", "").strip()
                if isinstance(result, dict):
                    return str(result.get("text", "")).strip()
                return str(result).strip()
            except Exception as exc:
                self.log_debug(f"Offline STT failed: {exc}")
        try:
            return recognizer.recognize_google(audio, language="en-in")
        except Exception:
            return "None"

    def listen(self):
        with sr.Microphone() as source:
            print("Listening for command...")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
            except sr.WaitTimeoutError:
                return "None"

        print("Recognizing command...")
        query = self._recognize_audio(self.recognizer, audio)
        print(f"User said: {query}\n")
        return query

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
                        
                        text = self._recognize_audio(bg_recognizer, audio).lower()
                        self.log_debug(f"Heard (Low Confidence): '{text}'")
                        
                        if any(word in text for word in self.wake_words):
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
