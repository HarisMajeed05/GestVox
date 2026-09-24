import os
from dotenv import load_dotenv

load_dotenv()

# API keys and models
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_REASONING_EFFORT = "low"            # low keeps replies fast for voice use
# Languages
# MULTILINGUAL lets Whisper detect the language of each sentence, which is
# what makes mixed Urdu-English speech work. Set False for English only.
MULTILINGUAL = True
LANGUAGES = ["en", "ur", "pa"]             # English, Urdu, Punjabi

# STT_BACKEND: "local" runs faster-whisper on this PC (no network delay,
# works offline), "groq" uses Groq's Whisper (much better for Urdu and
# Punjabi, adds ~0.5-1.5s)
STT_BACKEND = "groq"
STT_LOCAL_MODEL = "small"                  # use a multilingual model, not .en
STT_MODEL_FAST = "whisper-large-v3-turbo"  # Groq: idle listening
STT_MODEL_ACCURATE = "whisper-large-v3"    # Groq: commands during a session

# Wake word and session phrases, across all supported languages
WAKE_WORDS = [
    "hey vox", "hey gestvox", "hi vox", "he vox",     # English
    "ہے ووکس", "ہے وکس", "او ووکس", "سنو ووکس",        # Urdu script
    "suno vox", "oye vox",                             # Roman Urdu / Punjabi
]
END_SESSION_PHRASES = [
    "bye", "goodbye", "that's all", "stop listening",
    "خدا حافظ", "اللہ حافظ", "بس", "ٹھیک ہے بس",
    "khuda hafiz", "allah hafiz", "bas", "bas karo",
]
SWITCH_TO_VOICE_PHRASES = ["switch to voice", "voice mode", "use voice"]
SWITCH_TO_GESTURE_PHRASES = ["switch to gesture", "gesture mode", "use gesture"]

# Camera
# CAMERA_SOURCE: "local" uses CAM_INDEX (webcam on this PC).
# "remote" reads a network stream from another device running camera_server.py
CAMERA_SOURCE = "local"
CAM_INDEX = 0
REMOTE_CAMERA_URL = "http://100.114.205.1:8080/video"
FRAME_WIDTH = 640
FRAME_HEIGHT = 360
SHOW_PREVIEW = True

# Hand tracking
HAND_DETECTION_CONFIDENCE = 0.6
HAND_TRACKING_CONFIDENCE = 0.6
MAX_NUM_HANDS = 2             # two hands enables the pinch-zoom gesture
GESTURE_MIN_SCORE = 0.65      # minimum confidence for built-in gestures
FRAME_MARGIN = 80             # ignore frame edges for stable cursor mapping

# Cursor smoothing (One Euro filter): lower min_cutoff = steadier when slow,
# higher beta = less lag when moving fast
CURSOR_MIN_CUTOFF = 1.0
CURSOR_BETA = 0.007

# Pinch thresholds as a fraction of hand size (wrist to middle knuckle)
CLICK_CLOSE_RATIO = 0.35      # pinch closes below this
CLICK_RELEASE_RATIO = 0.45    # pinch must open past this to re-arm
CLICK_COOLDOWN = 0.2          # seconds between clicks
DOUBLE_CLICK_WINDOW = 0.4     # two clicks within this count as a double-click
RIGHT_CLICK_COOLDOWN = 0.5
SCROLL_STEP = 120             # one mouse wheel notch on Windows
DRAG_HOLD_TIME = 0.45         # seconds a pinch is held before it becomes a drag
SWIPE_MIN_RATIO = 1.2         # swipe distance as a multiple of hand size
SWIPE_MAX_TIME = 0.5          # seconds a swipe must complete within
ZOOM_STEP_RATIO = 0.15        # two-hand distance change that triggers one zoom step

# Multi-user
VOICE_LOGIN_ENABLED = True    # set False to skip login and use shared memory

# Microphone and speech detection
MIC_DEVICE_INDEX = 2          # run list_mics.py to pick the right one
MIC_ENERGY_THRESHOLD = 300
MIC_PAUSE_THRESHOLD = 0.4     # seconds of silence that end a phrase
LISTEN_BEEP = True            # short beep when it is ready for your next command
BARGE_IN = True               # lets you interrupt the assistant mid-sentence
VAD_AGGRESSIVENESS = 2        # 0-3, higher filters more background noise
VAD_MIN_SPEECH_RATIO = 0.15   # audio with less speech than this is skipped

# Text to speech
# "edge" uses Microsoft neural voices (needs internet, supports Urdu),
# "pyttsx3" is offline but English only
TTS_BACKEND = "edge"
TTS_VOICES = {
    "en": "en-US-AriaNeural",
    "ur": "ur-PK-AsadNeural",     # or ur-PK-UzmaNeural for a female voice
    "pa": "ur-PK-AsadNeural",     # Punjabi has no neural voice, Urdu reads it well
}
TTS_RATE = 180
TTS_VOLUME = 1.0

# App
APP_NAME = "GestVox"