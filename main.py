import threading
import sys
import os
import time
import socket
from tkinter import messagebox
from dotenv import load_dotenv

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engine.brain import MavrickBrain
from engine.voice import VoiceEngine
from gui.app import MavrickUI

class MavrickAssistant:
    def __init__(self):
        # Single Instance Lock
        self._lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Try to bind to a specific local port
            self._lock_socket.bind(('127.0.0.1', 47200))
        except socket.error:
            # If the port is already in use, an instance is already running
            print("Mavrick is already running. Exiting...")
            messagebox.showwarning("Mavrick HUD", "An instance of Mavrick is already active.")
            sys.exit(0)

        load_dotenv(override=True)
        self.brain = MavrickBrain()
        self.voice = VoiceEngine()
        self.ui = MavrickUI()
        
        # Override UI commands
        self.ui.btn_listen.configure(command=self.start_voice_thread)
        self.ui.on_engage = self.start_voice_thread
        self.is_running = False
        self.continuous_mode = False
        self.should_stop_listening = False
        self.debug_mode = os.getenv("DEBUG_MODE", "False") == "True"
        
        # Start background listener
        self.voice.start_background_listening(self.on_wake_word, lambda: self.is_running)
        self.log_debug("Background awareness activated.")
        self.ui.status_label.configure(text="NETWORK STATUS: STANDBY (AWARE)", text_color=self.ui.secondary_teal)

    def log_debug(self, msg):
        if self.debug_mode:
            print(f" [DEBUG] [MAIN]: {msg}")

    def on_wake_word(self):
        self.log_debug(f"on_wake_word triggered. Current State - is_running: {self.is_running}")
        if not self.is_running:
            self.continuous_mode = True
            self.should_stop_listening = False
            self.is_running = True # Lock immediately
            self.log_debug("Wake word confirmed. Initializing response sequence.")
            
            # UI Feedback
            self.ui.status_label.configure(text="NETWORK STATUS: AWARE", text_color="#00ff00")
            self.ui.log_message("> Mavrick: Wake word detected.")
            self.voice.play_ui_sound("wake")
            
            # Vocal Confirmation
            self.voice.speak("Yes, Sir?")
            
            # Transition to processing the actual command
            print("[DEBUG] Starting process_command thread from wake word")
            thread = threading.Thread(target=self.process_command, daemon=True, args=(True,))
            thread.start()

    def start_voice_thread(self):
        if not self.is_running:
            self.continuous_mode = True
            self.should_stop_listening = False
            thread = threading.Thread(target=self.process_command, daemon=True, args=(False,))
            thread.start()

    def process_command(self, was_woken=False):
        try:
            self.is_running = True
            if not was_woken:
                self.ui.status_label.configure(text="NETWORK STATUS: LISTENING", text_color=self.ui.alert_orange)
                self.ui.log_message("> Mavrick: Listening for command...")
                self.voice.play_ui_sound("listen")
            else:
                self.log_debug("Responsive listening active (Woken).")
                self.ui.log_message("> Mavrick: I'm listening...")
            
            # Listen
            query = self.voice.listen()
            self.log_debug(f"Raw query captured: '{query}'")
            
            if query != "None" and query != "":
                # Check for termination phrases
                termination_phrases = ["stop listening", "go to sleep", "terminate session", "thank you mavrick", "that's all"]
                if any(phrase in query.lower() for phrase in termination_phrases):
                    self.log_debug(f"Termination phrase detected in: '{query}'")
                    self.ui.log_message(f"> User: {query}")
                    self.voice.speak("Understood. Returning to standby.")
                    self.continuous_mode = False
                    self.should_stop_listening = True
                    return

                self.ui.status_label.configure(text="NETWORK STATUS: THINKING", text_color="#fdfd96")
                self.ui.log_message(f"> User: {query}")
                self.log_debug("Sending query to Neural Engine (Brain)...")
                
                # UI Sound
                self.voice.play_ui_sound("think")
                
                # Brain response
                response = self.brain.get_response(query)
                self.log_debug(f"Brain reasoning complete. Response length: {len(response)}")
                
                # Intercept Special Markers
                if "SWITCHING_PERSONA_TO_" in response:
                    new_persona = response.replace("SWITCHING_PERSONA_TO_", "").strip().lower()
                    self.log_debug(f"Persona shift requested: {new_persona}")
                    self.voice.set_persona(new_persona)
                    # Clean up response text for user
                    response = f"Personality matrix successfully shifted to {new_persona.upper()}."
                    self.ui.log_message(f"> SYSTEM: Persona switched to {new_persona.upper()}")
                
                self.ui.log_box.insert("end", f"\n> Mavrick: {response}")
                self.ui.log_box.see("end")
                self.ui.status_label.configure(text="NETWORK STATUS: SPEAKING", text_color="#00ff00")
                
                # Speak
                self.voice.speak(response)
                
                # Update HUD Stats
                self.ui.update_stats(self.brain.session_cost, self.brain.total_tokens, self.brain.current_balance)
            else:
                self.log_debug("No audible input or confidence too low.")
                self.ui.status_label.configure(text="NETWORK STATUS: STANDBY", text_color=self.ui.primary_cyan)
                self.ui.log_message("> No input detected.")
        except Exception as e:
            self.log_debug(f"CRITICAL ERROR in process_command: {e}")
            if "context_length_exceeded" in str(e).lower() or "BadRequestError" in str(type(e).__name__):
                self.log_debug("Context link corrupted. Performing emergency memory flush...")
                self.ui.log_message("> SYSTEM: Context corrupted. Rebooting memory...")
                self.ui.status_label.configure(text="REBOOTING CONTEXT", text_color="#ff4b2b")
                self.brain.memory = [self.brain.memory[0]] # Hard reset to system prompt
                time.sleep(1.0)
            else:
                self.ui.log_message(f"> SYSTEM ERROR: {str(e)[:50]}")
        finally:
            self.log_debug("Finalizing command lifecycle. Resetting state.")
            self.is_running = False
            
            # If in continuous mode and we haven't been told to stop, loop back
            if self.continuous_mode and not self.should_stop_listening:
                self.log_debug("Continuous loop: Re-engaging listener.")
                time.sleep(0.5) # Short breathing room
                self.start_voice_thread()
            else:
                self.log_debug("Exiting continuous mode. Returning to Standby (Aware).")
                self.ui.status_label.configure(text="NETWORK STATUS: STANDBY (AWARE)", text_color=self.ui.secondary_teal)

    def boot_sequence(self):
        # Thematic startup logs and voice
        time.sleep(1.0)
        
        msg1 = "INITIALIZING NEURAL INTERFACE..."
        self.ui.log_message(msg1)
        self.voice.speak(msg1)
        
        msg2 = "LINK ESTABLISHED."
        self.ui.log_message(msg2)
        self.voice.speak(msg2)
        
        # Initial status update
        self.ui.update_stats(0, 0, self.brain.current_balance)
        self.voice.speak(f"Systems initialization complete... Welcome back, {self.brain.user_name}.")
        
        # Auto-engage continuous listening on boot
        print("Auto-engaging continuous listening mode...")
        self.start_voice_thread()

    def run(self):
        # Start boot sequence in a thread so it doesn't block UI start
        threading.Thread(target=self.boot_sequence, daemon=True).start()
        self.ui.mainloop()

if __name__ == "__main__":
    assistant = MavrickAssistant()
    assistant.run()
