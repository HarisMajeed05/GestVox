import tkinter as tk
from modules.mode_manager import mode_manager
import config


class Overlay:
    def __init__(self):
        self._root = tk.Tk()
        self._root.title(config.APP_NAME)
        self._root.geometry("220x100+40+40")
        self._root.attributes("-topmost", True)
        self._root.resizable(False, False)

        self._status_label = tk.Label(
            self._root, text="Mode: GESTURE", font=("Segoe UI", 12, "bold")
        )
        self._status_label.pack(pady=(15, 5))

        self._toggle_btn = tk.Button(
            self._root, text="Switch to VOICE", command=self._on_toggle,
            font=("Segoe UI", 10),
        )
        self._toggle_btn.pack(pady=5)

        mode_manager.on_change(self._on_mode_change)

    def _on_toggle(self):
        mode_manager.toggle_mode()

    def _on_mode_change(self, mode):
        # Called from a background thread; hand off to tkinter's main loop
        self._root.after(0, self._update_ui, mode)

    def _update_ui(self, mode):
        self._status_label.config(text=f"Mode: {mode}")
        next_mode = "VOICE" if mode == "GESTURE" else "GESTURE"
        self._toggle_btn.config(text=f"Switch to {next_mode}")

    def run(self):
        self._root.mainloop()
