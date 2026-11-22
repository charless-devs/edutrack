# EduTrack — Student Academic Performance & Attendance Monitoring

EduTrack is a desktop application built with **Python**, **Tkinter**, and **SQLite**. It gives teachers a
single window to manage students, record daily attendance, log grades, and instantly see which students
are at academic risk.

Everything runs locally — no server, no internet connection, and no external dependencies beyond the
Python standard library.

---

## Table of Contents

- [Features](#features)
- [Screenshots](#screenshots)
- [Requirements](#requirements)
- [Getting Started](#getting-started)
- [How to Use](#how-to-use)
  - [Students Tab](#students-tab)
  - [Attendance Tab](#attendance-tab)
  - [Grades Tab](#grades-tab)
  - [Reports Tab](#reports-tab)
- [Database Schema](#database-schema)
- [Risk Rules](#risk-rules)
- [Project Structure](#project-structure)
- [CSV Export](#csv-export)

---

## Features

- **Student management** — add, update, and delete student records (Student No., Full Name, Section)
- **Daily attendance** — mark students as *Present*, *Absent*, *Late*, or *Excused* for any date
- **Section filtering** — view all students or narrow the list to a single section
- **Bulk marking** — mark every visible student as Present with one click
- **Grade recording** — store scores per subject and assessment, with automatic percentage calculation
- **Live average** — running average of a student's grades updates as records are added or removed
- **At-risk reporting** — automatic flagging of students below the attendance or grade thresholds
- **CSV export** — save the report to a spreadsheet with a single click
- **Local SQLite storage** — data persists in `edutrack.db` next to the script

---

## Screenshots

### Students Tab

Manage the class roster: enter a Student No., Full Name, and Section, then use **Add**, **Update**,
**Delete**, or **Clear**. Clicking a row in the table loads that student into the form.

![Students Tab](Screenshot%202026-11-22%20214701.png)

### Attendance Tab

Pick a date and an optional section, press **Load**, then select students and mark their status.
The **Mark ALL shown as Present** button speeds up full-class check-in.

![Attendance Tab](Screenshot%202026-11-22%20214727.png)

### Grades Tab

Choose a student from the dropdown, enter the subject, assessment, score, and max score, then press
**Add Grade**. The percentage is calculated automatically and the overall average is shown at the
bottom.

![Grades Tab](Screenshot%202026-11-22%20214813.png)

### Reports Tab

A consolidated view of every student's attendance percentage and average grade. Students who fall
below the thresholds are highlighted in red and marked **At Risk**.

![Reports Tab](Screenshot%202026-11-22%20214757.png)

---

## Requirements

- Python **3.8 or newer** (Tkinter is included with the standard Python installer on Windows)
- No third-party packages are required

To confirm Tkinter is available:

```bash
python -c "import tkinter; print(tkinter.TkVersion)"
```

---

## Getting Started

1. Clone or download this folder.

2. Run the application:

   ```bash
   python test.py
   ```

3. The database file `edutrack.db` is created automatically on first launch. All tables
   (`students`, `attendance`, `grades`) are created if they do not already exist.

---

## How to Use

### Students Tab

1. Fill in **Student No.**, **Full Name**, and **Section**.
2. Click **Add** to save the student.
3. Click a row in the table to load an existing student, edit the fields, then click **Update**.
4. Click **Delete** to remove the selected student — all of their attendance and grade records are
   deleted with them (cascade delete).
5. Click **Clear** to reset the form.

> A Student No. must be unique. Attempting to add or update with a duplicate number shows an error.

### Attendance Tab

1. Enter the date in `YYYY-MM-DD` format (today's date is pre-filled).
2. Optionally choose a **Section** from the dropdown, or leave it on *All*.
3. Click **Load** (or press **Enter**) to refresh the list.
4. Select one or more rows — hold **Ctrl**/**Shift** for multiple selection.
5. Click **Present**, **Absent**, **Late**, or **Excused** to mark the selected students.
6. Click **Mark ALL shown as Present** to mark every student currently displayed.

Marking is an upsert: re-marking the same student on the same date simply overwrites the previous
status, so no duplicate records are created.

### Grades Tab

1. Pick a student from the **Student** dropdown.
2. Enter the **Subject**, **Assessment**, **Score**, and **Max Score** (defaults to 100).
3. Click **Add Grade**. The record appears in the table with its percentage.
4. Select rows in the table and click **Delete Selected** to remove them.
5. The **Average** label at the bottom always reflects the currently selected student's grades.

Validation rules:

- Score must be a number ≥ 0
- Max Score must be > 0
- Subject and Assessment are both required

### Reports Tab

1. Click **Refresh** to recompute the report (it also refreshes automatically when you switch tabs).
2. Each row shows the student's **Attendance %** and **Average Grade %**.
3. Students marked **At Risk** are highlighted with a light red background.
4. Click **Export to CSV** to save the report.

---

## Database Schema

The SQLite database (`edutrack.db`) contains three tables:

```sql
students (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_no  TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    section     TEXT NOT NULL
);

attendance (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id  INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    date        TEXT NOT NULL,          -- YYYY-MM-DD
    status      TEXT NOT NULL,          -- Present | Absent | Late | Excused
    UNIQUE(student_id, date)            -- one record per student per day
);

grades (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id  INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    subject     TEXT NOT NULL,
    assessment  TEXT NOT NULL,
    score       REAL NOT NULL,
    max_score   REAL NOT NULL
);
```

Notes:

- `PRAGMA foreign_keys = ON` is enabled, so deleting a student removes their attendance and grades.
- The `UNIQUE(student_id, date)` constraint guarantees one attendance entry per student per day.

---

## Risk Rules

Defined as constants at the top of `test.py`:

```python
MIN_ATTENDANCE = 80.0  # % below this = at risk
MIN_GRADE = 75.0       # % below this = at risk
```

| Metric          | Calculation                                                              | At Risk when |
| --------------- | ------------------------------------------------------------------------ | ------------ |
| Attendance %    | (Present + Late) ÷ (all statuses except Excused) × 100                   | < 80%        |
| Average Grade % | average of (score ÷ max_score × 100) across all of the student's grades  | < 75%        |

A student is flagged **At Risk** if *either* condition is true. **Excused** absences are excluded
from the attendance denominator so they do not penalize the student, while **Late** counts as
attended.

---

## Project Structure

```
tonio2/
├── test.py                        # Main application (UI + database logic)
├── edutrack.db                    # SQLite database (created on first run)
├── README.md                      # This file
└── Screenshot 2026-11-22 *.png    # UI screenshots used above
```

### Code Overview

| Section in `test.py`   | Purpose                                                            |
| ---------------------- | ------------------------------------------------------------------ |
| `DB` class             | Connection handling, table creation, and `q()` / `x()` query helpers |
| `EduTrack.__init__`    | Window setup and the four-tab `ttk.Notebook`                        |
| `build_students` / `refresh_students` | Student form and roster table             |
| `build_attendance` / `refresh_attendance` / `mark` | Date/section filters and status marking |
| `build_grades` / `refresh_grades` / `add_grade`   | Grade entry, percentages, and average     |
| `build_reports` / `refresh_reports` / `export_csv`| At-risk report and CSV export             |
| `refresh_all`          | Refreshes every tab (also fired on tab change)                      |

---

## CSV Export

**Export to CSV** on the Reports tab writes a file named `edutrack_report_YYYY-MM-DD.csv` with the
columns:

```
Student No., Name, Section, Attendance %, Average Grade %, Status
```

The file opens directly in Excel, Google Sheets, or LibreOffice Calc.
