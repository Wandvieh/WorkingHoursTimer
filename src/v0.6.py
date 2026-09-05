import time
import datetime
import json
import os
import csv
import subprocess
import tkinter as tk
from tkinter import font, filedialog
from tkinter import simpledialog, messagebox
import win32gui
from filelock import FileLock


# ============================================================
# CONFIGURATION
# ============================================================

CONFIG_FILE = "config.json"
DEFAULT_TARGET = "Photoshop"
CHECK_INTERVAL = 1000  # ms

FILE = "timelog.csv"
LOCK_PATH = "timelog.csv.lock"


# ============================================================
# WINDOWS / TIMER HELPERS
# ============================================================

def get_active_window_title():
    return win32gui.GetWindowText(win32gui.GetForegroundWindow())


def format_seconds(seconds):
    return str(datetime.timedelta(seconds=int(seconds)))


# ============================================================
# CONFIG
# ============================================================

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

                return (
                    data.get("target_window", DEFAULT_TARGET),
                    data.get("timer_title", ""),
                    data.get("programs", [])
                )

        except Exception:
            return DEFAULT_TARGET, "", []

    return DEFAULT_TARGET, "", []


def save_config(target, title, programs):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "target_window": target,
                "timer_title": title,
                "programs": programs
            },
            f,
            indent=4,
            ensure_ascii=False
        )


# ============================================================
# PROGRAM MANAGER
# ============================================================

class ProgramManager:
    def __init__(self, parent, programs, on_change):
        self.parent = parent
        self.programs = programs
        self.on_change = on_change

        self.window = tk.Toplevel(parent)
        self.window.title("Programs")
        self.window.geometry("550x350")
        self.window.resizable(False, False)

        self.create_ui()

    def create_ui(self):

        tk.Label(
            self.window,
            text="Programs to start",
            font=("Helvetica", 14, "bold")
        ).pack(pady=(15, 10))

        # ----------------------------------------------------
        # Listbox
        # ----------------------------------------------------

        frame = tk.Frame(self.window)
        frame.pack(fill="both", expand=True, padx=20)

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")

        self.listbox = tk.Listbox(
            frame,
            height=10,
            width=65,
            yscrollcommand=scrollbar.set
        )

        self.listbox.pack(side="left", fill="both", expand=True)

        scrollbar.config(command=self.listbox.yview)

        self.refresh_list()

        # ----------------------------------------------------
        # Buttons
        # ----------------------------------------------------

        button_frame = tk.Frame(self.window)
        button_frame.pack(pady=15)

        tk.Button(
            button_frame,
            text="Add Program…",
            width=15,
            command=self.add_program
        ).grid(row=0, column=0, padx=5)

        tk.Button(
            button_frame,
            text="Remove",
            width=15,
            command=self.remove_program
        ).grid(row=0, column=1, padx=5)

        tk.Button(
            button_frame,
            text="Close",
            width=15,
            command=self.window.destroy
        ).grid(row=0, column=2, padx=5)

    # --------------------------------------------------------
    # Refresh list
    # --------------------------------------------------------

    def refresh_list(self):
        self.listbox.delete(0, tk.END)

        for program in self.programs:
            self.listbox.insert(tk.END, program)

    # --------------------------------------------------------
    # Add program
    # --------------------------------------------------------

    def add_program(self):

        path = filedialog.askopenfilename(
            parent=self.window,
            title="Select Program",
            filetypes=[
                ("Windows Programs", "*.exe"),
                ("All Files", "*.*")
            ]
        )

        if not path:
            return

        path = os.path.normpath(path)

        # Prevent duplicates
        if path in self.programs:
            messagebox.showinfo(
                "Already Added",
                "This program is already in the list.",
                parent=self.window
            )
            return

        self.programs.append(path)

        self.refresh_list()
        self.on_change()

    # --------------------------------------------------------
    # Remove program
    # --------------------------------------------------------

    def remove_program(self):

        selection = self.listbox.curselection()

        if not selection:
            messagebox.showwarning(
                "No Selection",
                "Please select a program first.",
                parent=self.window
            )
            return

        index = selection[0]

        program = self.programs[index]

        answer = messagebox.askyesno(
            "Remove Program",
            f"Remove this program?\n\n{program}",
            parent=self.window
        )

        if not answer:
            return

        del self.programs[index]

        self.refresh_list()
        self.on_change()


# ============================================================
# MAIN APPLICATION
# ============================================================

class TimeTrackerApp:

    def __init__(self, root):

        self.root = root

        self.root.title("Paused")
        self.root.resizable(False, False)

        # ----------------------------------------------------
        # Fonts
        # ----------------------------------------------------

        self.timer_font = font.Font(
            family="Helvetica",
            size=36,
            weight="bold"
        )

        # ----------------------------------------------------
        # Title
        # ----------------------------------------------------

        self.title_label = tk.Label(
            root,
            text="",
            font=("Helvetica", 12, "bold")
        )

        self.title_label.pack(pady=(10, 0))

        # ----------------------------------------------------
        # Timer
        # ----------------------------------------------------

        self.label = tk.Label(
            root,
            text="00:00:00",
            font=self.timer_font,
            fg="gray"
        )

        self.label.pack(
            padx=20,
            pady=(10, 10)
        )

        # ----------------------------------------------------
        # Tracking label
        # ----------------------------------------------------

        self.target_label = tk.Label(
            root,
            text="",
            font=("Helvetica", 10)
        )

        self.target_label.pack(
            pady=(0, 10)
        )

        # ----------------------------------------------------
        # Buttons
        # ----------------------------------------------------

        button_frame = tk.Frame(root)
        button_frame.pack()

        self.settings_button = tk.Button(
            button_frame,
            text="Change App…",
            command=self.change_target_dialog
        )

        self.settings_button.grid(
            row=0,
            column=0,
            padx=5,
            pady=5
        )

        self.programs_button = tk.Button(
            button_frame,
            text="Programs…",
            command=self.open_program_manager
        )

        self.programs_button.grid(
            row=0,
            column=1,
            padx=5,
            pady=5
        )

        self.start_programs_button = tk.Button(
            button_frame,
            text="Start Workspace",
            command=self.start_workspace
        )

        self.start_programs_button.grid(
            row=0,
            column=2,
            padx=5,
            pady=5
        )

        self.pause_button = tk.Button(
            button_frame,
            text="Pause",
            command=self.toggle_pause
        )

        self.pause_button.grid(
            row=1,
            column=0,
            padx=5,
            pady=5
        )

        self.save_button = tk.Button(
            button_frame,
            text="Save",
            command=self.save_time_to_csv
        )

        self.save_button.grid(
            row=1,
            column=1,
            padx=5,
            pady=5
        )

        # ----------------------------------------------------
        # State
        # ----------------------------------------------------

        (
            self.target_window,
            self.timer_title,
            self.programs
        ) = load_config()

        self.tracking = False
        self.paused = False

        self.start_time = 0
        self.total_time = 0

        # ----------------------------------------------------
        # Initial UI
        # ----------------------------------------------------

        self.update_target_label()
        self.update_title_label()

        self.update_timer()


    # ========================================================
    # TARGET WINDOW
    # ========================================================

    def update_target_label(self):

        if self.target_window.strip() == "":
            self.target_label.config(
                text="Tracking: All Windows (Always On)"
            )
        else:
            self.target_label.config(
                text=f"Tracking: {self.target_window}"
            )


    # ========================================================
    # TITLE
    # ========================================================

    def update_title_label(self):

        self.title_label.config(
            text=self.timer_title
            if self.timer_title.strip()
            else ""
        )


    # ========================================================
    # PROGRAM MANAGER
    # ========================================================

    def open_program_manager(self):

        ProgramManager(
            self.root,
            self.programs,
            self.programs_changed
        )


    def programs_changed(self):

        save_config(
            self.target_window,
            self.timer_title,
            self.programs
        )


    # ========================================================
    # START WORKSPACE
    # ========================================================

    def start_workspace(self):

        if not self.programs:

            messagebox.showinfo(
                "No Programs",
                "No programs have been configured yet.\n\n"
                "Open 'Programs…' and add some programs first."
            )

            return

        failed_programs = []

        for program in self.programs:

            try:

                if not os.path.exists(program):

                    failed_programs.append(
                        f"{program}\n(File not found)"
                    )

                    continue

                # Start the program
                subprocess.Popen([program])

            except Exception as e:

                failed_programs.append(
                    f"{program}\n({e})"
                )

        if failed_programs:

            messagebox.showwarning(
                "Some Programs Could Not Be Started",
                "The following programs could not be started:\n\n"
                + "\n\n".join(failed_programs)
            )

        else:

            # Give Windows a moment to start the programs.
            # We don't do any window positioning yet.
            self.root.after(
                500,
                self.start_workspace_timer
            )


    def start_workspace_timer(self):

        # The workspace has been started.
        #
        # For now we simply leave the timer logic as it is.
        # Later we can decide whether starting a workspace
        # should automatically start a specific project/session.

        pass


    # ========================================================
    # SETTINGS
    # ========================================================

    def change_target_dialog(self):

        dialog = tk.Toplevel(self.root)

        dialog.title("Settings")
        dialog.geometry("300x200")
        dialog.resizable(False, False)

        tk.Label(
            dialog,
            text="Window title to track:"
        ).pack(pady=(10, 0))

        entry_var = tk.StringVar(
            value=self.target_window
        )

        entry = tk.Entry(
            dialog,
            textvariable=entry_var,
            width=30
        )

        entry.pack(pady=(0, 5))

        check_var = tk.BooleanVar(
            value=self.target_window.strip() == ""
        )

        def toggle_entry():

            entry.config(
                state=tk.DISABLED
                if check_var.get()
                else tk.NORMAL
            )

        check = tk.Checkbutton(
            dialog,
            text="Track all the time (ignore window)",
            variable=check_var,
            command=toggle_entry
        )

        check.pack()

        tk.Label(
            dialog,
            text="Timer Title (optional):"
        ).pack(pady=(10, 0))

        title_var = tk.StringVar(
            value=self.timer_title
        )

        title_entry = tk.Entry(
            dialog,
            textvariable=title_var,
            width=30
        )

        title_entry.pack()

        def apply():

            new_target = (
                ""
                if check_var.get()
                else entry_var.get().strip()
            )

            new_title = title_var.get().strip()

            self.target_window = new_target
            self.timer_title = new_title

            save_config(
                self.target_window,
                self.timer_title,
                self.programs
            )

            self.update_target_label()
            self.update_title_label()

            dialog.destroy()

        tk.Button(
            dialog,
            text="Save",
            command=apply
        ).pack(pady=(15, 10))

        toggle_entry()

        entry.focus()


    # ========================================================
    # PAUSE
    # ========================================================

    def toggle_pause(self):

        if self.paused:

            self.paused = False

            if self.should_be_tracking():

                self.start_time = time.time()
                self.tracking = True

                self.label.config(fg="black")
                self.root.title("Tracking…")

            self.pause_button.config(
                text="Pause"
            )

        else:

            if self.tracking:

                self.total_time += (
                    time.time() - self.start_time
                )

            self.tracking = False
            self.paused = True

            self.label.config(fg="gray")
            self.root.title("Paused (Manual)")

            self.pause_button.config(
                text="Resume"
            )


    # ========================================================
    # TRACKING CONDITION
    # ========================================================

    def should_be_tracking(self):

        if self.paused:
            return False

        if self.target_window.strip() == "":
            return True

        return (
            self.target_window.lower()
            in get_active_window_title().lower()
        )


    # ========================================================
    # TIMER UPDATE
    # ========================================================

    def update_timer(self):

        if self.should_be_tracking():

            if not self.tracking:

                self.start_time = time.time()
                self.tracking = True

                self.label.config(fg="black")
                self.root.title("Tracking…")

        else:

            if self.tracking:

                self.total_time += (
                    time.time() - self.start_time
                )

                self.tracking = False

                self.label.config(fg="gray")
                self.root.title("Paused")

        total = self.total_time

        if self.tracking:

            total += (
                time.time() - self.start_time
            )

        self.label.config(
            text=format_seconds(total)
        )

        self.root.after(
            CHECK_INTERVAL,
            self.update_timer
        )


    # ========================================================
    # SAVE TIME
    # ========================================================

    def save_time_to_csv(self):

        if not self.timer_title.strip():

            title = simpledialog.askstring(
                "Title Required",
                "Enter a title for this session:"
            )

            if not title:

                messagebox.showwarning(
                    "Cancelled",
                    "Cannot save without a title."
                )

                return

            self.timer_title = title.strip()

            self.update_title_label()

            save_config(
                self.target_window,
                self.timer_title,
                self.programs
            )

        if self.tracking:

            elapsed = (
                time.time() - self.start_time
            )

            self.total_time += elapsed
            self.tracking = False

            self.label.config(fg="gray")
            self.root.title("Paused")

        time_str = format_seconds(
            self.total_time
        )

        today_str = datetime.datetime.now().strftime(
            "%d.%m.%Y"
        )

        rows = {}
        fieldnames = set()

        with FileLock(LOCK_PATH):

            if os.path.exists(FILE):

                with open(
                    FILE,
                    "r",
                    newline="",
                    encoding="utf-8"
                ) as f:

                    reader = csv.DictReader(f)

                    for row in reader:

                        date = row["Date"]

                        rows[date] = row
                        fieldnames.update(row.keys())

            fieldnames.add("Date")
            fieldnames.add(self.timer_title)

            ordered_fields = (
                ["Date"]
                + sorted(
                    fn
                    for fn in fieldnames
                    if fn != "Date"
                )
            )

            if today_str in rows:

                row = rows[today_str]

                prev_time = row.get(
                    self.timer_title,
                    ""
                ).strip()

                if prev_time:

                    try:

                        h, m, s = map(
                            int,
                            prev_time.split(":")
                        )

                        old_td = datetime.timedelta(
                            hours=h,
                            minutes=m,
                            seconds=s
                        )

                        new_td = datetime.timedelta(
                            seconds=int(
                                self.total_time
                            )
                        )

                        total_td = (
                            old_td + new_td
                        )

                        row[self.timer_title] = str(
                            total_td
                        )

                    except Exception:

                        row[self.timer_title] = time_str

                else:

                    row[self.timer_title] = time_str

            else:

                row = {
                    field: ""
                    for field in ordered_fields
                }

                row["Date"] = today_str
                row[self.timer_title] = time_str

                rows[today_str] = row

            sorted_rows = sorted(
                rows.values(),
                key=lambda r:
                    datetime.datetime.strptime(
                        r["Date"],
                        "%d.%m.%Y"
                    ),
                reverse=True
            )

            with open(
                FILE,
                "w",
                newline="",
                encoding="utf-8"
            ) as f:

                writer = csv.DictWriter(
                    f,
                    fieldnames=ordered_fields
                )

                writer.writeheader()

                for row in sorted_rows:
                    writer.writerow(row)

        messagebox.showinfo(
            "Saved",
            f"Time saved to {FILE} under "
            f"'{self.timer_title}' for {today_str}."
        )

        self.total_time = 0

        self.label.config(
            text="0:00:00"
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = TimeTrackerApp(root)

    root.mainloop()