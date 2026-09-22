import os
import re
import tempfile
import speech_recognition as sr
from modules import voice_auth
from modules.user_session import user_session
from modules.tts_engine import tts_engine
from modules.stt_engine import stt_engine
import config


def _record_sample(recognizer, mic, seconds=4):
    with mic as source:
        audio = recognizer.record(source, duration=seconds)
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    with open(path, "wb") as f:
        f.write(audio.get_wav_data())
    return path, audio


def _extract_name(text):
    match = re.search(r"(?:name is|i am|i'm|call me)\s+([a-z]+)", text.lower())
    return match.group(1) if match else None


def _cleanup(paths):
    for p in paths:
        if p and os.path.exists(p):
            os.remove(p)


def _enroll(recognizer, mic, username, first_sample=None):
    # Collects two samples (reusing one if given) and saves the averaged profile
    samples = [first_sample] if first_sample else []
    while len(samples) < 2:
        tts_engine.speak("Say another short sentence to train your voice.")
        path, _ = _record_sample(recognizer, mic, seconds=4)
        samples.append(path)
    voice_auth.enroll_user(username, samples)
    _cleanup(samples)


def run_login_flow():
    # Identifies the speaker at startup, or enrolls them if the voice is new.
    # Falls back to no login (shared memory) if it can't get a usable sample.
    recognizer = sr.Recognizer()
    mic = sr.Microphone(device_index=config.MIC_DEVICE_INDEX)

    print("[Auth] Starting voice login flow...")
    try:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
        tts_engine.speak("Please say a short sentence so I can recognize your voice.")
        wav_path, _ = _record_sample(recognizer, mic, seconds=4)
        print("[Auth] Recorded voice sample.")
    except OSError as e:
        print(f"[Auth] No mic available for login ({e}), continuing without a profile.")
        return

    username, score = voice_auth.identify_user(wav_path)
    print(f"[Auth] Best match: {username}, similarity: {score:.2f}")
    if username:
        voice_auth.update_profile(username, wav_path)
        user_session.login(username)
        tts_engine.speak(f"Welcome back, {username}.")
        _cleanup([wav_path])
        return

    # Unknown voice: ask for a name with a fresh recording
    print("[Auth] No known voice matched. Asking for a name.")
    tts_engine.speak("I don't recognize your voice. Please say, my name is, and then your name.")
    name_path, name_audio = _record_sample(recognizer, mic, seconds=5)
    text = stt_engine.transcribe(name_audio)
    print(f"[Auth] Heard for enrollment: \"{text}\"")
    name = _extract_name(text)

    if not name:
        print("[Auth] Could not extract a name. Continuing without a profile.")
        tts_engine.speak("I didn't catch a name. Continuing without a saved profile.")
        _cleanup([wav_path, name_path])
        return

    _enroll(recognizer, mic, name, first_sample=wav_path)
    _cleanup([name_path])
    user_session.login(name)
    print(f"[Auth] Enrolled new user: {name}")
    tts_engine.speak(f"Nice to meet you, {name}. Your profile is ready.")


def enroll_new_user(username):
    # Used for a voice command like "create profile for <name>"
    recognizer = sr.Recognizer()
    mic = sr.Microphone(device_index=config.MIC_DEVICE_INDEX)
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
    _enroll(recognizer, mic, username)
    user_session.login(username)
    print(f"[Auth] Enrolled new user via command: {username}")
    return f"Profile created for {username}."