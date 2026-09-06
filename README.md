# WorkingHoursTimer
Easily document your working hours


## To Do


- Nachfragen ob Zeit speichern wenn es in die Overview geht; in overview the timer does not continue / is totally killed off
- Need a button "Edit programs" when on a timer screen
- Better GUI design
- Don't lose the text in the text field when clicking "Track all the time"

# Overview of changes
- v8
  - Change the Layout of the Program: lost the "Manage Sessions" window and just uses the overview
  - Timer is automatically paused when starting a session
  - Manage saving the sessions so no time will be overwritten (is added instead)
  - Program asks whether time should be saved before closing the program
- v7
  - can now manage multiple sessions, each with their own programs
  - saves are now made under the session name
- v6
  - can now add programs to the config and can start them with a button click
- v5
  - added saving functionality: logs to timelog.csv using the date and title
  - resets the timer after saving
  - if the current date is already in the timelog file, it adds the tracked time to the time in the file
  - adds a filelock so I can run and save multiple instances
- v4
  - Added a pause button
- v3
  - added functionality to the timer so it can run without following a specific window (that is, running all the time)
- v2
  - added functionality so that the user can input the window name its following
- v1
  - simple functionality of a timer running on screen



