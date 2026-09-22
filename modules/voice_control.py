import speech_recognition as sr
import threading
import time
import config
from modules.mode_manager import mode_manager
from modules.ai_brain import ai_brain
from modules.tts_engine import tts_engine


class VoiceControl:
    def __init__(self, toggle_callback=None):
        self._toggle_callback = toggle_callback
        self._running = False
        self._thread = None
        self._recognizer = sr.Recognizer()
        self._recognizer.energy_threshold = config.MIC_ENERGY_THRESHOLD
        self._recognizer.pause_threshold = config.MIC_PAUSE_THRESHOLD
        self._mic = sr.Microphone(device_index=config.MIC_DEVICE_INDEX)
        self._awake = False

        try:
            with self._mic as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=1)
        except OSError as e:
            print(f"Microphone init failed: {e}. Run list_mics.py and set "
                  f"MIC_DEVICE_INDEX in config.py.")

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _listen_once(self, timeout=None, phrase_time_limit=8):
        try:
            with self._mic as source:
                audio = self._recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_time_limit
                )
        except sr.WaitTimeoutError:
            return ""
        except OSError:
            time.sleep(1)  # transient device error, back off and retry next loop
            return ""
        try:
            return self._recognizer.recognize_google(audio).lower()
        except (sr.UnknownValueError, sr.RequestError):
            return ""

    def _run(self):
        while self._running:
            text = self._listen_once(timeout=3)
            if not text:
                continue

            # Mode switch phrases work regardless of wake word or active mode
            if any(p in text for p in config.SWITCH_TO_GESTURE_PHRASES):
                mode_manager.set_mode("GESTURE")
                tts_engine.speak_async("Switched to gesture mode.")
                continue
            if any(p in text for p in config.SWITCH_TO_VOICE_PHRASES):
                mode_manager.set_mode("VOICE")
                tts_engine.speak_async("Switched to voice mode.")
                continue

            if mode_manager.get_mode() != "VOICE":
                continue

            if any(w in text for w in config.WAKE_WORDS):
                tts_engine.speak_async("Yes?")
                command = self._listen_once(timeout=5, phrase_time_limit=12)
                if command:
                    self._handle_command(command)

    def _handle_command(self, command):
        if "exit" in command or "quit" in command or "close" in command:
            tts_engine.speak_async("Okay, goodbye.")
            return
        # Anything not a recognized system command goes to the AI brain
        reply = ai_brain.ask(command)
        tts_engine.speak_async(reply)