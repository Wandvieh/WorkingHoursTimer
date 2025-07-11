import time
import datetime
import json
import os
import csv
import tkinter as tk
from tkinter import font
from tkinter import simpledialog, messagebox
import win32gui
from filelock import FileLock

CONFIG_FILE = "config.json"
DEFAULT_TARGET = "Photoshop"
CHECK_INTERVAL = 1000  # ms
FILE = "timelog.csv"
LOCK_PATH = "timelog.csv.lock"

def get_active_window_title():
    return win32gui.GetWindowText(win32gui.GetForegroundWindow())

def format_seconds(seconds):
    return str(datetime.timedelta(seconds=int(seconds)))

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                return data.get("target_window", DEFAULT_TARGET), data.get("timer_title", "")
        except Exception:
            return DEFAULT_TARGET, ""
    return DEFAULT_TARGET, ""

def save_config(target, title):
    with open(CONFIG_FILE, "w") as f:
        json.dump({
            "target_window": target,
            "timer_title": title
        }, f)

class TimeTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Paused")
        self.root.resizable(False, False)

        self.timer_font = font.Font(family="Helvetica", size=36, weight="bold")

        # Optional title above timer
        self.title_label = tk.Label(root, text="", font=("Helvetica", 12, "bold"))
        self.title_label.pack(pady=(10, 0))

        self.label = tk.Label(root, text="00:00:00", font=self.timer_font, fg="gray")
        self.label.pack(padx=20, pady=(10, 10))

        self.target_label = tk.Label(root, text="", font=("Helvetica", 10))
        self.target_label.pack(pady=(0, 10))

        button_frame = tk.Frame(root)
        button_frame.pack()

        self.settings_button = tk.Button(button_frame, text="Change App…", command=self.change_target_dialog)
        self.settings_button.grid(row=0, column=0, padx=5)

        self.pause_button = tk.Button(button_frame, text="Pause", command=self.toggle_pause)
        self.pause_button.grid(row=0, column=1, padx=5)

        self.save_button = tk.Button(button_frame, text="Save", command=self.save_time_to_csv)
        self.save_button.grid(row=0, column=2,padx=5)
        

        # State
        self.target_window, self.timer_title = load_config()
        self.tracking = False
        self.paused = False
        self.start_time = 0
        self.total_time = 0

        self.update_target_label()
        self.update_title_label()
        self.update_timer()

    def update_target_label(self):
        if self.target_window.strip() == "":
            self.target_label.config(text="Tracking: All Windows (Always On)")
        else:
            self.target_label.config(text=f"Tracking: {self.target_window}")

    def update_title_label(self):
        self.title_label.config(text=self.timer_title if self.timer_title.strip() else "")

    def change_target_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Settings")
        dialog.geometry("300x200")
        dialog.resizable(False, False)

        tk.Label(dialog, text="Window title to track:").pack(pady=(10, 0))
        entry_var = tk.StringVar(value=self.target_window)
        entry = tk.Entry(dialog, textvariable=entry_var, width=30)
        entry.pack(pady=(0, 5))

        check_var = tk.BooleanVar(value=self.target_window.strip() == "")
        def toggle_entry():
            entry.config(state=tk.DISABLED if check_var.get() else tk.NORMAL)
        check = tk.Checkbutton(dialog, text="Track all the time (ignore window)", variable=check_var, command=toggle_entry)
        check.pack()

        tk.Label(dialog, text="Timer Title (optional):").pack(pady=(10, 0))
        title_var = tk.StringVar(value=self.timer_title)
        title_entry = tk.Entry(dialog, textvariable=title_var, width=30)
        title_entry.pack()

        def apply():
            new_target = "" if check_var.get() else entry_var.get().strip()
            new_title = title_var.get().strip()
            self.target_window = new_target
            self.timer_title = new_title
            save_config(self.target_window, self.timer_title)
            self.update_target_label()
            self.update_title_label()
            dialog.destroy()

        tk.Button(dialog, text="Save", command=apply).pack(pady=(15, 10))

        toggle_entry()
        entry.focus()

    def toggle_pause(self):
        if self.paused:
            self.paused = False
            if self.should_be_tracking():
                self.start_time = time.time()
                self.tracking = True
                self.label.config(fg="black")
                self.root.title("Tracking…")
            self.pause_button.config(text="Pause")
        else:
            if self.tracking:
                self.total_time += time.time() - self.start_time
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
        return self.target_window.lower() in get_active_window_title().lower()

    def update_timer(self):
        if self.should_be_tracking():
            if not self.tracking:
                self.start_time = time.time()
                self.tracking = True
                self.label.config(fg="black")
                self.root.title("Tracking…")
        else:
            if self.tracking:
                self.total_time += time.time() - self.start_time
                self.tracking = False
                self.label.config(fg="gray")
                self.root.title("Paused")

        total = self.total_time
        if self.tracking:
            total += time.time() - self.start_time

        self.label.config(text=format_seconds(total))
        self.root.after(CHECK_INTERVAL, self.update_timer)

    def save_time_to_csv(self):
        if not self.timer_title.strip():
            title = simpledialog.askstring("Title Required", "Enter a title for this session:")
            if not title:
                messagebox.showwarning("Cancelled", "Cannot save without a title.")
                return
            self.timer_title = title.strip()
            self.update_title_label()
            save_config(self.timer_title, self.target_window)

        if self.tracking:
            elapsed = time.time() - self.start_time
            self.total_time += elapsed
            self.tracking = False
            self.label.config(fg="gray")
            self.root.title("Paused")

        time_str = format_seconds(self.total_time)
        today_str = datetime.datetime.now().strftime("%d.%m.%Y")

        rows = {}
        fieldnames = set()

        # Safe write block
        with FileLock(LOCK_PATH):
            if os.path.exists(FILE):
                with open(FILE, "r", newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        date = row["Date"]
                        rows[date] = row
                        fieldnames.update(row.keys())

            fieldnames.add("Date")
            fieldnames.add(self.timer_title)
            ordered_fields = ["Date"] + sorted(fn for fn in fieldnames if fn != "Date")

            if today_str in rows:
                row = rows[today_str]
                prev_time = row.get(self.timer_title, "").strip()
                if prev_time:
                    try:
                        h, m, s = map(int, prev_time.split(":"))
                        old_td = datetime.timedelta(hours=h, minutes=m, seconds=s)
                        new_td = datetime.timedelta(seconds=int(self.total_time))
                        total_td = old_td + new_td
                        row[self.timer_title] = str(total_td)
                    except Exception:
                        row[self.timer_title] = time_str
                else:
                    row[self.timer_title] = time_str
            else:
                row = {field: "" for field in ordered_fields}
                row["Date"] = today_str
                row[self.timer_title] = time_str
                rows[today_str] = row

            sorted_rows = sorted(rows.values(), key=lambda r: datetime.datetime.strptime(r["Date"], "%d.%m.%Y"), reverse=True)

            with open(FILE, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=ordered_fields)
                writer.writeheader()
                for row in sorted_rows:
                    writer.writerow(row)

        messagebox.showinfo("Saved", f"Time saved to {FILE} under '{self.timer_title}' for {today_str}.")
        self.total_time = 0
        self.label.config(text="0:00:00")

# === RUN ===
if __name__ == "__main__":
    root = tk.Tk()
    app = TimeTrackerApp(root)
    root.mainloop()