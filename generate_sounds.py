import wave
import struct
import math
import os

def generate_beep(filename, freq=1000, duration=0.1, volume=0.5):
    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    
    with wave.open(filename, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        
        for i in range(num_samples):
            # Sine wave with simple envelope to avoid clicking
            envelope = 1.0
            if i < 100: envelope = i / 100
            elif i > num_samples - 100: envelope = (num_samples - i) / 100
            
            value = int(volume * envelope * 32767.0 * math.sin(2.0 * math.pi * freq * i / sample_rate))
            data = struct.pack('<h', value)
            f.writeframesraw(data)

if __name__ == "__main__":
    if not os.path.exists("assets"):
        os.makedirs("assets")
        
    # Tone 1: Wake (High blip)
    generate_beep("assets/wake.wav", freq=1200, duration=0.1)
    # Tone 2: Thinking (Low double blip)
    generate_beep("assets/think.wav", freq=800, duration=0.08)
    # Tone 3: Listen (Mid ping)
    generate_beep("assets/listen.wav", freq=1000, duration=0.15)
    print("UI sounds generated in assets/")
