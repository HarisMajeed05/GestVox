import os
from dotenv import load_dotenv

load_dotenv()

# API keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"

# Wake word settings
WAKE_WORDS = ["hey air", "hey control", "air control"]
SWITCH_TO_VOICE_PHRASES = ["switch to voice", "voice mode", "use voice"]
SWITCH_TO_GESTURE_PHRASES = ["switch to gesture", "gesture mode", "use gesture"]

# Gesture settings (tuned for accuracy + responsiveness)
CAM_INDEX = 0
FRAME_WIDTH = 960
FRAME_HEIGHT = 540
HAND_DETECTION_CONFIDENCE = 0.8
HAND_TRACKING_CONFIDENCE = 0.8
MAX_NUM_HANDS = 1
SMOOTHING_FACTOR = 5          # higher = smoother, slightly more lag
CLICK_DISTANCE_THRESHOLD = 35 # pixels, thumb-index pinch distance
SCROLL_SENSITIVITY = 15
FRAME_MARGIN = 100            # ignore edges of frame for stable cursor mapping

# Voice settings
MIC_ENERGY_THRESHOLD = 300
MIC_PAUSE_THRESHOLD = 0.6
TTS_RATE = 175
TTS_VOLUME = 1.0

# App
APP_NAME = "GestVox"
