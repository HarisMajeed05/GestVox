import re
import queue
import threading
import pyttsx3
import config


def _clean_for_speech(text):
    # Removes markdown and symbols that sound wrong when read aloud
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_#`>|~]", " ", text)
    text = re.sub(r"https?://\S+", "a link", text)
    return re.sub(r"\s+", " ", text).strip()


class TTSEngine:
    # pyttsx3 (SAPI5) is not thread-safe and hangs when runAndWait is called
    # from different threads, so one worker thread owns the engine and all
    # speech requests go through a queue.
    def __init__(self):
        self._queue = queue.Queue()
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=10)

    def _worker(self):
        try:
            import comtypes
            comtypes.CoInitialize()
        except Exception:
            pass
        engine = pyttsx3.init()
        engine.setProperty("rate", config.TTS_RATE)
        engine.setProperty("volume", config.TTS_VOLUME)
        self._ready.set()

        while True:
            text, done = self._queue.get()
            try:
                engine.say(text)
                engine.runAndWait()
            except Exception as e:
                print(f"[TTS] Speech failed: {e}")
            finally:
                done.set()

    def speak(self, text):
        # Blocks until the text has been spoken
        text = _clean_for_speech(text or "")
        if not text:
            return
        done = threading.Event()
        self._queue.put((text, done))
        done.wait(timeout=60)

    def speak_async(self, text):
        text = _clean_for_speech(text or "")
        if text:
            self._queue.put((text, threading.Event()))


tts_engine = TTSEngine()