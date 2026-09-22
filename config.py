import os
from dotenv import load_dotenv

load_dotenv()

# API keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"

# Wake word settings
WAKE_WORDS = ["hey vox", "hey gest", "gestvox", "hey gestvox"]
SWITCH_TO_VOICE_PHRASES = ["switch to voice", "voice mode", "use voice"]
SWITCH_TO_GESTURE_PHRASES = ["switch to gesture", "gesture mode", "use gesture"]

# Gesture settings (tuned for accuracy + responsiveness)
# CAMERA_SOURCE: "local" uses CAM_INDEX (webcam on this PC).
# "remote" reads a network stream from another device (e.g. a laptop)
# running camera_server.py, useful when this PC has no camera.
CAMERA_SOURCE = "local"       # "local" or "remote"
CAM_INDEX = 0
REMOTE_CAMERA_URL = "http://100.114.205.1:8080/video"  # set to laptop's stream URL
FRAME_WIDTH = 640
FRAME_HEIGHT = 360
HAND_MODEL_COMPLEXITY = 1  # 0 = fastest/least accurate, 1 = balanced
HAND_DETECTION_CONFIDENCE = 0.6
HAND_TRACKING_CONFIDENCE = 0.6
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