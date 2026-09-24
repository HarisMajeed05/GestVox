import re
import webrtcvad
from groq import Groq
import config

BASE_PROMPT = (
    "GestVox, hey vox. Open Brave, Chrome, Spotify, Discord, VS Code, "
    "YouTube, Notepad. Volume up, volume down, mute, screenshot, lock the PC, "
    "next song, switch to gesture mode, bye."
)

# Phrases Whisper commonly produces from silence or background noise
HALLUCINATIONS = {"", "you", "thank you", "thanks for watching", "bye bye", "so"}

VAD_RATE = 16000
VAD_FRAME_BYTES = int(VAD_RATE * 0.03) * 2  # 30ms of 16-bit mono audio


class SttEngine:
    def __init__(self):
        self._client = Groq(api_key=config.GROQ_API_KEY)
        self._vad = webrtcvad.Vad(config.VAD_AGGRESSIVENESS)
        self._prompt = None
        self._local_model = None
        self.last_language = "en"  # language of the most recent transcription

    def _get_local_model(self):
        # Loaded on first use; the model downloads once (~150MB for base.en)
        if self._local_model is None:
            from faster_whisper import WhisperModel
            print(f"[STT] Loading local model {config.STT_LOCAL_MODEL}...")
            self._local_model = WhisperModel(
                config.STT_LOCAL_MODEL, device="cpu", compute_type="int8",
            )
            print("[STT] Local model ready.")
        return self._local_model

    def _transcribe_local(self, wav_bytes):
        import io
        model = self._get_local_model()
        segments, info = model.transcribe(
            io.BytesIO(wav_bytes),
            language=self._language_arg(),
            beam_size=1,              # greedy decoding is much faster
            vad_filter=True,
            condition_on_previous_text=False,
            initial_prompt=self._get_prompt(),
        )
        text = " ".join(seg.text.strip() for seg in segments)
        self._set_language(getattr(info, "language", "en"))
        return text

    def _language_arg(self):
        # None lets Whisper detect the language per utterance, which is what
        # makes mixed Urdu-English speech work
        return None if config.MULTILINGUAL else "en"

    def _set_language(self, detected):
        code = (detected or "en").lower()[:2]
        self.last_language = code if code in config.LANGUAGES else "en"

    def _get_prompt(self):
        # Adds installed app names so Whisper spells them correctly.
        # Whisper prompts are limited to 224 tokens, so the list is capped.
        if self._prompt is None:
            names = []
            try:
                from modules import system_control
                names = [n for n in system_control.installed_app_names() if len(n) <= 20][:40]
            except Exception:
                pass
            apps = ", ".join(n.title() for n in names)
            self._prompt = (BASE_PROMPT + (f" Apps: {apps}." if apps else ""))[:800]
        # An English prompt biases language detection, so it is skipped
        # when more than one language is expected
        return None if config.MULTILINGUAL else self._prompt

    def _speech_ratio(self, raw):
        frames = [raw[i:i + VAD_FRAME_BYTES]
                  for i in range(0, len(raw) - VAD_FRAME_BYTES + 1, VAD_FRAME_BYTES)]
        if not frames:
            return 0.0
        voiced = sum(1 for f in frames if self._vad.is_speech(f, VAD_RATE))
        return voiced / len(frames)

    def transcribe(self, audio_data, accurate=False):
        # Skips audio that is mostly noise, which prevents hallucinated text
        # and saves API calls
        raw = audio_data.get_raw_data(convert_rate=VAD_RATE, convert_width=2)
        if self._speech_ratio(raw) < config.VAD_MIN_SPEECH_RATIO:
            return ""

        wav_bytes = audio_data.get_wav_data(convert_rate=VAD_RATE, convert_width=2)

        # Local transcription avoids a network round trip, which is the
        # biggest single delay in a spoken conversation
        if config.STT_BACKEND == "local":
            try:
                text = self._transcribe_local(wav_bytes)
            except Exception as e:
                print(f"[STT] Local transcription failed, using Groq: {e}")
            else:
                return self._clean(text)

        model = config.STT_MODEL_ACCURATE if accurate else config.STT_MODEL_FAST
        try:
            result = self._client.audio.transcriptions.create(
                file=("audio.wav", wav_bytes),
                model=model,
                response_format="verbose_json",
                language=self._language_arg(),
                temperature=0.0,
                prompt=self._get_prompt(),
            )
        except Exception as e:
            print(f"[STT] Transcription failed: {e}")
            return ""

        data = result.model_dump() if hasattr(result, "model_dump") else dict(result)
        self._set_language(data.get("language", "en"))
        segments = data.get("segments") or []
        if segments:
            # Drops segments Whisper itself marks as likely silence
            kept = [
                s.get("text", "") for s in segments
                if not (s.get("no_speech_prob", 0) > 0.6 and s.get("avg_logprob", 0) < -1.0)
            ]
            text = " ".join(t.strip() for t in kept)
        else:
            text = data.get("text", "")

        return self._clean(text)

    @staticmethod
    def _clean(text):
        text = (text or "").strip().lower()
        check = re.sub(r"[^\w\s]", "", text).strip()
        if check in HALLUCINATIONS:
            return ""
        return text


stt_engine = SttEngine()