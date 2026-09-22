import cv2
import pyautogui
import math
import time
import threading
import config
from modules.mode_manager import mode_manager
from modules.gesture_model import GestureModel
from modules import system_control as sc

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0  # default 0.1s pause after every call was causing cursor lag
screen_w, screen_h = pyautogui.size()

# Cooldown per built-in gesture so a held pose doesn't repeat-fire
BUILTIN_GESTURE_COOLDOWN = 1.2
BUILTIN_GESTURE_HOLD_TIME = 0.5  # seconds a gesture must be held before it fires

# Standard MediaPipe hand landmark connections, for drawing the skeleton
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]


def draw_landmarks(frame, landmarks):
    for a, b in HAND_CONNECTIONS:
        cv2.line(frame, landmarks[a], landmarks[b], (0, 200, 0), 2)
    for point in landmarks:
        cv2.circle(frame, point, 4, (0, 100, 255), -1)


def distance(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


class LatestFrameReader:
    # Continuously reads frames in a background thread and only keeps the
    # most recent one. Prevents lag from network stream buffering, where
    # the default read() call returns old queued frames instead of live ones.
    def __init__(self, cap):
        self._cap = cap
        self._frame = None
        self._lock = threading.Lock()
        self._running = True
        self._thread = threading.Thread(target=self._update, daemon=True)
        self._thread.start()

    def _update(self):
        while self._running:
            ok, frame = self._cap.read()
            if ok:
                with self._lock:
                    self._frame = frame

    def read(self):
        with self._lock:
            if self._frame is None:
                return False, None
            return True, self._frame.copy()

    def stop(self):
        self._running = False
        self._thread.join(timeout=2)


class GestureControl:
    def __init__(self, toggle_callback=None):
        self._toggle_callback = toggle_callback
        self._running = False
        self._thread = None
        self._prev_x, self._prev_y = 0, 0
        self._clicking = False
        self._last_click_time = 0
        self._current_gesture = "None"

        self._model = GestureModel(num_hands=config.MAX_NUM_HANDS)

        # Built-in gesture actions: name -> (label, handler function)
        self._builtin_actions = {
            "Closed_Fist": ("Fist -> switch mode", self._toggle_callback),
            "Open_Palm": ("Open palm -> play/pause", lambda: sc.media_control("play_pause")),
            "Thumb_Up": ("Thumbs up -> volume up", lambda: sc.set_volume("up")),
            "Thumb_Down": ("Thumbs down -> volume down", lambda: sc.set_volume("down")),
            "Victory": ("Victory -> screenshot", sc.take_screenshot),
        }
        self._gesture_hold_start = None
        self._last_builtin_name = None
        self._last_builtin_time = 0

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self):
        if config.CAMERA_SOURCE == "remote":
            source = config.REMOTE_CAMERA_URL
        else:
            source = config.CAM_INDEX

        backend = cv2.CAP_DSHOW if config.CAMERA_SOURCE == "local" else cv2.CAP_FFMPEG
        cap = cv2.VideoCapture(source, backend)
        if config.CAMERA_SOURCE == "local":
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

        if not cap.isOpened():
            print(f"Could not open camera source: {source}")
            self._running = False
            return

        reader = LatestFrameReader(cap)

        while self._running:
            ok, frame = reader.read()
            if not ok:
                continue
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            landmarks, gesture_name, gesture_score = self._model.process(rgb)

            if landmarks:
                draw_landmarks(frame, landmarks)
                self._handle_frame(landmarks, gesture_name, gesture_score, w, h)
            else:
                self._current_gesture = "None"
                self._gesture_hold_start = None
                cv2.putText(
                    frame, "No hand detected", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2,
                )

            cv2.putText(
                frame, f"Mode: {mode_manager.get_mode()}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2,
            )
            cv2.putText(
                frame, f"Gesture: {self._current_gesture}", (10, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 200, 0), 2,
            )
            cv2.imshow(config.APP_NAME, frame)
            if cv2.waitKey(1) & 0xFF == 27:  # Esc closes preview window only
                break

        reader.stop()
        cap.release()
        cv2.destroyAllWindows()

    def _handle_frame(self, landmarks, gesture_name, gesture_score, w, h):
        if gesture_name in self._builtin_actions and gesture_score > 0.6:
            self._handle_builtin_gesture(gesture_name)
            return  # a recognized built-in gesture takes priority this frame

        self._gesture_hold_start = None
        if mode_manager.get_mode() == "GESTURE":
            self._handle_cursor_and_pinch(landmarks, w, h)
        else:
            self._current_gesture = "None"

    def _handle_builtin_gesture(self, gesture_name):
        label, action = self._builtin_actions[gesture_name]
        self._current_gesture = label
        now = time.time()

        if gesture_name != self._last_builtin_name or self._gesture_hold_start is None:
            self._gesture_hold_start = now
            self._last_builtin_name = gesture_name
            return

        held_long_enough = now - self._gesture_hold_start >= BUILTIN_GESTURE_HOLD_TIME
        cooldown_passed = now - self._last_builtin_time >= BUILTIN_GESTURE_COOLDOWN
        if held_long_enough and cooldown_passed and action:
            self._log_gesture(label)
            action()
            self._last_builtin_time = now
            self._gesture_hold_start = now  # require re-hold before firing again

    def _handle_cursor_and_pinch(self, landmarks, w, h):
        index_tip = landmarks[8]
        thumb_tip = landmarks[4]
        middle_tip = landmarks[12]
        self._current_gesture = "Cursor move"
        self._last_builtin_name = None

        x = _map_range(index_tip[0], config.FRAME_MARGIN, w - config.FRAME_MARGIN, 0, screen_w)
        y = _map_range(index_tip[1], config.FRAME_MARGIN, h - config.FRAME_MARGIN, 0, screen_h)
        smooth_x = self._prev_x + (x - self._prev_x) / config.SMOOTHING_FACTOR
        smooth_y = self._prev_y + (y - self._prev_y) / config.SMOOTHING_FACTOR
        pyautogui.moveTo(smooth_x, smooth_y)
        self._prev_x, self._prev_y = smooth_x, smooth_y

        hand_size = distance(landmarks[0], landmarks[9]) or 1
        pinch_ratio = distance(thumb_tip, index_tip) / hand_size
        now = time.time()
        if pinch_ratio < config.CLICK_CLOSE_RATIO:
            if not self._clicking and now - self._last_click_time > config.CLICK_COOLDOWN:
                if now - self._last_click_time < 0.4:
                    pyautogui.doubleClick()
                    self._current_gesture = "Double-click"
                    self._log_gesture("Double-click")
                else:
                    pyautogui.click()
                    self._current_gesture = "Click"
                    self._log_gesture("Click")
                self._last_click_time = now
                self._clicking = True
        elif pinch_ratio > config.CLICK_RELEASE_RATIO:
            self._clicking = False

        scroll_ratio = distance(thumb_tip, middle_tip) / hand_size
        if scroll_ratio < config.CLICK_CLOSE_RATIO:
            delta = self._prev_y - y
            if abs(delta) > 2:
                pyautogui.scroll(int(delta / config.SCROLL_SENSITIVITY) * 10)
                direction = "up" if delta > 0 else "down"
                self._current_gesture = f"Scroll {direction}"
                self._log_gesture(f"Scroll {direction}")

    def _log_gesture(self, name):
        print(f"[Gesture] {name}")


def _map_range(value, in_min, in_max, out_min, out_max):
    value = max(in_min, min(in_max, value))
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min