import cv2
import mediapipe as mp
import pyautogui
import math
import time
import threading
import config
from modules.mode_manager import mode_manager

pyautogui.FAILSAFE = False
screen_w, screen_h = pyautogui.size()


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
        self._fist_start_time = None
        self._fist_triggered = False

        self._mp_hands = mp.solutions.hands
        self._hands = self._mp_hands.Hands(
            max_num_hands=config.MAX_NUM_HANDS,
            model_complexity=config.HAND_MODEL_COMPLEXITY,
            min_detection_confidence=config.HAND_DETECTION_CONFIDENCE,
            min_tracking_confidence=config.HAND_TRACKING_CONFIDENCE,
        )
        self._drawer = mp.solutions.drawing_utils

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

    def _is_fist(self, landmarks):
        # Fist = all four fingertips below their middle knuckle (folded)
        tips = [8, 12, 16, 20]
        pips = [6, 10, 14, 18]
        folded = sum(
            1 for t, p in zip(tips, pips) if landmarks[t][1] > landmarks[p][1]
        )
        return folded >= 4

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
            result = self._hands.process(rgb)

            if result.multi_hand_landmarks:
                hand = result.multi_hand_landmarks[0]
                self._drawer.draw_landmarks(frame, hand, self._mp_hands.HAND_CONNECTIONS)
                landmarks = [(int(lm.x * w), int(lm.y * h)) for lm in hand.landmark]

                if mode_manager.get_mode() == "GESTURE":
                    self._handle_gestures(landmarks, w, h)
            else:
                self._fist_start_time = None
                self._fist_triggered = False
                cv2.putText(
                    frame, "No hand detected", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2,
                )

            cv2.putText(
                frame, f"Mode: {mode_manager.get_mode()}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2,
            )
            cv2.imshow(config.APP_NAME, frame)
            if cv2.waitKey(1) & 0xFF == 27:  # Esc closes preview window only
                break

        reader.stop()
        cap.release()
        cv2.destroyAllWindows()

    def _handle_gestures(self, landmarks, w, h):
        index_tip = landmarks[8]
        thumb_tip = landmarks[4]
        middle_tip = landmarks[12]

        # Fist held for 1s toggles mode (gesture <-> voice)
        if self._is_fist(landmarks):
            if self._fist_start_time is None:
                self._fist_start_time = time.time()
            elif not self._fist_triggered and time.time() - self._fist_start_time > 1.0:
                self._fist_triggered = True
                if self._toggle_callback:
                    self._toggle_callback()
            return
        else:
            self._fist_start_time = None
            self._fist_triggered = False

        # Map index fingertip position to screen coordinates
        x = int(
            _map_range(index_tip[0], config.FRAME_MARGIN, w - config.FRAME_MARGIN, 0, screen_w)
        )
        y = int(
            _map_range(index_tip[1], config.FRAME_MARGIN, h - config.FRAME_MARGIN, 0, screen_h)
        )
        smooth_x = self._prev_x + (x - self._prev_x) / config.SMOOTHING_FACTOR
        smooth_y = self._prev_y + (y - self._prev_y) / config.SMOOTHING_FACTOR
        pyautogui.moveTo(smooth_x, smooth_y)
        self._prev_x, self._prev_y = smooth_x, smooth_y

        # Pinch (thumb+index) = click, quick double pinch = double-click
        pinch_dist = distance(thumb_tip, index_tip)
        if pinch_dist < config.CLICK_DISTANCE_THRESHOLD:
            if not self._clicking:
                now = time.time()
                if now - self._last_click_time < 0.4:
                    pyautogui.doubleClick()
                else:
                    pyautogui.click()
                self._last_click_time = now
                self._clicking = True
        else:
            self._clicking = False

        # Thumb + middle pinch = scroll, direction from vertical hand movement
        scroll_dist = distance(thumb_tip, middle_tip)
        if scroll_dist < config.CLICK_DISTANCE_THRESHOLD:
            delta = self._prev_y - y
            if abs(delta) > 2:
                pyautogui.scroll(int(delta / config.SCROLL_SENSITIVITY) * 10)


def _map_range(value, in_min, in_max, out_min, out_max):
    value = max(in_min, min(in_max, value))
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min