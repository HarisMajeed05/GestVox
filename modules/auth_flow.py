import os
import tempfile
import speech_recognition as sr
from modules import voice_auth
from modules.user_session import user_session
from modules.tts_engine import tts_engine
import config

ENROLL_PHRASE_PROMPT = (
    "I don't recognize your voice. Say 'my name is' followed by your name "
    "to create a profile, or just speak normally to try again."
)


def _record_sample(recognizer, mic, seconds=4):
    with mic as source:
        audio = recognizer.record(source, duration=seconds)
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    with open(path, "wb") as f:
        f.write(audio.get_wav_data())
    return path, audio


def run_login_flow():
    # Blocks briefly at startup to identify or enroll the speaker.
    # Falls back to no login (shared/default memory) if it can't get a sample.
    recognizer = sr.Recognizer()
    mic = sr.Microphone(device_index=config.MIC_DEVICE_INDEX)

    tts_engine.speak("Please say a short phrase so I can recognize your voice.")
    try:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
        wav_path, audio = _record_sample(recognizer, mic, seconds=4)
    except OSError:
        print("No mic available for login, continuing without a user profile.")
        return

    username, score = voice_auth.identify_user(wav_path)
    if username:
        user_session.login(username)
        tts_engine.speak(f"Welcome back, {username}.")
        os.remove(wav_path)
        return

    # Unknown voice, try to enroll via spoken name
    tts_engine.speak(ENROLL_PHRASE_PROMPT)
    try:
        text = recognizer.recognize_google(audio).lower()
    except (sr.UnknownValueError, sr.RequestError):
        text = ""

    if "my name is" in text:
        name = text.split("my name is", 1)[1].strip().split(" ")[0]
        if name:
            voice_auth.enroll_user(name, wav_path)
            user_session.login(name)
            tts_engine.speak(f"Nice to meet you, {name}. I've created your profile.")
            os.remove(wav_path)
            return

    tts_engine.speak("Continuing without a saved profile for now.")
    os.remove(wav_path)


def enroll_new_user(username):
    # Used for a voice command like "create profile for <name>" instead of startup flow
    recognizer = sr.Recognizer()
    mic = sr.Microphone(device_index=config.MIC_DEVICE_INDEX)
    tts_engine.speak(f"Okay {username}, say a short phrase to register your voice.")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
        audio = recognizer.record(source, duration=4)
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    with open(path, "wb") as f:
        f.write(audio.get_wav_data())
    voice_auth.enroll_user(username, path)
    user_session.login(username)
    os.remove(path)
    return f"Profile created for {username}."