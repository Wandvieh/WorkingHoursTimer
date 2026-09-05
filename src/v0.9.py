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
# CONFIGURATION
CONFIG_FILE = "config.json"
DEFAULT_TARGET = "Photoshop"
CHECK_INTERVAL = 1000  # ms
FILE = "timelog.csv"
LOCK_PATH = "timelog.csv.lock"
# WINDOWS / TIMER HELPERS
def get_active_window_title():
    return win32gui.GetWindowText(
        win32gui.GetForegroundWindow())
def format_seconds(seconds):
    return str(datetime.timedelta(seconds=int(seconds)))
# CONFIG
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(
                CONFIG_FILE,
                "r",
                encoding="utf-8") as f:
                data = json.load(f)
                return (
                    data.get(
                        "target_window",
                        DEFAULT_TARGET),
                    data.get(
                        "timer_title",
                        ""),
                    data.get(
                        "sessions",
                        []))
        except Exception:
            return DEFAULT_TARGET, "", []
    return DEFAULT_TARGET, "", []
def save_config(
    target_window,
    timer_title,
    sessions):
    with open(
        CONFIG_FILE,
        "w",
        encoding="utf-8") as f:
        json.dump(
            {
                "target_window": target_window,
                "timer_title": timer_title,
                "sessions": sessions
            },
            f,
            indent=4,
            ensure_ascii=False)
# MAIN APPLICATION
class TimeTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sessions")
        self.root.resizable(False, False)
        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.on_close)
        # Fonts
        self.timer_font = font.Font(
            family="Helvetica",
            size=36,
            weight="bold")
        # State
        (
            self.target_window,
            self.timer_title,
            self.sessions
        ) = load_config()
        self.current_session_index = None
        self.tracking = False
        self.paused = True
        self.start_time = 0
        self.total_time = 0
        # UI
        self.create_ui()
        # Start directly with Overview
        self.show_overview()
        self.update_all_labels()
        self.update_timer()
    # UI
    def create_ui(self):
        # SESSION BAR
        self.session_bar = tk.Frame(
            self.root,
            bd=1,
            relief="solid")
        self.session_bar.pack(
            fill="x",
            padx=10,
            pady=(10, 5))
        self.overview_button = tk.Button(
            self.session_bar,
            text="Overview",
            command=self.toggle_overview)
        self.overview_button.pack(
            padx=8,
            pady=6)
        # OVERVIEW
        self.overview_frame = tk.Frame(
            self.root)
        # TIMER / NORMAL VIEW
        self.main_frame = tk.Frame(
            self.root)
        # Session name
        self.session_label = tk.Label(
            self.main_frame,
            text="No Session",
            font=("Helvetica", 14, "bold"))
        self.session_label.pack(
            pady=(5, 0))
        # Timer title
        self.title_label = tk.Label(
            self.main_frame,
            text="",
            font=("Helvetica", 12, "bold"))
        self.title_label.pack(
            pady=(5, 0))
        # Timer
        self.label = tk.Label(
            self.main_frame,
            text="00:00:00",
            font=self.timer_font,
            fg="gray")
        self.label.pack(
            padx=20,
            pady=(10, 10))
        # Tracking
        self.target_label = tk.Label(
            self.main_frame,
            text="",
            font=("Helvetica", 10))
        self.target_label.pack(
            pady=(0, 10))
        # Buttons
        button_frame = tk.Frame(
            self.main_frame)
        button_frame.pack()
        self.settings_button = tk.Button(
            button_frame,
            text="Change App…",
            command=self.change_target_dialog)
        self.settings_button.grid(
            row=0,
            column=0,
            padx=5,
            pady=5)
        self.start_programs_button = tk.Button(
            button_frame,
            text="Start Workspace",
            command=self.start_workspace)
        self.start_programs_button.grid(
            row=0,
            column=1,
            padx=5,
            pady=5)
        if self.paused:
            button_text = "Start Timer"
        else:
            button_text = "Pause"
        self.pause_button = tk.Button(
            button_frame,
            text=button_text,
            command=self.toggle_pause)
        self.pause_button.grid(
            row=1,
            column=0,
            padx=5,
            pady=5)
        self.save_button = tk.Button(
            button_frame,
            text="Save",
            command=self.save_time_to_csv)
        self.save_button.grid(
            row=1,
            column=1,
            padx=5,
            pady=5)
    # OVERVIEW
    def toggle_overview(self):
        if self.overview_frame.winfo_ismapped():
            self.hide_overview()
        else:
            self.show_overview()
    # SHOW OVERVIEW
    def show_overview(self):
        self.main_frame.pack_forget()
        self.overview_frame.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=5)
        self.create_overview()
        self.root.title("Sessions")
    # HIDE OVERVIEW
    def hide_overview(self):
        self.overview_frame.pack_forget()
        self.main_frame.pack(
            fill="both",
            expand=True)
        session = self.get_current_session()
        if session:
            self.root.title(
                session.get(
                    "name",
                    "Timer"))
        else:
            self.root.title("Timer")
    # CREATE OVERVIEW
    def create_overview(self):
        # Delete old contents
        for widget in self.overview_frame.winfo_children():
            widget.destroy()
        # Header
        tk.Label(
            self.overview_frame,
            text="Sessions",
            font=("Helvetica", 18, "bold")
        ).pack(
            pady=(10, 5))
        tk.Label(
            self.overview_frame,
            text="Select a session to start working."
        ).pack(
            pady=(0, 15))
        # Sessions
        if not self.sessions:
            tk.Label(
                self.overview_frame,
                text=(
                    "No sessions yet."
                ),
                font=("Helvetica", 11)
            ).pack(
                pady=30)
        else:
            for index, session in enumerate(
                self.sessions
            ):
                self.create_session_card(
                    index,
                    session)
        # New Session
        tk.Button(
            self.overview_frame,
            text="New Session…",
            width=18,
            command=self.new_session
        ).pack(
            pady=(15, 5))
    # SESSION CARD
    def create_session_card(
        self,
        index,
        session
    ):
        name = session.get(
            "name",
            "Unnamed")
        programs = session.get(
            "programs",
            [])
        # Outer frame
        frame = tk.Frame(
            self.overview_frame,
            bd=1,
            relief="solid")
        frame.pack(
            fill="x",
            padx=15,
            pady=5)
        # Session name
        tk.Label(
            frame,
            text=name,
            font=("Helvetica", 13, "bold"),
            width=20,
            anchor="w"
        ).grid(
            row=0,
            column=0,
            padx=(10, 5),
            pady=10,
            sticky="w")
        # Programs
        program_names = []
        for program in programs:
            program_names.append(
                os.path.basename(program))
        if program_names:
            program_text = ", ".join(
                program_names)
        else:
            program_text = "No programs configured"
        tk.Label(
            frame,
            text=program_text,
            anchor="w"
        ).grid(
            row=0,
            column=1,
            padx=5,
            pady=10,
            sticky="w")
        # Buttons
        button_frame = tk.Frame(
            frame)
        button_frame.grid(
            row=1,
            column=0,
            columnspan=3,
            pady=(0, 10))
        # Start
        tk.Button(
            button_frame,
            text="Start",
            width=10,
            command=lambda i=index:
                self.start_session(i)
        ).grid(
            row=0,
            column=0,
            padx=3)
        # Edit
        tk.Button(
            button_frame,
            text="Edit",
            width=10,
            command=lambda i=index:
                self.edit_session(i)
        ).grid(
            row=0,
            column=1,
            padx=3)
        # Delete
        tk.Button(
            button_frame,
            text="Delete",
            width=10,
            command=lambda i=index:
                self.delete_session(i)
        ).grid(
            row=0,
            column=2,
            padx=3)
    # NEW SESSION
    def new_session(self):
        name = simpledialog.askstring(
            "New Session",
            "Name of the session:",
            parent=self.root)
        if not name:
            return
        name = name.strip()
        if not name:
            return
        # Check duplicate names
        for session in self.sessions:
            if session.get(
                "name",
                ""
            ).lower() == name.lower():
                messagebox.showwarning(
                    "Already Exists",
                    (
                        "A session with this name "
                        "already exists."
                    ),
                    parent=self.root)
                return
        session = {
            "name": name,
            "programs": []
        }
        self.sessions.append(
            session)
        save_config(
            self.target_window,
            self.timer_title,
            self.sessions)
        self.create_overview()
        # Open editor directly after creating
        self.edit_session(
            len(self.sessions) - 1)
    # EDIT SESSION
    def edit_session(
        self,
        index
    ):
        if index < 0 or index >= len(self.sessions):
            return
        session = self.sessions[index]
        dialog = tk.Toplevel(
            self.root)
        dialog.title(
            "Edit Session")
        dialog.geometry(
            "650x450")
        dialog.resizable(
            False,
            False)
        # Name
        tk.Label(
            dialog,
            text="Session Name:").pack(
            pady=(15, 5))
        name_var = tk.StringVar(
            value=session.get(
                "name",
                ""))
        name_entry = tk.Entry(
            dialog,
            textvariable=name_var,
            width=50)
        name_entry.pack(
            pady=(0, 15))
        # Programs
        tk.Label(
            dialog,
            text="Programs:").pack()
        frame = tk.Frame(
            dialog)
        frame.pack(
            fill="both",
            expand=True,
            padx=20)
        scrollbar = tk.Scrollbar(
            frame)
        scrollbar.pack(
            side="right",
            fill="y")
        program_list = tk.Listbox(
            frame,
            height=12,
            width=75,
            yscrollcommand=scrollbar.set)
        program_list.pack(
            side="left",
            fill="both",
            expand=True)
        scrollbar.config(
            command=program_list.yview)
        # Load existing programs
        for program in session.get(
            "programs",
            []
        ):
            program_list.insert(
                tk.END,
                program)
        # Program buttons
        program_buttons = tk.Frame(
            dialog)
        program_buttons.pack(
            pady=10)
        def add_program():
            path = filedialog.askopenfilename(
                parent=dialog,
                title="Select Program",
                filetypes=[
                    (
                        "Windows Programs",
                        "*.exe"
                    ),
                    (
                        "All Files",
                        "*.*")
                ])
            if not path:
                return
            path = os.path.normpath(
                path)
            existing = list(
                program_list.get(
                    0,
                    tk.END))
            if path in existing:
                messagebox.showinfo(
                    "Already Added",
                    (
                        "This program is already "
                        "in the session."
                    ),
                    parent=dialog)
                return
            program_list.insert(
                tk.END,
                path)
        def remove_program():
            selection = (
                program_list.curselection())
            if not selection:
                return
            program_list.delete(
                selection[0])
        tk.Button(
            program_buttons,
            text="Add Program…",
            width=16,
            command=add_program
        ).grid(
            row=0,
            column=0,
            padx=5)
        tk.Button(
            program_buttons,
            text="Remove",
            width=16,
            command=remove_program
        ).grid(
            row=0,
            column=1,
            padx=5)
        # Save / Cancel
        bottom_frame = tk.Frame(
            dialog)
        bottom_frame.pack(
            pady=(5, 15))
        def save():
            new_name = (
                name_var.get().strip())
            if not new_name:
                messagebox.showwarning(
                    "Name Required",
                    "Please enter a session name.",
                    parent=dialog)
                return
            # Check duplicate name
            for other_index, other_session in enumerate(
                self.sessions
            ):
                if other_index == index:
                    continue
                if other_session.get(
                    "name",
                    ""
                ).lower() == new_name.lower():
                    messagebox.showwarning(
                        "Already Exists",
                        (
                            "A session with this name "
                            "already exists."
                        ),
                        parent=dialog)
                    return
            programs = list(
                program_list.get(
                    0,
                    tk.END))
            session["name"] = new_name
            session["programs"] = programs
            # If currently selected session was renamed,
            # update timer labels as well.
            if self.current_session_index == index:
                self.timer_title = new_name
                self.update_all_labels()
            save_config(
                self.target_window,
                self.timer_title,
                self.sessions)
            self.create_overview()
            dialog.destroy()
        tk.Button(
            bottom_frame,
            text="Save",
            width=16,
            command=save
        ).grid(
            row=0,
            column=0,
            padx=5)
        tk.Button(
            bottom_frame,
            text="Cancel",
            width=16,
            command=dialog.destroy
        ).grid(
            row=0,
            column=1,
            padx=5)
        name_entry.focus()
    # DELETE SESSION
    def delete_session(
        self,
        index
    ):
        if index < 0 or index >= len(self.sessions):
            return
        session = self.sessions[index]
        name = session.get(
            "name",
            "Unnamed")
        answer = messagebox.askyesno(
            "Delete Session",
            f"Delete session '{name}'?",
            parent=self.root)
        if not answer:
            return
        # If deleting current session
        if self.current_session_index == index:
            # Stop current timer
            if self.tracking:
                self.total_time += (
                    time.time()
                    - self.start_time)
                self.tracking = False
            self.total_time = 0
            self.start_time = 0
            self.current_session_index = None
            self.paused = True
        elif (
            self.current_session_index is not None
            and self.current_session_index > index
        ):
            self.current_session_index -= 1
        del self.sessions[index]
        save_config(
            self.target_window,
            self.timer_title,
            self.sessions)
        self.create_overview()
        self.update_all_labels()
    # START SESSION
    def start_session(
        self,
        index
    ):
        if index < 0 or index >= len(self.sessions):
            return
        # Select session
        self.current_session_index = index
        session = self.get_current_session()
        if not session:
            return
        # Reset timer
        if self.tracking:
            self.total_time += (
                time.time()
                - self.start_time)
            self.tracking = False
        self.total_time = 0
        self.start_time = 0
        self.timer_title = session.get(
            "name",
            "")
        self.paused = False
        self.pause_button.config(
            text="Pause")
        self.label.config(
            text="00:00:00",
            fg="gray")
        save_config(
            self.target_window,
            self.timer_title,
            self.sessions)
        self.update_all_labels()
        # Start programs
        self.start_workspace(
            show_message=True)
        # Go to timer
        self.hide_overview()
    # CURRENT SESSION
    def get_current_session(self):
        if self.current_session_index is None:
            return None
        if (
            self.current_session_index
            >= len(self.sessions)
        ):
            return None
        return self.sessions[
            self.current_session_index
        ]
    # START WORKSPACE
    def start_workspace(
        self,
        show_message=False
    ):
        session = self.get_current_session()
        if not session:
            if show_message:
                messagebox.showinfo(
                    "No Session",
                    (
                        "Please create and select "
                        "a session first."))
            return
        programs = session.get(
            "programs",
            [])
        if not programs:
            if show_message:
                messagebox.showinfo(
                    "No Programs",
                    (
                        f"The session "
                        f"'{session.get('name', '')}' "
                        "does not have any programs "
                        "configured."))
            return
        failed_programs = []
        for program in programs:
            try:
                if not os.path.exists(program):
                    failed_programs.append(
                        f"{program}\n(File not found)")
                    continue
                subprocess.Popen(
                    [program])
            except Exception as e:
                failed_programs.append(
                    f"{program}\n({e})")
        if failed_programs:
            messagebox.showwarning(
                "Some Programs Could Not Be Started",
                ("The following programs "
                    "could not be started:\n\n"
                    + "\n\n".join(
                        failed_programs)))
    # LABELS
    def update_all_labels(self):
        self.update_session_label()
        self.update_target_label()
        self.update_title_label()
    def update_session_label(self):
        session = self.get_current_session()
        if session:
            self.session_label.config(
                text=session.get(
                    "name",
                    "Unnamed"))
        else:
            self.session_label.config(
                text="No Session")
    def update_target_label(self):
        if self.target_window.strip() == "":
            self.target_label.config(
                text=(
                    "Tracking: All Windows "
                    "(Always On)"))
        else:
            self.target_label.config(
                text=(
                    f"Tracking: "
                    f"{self.target_window}"))
    def update_title_label(self):
        self.title_label.config(
            text=(
                self.timer_title
                if self.timer_title.strip()
                else ""))
    # SETTINGS
    def change_target_dialog(self):
        dialog = tk.Toplevel(
            self.root)
        dialog.title(
            "Settings")
        dialog.geometry(
            "300x170")
        dialog.resizable(
            False,
            False)
        tk.Label(
            dialog,
            text="Window title to track:"
        ).pack(
            pady=(10, 0))
        entry_var = tk.StringVar(
            value=self.target_window)
        entry = tk.Entry(
            dialog,
            textvariable=entry_var,
            width=30)
        entry.pack(
            pady=(0, 5))
        check_var = tk.BooleanVar(
            value=(
                self.target_window.strip()
                == ""))
        def toggle_entry():
            entry.config(
                state=(
                    tk.DISABLED
                    if check_var.get()
                    else tk.NORMAL))
        tk.Checkbutton(
            dialog,
            text=(
                "Track all the time "
                "(ignore window)"
            ),
            variable=check_var,
            command=toggle_entry
        ).pack()
        def apply():
            new_target = (
                ""
                if check_var.get()
                else entry_var.get().strip())
            self.target_window = new_target
            save_config(
                self.target_window,
                self.timer_title,
                self.sessions)
            self.update_all_labels()
            dialog.destroy()
        tk.Button(
            dialog,
            text="Save",
            command=apply
        ).pack(
            pady=(15, 10))
        toggle_entry()
        entry.focus()
    # PAUSE
    def toggle_pause(self):
        if self.paused:
            self.paused = False
            if self.should_be_tracking():
                self.start_time = time.time()
                self.tracking = True
                self.label.config(
                    fg="black")
                self.root.title(
                    "Tracking…")
            self.pause_button.config(
                text="Pause")
        else:
            self.pause()
    def pause(self):
        if not self.paused:
            if self.tracking:
                self.total_time += (
                    time.time()
                    - self.start_time)
            self.tracking = False
            self.paused = True
            self.label.config(
                fg="gray")
            self.root.title(
                "Paused (Manual)")
            self.pause_button.config(
                text="Resume")
    # TRACKING CONDITION
    def should_be_tracking(self):
        if self.paused:
            return False
        if self.target_window.strip() == "":
            return True
        return (
            self.target_window.lower()
            in get_active_window_title().lower())
    # TIMER UPDATE
    def update_timer(self):
        if self.should_be_tracking():
            if not self.tracking:
                self.start_time = time.time()
                self.tracking = True
                self.label.config(
                    fg="black")
                self.root.title(
                    "Tracking…")
        else:
            if self.tracking:
                self.total_time += (
                    time.time()
                    - self.start_time)
                self.tracking = False
                self.label.config(
                    fg="gray")
                self.root.title(
                    "Paused")
        total = self.total_time
        if self.tracking:
            total += (
                time.time()
                - self.start_time)
        self.label.config(
            text=format_seconds(total))
        self.root.after(
            CHECK_INTERVAL,
            self.update_timer)
    # SAVE TIME
    def save_time_to_csv(self):
        self.toggle_pause()
        session = self.get_current_session()
        if not session:
            messagebox.showwarning(
                "No Session",
                "Please select a session first.")
            return
        session_name = session.get(
            "name",
            ""
        ).strip()
        if not session_name:
            messagebox.showwarning(
                "Invalid Session",
                "The current session has no name.")
            return
        # Current running time
        if self.tracking:
            elapsed = (
                time.time()
                - self.start_time)
            self.total_time += elapsed
            self.tracking = False
            self.label.config(
                fg="gray")
            self.root.title(
                "Paused")
        if self.total_time <= 0:
            messagebox.showwarning(
                "Nothing to save",
                "There is no time to save.")
            return
        # Date / time
        today_str = (
            datetime.datetime.now()
            .strftime("%d.%m.%Y"))
        new_seconds = int(
            self.total_time)
        # CSV
        rows = []
        fieldnames = []
        with FileLock(LOCK_PATH):
            if os.path.exists(FILE):
                with open(
                    FILE,
                    "r",
                    newline="",
                    encoding="utf-8"
                ) as f:
                    reader = csv.DictReader(f)
                    if reader.fieldnames:
                        fieldnames = list(
                            reader.fieldnames)
                    for row in reader:
                        rows.append(row)
            # Fields
            if "Date" not in fieldnames:
                fieldnames.insert(
                    0,
                    "Date")
            if session_name not in fieldnames:
                fieldnames.append(
                    session_name)
            # Find today's row
            today_row = None
            for row in rows:
                if (
                    row.get(
                        "Date",
                        ""
                    ).strip()
                    == today_str
                ):
                    today_row = row
                    break
            # Create today's row
            if today_row is None:
                today_row = {
                    field: ""
                    for field in fieldnames
                }
                today_row["Date"] = today_str
                today_row[session_name] = (
                    format_seconds(
                        new_seconds))
                rows.append(
                    today_row)
            # Add to existing time
            else:
                previous_time = (
                    today_row.get(
                        session_name,
                        ""
                    ).strip())
                previous_seconds = 0
                if previous_time:
                    try:
                        parts = (
                            previous_time.split(":"))
                        if len(parts) == 3:
                            hours, minutes, seconds = (
                                map(
                                    int,
                                    parts))
                            previous_seconds = (
                                hours * 3600
                                + minutes * 60
                                + seconds
                            )
                    except ValueError:
                        previous_seconds = 0
                total_seconds = (
                    previous_seconds
                    + new_seconds
                )
                today_row[session_name] = (
                    format_seconds(
                        total_seconds))
            # Field order
            ordered_fields = (
                ["Date"]
                + sorted(
                    field
                    for field in fieldnames
                    if field != "Date"
                )
            )
            # Alle Zeilen mit fehlenden Feldern auffüllen
            for row in rows:
                for field in ordered_fields:
                    if field not in row:
                        row[field] = ""
            # Sort by date
            def parse_date(row):
                try:
                    return datetime.datetime.strptime(
                        row.get("Date", ""),
                        "%d.%m.%Y"
                    )
                except ValueError:
                    return datetime.datetime.min
            rows.sort(
                key=parse_date,
                reverse=True)
            # Write CSV
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
                writer.writerows(rows)
        # Reset
        saved_time = format_seconds(
            new_seconds)
        messagebox.showinfo(
            "Saved",
            (
                f"Time saved to {FILE}\n\n"
                f"Session: {session_name}\n"
                f"Date: {today_str}\n"
                f"Added: {saved_time}"
            )
        )
        self.total_time = 0
        self.label.config(text="0:00:00")
    # CLOSE
    def on_close(self):
        self.pause()
        if self.total_time > 0 or self.tracking:
            result = messagebox.askyesnocancel(
                "Close",
                ("Do you want to save the current time before closing?")
            )
            if result is True:
                self.save_time_to_csv()
                self.root.destroy()
            elif result is False:
                self.root.destroy()
            # Cancel -> nichts machen
            return
        # Keine Zeit vorhanden
        self.root.destroy()
# RUN
if __name__ == "__main__":
    root = tk.Tk()
    app = TimeTrackerApp(root)
    root.mainloop()