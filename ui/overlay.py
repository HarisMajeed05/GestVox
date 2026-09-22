import customtkinter as ctk
from modules.mode_manager import mode_manager
import config

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

MODE_COLORS = {"GESTURE": "#4da3ff", "VOICE": "#5be37a"}


class Overlay:
    def __init__(self):
        self._root = ctk.CTk()
        self._root.title(config.APP_NAME)
        self._root.geometry("420x220+40+40")
        self._root.attributes("-topmost", True)
        self._root.overrideredirect(True)  # borderless floating panel
        self._root.configure(fg_color="#1a1a1a")

        self._card = ctk.CTkFrame(
            self._root, corner_radius=18, fg_color="#242424",
            border_width=1, border_color="#3a3a3a",
        )
        self._card.pack(fill="both", expand=True, padx=6, pady=6)
        self._card.bind("<ButtonPress-1>", self._start_drag)
        self._card.bind("<B1-Motion>", self._on_drag)

        header = ctk.CTkFrame(self._card, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(12, 0))
        ctk.CTkLabel(
            header, text=config.APP_NAME, font=("Segoe UI", 22, "bold"),
            text_color="#f0f0f0",
        ).pack(side="left")
        ctk.CTkButton(
            header, text="×", width=32, height=32, fg_color="transparent",
            hover_color="#3a3a3a", text_color="#aaaaaa", font=("Segoe UI", 18),
            command=self._root.destroy,
        ).pack(side="right")

        status_row = ctk.CTkFrame(self._card, fg_color="transparent")
        status_row.pack(fill="x", padx=22, pady=(18, 8))
        self._dot = ctk.CTkLabel(
            status_row, text="●", font=("Segoe UI", 20),
            text_color=MODE_COLORS["GESTURE"],
        )
        self._dot.pack(side="left")
        self._status_label = ctk.CTkLabel(
            status_row, text="GESTURE MODE", font=("Segoe UI", 18, "bold"),
            text_color="#e0e0e0",
        )
        self._status_label.pack(side="left", padx=(10, 0))

        self._toggle_btn = ctk.CTkButton(
            self._card, text="Switch to Voice", height=56, corner_radius=12,
            font=("Segoe UI", 16, "bold"), fg_color="#3a3a3a",
            hover_color="#4a4a4a", command=self._on_toggle,
        )
        self._toggle_btn.pack(fill="x", padx=22, pady=(12, 22))

        mode_manager.on_change(self._on_mode_change)
        self._drag_x = 0
        self._drag_y = 0

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        x = self._root.winfo_x() + event.x - self._drag_x
        y = self._root.winfo_y() + event.y - self._drag_y
        self._root.geometry(f"+{x}+{y}")

    def _on_toggle(self):
        mode_manager.toggle_mode()

    def _on_mode_change(self, mode):
        self._root.after(0, self._update_ui, mode)

    def _update_ui(self, mode):
        self._status_label.configure(text=f"{mode} MODE")
        self._dot.configure(text_color=MODE_COLORS[mode])
        next_mode = "Voice" if mode == "GESTURE" else "Gesture"
        self._toggle_btn.configure(text=f"Switch to {next_mode}")

    def run(self):
        self._root.mainloop()