import time
import tkinter as tk
from tkinter import font
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

        button_frame = tk.Frame(root)
        button_frame.pack()

        self.settings_button = tk.Button(button_frame, text="Change App…", command=self.change_target_dialog)
        self.settings_button.grid(row=0, column=0, padx=5)

        self.pause_button = tk.Button(button_frame, text="Pause", command=self.toggle_pause)
        self.pause_button.grid(row=0, column=1, padx=5)

        # State
        self.target_window = load_config()
        self.tracking = False
        self.paused = False
        self.start_time = 0
        self.total_time = 0

        self.update_target_label()
        self.update_timer()

    def update_target_label(self):
        if self.target_window.strip() == "":
            self.target_label.config(text="Tracking: All Windows (Always On)")
        else:
            self.target_label.config(text=f"Tracking: {self.target_window}")

    def change_target_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Change Tracked App")
        dialog.geometry("300x150")
        dialog.resizable(False, False)

        tk.Label(dialog, text="Window title to track:").pack(pady=(10, 0))
        entry_var = tk.StringVar(value=self.target_window)
        entry = tk.Entry(dialog, textvariable=entry_var, width=30)
        entry.pack(pady=(0, 5))

        check_var = tk.BooleanVar(value=self.target_window.strip() == "")
        def toggle_entry():
            state = tk.DISABLED if check_var.get() else tk.NORMAL
            entry.config(state=state)

        check = tk.Checkbutton(dialog, text="Track all the time (ignore window)", variable=check_var, command=toggle_entry)
        check.pack()

        def apply():
            new_target = "" if check_var.get() else entry_var.get().strip()
            self.target_window = new_target
            save_config(self.target_window)
            self.update_target_label()
            dialog.destroy()

        tk.Button(dialog, text="Save", command=apply).pack(pady=(10, 10))

        toggle_entry()
        entry.focus()

    def toggle_pause(self):
        if self.paused:
            # Resuming
            self.paused = False
            if self.should_be_tracking():
                self.start_time = time.time()
                self.tracking = True
                self.label.config(fg="black")
                self.root.title("Tracking…")
            self.pause_button.config(text="Pause")
        else:
            # Pausing
            if self.tracking:
                session_time = time.time() - self.start_time
                self.total_time += session_time
            self.tracking = False
            self.paused = True
            self.label.config(fg="gray")
            self.root.title("Paused (Manual)")
            self.pause_button.config(text="Resume")

    def should_be_tracking(self):
        if self.paused:
            return False
        if self.target_window.strip() == "":
            return True
        active_title = get_active_window_title()
        return self.target_window.lower() in active_title.lower()

    def update_timer(self):
        if self.should_be_tracking():
            if not self.tracking:
                self.start_time = time.time()
                self.tracking = True
                self.label.config(fg="black")
                self.root.title("Tracking…")
        else:
            if self.tracking:
                session_time = time.time() - self.start_time
                self.total_time += session_time
                self.tracking = False
                self.label.config(fg="gray")
                self.root.title("Paused")

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