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
    def __init__(self, num_hands=1, min_confidence=0.6):
        _ensure_model()
        base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
        options = vision.GestureRecognizerOptions(
            base_options=base_options,
            num_hands=num_hands,
            min_hand_detection_confidence=min_confidence,
            min_hand_presence_confidence=min_confidence,
            min_tracking_confidence=min_confidence,
        )
        self._recognizer = vision.GestureRecognizer.create_from_options(options)

    def process(self, rgb_frame):
        """Returns (landmarks_px_or_None, gesture_name, gesture_score) for
        the first detected hand. landmarks_px is a list of (x, y) pixel
        tuples matching the input frame's dimensions."""
        h, w, _ = rgb_frame.shape
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self._recognizer.recognize(mp_image)

        if not result.hand_landmarks:
            return None, "None", 0.0

        landmarks_px = [
            (int(lm.x * w), int(lm.y * h)) for lm in result.hand_landmarks[0]
        ]

        gesture_name, gesture_score = "None", 0.0
        if result.gestures:
            top = result.gestures[0][0]
            gesture_name, gesture_score = top.category_name, top.score

        return landmarks_px, gesture_name, gesture_score