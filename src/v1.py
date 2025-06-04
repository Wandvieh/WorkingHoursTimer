import time
import tkinter as tk
from tkinter import font
import win32gui
import datetime

# === SETTINGS ===
TARGET_KEYWORD = "Visual Studio Code"  # Change this to the window you want to track
CHECK_INTERVAL = 1000  # in milliseconds (1000 = 1 sec)

# === CORE LOGIC ===
def get_active_window_title():
    return win32gui.GetWindowText(win32gui.GetForegroundWindow())

def format_seconds(seconds):
    return str(datetime.timedelta(seconds=int(seconds)))

# === GUI APP ===
class TimeTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Paused")
        self.root.resizable(False, False)

        # Font setup
        self.timer_font = font.Font(family="Helvetica", size=36, weight="bold")

        # Timer label
        self.label = tk.Label(root, text="00:00:00", font=self.timer_font, fg="gray")
        self.label.pack(padx=20, pady=20)

        # Time tracking variables
        self.tracking = False
        self.start_time = 0
        self.total_time = 0

        # Start the periodic check
        self.update_timer()

    def update_timer(self):
        active_title = get_active_window_title()

        if TARGET_KEYWORD.lower() in active_title.lower():
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

        # Update the label
        current_time = self.total_time
        if self.tracking:
            current_time += time.time() - self.start_time

        self.label.config(text=format_seconds(current_time))

        # Schedule the next update
        self.root.after(CHECK_INTERVAL, self.update_timer)

# === RUN ===
if __name__ == "__main__":
    root = tk.Tk()
    app = TimeTrackerApp(root)
    root.mainloop()