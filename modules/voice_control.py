import re
import speech_recognition as sr
import threading
import time
import config
from modules.mode_manager import mode_manager
from modules.ai_brain import ai_brain
from modules.tts_engine import tts_engine
from modules.stt_engine import stt_engine
from modules import command_router


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
        self._recognizer.non_speaking_duration = min(0.3, config.MIC_PAUSE_THRESHOLD)
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

    def _say(self, text):
        # Blocking speech so the mic doesn't record the assistant's own voice
        tts_engine.speak(text)

    def _listen_once(self, timeout=None, phrase_time_limit=12):
        try:
            with self._mic as source:
                audio = self._recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_time_limit
                )
        except sr.WaitTimeoutError:
            return ""
        except OSError as e:
            print(f"[Voice] Mic read error: {e}")
            time.sleep(1)  # transient device error, back off and retry next loop
            return ""

        start = time.time()
        text = stt_engine.transcribe(audio)
        if text:
            print(f"[Voice] Heard: \"{text}\" ({time.time() - start:.2f}s)")
        return text

    def _run(self):
        print("[Voice] Listening thread started.")
        while self._running:
            raw = self._listen_once(timeout=5)
            if not raw:
                continue
            text = command_router.normalize(raw)

            # Mode switch phrases work regardless of wake word or active mode
            if _contains_phrase(text, config.SWITCH_TO_GESTURE_PHRASES):
                print("[Voice] Matched: switch to gesture mode.")
                mode_manager.set_mode("GESTURE")
                self._say("Switched to gesture mode.")
                continue
            if _contains_phrase(text, config.SWITCH_TO_VOICE_PHRASES):
                print("[Voice] Matched: switch to voice mode.")
                mode_manager.set_mode("VOICE")
                self._say("Switched to voice mode.")
                continue

            if mode_manager.get_mode() != "VOICE":
                print("[Voice] Ignored (not in voice mode).")
                continue

            if not self._session_active:
                wake = next((w for w in config.WAKE_WORDS if w in text), None)
                if not wake:
                    print("[Voice] No wake word, ignoring.")
                    continue
                self._session_active = True
                print("[Voice] Session started.")
                # Allows "hey vox open brave" in a single sentence
                remainder = text.split(wake, 1)[1].strip()
                if remainder:
                    self._handle_command(remainder)
                else:
                    self._say("Yes?")
                continue

            if _contains_phrase(text, config.END_SESSION_PHRASES):
                self._session_active = False
                print("[Voice] Session ended.")
                self._say("Goodbye.")
                continue

            self._handle_command(text)

    def _handle_command(self, command):
        print(f"[Voice] Command: \"{command}\"")
        fast_result = command_router.try_handle(command)
        if fast_result is not None:
            print(f"[Voice] Handled locally: {fast_result}")
            ai_brain.record_exchange(command, fast_result)
            self._say(fast_result)
            return

        start = time.time()
        reply = ai_brain.ask(command)
        print(f"[Voice] AI reply ({time.time() - start:.2f}s): {reply}")
        self._say(reply)