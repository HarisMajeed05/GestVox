import os
from dotenv import load_dotenv

load_dotenv()

# API keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"

# Wake word settings
WAKE_WORDS = ["hey vox", "hey gestvox"]
SWITCH_TO_VOICE_PHRASES = ["switch to voice", "voice mode", "use voice"]
SWITCH_TO_GESTURE_PHRASES = ["switch to gesture", "gesture mode", "use gesture"]

# Gesture settings (tuned for accuracy + responsiveness)
# CAMERA_SOURCE: "local" uses CAM_INDEX (webcam on this PC).
# "remote" reads a network stream from another device (e.g. a laptop)
# running camera_server.py, useful when this PC has no camera.
CAMERA_SOURCE = "local"       # "local" or "remote"
CAM_INDEX = 0
REMOTE_CAMERA_URL = "http://192.168.1.100:8080/video"  # set to laptop's stream URL
FRAME_WIDTH = 1240
FRAME_HEIGHT = 360
HAND_MODEL_COMPLEXITY = 1  # 0 = fastest/least accurate, 1 = balanced
HAND_DETECTION_CONFIDENCE = 0.6
HAND_TRACKING_CONFIDENCE = 0.6
MAX_NUM_HANDS = 1
SMOOTHING_FACTOR = 3          # higher = smoother, slightly more lag
# Pinch thresholds as a fraction of hand size (wrist-to-middle-knuckle
# distance), so detection adapts to hand distance from the camera instead
# of relying on fixed pixel values.
CLICK_CLOSE_RATIO = 0.35   # pinch closes below this fraction of hand size
CLICK_RELEASE_RATIO = 0.45 # pinch must open past this fraction to re-arm
CLICK_COOLDOWN = 0.3       # seconds, minimum gap between clicks
RIGHT_CLICK_COOLDOWN = 0.5
SCROLL_SENSITIVITY = 15
FRAME_MARGIN = 100            # ignore edges of frame for stable cursor mapping

# Multi-user
VOICE_LOGIN_ENABLED = True  # set False to skip login and use shared memory

# Voice settings
MIC_DEVICE_INDEX = None  # None = system default. Run list_mics.py to see options.
MIC_ENERGY_THRESHOLD = 300
MIC_PAUSE_THRESHOLD = 0.6
TTS_RATE = 175
TTS_VOLUME = 1.0

# App
APP_NAME = "GestVox"