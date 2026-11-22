import csv
import os
import sqlite3
import tkinter as tk
from datetime import date, datetime
from tkinter import filedialog, messagebox, ttk

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "edutrack.db")
STATUSES = ["Present", "Absent", "Late", "Excused"]
MIN_ATTENDANCE = 80.0  # % below this = at risk
MIN_GRADE = 75.0       # % below this = at risk


class DB:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS students(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_no TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                section TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS attendance(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                date TEXT NOT NULL,
                status TEXT NOT NULL,
                UNIQUE(student_id, date)
            );
            CREATE TABLE IF NOT EXISTS grades(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
                subject TEXT NOT NULL,
                assessment TEXT NOT NULL,
                score REAL NOT NULL,
                max_score REAL NOT NULL
            );
            """
        )
        self.conn.commit()

    def q(self, sql, args=()):
        return self.conn.execute(sql, args).fetchall()

    def x(self, sql, args=()):
        cur = self.conn.execute(sql, args)
        self.conn.commit()
        return cur


class EduTrack(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("EduTrack - Student Academic Performance & Attendance Monitoring")
        self.geometry("980x600")
        self.minsize(900, 540)
        self.db = DB(DB_PATH)
        self.sel_student_id = None

        ttk.Style(self).theme_use("clam")
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=8, pady=8)

        self.tab_students = ttk.Frame(self.nb)
        self.tab_att = ttk.Frame(self.nb)
        self.tab_grades = ttk.Frame(self.nb)
        self.tab_report = ttk.Frame(self.nb)
        self.nb.add(self.tab_students, text="  Students  ")
        self.nb.add(self.tab_att, text="  Attendance  ")
        self.nb.add(self.tab_grades, text="  Grades  ")
        self.nb.add(self.tab_report, text="  Reports  ")

        self.build_students()
        self.build_attendance()
        self.build_grades()
        self.build_reports()
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self.refresh_all())
        self.refresh_all()

    # ---------- helpers ----------
    @staticmethod
    def make_tree(parent, cols, widths, height=14):
        frame = ttk.Frame(parent)
        tree = ttk.Treeview(frame, columns=cols, show="headings", height=height)
        for c, w in zip(cols, widths):
            tree.heading(c, text=c)
            tree.column(c, width=w, anchor="w")
        sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        return frame, tree

    def sections(self):
        return [r[0] for r in self.db.q("SELECT DISTINCT section FROM students ORDER BY section")]

    # ---------- Students tab ----------
    def build_students(self):
        t = self.tab_students
        form = ttk.LabelFrame(t, text="Student Information")
        form.pack(fill="x", padx=8, pady=8)
        self.v_no, self.v_name, self.v_sec = tk.StringVar(), tk.StringVar(), tk.StringVar()
        for i, (lbl, var) in enumerate(
            [("Student No.", self.v_no), ("Full Name", self.v_name), ("Section", self.v_sec)]
        ):
            ttk.Label(form, text=lbl).grid(row=0, column=i * 2, padx=6, pady=8, sticky="e")
            ttk.Entry(form, textvariable=var, width=22).grid(row=0, column=i * 2 + 1, padx=6)
        bar = ttk.Frame(form)
        bar.grid(row=1, column=0, columnspan=6, pady=(0, 8))
        for text, cmd in [("Add", self.add_student), ("Update", self.update_student),
                          ("Delete", self.delete_student), ("Clear", self.clear_student_form)]:
            ttk.Button(bar, text=text, command=cmd).pack(side="left", padx=4)

        frame, self.tree_students = self.make_tree(
            t, ("ID", "Student No.", "Name", "Section"), (50, 140, 380, 160))
        frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.tree_students.bind("<<TreeviewSelect>>", self.on_student_select)

    def refresh_students(self):
        self.tree_students.delete(*self.tree_students.get_children())
        for r in self.db.q("SELECT id, student_no, name, section FROM students ORDER BY name"):
            self.tree_students.insert("", "end", values=r)

    def clear_student_form(self):
        self.sel_student_id = None
        self.v_no.set(""); self.v_name.set(""); self.v_sec.set("")
        self.tree_students.selection_remove(self.tree_students.selection())

    def on_student_select(self, _e=None):
        sel = self.tree_students.selection()
        if not sel:
            return
        sid, no, name, sec = self.tree_students.item(sel[0], "values")
        self.sel_student_id = int(sid)
        self.v_no.set(no); self.v_name.set(name); self.v_sec.set(sec)

    def _student_fields(self):
        no, name, sec = self.v_no.get().strip(), self.v_name.get().strip(), self.v_sec.get().strip()
        if not (no and name and sec):
            messagebox.showwarning("Missing data", "Please fill in all fields.")
            return None
        return no, name, sec

    def add_student(self):
        f = self._student_fields()
        if not f:
            return
        try:
            self.db.x("INSERT INTO students(student_no, name, section) VALUES(?,?,?)", f)
        except sqlite3.IntegrityError:
            messagebox.showerror("Duplicate", "That Student No. already exists.")
            return
        self.clear_student_form(); self.refresh_all()

    def update_student(self):
        if self.sel_student_id is None:
            messagebox.showinfo("Select", "Select a student from the list first.")
            return
        f = self._student_fields()
        if not f:
            return
        try:
            self.db.x("UPDATE students SET student_no=?, name=?, section=? WHERE id=?",
                      (*f, self.sel_student_id))
        except sqlite3.IntegrityError:
            messagebox.showerror("Duplicate", "That Student No. already exists.")
            return
        self.clear_student_form(); self.refresh_all()

    def delete_student(self):
        if self.sel_student_id is None:
            messagebox.showinfo("Select", "Select a student from the list first.")
            return
        if messagebox.askyesno("Confirm", "Delete this student and all their records?"):
            self.db.x("DELETE FROM students WHERE id=?", (self.sel_student_id,))
            self.clear_student_form(); self.refresh_all()

    # ---------- Attendance tab ----------
    def build_attendance(self):
        t = self.tab_att
        top = ttk.Frame(t)
        top.pack(fill="x", padx=8, pady=8)
        ttk.Label(top, text="Date (YYYY-MM-DD)").pack(side="left", padx=4)
        self.v_date = tk.StringVar(value=date.today().isoformat())
        e = ttk.Entry(top, textvariable=self.v_date, width=12)
        e.pack(side="left", padx=4)
        e.bind("<Return>", lambda ev: self.refresh_attendance())
        ttk.Label(top, text="Section").pack(side="left", padx=(16, 4))
        self.v_att_sec = tk.StringVar(value="All")
        self.cb_att_sec = ttk.Combobox(top, textvariable=self.v_att_sec, width=16, state="readonly")
        self.cb_att_sec.pack(side="left", padx=4)
        self.cb_att_sec.bind("<<ComboboxSelected>>", lambda ev: self.refresh_attendance())
        ttk.Button(top, text="Load", command=self.refresh_attendance).pack(side="left", padx=8)

        frame, self.tree_att = self.make_tree(
            t, ("ID", "Student No.", "Name", "Section", "Status"), (50, 130, 320, 140, 120))
        frame.pack(fill="both", expand=True, padx=8)
        self.tree_att.configure(selectmode="extended")

        bar = ttk.LabelFrame(t, text="Mark selected students as")
        bar.pack(fill="x", padx=8, pady=8)
        for s in STATUSES:
            ttk.Button(bar, text=s, command=lambda s=s: self.mark(s)).pack(side="left", padx=6, pady=6)
        ttk.Button(bar, text="Mark ALL shown as Present",
                   command=lambda: self.mark("Present", all_rows=True)).pack(side="right", padx=6)

    def _valid_date(self):
        try:
            return datetime.strptime(self.v_date.get().strip(), "%Y-%m-%d").date().isoformat()
        except ValueError:
            messagebox.showerror("Invalid date", "Use the format YYYY-MM-DD.")
            return None

    def refresh_attendance(self):
        secs = ["All"] + self.sections()
        self.cb_att_sec["values"] = secs
        if self.v_att_sec.get() not in secs:
            self.v_att_sec.set("All")
        d = self._valid_date()
        if not d:
            return
        sql = ("SELECT s.id, s.student_no, s.name, s.section, COALESCE(a.status, '-') "
               "FROM students s LEFT JOIN attendance a ON a.student_id=s.id AND a.date=? ")
        args = [d]
        if self.v_att_sec.get() != "All":
            sql += "WHERE s.section=? "
            args.append(self.v_att_sec.get())
        sql += "ORDER BY s.name"
        self.tree_att.delete(*self.tree_att.get_children())
        for r in self.db.q(sql, args):
            self.tree_att.insert("", "end", values=r)

    def mark(self, status, all_rows=False):
        d = self._valid_date()
        if not d:
            return
        items = self.tree_att.get_children() if all_rows else self.tree_att.selection()
        if not items:
            messagebox.showinfo("Select", "Select one or more students first.")
            return
        for it in items:
            sid = int(self.tree_att.item(it, "values")[0])
            self.db.conn.execute(
                "INSERT INTO attendance(student_id, date, status) VALUES(?,?,?) "
                "ON CONFLICT(student_id, date) DO UPDATE SET status=excluded.status",
                (sid, d, status))
        self.db.conn.commit()
        self.refresh_attendance()

    # ---------- Grades tab ----------
    def build_grades(self):
        t = self.tab_grades
        form = ttk.LabelFrame(t, text="Record a Grade")
        form.pack(fill="x", padx=8, pady=8)
        self.v_g_student = tk.StringVar()
        self.v_g_subject, self.v_g_assess = tk.StringVar(), tk.StringVar()
        self.v_g_score, self.v_g_max = tk.StringVar(), tk.StringVar(value="100")

        ttk.Label(form, text="Student").grid(row=0, column=0, padx=6, pady=6, sticky="e")
        self.cb_g_student = ttk.Combobox(form, textvariable=self.v_g_student, width=34, state="readonly")
        self.cb_g_student.grid(row=0, column=1, columnspan=3, padx=6, sticky="w")
        self.cb_g_student.bind("<<ComboboxSelected>>", lambda e: self.refresh_grades())
        ttk.Label(form, text="Subject").grid(row=1, column=0, padx=6, pady=6, sticky="e")
        ttk.Entry(form, textvariable=self.v_g_subject, width=20).grid(row=1, column=1, padx=6)
        ttk.Label(form, text="Assessment").grid(row=1, column=2, padx=6, sticky="e")
        ttk.Entry(form, textvariable=self.v_g_assess, width=20).grid(row=1, column=3, padx=6)
        ttk.Label(form, text="Score").grid(row=2, column=0, padx=6, pady=6, sticky="e")
        ttk.Entry(form, textvariable=self.v_g_score, width=10).grid(row=2, column=1, padx=6, sticky="w")
        ttk.Label(form, text="Max Score").grid(row=2, column=2, padx=6, sticky="e")
        ttk.Entry(form, textvariable=self.v_g_max, width=10).grid(row=2, column=3, padx=6, sticky="w")
        ttk.Button(form, text="Add Grade", command=self.add_grade).grid(row=2, column=4, padx=10)
        ttk.Button(form, text="Delete Selected", command=self.delete_grade).grid(row=2, column=5, padx=4)

        frame, self.tree_grades = self.make_tree(
            t, ("ID", "Subject", "Assessment", "Score", "Max", "Percent"),
            (50, 200, 220, 90, 90, 100))
        frame.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        self.lbl_avg = ttk.Label(t, text="Average: -", font=("TkDefaultFont", 10, "bold"))
        self.lbl_avg.pack(anchor="w", padx=12, pady=(0, 8))
        self.grade_students = {}

    def refresh_grades_students(self):
        rows = self.db.q("SELECT id, student_no, name FROM students ORDER BY name")
        self.grade_students = {f"{no} - {name}": sid for sid, no, name in rows}
        self.cb_g_student["values"] = list(self.grade_students)
        if self.v_g_student.get() not in self.grade_students:
            self.v_g_student.set("")

    def refresh_grades(self):
        self.tree_grades.delete(*self.tree_grades.get_children())
        sid = self.grade_students.get(self.v_g_student.get())
        if sid is None:
            self.lbl_avg.config(text="Average: -")
            return
        pcts = []
        for gid, subj, asm, sc, mx in self.db.q(
                "SELECT id, subject, assessment, score, max_score FROM grades "
                "WHERE student_id=? ORDER BY id DESC", (sid,)):
            pct = sc / mx * 100
            pcts.append(pct)
            self.tree_grades.insert("", "end", values=(gid, subj, asm, f"{sc:g}", f"{mx:g}", f"{pct:.1f}%"))
        avg = f"{sum(pcts) / len(pcts):.1f}%" if pcts else "-"
        self.lbl_avg.config(text=f"Average: {avg}")

    def add_grade(self):
        sid = self.grade_students.get(self.v_g_student.get())
        if sid is None:
            messagebox.showwarning("Select", "Choose a student first.")
            return
        subj, asm = self.v_g_subject.get().strip(), self.v_g_assess.get().strip()
        try:
            sc, mx = float(self.v_g_score.get()), float(self.v_g_max.get())
            assert mx > 0 and sc >= 0
        except (ValueError, AssertionError):
            messagebox.showerror("Invalid", "Score must be a number >= 0 and Max Score > 0.")
            return
        if not (subj and asm):
            messagebox.showwarning("Missing data", "Enter subject and assessment.")
            return
        self.db.x("INSERT INTO grades(student_id, subject, assessment, score, max_score) "
                  "VALUES(?,?,?,?,?)", (sid, subj, asm, sc, mx))
        self.v_g_score.set("")
        self.refresh_grades()

    def delete_grade(self):
        sel = self.tree_grades.selection()
        if not sel:
            return
        for it in sel:
            self.db.conn.execute("DELETE FROM grades WHERE id=?",
                                 (int(self.tree_grades.item(it, "values")[0]),))
        self.db.conn.commit()
        self.refresh_grades()

    # ---------- Reports tab ----------
    def build_reports(self):
        t = self.tab_report
        top = ttk.Frame(t)
        top.pack(fill="x", padx=8, pady=8)
        ttk.Button(top, text="Refresh", command=self.refresh_reports).pack(side="left", padx=4)
        ttk.Button(top, text="Export to CSV", command=self.export_csv).pack(side="left", padx=4)
        ttk.Label(top, text=f"At Risk = attendance < {MIN_ATTENDANCE:g}% or average < {MIN_GRADE:g}%").pack(
            side="right", padx=8)
        frame, self.tree_rep = self.make_tree(
            t, ("Student No.", "Name", "Section", "Attendance %", "Average Grade %", "Status"),
            (120, 280, 120, 110, 130, 100))
        frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.tree_rep.tag_configure("risk", background="#fde0e0")
        self.report_rows = []

    def refresh_reports(self):
        self.tree_rep.delete(*self.tree_rep.get_children())
        self.report_rows = []
        rows = self.db.q(
            "SELECT s.student_no, s.name, s.section, "
            "(SELECT COUNT(*) FROM attendance a WHERE a.student_id=s.id AND a.status IN ('Present','Late')), "
            "(SELECT COUNT(*) FROM attendance a WHERE a.student_id=s.id AND a.status!='Excused'), "
            "(SELECT AVG(score*100.0/max_score) FROM grades g WHERE g.student_id=s.id) "
            "FROM students s ORDER BY s.name")
        for no, name, sec, attended, total, avg in rows:
            att = attended / total * 100 if total else None
            risk = (att is not None and att < MIN_ATTENDANCE) or (avg is not None and avg < MIN_GRADE)
            vals = (no, name, sec,
                    f"{att:.1f}" if att is not None else "-",
                    f"{avg:.1f}" if avg is not None else "-",
                    "At Risk" if risk else "Good")
            self.report_rows.append(vals)
            self.tree_rep.insert("", "end", values=vals, tags=("risk",) if risk else ())

    def export_csv(self):
        if not self.report_rows:
            messagebox.showinfo("Nothing to export", "No data in the report.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV files", "*.csv")],
            initialfile=f"edutrack_report_{date.today().isoformat()}.csv")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Student No.", "Name", "Section", "Attendance %", "Average Grade %", "Status"])
            w.writerows(self.report_rows)
        messagebox.showinfo("Exported", f"Saved to:\n{path}")

    # ---------- refresh ----------
    def refresh_all(self):
        self.refresh_students()
        self.refresh_attendance()
        self.refresh_grades_students()
        self.refresh_grades()
        self.refresh_reports()


if __name__ == "__main__":
    app = EduTrack()
    app.mainloop()