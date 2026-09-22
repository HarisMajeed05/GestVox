import os
import urllib.request
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/"
    "gesture_recognizer/float16/1/gesture_recognizer.task"
)
MODEL_PATH = os.path.join("assets", "gesture_recognizer.task")


def _ensure_model():
    if os.path.exists(MODEL_PATH):
        return
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    print("Downloading gesture recognition model (one-time, ~8MB)...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print("Model downloaded.")


class GestureModel:
    # Runs in VIDEO mode, which tracks the hand across frames instead of
    # detecting it from scratch each time: faster and steadier landmarks.
    def __init__(self, num_hands=1, detection_conf=0.6, tracking_conf=0.6):
        _ensure_model()
        options = vision.GestureRecognizerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=MODEL_PATH),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=num_hands,
            min_hand_detection_confidence=detection_conf,
            min_hand_presence_confidence=detection_conf,
            min_tracking_confidence=tracking_conf,
        )
        self._recognizer = vision.GestureRecognizer.create_from_options(options)
        self._last_ts = -1

    def process(self, rgb_frame, timestamp_ms):
        """Returns (landmarks_px or None, gesture_name, gesture_score) for the
        first detected hand. landmarks_px are (x, y) pixel tuples."""
        # VIDEO mode requires strictly increasing timestamps
        timestamp_ms = max(int(timestamp_ms), self._last_ts + 1)
        self._last_ts = timestamp_ms

        h, w, _ = rgb_frame.shape
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self._recognizer.recognize_for_video(mp_image, timestamp_ms)

        if not result.hand_landmarks:
            return None, "None", 0.0

        landmarks_px = [(int(lm.x * w), int(lm.y * h)) for lm in result.hand_landmarks[0]]
        gesture_name, gesture_score = "None", 0.0
        if result.gestures:
            top = result.gestures[0][0]
            gesture_name, gesture_score = top.category_name, top.score
        return landmarks_px, gesture_name, gesture_score