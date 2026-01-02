print("Testing threading...")
import threading
print("Testing sys...")
import sys
print("Testing os...")
import os
print("Testing dotenv...")
from dotenv import load_dotenv
load_dotenv()
print("Testing engine.brain...")
from engine.brain import MavrickBrain
print("Testing engine.voice...")
from engine.voice import VoiceEngine
print("Testing gui.app...")
from gui.app import MavrickUI
print("All imports successful.")
