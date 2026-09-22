import cv2
import math
import time
import threading
import pyautogui
import config
from modules.mode_manager import mode_manager
from modules.gesture_model import GestureModel
from modules import system_control as sc

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0  # default 0.1s pause after every call causes cursor lag
screen_w, screen_h = pyautogui.size()

BUILTIN_COOLDOWN = 1.2        # seconds before the same gesture can fire again
STILL_RATIO = 0.25            # hand must move less than this (x hand size) while holding

# Gestures that fold the index finger or put the thumb near other fingers.
# While one is detected, cursor and pinch actions pause to avoid accidental clicks.
POINTER_BLOCKING = {"Closed_Fist", "Thumb_Up", "Thumb_Down", "Victory", "ILoveYou"}

# Standard MediaPipe hand landmark connections, for drawing the skeleton
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]


def distance(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def map_range(value, in_min, in_max, out_min, out_max):
    value = max(in_min, min(in_max, value))
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


def draw_landmarks(frame, landmarks):
    for a, b in HAND_CONNECTIONS:
        cv2.line(frame, landmarks[a], landmarks[b], (0, 200, 0), 2)
    for point in landmarks:
        cv2.circle(frame, point, 4, (0, 100, 255), -1)


class OneEuroFilter:
    # Adaptive smoothing: strong smoothing when the hand moves slowly (no
    # jitter), light smoothing when it moves fast (no lag).
    def __init__(self, min_cutoff, beta, d_cutoff=1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.reset()

    def reset(self):
        self._x = None
        self._dx = 0.0
        self._t = None

    @staticmethod
    def _alpha(cutoff, dt):
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, x, t):
        if self._t is None:
            self._x, self._t = x, t
            return x
        dt = max(t - self._t, 1e-3)
        dx = (x - self._x) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        self._dx = a_d * dx + (1 - a_d) * self._dx
        cutoff = self.min_cutoff + self.beta * abs(self._dx)
        a = self._alpha(cutoff, dt)
        self._x = a * x + (1 - a) * self._x
        self._t = t
        return self._x


class LatestFrameReader:
    # Reads frames in a background thread and keeps only the newest one, so
    # network stream buffering never delivers stale frames. Each frame gets
    # an id so the main loop can skip frames it already processed.
    def __init__(self, cap):
        self._cap = cap
        self._frame = None
        self._frame_id = 0
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
                    self._frame_id += 1
            else:
                time.sleep(0.01)

    def read(self):
        with self._lock:
            if self._frame is None:
                return 0, None
            return self._frame_id, self._frame.copy()

    def stop(self):
        self._running = False
        self._thread.join(timeout=2)


class GestureControl:
    def __init__(self, toggle_callback=None):
        self._toggle_callback = toggle_callback
        self._running = False
        self._thread = None
        self._show_preview = config.SHOW_PREVIEW
        self._current_gesture = "None"

        self._filter_x = OneEuroFilter(config.CURSOR_MIN_CUTOFF, config.CURSOR_BETA)
        self._filter_y = OneEuroFilter(config.CURSOR_MIN_CUTOFF, config.CURSOR_BETA)
        self._clicking = False
        self._right_clicking = False
        self._last_click_time = 0
        self._last_right_click_time = 0
        self._scroll_anchor = None

        self._model = GestureModel(
            num_hands=config.MAX_NUM_HANDS,
            detection_conf=config.HAND_DETECTION_CONFIDENCE,
            tracking_conf=config.HAND_TRACKING_CONFIDENCE,
        )

        # name -> (label, action, hold seconds). Longer holds for actions
        # that are disruptive if triggered by accident.
        self._builtin_actions = {
            "Closed_Fist": ("Fist -> switch mode", self._toggle_callback, 0.8),
            "Open_Palm": ("Open palm -> play/pause", lambda: sc.media_control("play_pause"), 1.0),
            "Thumb_Up": ("Thumbs up -> volume up", lambda: sc.set_volume("up"), 0.5),
            "Thumb_Down": ("Thumbs down -> volume down", lambda: sc.set_volume("down"), 0.5),
            "Victory": ("Victory -> screenshot", sc.take_screenshot, 0.8),
            "ILoveYou": ("I love you -> lock PC", sc.lock_pc, 1.5),
        }
        self._hold_name = None
        self._hold_start = 0
        self._hold_anchor = None
        self._last_fire_time = {}

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

    def _open_camera(self):
        if config.CAMERA_SOURCE == "remote":
            cap = cv2.VideoCapture(config.REMOTE_CAMERA_URL, cv2.CAP_FFMPEG)
            source = config.REMOTE_CAMERA_URL
        else:
            cap = cv2.VideoCapture(config.CAM_INDEX, cv2.CAP_DSHOW)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
            source = config.CAM_INDEX
        if not cap.isOpened():
            print(f"[Gesture] Could not open camera source: {source}")
            return None
        print(f"[Gesture] Camera opened: {source}")
        return cap

    def _run(self):
        cap = self._open_camera()
        if cap is None:
            self._running = False
            return
        reader = LatestFrameReader(cap)
        last_id = 0

        while self._running:
            frame_id, frame = reader.read()
            if frame is None or frame_id == last_id:
                time.sleep(0.005)  # no new frame yet, avoid busy-looping
                continue
            last_id = frame_id

            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            now = time.time()
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            landmarks, gesture_name, score = self._model.process(rgb, now * 1000)

            if landmarks:
                draw_landmarks(frame, landmarks)
                self._handle_frame(landmarks, gesture_name, score, w, h, now)
            else:
                self._on_hand_lost()

            if self._show_preview:
                self._draw_overlay(frame, h, landmarks is not None)
                cv2.imshow(config.APP_NAME, frame)
                if cv2.waitKey(1) & 0xFF == 27:  # Esc hides the preview, tracking keeps running
                    self._show_preview = False
                    cv2.destroyWindow(config.APP_NAME)

        reader.stop()
        cap.release()
        cv2.destroyAllWindows()

    def _draw_overlay(self, frame, h, hand_found):
        cv2.putText(frame, f"Mode: {mode_manager.get_mode()}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        if not hand_found:
            cv2.putText(frame, "No hand detected", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.putText(frame, f"Gesture: {self._current_gesture}", (10, h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 200, 0), 2)

    def _on_hand_lost(self):
        # Resets state so the cursor doesn't jump when the hand comes back
        self._current_gesture = "None"
        self._filter_x.reset()
        self._filter_y.reset()
        self._clicking = False
        self._right_clicking = False
        self._scroll_anchor = None
        self._reset_hold()

    def _reset_hold(self):
        self._hold_name = None
        self._hold_anchor = None

    def _handle_frame(self, landmarks, gesture_name, score, w, h, now):
        mode = mode_manager.get_mode()
        recognized = gesture_name in self._builtin_actions and score >= config.GESTURE_MIN_SCORE

        # In voice mode only the fist (mode switch) works
        if recognized and (mode == "GESTURE" or gesture_name == "Closed_Fist"):
            self._handle_builtin(gesture_name, landmarks, now)
        else:
            self._reset_hold()

        if mode != "GESTURE":
            if not recognized:
                self._current_gesture = "Voice mode (fist to switch)"
            return
        if recognized and gesture_name in POINTER_BLOCKING:
            return
        self._handle_pointer(landmarks, w, h, now)

    def _handle_builtin(self, name, landmarks, now):
        label, action, hold_time = self._builtin_actions[name]
        self._current_gesture = label
        hand_size = distance(landmarks[0], landmarks[9]) or 1
        wrist = landmarks[0]

        # The hold restarts if the gesture changes or the hand moves, so
        # gestures made while moving the cursor don't fire by accident
        moved = (self._hold_anchor is not None and
                 distance(wrist, self._hold_anchor) > STILL_RATIO * hand_size)
        if name != self._hold_name or moved:
            self._hold_name = name
            self._hold_start = now
            self._hold_anchor = wrist
            return

        held = now - self._hold_start >= hold_time
        cooled = now - self._last_fire_time.get(name, 0) >= BUILTIN_COOLDOWN
        if held and cooled and action:
            self._log(label)
            try:
                action()
            except Exception as e:
                print(f"[Gesture] Action '{label}' failed: {e}")
            self._last_fire_time[name] = now
            self._hold_start = now  # must hold again to repeat

    def _handle_pointer(self, lm, w, h, now):
        hand_size = distance(lm[0], lm[9]) or 1
        thumb = lm[4]
        ratios = {
            "click": distance(thumb, lm[8]) / hand_size,
            "scroll": distance(thumb, lm[12]) / hand_size,
            "right": distance(thumb, lm[20]) / hand_size,
        }
        closest = min(ratios, key=ratios.get)

        # Scroll: thumb + middle pinch, vertical hand movement scrolls
        if closest == "scroll" and ratios["scroll"] < config.CLICK_CLOSE_RATIO:
            self._handle_scroll(lm, hand_size)
            return
        self._scroll_anchor = None

        # Cursor freezes while fingers are closing, so a pinch doesn't drag it off target
        if ratios[closest] > config.CLICK_RELEASE_RATIO:
            self._move_cursor(lm[8], w, h, now)
            self._current_gesture = "Cursor move"

        if closest == "click" and ratios["click"] < config.CLICK_CLOSE_RATIO:
            self._left_click(now)
        elif ratios["click"] > config.CLICK_RELEASE_RATIO:
            self._clicking = False

        if closest == "right" and ratios["right"] < config.CLICK_CLOSE_RATIO:
            self._right_click(now)
        elif ratios["right"] > config.CLICK_RELEASE_RATIO:
            self._right_clicking = False

    def _move_cursor(self, point, w, h, now):
        m = config.FRAME_MARGIN
        x = map_range(point[0], m, w - m, 0, screen_w - 1)
        y = map_range(point[1], m, h - m, 0, screen_h - 1)
        pyautogui.moveTo(self._filter_x(x, now), self._filter_y(y, now))

    def _left_click(self, now):
        if self._clicking or now - self._last_click_time < config.CLICK_COOLDOWN:
            return
        # A second single click inside the window is read by Windows as a
        # double-click, so no separate doubleClick call is needed
        is_double = now - self._last_click_time < config.DOUBLE_CLICK_WINDOW
        pyautogui.click()
        self._current_gesture = "Double-click" if is_double else "Click"
        self._log(self._current_gesture)
        self._last_click_time = now
        self._clicking = True

    def _right_click(self, now):
        if self._right_clicking or now - self._last_right_click_time < config.RIGHT_CLICK_COOLDOWN:
            return
        pyautogui.click(button="right")
        self._current_gesture = "Right-click"
        self._log("Right-click")
        self._last_right_click_time = now
        self._right_clicking = True

    def _handle_scroll(self, lm, hand_size):
        y = lm[9][1]  # middle knuckle, steadier than a fingertip while pinching
        if self._scroll_anchor is None:
            self._scroll_anchor = y
            self._current_gesture = "Scroll ready"
            return
        step_px = hand_size * 0.15
        dy = self._scroll_anchor - y
        steps = int(dy / step_px)
        if steps:
            pyautogui.scroll(steps * config.SCROLL_STEP)
            self._scroll_anchor = y
            direction = "up" if steps > 0 else "down"
            self._current_gesture = f"Scroll {direction}"
            self._log(f"Scroll {direction}")

    def _log(self, name):
        print(f"[Gesture] {name}")