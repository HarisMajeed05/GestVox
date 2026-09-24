import os
import re
import queue
import tempfile
import threading
import config

# Latin, Urdu/Arabic and Gurmukhi letters are kept; everything else is noise
_KEEP = r"\w\s.,!?'\-\u0600-\u06FF\u0A00-\u0A7F"


def _clean_for_speech(text):
    # Removes markdown and symbols that sound wrong when read aloud
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"https?://\S+", "a link", text)
    text = re.sub(rf"[^{_KEEP}]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class TTSEngine:
    # One worker thread owns the audio engines. pyttsx3 (SAPI5) is not
    # thread-safe, and a single owner also makes interrupting simple.
    def __init__(self):
        self._queue = queue.Queue()
        self._ready = threading.Event()
        self._speaking = threading.Event()
        self._stop_flag = threading.Event()
        self._pyttsx = None
        self._mixer = None
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=15)

    # ---------------- worker ----------------

    def _worker(self):
        try:
            import comtypes
            comtypes.CoInitialize()
        except Exception:
            pass
        self._init_pyttsx()
        if config.TTS_BACKEND == "edge":
            self._init_mixer()
        self._ready.set()

        while True:
            text, lang, done = self._queue.get()
            self._speaking.set()
            try:
                if self._stop_flag.is_set():
                    continue
                self._render(text, lang)
            except Exception as e:
                print(f"[TTS] Speech failed: {e}")
            finally:
                done.set()
                if self._queue.empty():
                    self._speaking.clear()
                    self._stop_flag.clear()

    def _init_pyttsx(self):
        try:
            import pyttsx3
            self._pyttsx = pyttsx3.init()
            self._pyttsx.setProperty("rate", config.TTS_RATE)
            self._pyttsx.setProperty("volume", config.TTS_VOLUME)
        except Exception as e:
            print(f"[TTS] pyttsx3 unavailable: {e}")

    def _init_mixer(self):
        try:
            import pygame
            pygame.mixer.init()
            self._mixer = pygame.mixer
        except Exception as e:
            print(f"[TTS] Audio playback unavailable, using offline voice: {e}")
            self._mixer = None

    def _render(self, text, lang):
        if config.TTS_BACKEND == "edge" and self._mixer:
            if self._speak_edge(text, lang):
                return
        self._speak_pyttsx(text)

    def _speak_edge(self, text, lang):
        # Neural voices, one per language. Punjabi has no voice of its own,
        # so it falls back to the Urdu voice.
        import asyncio
        import edge_tts

        voice = config.TTS_VOICES.get(lang) or config.TTS_VOICES["en"]
        path = os.path.join(tempfile.gettempdir(), f"gestvox_tts_{threading.get_ident()}.mp3")
        try:
            async def generate():
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(path)

            asyncio.run(generate())
            self._mixer.music.load(path)
            self._mixer.music.play()
            while self._mixer.music.get_busy():
                if self._stop_flag.is_set():
                    self._mixer.music.stop()
                    break
                threading.Event().wait(0.05)
            self._mixer.music.unload()
            return True
        except Exception as e:
            print(f"[TTS] Neural voice failed, using offline voice: {e}")
            return False

    def _speak_pyttsx(self, text):
        if not self._pyttsx:
            return
        self._pyttsx.say(text)
        self._pyttsx.runAndWait()

    # ---------------- public ----------------

    def speak(self, text, lang="en"):
        # Blocks until the text has been spoken
        text = _clean_for_speech(text or "")
        if not text:
            return
        done = threading.Event()
        self._speaking.set()
        self._queue.put((text, lang, done))
        done.wait(timeout=60)

    def speak_async(self, text, lang="en"):
        text = _clean_for_speech(text or "")
        if text:
            self._speaking.set()
            self._queue.put((text, lang, threading.Event()))

    def is_speaking(self):
        return self._speaking.is_set()

    def stop_speaking(self):
        # Drops anything queued and cuts off the sentence being spoken
        self._stop_flag.set()
        while not self._queue.empty():
            try:
                _, _, done = self._queue.get_nowait()
                done.set()
            except queue.Empty:
                break
        try:
            if self._mixer:
                self._mixer.music.stop()
            if self._pyttsx:
                self._pyttsx.stop()
        except Exception:
            pass
        self._speaking.clear()


tts_engine = TTSEngine()