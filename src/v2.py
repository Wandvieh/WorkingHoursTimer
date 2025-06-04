import time
import tkinter as tk
from tkinter import font, simpledialog, messagebox
import win32gui
import datetime
import json
import os

# === FILE SETTINGS ===
CONFIG_FILE = "config.json"

# === DEFAULTS ===
DEFAULT_TARGET = "Photoshop"
CHECK_INTERVAL = 1000  # milliseconds

# === CORE FUNCTIONS ===
def get_active_window_title():
    return win32gui.GetWindowText(win32gui.GetForegroundWindow())

def format_seconds(seconds):
    return str(datetime.timedelta(seconds=int(seconds)))

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                return data.get("target_window", DEFAULT_TARGET)
        except Exception:
            return DEFAULT_TARGET
    return DEFAULT_TARGET

def save_config(target):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"target_window": target}, f)

# === GUI CLASS ===
class TimeTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Paused")
        self.root.resizable(False, False)

        # Fonts
        self.timer_font = font.Font(family="Helvetica", size=36, weight="bold")

        # Labels and layout
        self.label = tk.Label(root, text="00:00:00", font=self.timer_font, fg="gray")
        self.label.pack(padx=20, pady=(20, 10))

        self.target_label = tk.Label(root, text="", font=("Helvetica", 10))
        self.target_label.pack(pady=(0, 10))

        self.settings_button = tk.Button(root, text="Change App", command=self.change_target)
        self.settings_button.pack(pady=(0, 20))

        # State
        self.target_window = load_config()
        self.tracking = False
        self.start_time = 0
        self.total_time = 0

        self.update_target_label()
        self.update_timer()

    def update_target_label(self):
        self.target_label.config(text=f"Tracking: {self.target_window}")

    def change_target(self):
        new_target = simpledialog.askstring("Change App", "Enter window title:",
                                            initialvalue=self.target_window)
        if new_target:
            self.target_window = new_target.strip()
            save_config(self.target_window)
            self.update_target_label()

    def update_timer(self):
        active_title = get_active_window_title()

        if self.target_window.lower() in active_title.lower():
            if not self.tracking:
                self.start_time = time.time()
                self.tracking = True
                self.root.title("Tracking…")
                self.label.config(fg="black")
        else:
            if self.tracking:
                session_time = time.time() - self.start_time
                self.total_time += session_time
                self.tracking = False
                self.root.title("Paused")
                self.label.config(fg="gray")

        current_time = self.total_time
        if self.tracking:
            current_time += time.time() - self.start_time

        self.label.config(text=format_seconds(current_time))
        self.root.after(CHECK_INTERVAL, self.update_timer)

# === RUN ===
if __name__ == "__main__":
    root = tk.Tk()
    app = TimeTrackerApp(root)
    root.mainloop()