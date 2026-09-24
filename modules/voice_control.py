import re
import winsound
import speech_recognition as sr
import threading
import time
import config
from modules.mode_manager import mode_manager
from modules.ai_brain import ai_brain
from modules.tts_engine import tts_engine
from modules.stt_engine import stt_engine
from modules import command_router
from modules import system_control as sc

CONFIRM_WORDS = ["yes", "yeah", "yep", "confirm", "do it", "go ahead", "sure"]


def _contains_phrase(text, phrases):
    return any(re.search(rf"\b{re.escape(p)}\b", text) for p in phrases)


class VoiceControl:
    def __init__(self, toggle_callback=None):
        self._toggle_callback = toggle_callback
        self._running = False
        self._thread = None
        self._session_active = False  # True between wake word and "bye"

        self._recognizer = sr.Recognizer()
        self._recognizer.energy_threshold = config.MIC_ENERGY_THRESHOLD
        self._recognizer.dynamic_energy_threshold = True
        self._recognizer.pause_threshold = config.MIC_PAUSE_THRESHOLD
        self._recognizer.non_speaking_duration = min(0.25, config.MIC_PAUSE_THRESHOLD)
        self._mic = sr.Microphone(device_index=config.MIC_DEVICE_INDEX)

        try:
            with self._mic as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=1)
            print(f"[Voice] Mic initialized (device_index={config.MIC_DEVICE_INDEX}, "
                  f"energy_threshold={self._recognizer.energy_threshold:.0f}).")
        except OSError as e:
            print(f"[Voice] Microphone init failed: {e}. Run list_mics.py and set "
                  f"MIC_DEVICE_INDEX in config.py.")

        mode_manager.on_change(self._on_mode_change)

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

    def _on_mode_change(self, mode):
        if mode != "VOICE" and self._session_active:
            self._session_active = False
            print("[Voice] Session ended (left voice mode).")

    def _say(self, text, lang=None):
        # With barge-in on, speech runs in the background so listening can
        # continue and the user can interrupt mid-sentence
        lang = lang or stt_engine.last_language
        if config.BARGE_IN:
            tts_engine.speak_async(text, lang)
            return
        tts_engine.speak(text, lang)
        if self._session_active and config.LISTEN_BEEP:
            winsound.Beep(1000, 70)  # signals that listening has resumed

    def _listen_once(self, source, timeout=None, phrase_time_limit=12, accurate=False):
        # OSError is left to the caller, which reopens the mic stream
        try:
            audio = self._recognizer.listen(
                source, timeout=timeout, phrase_time_limit=phrase_time_limit
            )
        except sr.WaitTimeoutError:
            return ""

        start = time.time()
        text = stt_engine.transcribe(audio, accurate=accurate)
        if text:
            print(f"[Voice] Heard [{stt_engine.last_language}]: \"{text}\" "
                  f"({time.time() - start:.2f}s)")
        return text

    def _run(self):
        print("[Voice] Listening thread started.")
        # The mic stream stays open for the thread's lifetime. Reopening it on
        # every listen adds a delay, especially with Bluetooth headsets that
        # switch audio profiles each time the mic opens.
        while self._running:
            try:
                with self._mic as source:
                    while self._running:
                        self._process_once(source)
            except OSError as e:
                print(f"[Voice] Mic error, reopening: {e}")
                time.sleep(1)

    def _process_once(self, source):
        # The accurate model is used only during a session, where commands matter
        raw = self._listen_once(source, timeout=5, accurate=self._session_active)
        if not raw:
            return
        if tts_engine.is_speaking():
            print("[Voice] Interrupted.")
            tts_engine.stop_speaking()
        text = command_router.normalize(raw)
        self._route(text)

    def _route(self, text):
        # Mode switch phrases work regardless of wake word or active mode
        if _contains_phrase(text, config.SWITCH_TO_GESTURE_PHRASES):
            print("[Voice] Matched: switch to gesture mode.")
            mode_manager.set_mode("GESTURE")
            self._say("Switched to gesture mode.")
            return
        if _contains_phrase(text, config.SWITCH_TO_VOICE_PHRASES):
            print("[Voice] Matched: switch to voice mode.")
            mode_manager.set_mode("VOICE")
            self._say("Switched to voice mode.")
            return

        if mode_manager.get_mode() != "VOICE":
            print("[Voice] Ignored (not in voice mode).")
            return

        if not self._session_active:
            wake = next((w for w in config.WAKE_WORDS if _contains_phrase(text, [w])), None)
            if not wake:
                print("[Voice] No wake word, ignoring.")
                return
            self._session_active = True
            print("[Voice] Session started.")
            # Allows "hey vox open brave" in a single sentence
            remainder = text.split(wake, 1)[1].strip()
            if remainder:
                self._handle_command(remainder)
            else:
                self._say("Yes?")
            return

        if _contains_phrase(text, config.END_SESSION_PHRASES):
            self._session_active = False
            print("[Voice] Session ended.")
            self._say("Goodbye.")
            return

        self._handle_command(text)

    def _handle_command(self, command):
        print(f"[Voice] Command: \"{command}\"")
        if sc.has_pending_action():
            if _contains_phrase(command, CONFIRM_WORDS):
                result = sc.confirm_pending()
            else:
                result = sc.cancel_pending()
            print(f"[Voice] Confirmation result: {result}")
            ai_brain.record_exchange(command, result)
            self._say(result)
            return

        fast_result = command_router.try_handle(command)
        if fast_result is not None:
            print(f"[Voice] Handled locally: {fast_result}")
            ai_brain.record_exchange(command, fast_result)
            self._say(fast_result)
            return

        # Sentences are spoken as they are generated instead of waiting
        # for the whole reply
        start = time.time()
        first = [True]

        lang = stt_engine.last_language

        def on_sentence(sentence):
            if first[0]:
                print(f"[Voice] First speech after {time.time() - start:.2f}s")
                first[0] = False
            tts_engine.speak_async(sentence, lang)

        reply = ai_brain.ask(command, on_sentence=on_sentence)
        print(f"[Voice] AI reply ({time.time() - start:.2f}s): {reply}")