import threading

# Shared state between gesture, voice, and UI threads.
# GESTURE and VOICE are the only two modes; both can run detection
# in the background but only the active mode's actions take effect.


class ModeManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._mode = "GESTURE"
        self._listeners = []

    def get_mode(self):
        with self._lock:
            return self._mode

    def set_mode(self, mode):
        mode = mode.upper()
        if mode not in ("GESTURE", "VOICE"):
            return
        with self._lock:
            if self._mode == mode:
                return
            self._mode = mode
            listeners = list(self._listeners)
        for callback in listeners:
            callback(mode)

    def toggle_mode(self):
        new_mode = "VOICE" if self.get_mode() == "GESTURE" else "GESTURE"
        self.set_mode(new_mode)
        return new_mode

    def on_change(self, callback):
        with self._lock:
            self._listeners.append(callback)


mode_manager = ModeManager()
