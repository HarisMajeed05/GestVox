import os
import threading

USERS_DIR = "users"


class UserSession:
    def __init__(self):
        self._lock = threading.Lock()
        self._username = None
        self._listeners = []

    def get_user(self):
        with self._lock:
            return self._username

    def is_logged_in(self):
        return self.get_user() is not None

    def login(self, username):
        with self._lock:
            self._username = username
            listeners = list(self._listeners)
        for callback in listeners:
            callback(username)

    def logout(self):
        self.login(None)

    def memory_path(self):
        # Per-user memory file; falls back to a shared file if nobody's logged in
        if not self.is_logged_in():
            return "gestvox_memory.json"
        return os.path.join(USERS_DIR, self.get_user(), "memory.json")

    def on_change(self, callback):
        with self._lock:
            self._listeners.append(callback)


user_session = UserSession()