import pyttsx3
import threading
import config


class TTSEngine:
    def __init__(self):
        self._lock = threading.Lock()
        self._engine = pyttsx3.init()
        self._engine.setProperty("rate", config.TTS_RATE)
        self._engine.setProperty("volume", config.TTS_VOLUME)

    def speak(self, text):
        # Runs in a lock so overlapping speak calls don't crash the engine
        with self._lock:
            self._engine.say(text)
            self._engine.runAndWait()

    def speak_async(self, text):
        threading.Thread(target=self.speak, args=(text,), daemon=True).start()


tts_engine = TTSEngine()
