"""
Records a few seconds of audio and prints what Whisper transcribes.
Run this directly to test STT quality in isolation from the rest of the app.
"""
import speech_recognition as sr
from modules.stt_engine import stt_engine
import config

recognizer = sr.Recognizer()
mic = sr.Microphone(device_index=config.MIC_DEVICE_INDEX)

print("Calibrating for ambient noise...")
with mic as source:
    recognizer.adjust_for_ambient_noise(source, duration=1)

print(f"Energy threshold: {recognizer.energy_threshold:.0f}")
print("Speak now (up to 6 seconds)...")

with mic as source:
    audio = recognizer.record(source, duration=6)

print("Transcribing...")
text = stt_engine.transcribe(audio)
print(f"Result: \"{text}\"")