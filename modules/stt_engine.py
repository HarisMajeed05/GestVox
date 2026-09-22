import re
from groq import Groq
import config

# Vocabulary hint so Whisper favors app names and command words it would
# otherwise misspell.
VOCAB_PROMPT = (
    "GestVox, hey vox. Open Brave, Chrome, Firefox, Edge, Spotify, Discord, "
    "VS Code, YouTube, Notepad, Calculator. Volume up, volume down, mute, "
    "screenshot, lock the PC, next song, bye."
)

# Phrases Whisper commonly produces from silence or background noise
HALLUCINATIONS = {"", "you", "thank you", "thanks for watching", "bye bye"}


class SttEngine:
    def __init__(self):
        self._client = Groq(api_key=config.GROQ_API_KEY)

    def transcribe(self, audio_data):
        # 16kHz mono 16-bit keeps the upload small without hurting accuracy
        wav_bytes = audio_data.get_wav_data(convert_rate=16000, convert_width=2)
        try:
            transcript = self._client.audio.transcriptions.create(
                file=("audio.wav", wav_bytes),
                model=config.STT_MODEL,
                response_format="text",
                language="en",
                temperature=0.0,
                prompt=VOCAB_PROMPT,
            )
        except Exception as e:
            print(f"[STT] Transcription failed: {e}")
            return ""

        text = str(transcript).strip().lower()
        check = re.sub(r"[^\w\s]", "", text).strip()
        if check in HALLUCINATIONS:
            return ""
        return text


stt_engine = SttEngine()