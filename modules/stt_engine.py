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
        return self._prompt

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
        model = config.STT_MODEL_ACCURATE if accurate else config.STT_MODEL_FAST
        try:
            result = self._client.audio.transcriptions.create(
                file=("audio.wav", wav_bytes),
                model=model,
                response_format="verbose_json",
                language="en",
                temperature=0.0,
                prompt=self._get_prompt(),
            )
        except Exception as e:
            print(f"[STT] Transcription failed: {e}")
            return ""

        data = result.model_dump() if hasattr(result, "model_dump") else dict(result)
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

        text = text.strip().lower()
        check = re.sub(r"[^\w\s]", "", text).strip()
        if check in HALLUCINATIONS:
            return ""
        return text


stt_engine = SttEngine()