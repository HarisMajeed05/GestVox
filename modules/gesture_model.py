import os
import math
import urllib.request
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
import config

RECOGNIZER_URL = (
    "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/"
    "gesture_recognizer/float16/1/gesture_recognizer.task"
)
RECOGNIZER_PATH = os.path.join("assets", "gesture_recognizer.task")

HAND_LANDMARKER_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
HAND_LANDMARKER_PATH = os.path.join("assets", "hand_landmarker.task")


def _setting(name, default):
    # New settings fall back to defaults, so an older config.py keeps working
    return getattr(config, name, default)


def _ensure_model(url, path, label):
    if os.path.exists(path):
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    print(f"Downloading {label} (one-time)...")
    urllib.request.urlretrieve(url, path)
    print("Model downloaded.")


def _to_pixels(hand, w, h):
    return [(int(lm.x * w), int(lm.y * h)) for lm in hand]


# ---------------------------------------------------------------------------
# Backend 1: gesture recognizer (landmark models + pretrained classifier)
# ---------------------------------------------------------------------------


class GestureModel:
    # VIDEO mode tracks the hand across frames instead of detecting it from
    # scratch each time, which is faster and gives steadier landmarks.
    def __init__(self, num_hands=1, detection_conf=0.6, tracking_conf=0.6):
        _ensure_model(
            RECOGNIZER_URL, RECOGNIZER_PATH, "gesture recognition model (~8MB)"
        )
        options = vision.GestureRecognizerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=RECOGNIZER_PATH),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=num_hands,
            min_hand_detection_confidence=detection_conf,
            min_hand_presence_confidence=detection_conf,
            min_tracking_confidence=tracking_conf,
        )
        self._recognizer = vision.GestureRecognizer.create_from_options(options)
        self._last_ts = -1

    def process(self, rgb_frame, timestamp_ms):
        """Returns a list of (landmarks_px, gesture_name, gesture_score), one
        entry per detected hand. landmarks_px are (x, y) pixel tuples."""
        # VIDEO mode requires strictly increasing timestamps
        timestamp_ms = max(int(timestamp_ms), self._last_ts + 1)
        self._last_ts = timestamp_ms

        h, w, _ = rgb_frame.shape
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self._recognizer.recognize_for_video(mp_image, timestamp_ms)

        hands = []
        for i, hand in enumerate(result.hand_landmarks or []):
            name, score = "None", 0.0
            if result.gestures and i < len(result.gestures) and result.gestures[i]:
                top = result.gestures[i][0]
                name, score = top.category_name, top.score
            hands.append((_to_pixels(hand, w, h), name, score))
        return hands


# ---------------------------------------------------------------------------
# Backend 2: hand landmarker + rule-based classifier
# ---------------------------------------------------------------------------

# (knuckle, middle joint, tip) landmark indices for each non-thumb finger
FINGER_JOINTS = {
    "index": (5, 6, 8),
    "middle": (9, 10, 12),
    "ring": (13, 14, 16),
    "pinky": (17, 18, 20),
}
PALM_POINTS = (0, 5, 9, 13, 17)  # wrist and the four knuckles


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def finger_states(lm):
    """A finger counts as extended when its tip is farther from the wrist
    than its middle joint. Works at any hand rotation."""
    wrist = lm[0]
    ratio = _setting("FINGER_EXTEND_RATIO", 1.05)
    return {
        name: _dist(lm[tip], wrist) > _dist(lm[pip], wrist) * ratio
        for name, (_, pip, tip) in FINGER_JOINTS.items()
    }


def thumb_is_out(lm, hand_size):
    """The thumb counts as out when its tip is well away from the palm
    centre. A thumb wrapped over the fingers (fist) stays close to it."""
    cx = sum(lm[i][0] for i in PALM_POINTS) / len(PALM_POINTS)
    cy = sum(lm[i][1] for i in PALM_POINTS) / len(PALM_POINTS)
    return _dist(lm[4], (cx, cy)) / hand_size > _setting("THUMB_OUT_RATIO", 0.75)


def classify_landmarks(lm):
    """Returns a gesture name using the same labels as the pretrained
    recognizer, plus "Pinch" and "Pointing_Up". Uses 2D positions only, so
    a hand pointing straight at the camera can be misread."""
    hand_size = _dist(lm[0], lm[9]) or 1.0
    fingers = finger_states(lm)
    thumb = thumb_is_out(lm, hand_size)
    up_count = sum(fingers.values())

    # An extended finger touching the thumb is a click/scroll pinch, not a pose
    guard = _setting("PINCH_GUARD_RATIO", 0.4)
    for name, (_, _, tip) in FINGER_JOINTS.items():
        if fingers[name] and _dist(lm[4], lm[tip]) / hand_size < guard:
            return "Pinch"

    if up_count == 4:
        return "Open_Palm"

    if up_count == 0:
        if not thumb:
            return "Closed_Fist"
        # Thumb direction decides up or down; a sideways thumb is ignored
        rise = (lm[2][1] - lm[4][1]) / hand_size
        if rise > 0.5:
            return "Thumb_Up"
        if rise < -0.5:
            return "Thumb_Down"
        return "None"

    if (
        fingers["index"]
        and fingers["middle"]
        and not fingers["ring"]
        and not fingers["pinky"]
    ):
        return "Victory"
    if (
        thumb
        and fingers["index"]
        and fingers["pinky"]
        and not fingers["middle"]
        and not fingers["ring"]
    ):
        return "ILoveYou"
    if fingers["index"] and up_count == 1:
        return "Pointing_Up"
    return "None"


class _Debounce:
    # A new label only takes over after it has been seen for several frames
    # in a row, which removes single-frame flicker from rule-based labels.
    def __init__(self, frames):
        self._frames = max(1, frames)
        self._stable = "None"
        self._candidate = "None"
        self._count = 0

    def update(self, label):
        if label == self._candidate:
            self._count += 1
        else:
            self._candidate, self._count = label, 1
        if self._count >= self._frames:
            self._stable = self._candidate
        return self._stable


class LandmarkGestureModel:
    # Same output shape as GestureModel, so the rest of the app doesn't care
    # which backend is running. Gestures come from classify_landmarks().
    def __init__(self, num_hands=1, detection_conf=0.6, tracking_conf=0.6):
        _ensure_model(
            HAND_LANDMARKER_URL, HAND_LANDMARKER_PATH, "hand landmark model (~8MB)"
        )
        options = vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=HAND_LANDMARKER_PATH),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=num_hands,
            min_hand_detection_confidence=detection_conf,
            min_hand_presence_confidence=detection_conf,
            min_tracking_confidence=tracking_conf,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)
        self._last_ts = -1
        self._debounce = {}

    def process(self, rgb_frame, timestamp_ms):
        timestamp_ms = max(int(timestamp_ms), self._last_ts + 1)
        self._last_ts = timestamp_ms

        h, w, _ = rgb_frame.shape
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)

        frames = _setting("GESTURE_STABLE_FRAMES", 3)
        hands = []
        for i, hand in enumerate(result.hand_landmarks or []):
            landmarks = _to_pixels(hand, w, h)
            debounce = self._debounce.setdefault(i, _Debounce(frames))
            name = debounce.update(classify_landmarks(landmarks))
            hands.append((landmarks, name, 1.0))

        # Forget state for hands that left the frame
        for index in [k for k in self._debounce if k >= len(hands)]:
            del self._debounce[index]
        return hands


def create_gesture_model(num_hands, detection_conf, tracking_conf):
    backend = _setting("GESTURE_BACKEND", "recognizer")
    model_class = LandmarkGestureModel if backend == "landmarks" else GestureModel
    print(
        f"[Gesture] Backend: {'landmarks' if model_class is LandmarkGestureModel else 'recognizer'}"
    )
    return model_class(num_hands, detection_conf, tracking_conf)
