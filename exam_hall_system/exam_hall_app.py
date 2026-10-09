"""
College Exam Hall Management System — Faculty Edition
=====================================================
A friendly desktop tool for college staff to plan and run exams.

Features:
  • Bulk import students from CSV
  • Interleave departments (prevents copying)
  • Department-aware invigilator assignment
  • Hall calculator
  • Visual hall layout with colour coding
  • Printable seat slips (one per desk)
  • Master report printout

No technical knowledge required. Every screen explains itself.
"""

# ============================================================
#  IMPORTS
# ============================================================
import os
import csv
import math
import tempfile
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime


# ============================================================
#  DATA STORE
# ============================================================
class Store:
    def __init__(self):
        self.exam = {
            "name": "Mid-Semester Exam 2025",
            "department": "All Departments",
            "date": datetime.now().strftime("%d %b %Y"),
            "time": "10:00 AM",
            "duration": "3 hours",
        }
        self.students = []       # {id, seat, name, dept, hall, status}
        self.invigilators = []   # {id, name, dept, priority, hall, status}
        self.halls = []          # {id, name, capacity, filled, status}
        self.files = []          # {id, name, dept, start, size}
        self.folders = {
            "Computer":   ["SeatingPlan.pdf", "StudentList.csv"],
            "Mechanical": ["SeatingPlan.pdf", "StudentList.csv"],
            "Civil":      ["SeatingPlan.pdf", "StudentList.csv"],
        }
        self.last_deadlock = None
        self._bitmap = [0] * 64

        self._pid = 1
        self._tid = 1
        self._hid = 1
        self._fid = 1

    def new_pid(self):
        v = self._pid; self._pid += 1; return v

    def new_tid(self):
        v = self._tid; self._tid += 1; return v

    def new_hid(self):
        v = self._hid; self._hid += 1; return v

    def new_fid(self):
        v = self._fid; self._fid += 1; return v


STORE = Store()


# ============================================================
#  SAMPLE DATA  —  3 tiers: small / medium / large
# ============================================================
_FIRST_NAMES = [
    "Aarav", "Aditi", "Advait", "Aishwarya", "Akash", "Ananya",
    "Aniket", "Anjali", "Arjun", "Avni", "Bhavya", "Bhoomi",
    "Chaitanya", "Charvi", "Darsh", "Devika", "Dhruv", "Diya",
    "Ekta", "Eshan", "Farhan", "Gauri", "Gaurav", "Harsha",
    "Hemant", "Ishaan", "Ishita", "Jayesh", "Jhanvi", "Jiya",
    "Kabir", "Kanika", "Karan", "Kavya", "Khushi", "Kiaan",
    "Krish", "Kritika", "Lakshya", "Lavanya", "Madhav", "Mahi",
    "Manav", "Manish", "Meera", "Mihir", "Mira", "Mohit",
    "Mrunal", "Naina", "Nakul", "Nandini", "Naveen", "Neha",
    "Nikhil", "Nisha", "Nitya", "Ojas", "Omkar", "Pallavi",
    "Parth", "Pooja", "Pranav", "Pranjal", "Pratik", "Priyanka",
    "Purva", "Rachit", "Rahul", "Rajvi", "Rakesh", "Rashi",
    "Ravi", "Riya", "Rohit", "Rohini", "Rudra", "Saanvi",
    "Sahil", "Sakshi", "Samarth", "Sanika", "Sanskar", "Sara",
    "Sarthak", "Sejal", "Shanaya", "Shashwat", "Shreya", "Siddharth",
    "Simran", "Sneha", "Soham", "Sonal", "Sourav", "Sparsh",
    "Sruthi", "Subodh", "Suhani", "Suresh", "Suyash", "Swara",
]
_LAST_NAMES = [
    "Sharma", "Desai", "Joshi", "Nair", "Reddy", "Iyer",
    "Kulkarni", "Menon", "Bhatt", "Kapoor", "Patel", "Shah",
    "Rao", "Sinha", "Mehta", "Pillai", "Verma", "Ghosh",
    "Saxena", "Trivedi", "Sheikh", "Mishra", "Pandey", "Kumar",
    "Yadav", "Dutta", "Choksi", "Bose", "Agarwal", "Malhotra",
]
_DEPARTMENTS = ["Computer", "Mechanical", "Civil", "Electronics"]
_DEPT_LETTERS = {"Computer": "A", "Mechanical": "B",
                 "Civil": "C", "Electronics": "D"}


# --- Sample dataset presets ------------------------------------
SAMPLE_PRESETS = {
    "Small (quick demo)": {
        "students": 12,
        "halls": [("Hall A", 5), ("Hall B", 4), ("Hall C", 5)],
        "invigilators": 5,
    },
    "Medium (realistic)": {
        "students": 120,
        "halls": [("Hall A", 40), ("Hall B", 40),
                  ("Hall C", 40)],
        "invigilators": 12,
    },
    "Large (stress test)": {
        "students": 300,
        "halls": [("Hall A", 60), ("Hall B", 60), ("Hall C", 60),
                  ("Hall D", 60), ("Hall E", 60)],
        "invigilators": 20,
    },
}


def _random_name(used):
    """Return a name not already in `used` (falls back to a suffix)."""
    import random
    for _ in range(200):
        n = f"{random.choice(_FIRST_NAMES)} {random.choice(_LAST_NAMES)}"
        if n not in used:
            used.add(n)
            return n
    n = f"{random.choice(_FIRST_NAMES)} {random.choice(_LAST_NAMES)} " \
        f"{len(used)+1}"
    used.add(n)
    return n


def load_sample_data(preset="Medium (realistic)"):
    """
    Load a preset sample dataset.
    preset: one of the keys in SAMPLE_PRESETS.
    """
    import random
    random.seed(42)  # reproducible

    cfg = SAMPLE_PRESETS[preset]
    n_students = cfg["students"]
    halls_spec = cfg["halls"]
    n_inv = cfg["invigilators"]

    # Clear existing data
    STORE.students.clear()
    STORE.invigilators.clear()
    STORE.halls.clear()
    STORE.files.clear()
    for i in range(len(STORE._bitmap)):
        STORE._bitmap[i] = 0

    STORE._pid = 1
    STORE._tid = 1
    STORE._hid = 1
    STORE._fid = 1

    # --- Students (balanced across departments) ---
    used_names = set()
    counters = {d: 1 for d in _DEPARTMENTS}
    depts_cycle = list(_DEPARTMENTS)

    for i in range(n_students):
        dept = depts_cycle[i % len(depts_cycle)]
        seat = f"{_DEPT_LETTERS[dept]}{counters[dept]:03d}"
        counters[dept] += 1
        name = _random_name(used_names)
        STORE.students.append({
            "id": STORE.new_pid(), "seat": seat, "name": name,
            "dept": dept, "hall": "—", "status": "Waiting"
        })

    # --- Halls ---
    for hname, cap in halls_spec:
        STORE.halls.append({
            "id": STORE.new_hid(), "name": hname, "capacity": cap,
            "filled": 0, "status": "Empty"
        })

    # --- Invigilators ---
    titles = ["Prof.", "Dr.", "Mr.", "Ms.", "Mrs."]
    priorities = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6,
                  7, 7, 8, 8, 9, 9, 10, 10]
    for i in range(n_inv):
        t = titles[i % len(titles)]
        name = f"{t} {_random_name(used_names)}"
        dept = depts_cycle[i % len(depts_cycle)]
        prio = priorities[i % len(priorities)]
        STORE.invigilators.append({
            "id": STORE.new_tid(), "name": name, "dept": dept,
            "priority": prio, "hall": "—", "status": "Available"
        })

    # --- Rename the exam ---
    STORE.exam["name"] = f"Mid-Semester Exam 2025 ({preset.split()[0]})"
    STORE.exam["department"] = "All Departments"
    STORE.exam["date"] = datetime.now().strftime("%d %b %Y")
    STORE.exam["time"] = "10:00 AM"

# ============================================================
#  ALGORITHMS
# ============================================================
def load_demo_data():
    """Alias kept for backwards compatibility — loads Medium preset."""
    load_sample_data("Medium (realistic)")

def do_fcfs_allocation(interleave=False):
    """
    Assign each student in arrival order to the first hall with space.
    If interleave=True, round-robin across departments so that neighbours
    are from different departments (helps prevent copying).
    """
    for h in STORE.halls:
        h["filled"] = 0
        h["status"] = "Empty"
    for s in STORE.students:
        s["hall"] = "—"
        s["status"] = "Waiting"

    if interleave:
        by_dept = {}
        for s in STORE.students:
            by_dept.setdefault(s["dept"], []).append(s)
        ordered = []
        dept_lists = list(by_dept.values())
        while any(dept_lists):
            for lst in dept_lists:
                if lst:
                    ordered.append(lst.pop(0))
    else:
        ordered = list(STORE.students)

    placed, waiting = 0, 0
    for s in ordered:
        placed_here = False
        for h in STORE.halls:
            if h["filled"] < h["capacity"]:
                h["filled"] += 1
                s["hall"] = h["name"]
                s["status"] = "Seated"
                if h["filled"] >= h["capacity"]:
                    h["status"] = "Full"
                else:
                    h["status"] = "In use"
                placed += 1
                placed_here = True
                break
        if not placed_here:
            s["status"] = "No space"
            waiting += 1
    return placed, waiting


def do_priority_assignment(match_department=False):
    """
    Assign highest-priority invigilator to each hall that has students.
    If match_department=True, prefer an invigilator whose department is
    NOT the majority department in that hall.
    """
    for t in STORE.invigilators:
        t["hall"] = "—"
        t["status"] = "Available"

    active_halls = [h for h in STORE.halls if h["filled"] > 0]
    pool = sorted(STORE.invigilators, key=lambda x: (x["priority"], x["id"]))

    assigned = 0
    for hall in active_halls:
        if not pool:
            break

        chosen = None
        if match_department:
            depts_here = [s["dept"] for s in STORE.students
                          if s["hall"] == hall["name"]]
            majority = max(set(depts_here), key=depts_here.count) \
                if depts_here else None
            for i, inv in enumerate(pool):
                if inv["dept"] != majority:
                    chosen = pool.pop(i)
                    break

        if chosen is None:
            chosen = pool.pop(0)

        chosen["hall"] = hall["name"]
        chosen["status"] = "On duty"
        assigned += 1

    for t in pool:
        t["status"] = "Not needed"
    return assigned, len(active_halls)


def check_conflicts():
    """Simplified deadlock check in plain language."""
    conflicts = []
    seats_needed = len([s for s in STORE.students
                        if s["status"] != "Seated"])
    total_free = sum(h["capacity"] - h["filled"] for h in STORE.halls)

    hall_map = {}
    for t in STORE.invigilators:
        if t["hall"] != "—":
            hall_map.setdefault(t["hall"], []).append(t["name"])
    for hall, names in hall_map.items():
        if len(names) > 1:
            conflicts.append(
                f"Hall {hall} has {len(names)} invigilators assigned "
                f"({', '.join(names)})."
            )

    if seats_needed > 0 and total_free == 0:
        conflicts.append(
            f"{seats_needed} student(s) have no seat because all "
            f"halls are full."
        )

    STORE.last_deadlock = {
        "conflicts": conflicts,
        "seats_needed": seats_needed,
        "total_free": total_free,
        "checked_at": datetime.now().strftime("%d %b %Y, %H:%M"),
    }
    return conflicts


# ============================================================
#  GUI HELPERS
# ============================================================
GREEN = "#0f8a3c"
AMBER = "#c77700"
RED   = "#c62828"
BLUE  = "#1f3a5f"
LIGHT = "#f0f2f5"


def friendly_banner(parent, title, subtitle, emoji="🎓"):
    box = tk.Frame(parent, bg=LIGHT)
    box.pack(fill="x", pady=(0, 10))
    tk.Label(box, text=f"{emoji}  {title}", bg=LIGHT, fg=BLUE,
             font=("Segoe UI", 16, "bold")).pack(anchor="w")
    tk.Label(box, text=subtitle, bg=LIGHT, fg="#556677",
             font=("Segoe UI", 10), wraplength=900,
             justify="left").pack(anchor="w")


def big_button(parent, text, command, color=BLUE):
    return tk.Button(parent, text=text, command=command,
                     bg=color, fg="white", activebackground=color,
                     font=("Segoe UI", 11, "bold"),
                     padx=18, pady=10, bd=0, cursor="hand2",
                     relief="flat")


def card(parent, title=None):
    outer = tk.Frame(parent, bg="white", highlightthickness=1,
                     highlightbackground="#dde3ea")
    outer.pack(fill="x", pady=6)
    if title:
        tk.Label(outer, text=title, bg="white", fg=BLUE,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w",
                                                     padx=14, pady=(10, 4))
    return outer


def stat_badge(parent, label, value, color=BLUE):
    f = tk.Frame(parent, bg="white")
    tk.Label(f, text=str(value), bg="white", fg=color,
             font=("Segoe UI", 22, "bold")).pack()
    tk.Label(f, text=label, bg="white", fg="#666",
             font=("Segoe UI", 9)).pack()
    return f


# ============================================================
#  MAIN APP
# ============================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Exam Hall Manager — Faculty Edition")
        self.geometry("1180x760")
        self.configure(bg=LIGHT)
        self.minsize(1000, 640)
        self._styles()
        self._layout()
        self.show("home")

    def _styles(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure("Treeview", rowheight=26, font=("Segoe UI", 10))
        s.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"),
                    background="#eef2f7")
        s.configure("TButton", padding=6, font=("Segoe UI", 10))
        s.configure("TLabel", background=LIGHT, font=("Segoe UI", 10))
        s.configure("TEntry", padding=4)

    def _layout(self):
        side = tk.Frame(self, bg=BLUE, width=240)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        tk.Label(side, text="🎓", bg=BLUE, fg="white",
                 font=("Segoe UI", 30)).pack(pady=(18, 0))
        tk.Label(side, text="Exam Hall Manager", bg=BLUE, fg="white",
                 font=("Segoe UI", 12, "bold")).pack()
        tk.Label(side, text="Faculty Edition", bg=BLUE, fg="#b8c7dc",
                 font=("Segoe UI", 9)).pack(pady=(0, 18))

        self.nav = {}
        menu = [
            ("🏠  Home",                "home"),
            ("🧭  Set Up New Exam",     "wizard"),
            ("👥  Students",            "students"),
            ("🏛️  Exam Halls",          "halls"),
            ("🪑  Assign Seats",        "seats"),
            ("👨‍🏫  Assign Invigilators", "invig"),
            ("🗺️  Hall Layout",         "layout"),
            ("🖨️  Print Seat Slips",    "slips"),
            ("⚠️  Check for Issues",    "check"),
            ("💾  Save Seating Files",  "files"),
            ("📁  Department Records",  "dirs"),
            ("📊  Reports",             "reports"),
        ]
        for label, key in menu:
            b = tk.Button(side, text=label, anchor="w", padx=16, pady=9,
                          bg=BLUE, fg="white", bd=0, cursor="hand2",
                          activebackground="#2c5282",
                          font=("Segoe UI", 10),
                          command=lambda k=key: self.show(k))
            b.pack(fill="x")
            b.bind("<Enter>", lambda e, w=b: w.config(bg="#2c5282"))
            b.bind("<Leave>",
                   lambda e, w=b, k=key: w.config(
                       bg="#2c5282"
                       if getattr(self, "current", "") == k else BLUE))
            self.nav[key] = b

        self.body = tk.Frame(self, bg=LIGHT)
        self.body.pack(side="left", fill="both", expand=True,
                       padx=14, pady=12)

        self.status = tk.Label(self, text="", anchor="w",
                               bg="#e1e5ec", fg=BLUE,
                               font=("Segoe UI", 9), padx=12, pady=4)
        self.status.pack(side="bottom", fill="x")

        self.screens = {}
        for key in ["home", "wizard", "students", "halls", "seats",
                    "invig", "layout", "slips", "check", "files",
                    "dirs", "reports"]:
            self.screens[key] = tk.Frame(self.body, bg=LIGHT)

    def show(self, key):
        self.current = key
        for f in self.screens.values():
            f.pack_forget()
        for k, b in self.nav.items():
            b.config(bg="#2c5282" if k == key else BLUE)

        frame = self.screens[key]
        for w in frame.winfo_children():
            w.destroy()
        frame.pack(fill="both", expand=True)

        builder = {
            "home":     self.screen_home,
            "wizard":   self.screen_wizard,
            "students": self.screen_students,
            "halls":    self.screen_halls,
            "seats":    self.screen_seats,
            "invig":    self.screen_invig,
            "layout":   self.screen_layout,
            "slips":    self.screen_slips,
            "check":    self.screen_check,
            "files":    self.screen_files,
            "dirs":     self.screen_dirs,
            "reports":  self.screen_reports,
        }[key]
        builder(frame)
        self._refresh_status()

    def _refresh_status(self):
        seated = sum(1 for s in STORE.students if s["status"] == "Seated")
        self.status.config(
            text=f"  Exam: {STORE.exam['name']}  |  "
                 f"Students: {len(STORE.students)} (seated: {seated})  |  "
                 f"Halls: {len(STORE.halls)}  |  "
                 f"Invigilators: {len(STORE.invigilators)}"
        )

    # ============================================================
    #  HOME
    # ============================================================
    def screen_home(self, parent):
        friendly_banner(parent,
                        f"Welcome — {STORE.exam['name']}",
                        f"{STORE.exam['department']}  •  "
                        f"{STORE.exam['date']} at {STORE.exam['time']}  •  "
                        f"Duration: {STORE.exam['duration']}",
                        "🏠")

        row = tk.Frame(parent, bg=LIGHT)
        row.pack(fill="x", pady=(0, 10))

        seated = sum(1 for s in STORE.students if s["status"] == "Seated")
        waiting = len(STORE.students) - seated
        active_halls = sum(1 for h in STORE.halls if h["filled"] > 0)
        free_halls = len(STORE.halls) - active_halls

        cards = [
            ("Total Students", len(STORE.students), BLUE),
            ("Seated",         seated,              GREEN),
            ("Waiting",        waiting,
             AMBER if waiting else GREEN),
            ("Exam Halls",     len(STORE.halls),    BLUE),
            ("Halls in Use",   active_halls,        BLUE),
            ("Halls Free",     free_halls,          BLUE),
            ("Invigilators",   len(STORE.invigilators), BLUE),
        ]
        for label, val, color in cards:
            c = tk.Frame(row, bg="white", highlightthickness=1,
                         highlightbackground="#dde3ea")
            c.pack(side="left", padx=4, fill="both", expand=True)
            stat_badge(c, label, val, color).pack(pady=10)

        guide = card(parent, "📌  What would you like to do?")
        steps = tk.Frame(guide, bg="white")
        steps.pack(fill="x", padx=14, pady=(0, 12))

        def step(icon, title, desc, target):
            f = tk.Frame(steps, bg="white")
            f.pack(side="left", padx=8, fill="both", expand=True)
            tk.Label(f, text=icon, bg="white",
                     font=("Segoe UI", 22)).pack(anchor="w")
            tk.Label(f, text=title, bg="white", fg=BLUE,
                     font=("Segoe UI", 11, "bold")).pack(anchor="w")
            tk.Label(f, text=desc, bg="white", fg="#556677",
                     wraplength=180, justify="left",
                     font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 8))
            big_button(f, "Open",
                       lambda t=target: self.show(t)).pack(anchor="w")

        step("📥", "Import Students",
             "Bulk-load a CSV file with seat, name and department.",
             "students")
        step("🪑", "Assign Seats",
             "Seat students in halls, with optional department mixing.",
             "seats")
        step("🗺️", "View Hall Layout",
             "Visual grid you can print and stick on the wall.",
             "layout")
        step("🖨️", "Print Seat Slips",
             "One slip per desk — print, cut, stick on the desk.",
             "slips")

        foot = tk.Frame(parent, bg=LIGHT)
        foot.pack(fill="x", pady=(12, 0))
        tk.Label(foot,
                 text="Not sure where to begin? Load a ready-made dataset.",
                 bg=LIGHT, fg="#556677",
                 font=("Segoe UI", 10)).pack(side="left")
        tk.Button(foot, text="📦  Load sample data",
                  bd=0, bg=LIGHT, fg=BLUE, cursor="hand2",
                  font=("Segoe UI", 10, "underline"),
                  command=self._load_demo).pack(side="left", padx=6)

    def _load_demo(self):
        """Ask which dataset size to load, then load it."""
        choice = self._ask_sample_size()
        if not choice:
            return

        cfg = SAMPLE_PRESETS[choice]
        halls_note = f"{len(cfg['halls'])} halls"
        msg = (f"Load the '{choice}' dataset?\n\n"
               f"• {cfg['students']} students\n"
               f"• {halls_note}\n"
               f"• {cfg['invigilators']} invigilators\n\n"
               f"Current data will be replaced.")
        if not messagebox.askyesno("Confirm", msg):
            return

        load_sample_data(choice)
        messagebox.showinfo(
            "Sample data loaded",
            f"{cfg['students']} students, "
            f"{len(cfg['halls'])} halls and "
            f"{cfg['invigilators']} invigilators are ready.\n\n"
            f"Next: go to 'Assign Seats'."
        )
        self.show("home")

    def _ask_sample_size(self):
        """Small modal dialog to pick which dataset to load."""
        dlg = tk.Toplevel(self)
        dlg.title("Choose a sample dataset")
        dlg.configure(bg=LIGHT)
        dlg.geometry("420x360")
        dlg.transient(self)
        dlg.grab_set()
        dlg.resizable(False, False)

        tk.Label(dlg, text="📦  Which sample dataset?",
                 bg=LIGHT, fg=BLUE,
                 font=("Segoe UI", 13, "bold")).pack(pady=(18, 4))
        tk.Label(dlg,
                 text="Pick a size that matches your demo or test.",
                 bg=LIGHT, fg="#556677",
                 font=("Segoe UI", 9)).pack(pady=(0, 12))

        result = {"value": None}

        def pick(name):
            result["value"] = name
            dlg.destroy()

        for name, cfg in SAMPLE_PRESETS.items():
            row = tk.Frame(dlg, bg="white",
                           highlightthickness=1,
                           highlightbackground="#dde3ea")
            row.pack(fill="x", padx=18, pady=6)

            info = tk.Frame(row, bg="white")
            info.pack(side="left", fill="x", expand=True,
                      padx=12, pady=10)

            emoji = {"Small (quick demo)": "🌱",
                     "Medium (realistic)": "🌳",
                     "Large (stress test)": "🌲"}.get(name, "📦")

            tk.Label(info, text=f"{emoji}  {name}",
                     bg="white", fg=BLUE,
                     font=("Segoe UI", 11, "bold"),
                     anchor="w").pack(anchor="w")
            tk.Label(info,
                     text=f"{cfg['students']} students  •  "
                          f"{len(cfg['halls'])} halls  •  "
                          f"{cfg['invigilators']} invigilators",
                     bg="white", fg="#556677",
                     font=("Segoe UI", 9),
                     anchor="w").pack(anchor="w")

            tk.Button(row, text="Load", bg=BLUE, fg="white",
                      activebackground="#2c5282",
                      bd=0, padx=16, pady=6,
                      font=("Segoe UI", 10, "bold"),
                      cursor="hand2",
                      command=lambda n=name: pick(n)
                      ).pack(side="right", padx=12, pady=10)

        tk.Button(dlg, text="Cancel", bg=LIGHT, fg="#556677",
                  bd=0, font=("Segoe UI", 10),
                  cursor="hand2",
                  command=dlg.destroy
                  ).pack(pady=(6, 16))

        self.wait_window(dlg)
        return result["value"]

    # ============================================================
    #  WIZARD
    # ============================================================
    def screen_wizard(self, parent):
        friendly_banner(parent, "Set Up a New Exam",
                        "Answer 3 quick questions. You can change "
                        "anything later.", "🧭")

        form = card(parent, "1.  Exam details")
        f = tk.Frame(form, bg="white")
        f.pack(fill="x", padx=14, pady=(0, 14))

        self.w_name = tk.StringVar(value=STORE.exam["name"])
        self.w_dept = tk.StringVar(value=STORE.exam["department"])
        self.w_date = tk.StringVar(value=STORE.exam["date"])
        self.w_time = tk.StringVar(value=STORE.exam["time"])

        rows = [
            ("Exam name", self.w_name),
            ("Department(s)", self.w_dept),
            ("Date", self.w_date),
            ("Start time", self.w_time),
        ]
        for i, (label, var) in enumerate(rows):
            tk.Label(f, text=label, bg="white", fg="#333",
                     font=("Segoe UI", 10), width=16, anchor="w"
                     ).grid(row=i, column=0, sticky="w", pady=6)
            ttk.Entry(f, textvariable=var, width=40
                      ).grid(row=i, column=1, sticky="w", pady=6)

        form2 = card(parent, "2.  How many students per hall?")
        g = tk.Frame(form2, bg="white")
        g.pack(fill="x", padx=14, pady=(0, 14))
        tk.Label(g,
                 text="Seats per hall (you can fine-tune per hall later):",
                 bg="white", fg="#333", font=("Segoe UI", 10)
                 ).pack(anchor="w")
        self.w_cap = tk.StringVar(value="30")
        ttk.Entry(g, textvariable=self.w_cap, width=8
                  ).pack(anchor="w", pady=4)

        form3 = card(parent, "3.  Quick start")
        h = tk.Frame(form3, bg="white")
        h.pack(fill="x", padx=14, pady=(0, 14))
        tk.Label(h, text="Choose how to begin:",
                 bg="white", fg="#333",
                 font=("Segoe UI", 10)).pack(anchor="w")

        def save_basic():
            name = self.w_name.get().strip()
            if not name:
                messagebox.showerror("Missing info",
                                     "Please enter an exam name.")
                return
            STORE.exam["name"] = name
            STORE.exam["department"] = self.w_dept.get().strip() or "All"
            STORE.exam["date"] = self.w_date.get().strip()
            STORE.exam["time"] = self.w_time.get().strip()
            messagebox.showinfo("Saved",
                                "Exam details saved. Now add students "
                                "and halls.")
            self.show("students")

        def start_demo():
            self._load_demo()
            self.show("seats")

        btns = tk.Frame(h, bg="white")
        btns.pack(anchor="w", pady=8)
        big_button(btns, "💾  Save & continue to Students",
                   save_basic).pack(side="left", padx=4)
        big_button(btns, "⚡  Start with demo data",
                   start_demo, color=GREEN).pack(side="left", padx=4)

    # ============================================================
    #  STUDENTS
    # ============================================================
    def screen_students(self, parent):
        friendly_banner(parent, "Students",
                        "Add students one-by-one, or import a CSV "
                        "file in bulk. Each row shows where they sit.",
                        "👥")

        form = card(parent, "Add a student")
        f = tk.Frame(form, bg="white")
        f.pack(fill="x", padx=14, pady=(0, 14))

        self.s_seat = tk.StringVar()
        self.s_name = tk.StringVar()
        self.s_dept = tk.StringVar()

        fields = [("Seat no.", self.s_seat, 10),
                  ("Full name", self.s_name, 24),
                  ("Department", self.s_dept, 16)]
        for i, (label, var, w) in enumerate(fields):
            tk.Label(f, text=label, bg="white", fg="#333",
                     font=("Segoe UI", 10)).grid(row=0, column=i * 2,
                                                 padx=(6, 4), pady=6,
                                                 sticky="e")
            ttk.Entry(f, textvariable=var, width=w
                      ).grid(row=0, column=i * 2 + 1,
                             padx=(0, 12), pady=6)

        def add_one():
            seat = self.s_seat.get().strip()
            name = self.s_name.get().strip()
            dept = self.s_dept.get().strip() or "General"
            if not seat or not name:
                messagebox.showerror("Missing info",
                                     "Please fill in seat number "
                                     "and name.")
                return
            if any(s["seat"].lower() == seat.lower()
                   for s in STORE.students):
                messagebox.showerror("Duplicate seat",
                                     f"Seat '{seat}' is already used.")
                return
            STORE.students.append({
                "id": STORE.new_pid(), "seat": seat, "name": name,
                "dept": dept, "hall": "—", "status": "Waiting"
            })
            self.s_seat.set("")
            self.s_name.set("")
            self.show("students")

        ttk.Button(f, text="➕ Add student", command=add_one
                   ).grid(row=0, column=6, padx=6)

        def bulk_import():
            path = filedialog.askopenfilename(
                title="Select a CSV file (columns: seat, name, dept)",
                filetypes=[("CSV files", "*.csv"),
                           ("All files", "*.*")])
            if not path:
                return
            added = 0
            skipped = 0
            try:
                with open(path, newline="",
                          encoding="utf-8-sig") as fh:
                    reader = csv.DictReader(fh)
                    for row in reader:
                        row_l = {k.strip().lower(): (v or "").strip()
                                 for k, v in row.items() if k}
                        seat = (row_l.get("seat")
                                or row_l.get("seat no")
                                or row_l.get("seat_no") or "")
                        name = (row_l.get("name")
                                or row_l.get("student")
                                or row_l.get("full name") or "")
                        dept = (row_l.get("dept")
                                or row_l.get("department")
                                or "General")
                        if not seat or not name:
                            skipped += 1
                            continue
                        if any(s["seat"].lower() == seat.lower()
                               for s in STORE.students):
                            skipped += 1
                            continue
                        STORE.students.append({
                            "id": STORE.new_pid(), "seat": seat,
                            "name": name, "dept": dept,
                            "hall": "—", "status": "Waiting"
                        })
                        added += 1
            except Exception as e:
                messagebox.showerror("Import failed",
                                     f"Could not read file:\n{e}")
                return
            messagebox.showinfo(
                "Import complete",
                f"Added {added} student(s).\n"
                f"Skipped {skipped} (missing data or duplicate seat)."
            )
            self.show("students")

        def download_template():
            path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                initialfile="students_template.csv",
                filetypes=[("CSV files", "*.csv")])
            if not path:
                return
            with open(path, "w", newline="",
                      encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["seat", "name", "dept"])
                w.writerow(["A01", "Arjun Mehta", "Computer"])
                w.writerow(["A02", "Bhavya Shah", "Computer"])
                w.writerow(["B01", "Chirag Patel", "Mechanical"])
            messagebox.showinfo("Template saved",
                                f"Template written to:\n{path}\n\n"
                                f"Fill it and use 'Import CSV'.")

        ttk.Button(f, text="📥 Import CSV", command=bulk_import
                   ).grid(row=0, column=7, padx=6)
        ttk.Button(f, text="📋 Template", command=download_template
                   ).grid(row=0, column=8, padx=6)

        tree_frame = tk.Frame(parent, bg=LIGHT)
        tree_frame.pack(fill="both", expand=True, pady=(6, 0))
        cols = ("seat", "name", "dept", "hall", "status")
        heads = ("Seat", "Student Name", "Department", "Hall", "Status")
        tree = ttk.Treeview(tree_frame, columns=cols,
                            show="headings", height=14)
        for c, h in zip(cols, heads):
            tree.heading(c, text=h)
            tree.column(c,
                        anchor="center" if c != "name" else "w",
                        width=140 if c == "name" else 120)
        tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(tree_frame, command=tree.yview)
        sb.pack(side="right", fill="y")
        tree.config(yscrollcommand=sb.set)

        for i, s in enumerate(STORE.students):
            tree.insert("", "end", iid=str(i),
                        values=(s["seat"], s["name"], s["dept"],
                                s["hall"], s["status"]))
            if s["status"] == "Seated":
                tree.item(str(i), tags=("ok",))
            elif s["status"] == "No space":
                tree.item(str(i), tags=("bad",))
        tree.tag_configure("ok", background="#e6f5ea")
        tree.tag_configure("bad", background="#fdecec")

        bar = tk.Frame(parent, bg=LIGHT)
        bar.pack(fill="x", pady=6)

        def delete_sel():
            sel = tree.selection()
            if not sel:
                messagebox.showinfo("Nothing selected",
                                    "Pick a row first.")
                return
            if not messagebox.askyesno("Delete students",
                                       f"Remove {len(sel)} student(s)?"):
                return
            for iid in sorted((int(x) for x in sel), reverse=True):
                STORE.students.pop(iid)
            self.show("students")

        ttk.Button(bar, text="🗑  Delete selected",
                   command=delete_sel).pack(side="left")
        ttk.Button(bar, text="📦  Load sample data",
                   command=self._load_demo).pack(side="left", padx=6)

    # ============================================================
    #  HALLS  (with calculator)
    # ============================================================
    def screen_halls(self, parent):
        friendly_banner(parent, "Exam Halls",
                        "Add halls and use the calculator to check how "
                        "many halls you need for a given student count.",
                        "🏛️")

        form = card(parent, "Add a hall")
        f = tk.Frame(form, bg="white")
        f.pack(fill="x", padx=14, pady=(0, 14))
        self.h_name = tk.StringVar()
        self.h_cap = tk.StringVar(value="30")

        tk.Label(f, text="Hall name", bg="white", fg="#333",
                 font=("Segoe UI", 10)).grid(row=0, column=0, padx=6)
        ttk.Entry(f, textvariable=self.h_name, width=20
                  ).grid(row=0, column=1, padx=6)
        tk.Label(f, text="Seats", bg="white", fg="#333",
                 font=("Segoe UI", 10)).grid(row=0, column=2, padx=6)
        ttk.Entry(f, textvariable=self.h_cap, width=8
                  ).grid(row=0, column=3, padx=6)

        def add_hall():
            name = self.h_name.get().strip()
            if not name:
                messagebox.showerror("Missing name",
                                     "Enter a hall name.")
                return
            try:
                cap = int(self.h_cap.get())
                if cap <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid seats",
                                     "Seats must be a positive number.")
                return
            if any(h["name"].lower() == name.lower()
                   for h in STORE.halls):
                messagebox.showerror("Duplicate hall",
                                     "A hall with that name "
                                     "already exists.")
                return
            STORE.halls.append({
                "id": STORE.new_hid(), "name": name, "capacity": cap,
                "filled": 0, "status": "Empty"
            })
            self.h_name.set("")
            self.show("halls")

        ttk.Button(f, text="➕ Add hall", command=add_hall
                   ).grid(row=0, column=4, padx=8)

        # ---- Calculator ----
        calc = card(parent, "📐  How many halls do I need?")
        cf = tk.Frame(calc, bg="white")
        cf.pack(fill="x", padx=14, pady=(0, 14))
        self.calc_students = tk.StringVar(
            value=str(max(len(STORE.students), 100)))
        self.calc_per_hall = tk.StringVar(value="30")

        tk.Label(cf, text="Total students", bg="white", fg="#333",
                 font=("Segoe UI", 10)).grid(row=0, column=0, padx=6)
        ttk.Entry(cf, textvariable=self.calc_students, width=8
                  ).grid(row=0, column=1, padx=6)
        tk.Label(cf, text="Seats per hall", bg="white", fg="#333",
                 font=("Segoe UI", 10)).grid(row=0, column=2, padx=6)
        ttk.Entry(cf, textvariable=self.calc_per_hall, width=8
                  ).grid(row=0, column=3, padx=6)

        calc_result = tk.Label(cf, text="", bg="white", fg=BLUE,
                               font=("Segoe UI", 11, "bold"))
        calc_result.grid(row=0, column=4, padx=12)

        def compute_halls():
            try:
                n = int(self.calc_students.get())
                c = int(self.calc_per_hall.get())
                if n <= 0 or c <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid input",
                                     "Both numbers must be positive.")
                return
            halls_needed = math.ceil(n / c)
            leftover = halls_needed * c - n
            calc_result.config(
                text=f"You need {halls_needed} hall(s). "
                     f"({leftover} empty seat(s) in the last hall.)"
            )

        ttk.Button(cf, text="📐 Calculate",
                   command=compute_halls).grid(row=0, column=5, padx=6)

        # ---- Hall table ----
        tree_frame = tk.Frame(parent, bg=LIGHT)
        tree_frame.pack(fill="both", expand=True, pady=(6, 0))
        cols = ("name", "capacity", "filled", "free", "status")
        heads = ("Hall", "Seats", "Filled", "Free", "Status")
        tree = ttk.Treeview(tree_frame, columns=cols,
                            show="headings", height=12)
        for c, h in zip(cols, heads):
            tree.heading(c, text=h)
            tree.column(c, anchor="center", width=130)
        tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(tree_frame, command=tree.yview)
        sb.pack(side="right", fill="y")
        tree.config(yscrollcommand=sb.set)

        for i, h in enumerate(STORE.halls):
            free = h["capacity"] - h["filled"]
            tree.insert("", "end", iid=str(i),
                        values=(h["name"], h["capacity"],
                                h["filled"], free, h["status"]))
            if h["status"] == "Full":
                tree.item(str(i), tags=("full",))
            elif h["status"] == "In use":
                tree.item(str(i), tags=("inuse",))
        tree.tag_configure("full", background="#fdecec")
        tree.tag_configure("inuse", background="#fff8e1")

        bar = tk.Frame(parent, bg=LIGHT)
        bar.pack(fill="x", pady=6)

        def del_hall():
            sel = tree.selection()
            if not sel:
                messagebox.showinfo("Nothing selected",
                                    "Pick a hall first.")
                return
            if not messagebox.askyesno("Delete halls",
                                       f"Remove {len(sel)} hall(s)?"):
                return
            for iid in sorted((int(x) for x in sel), reverse=True):
                STORE.halls.pop(iid)
            self.show("halls")

        ttk.Button(bar, text="🗑  Delete selected",
                   command=del_hall).pack(side="left")

    # ============================================================
    #  ASSIGN SEATS
    # ============================================================
    def screen_seats(self, parent):
        friendly_banner(parent, "Assign Seats",
                        "We'll place each student into the first hall "
                        "with free space. Optionally mix departments.",
                        "🪑")

        if not STORE.students or not STORE.halls:
            warn = card(parent, "Before we can assign seats…")
            tk.Label(warn,
                     text="You need at least one student and one hall.",
                     bg="white", fg="#333",
                     font=("Segoe UI", 10)).pack(anchor="w",
                                                 padx=14, pady=10)
            bar = tk.Frame(warn, bg="white")
            bar.pack(anchor="w", padx=14, pady=(0, 12))
            big_button(bar, "Go to Students",
                       lambda: self.show("students")
                       ).pack(side="left", padx=4)
            big_button(bar, "Go to Halls",
                       lambda: self.show("halls")
                       ).pack(side="left", padx=4)
            return

        action = card(parent)
        a = tk.Frame(action, bg="white")
        a.pack(fill="x", padx=14, pady=14)
        tk.Label(a, text="Ready when you are.",
                 bg="white", fg=BLUE,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(a, text="Click the button to seat every student.",
                 bg="white", fg="#556677",
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 6))

        self.interleave_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            a,
            text="🔀  Mix departments (students from different "
                 "departments sit next to each other — harder to copy)",
            variable=self.interleave_var,
            bg="white", fg="#333", activebackground="white",
            font=("Segoe UI", 10), anchor="w",
            justify="left", wraplength=750,
        ).pack(anchor="w", pady=(0, 10))

        def run_assign():
            interleave = self.interleave_var.get()
            placed, waiting = do_fcfs_allocation(interleave=interleave)
            msg = f"{placed} student(s) seated"
            msg += " (departments interleaved)." if interleave else "."
            if waiting:
                msg += (f"\n\n{waiting} student(s) could not be seated "
                        f"because all halls were full.")
            else:
                msg += "\n\nEveryone got a seat."
            messagebox.showinfo("Done", msg)
            self.show("seats")

        bar = tk.Frame(a, bg="white")
        bar.pack(anchor="w")
        big_button(bar, "▶  Assign seats now",
                   run_assign, color=GREEN).pack(side="left")
        big_button(bar, "↺  Start over",
                   lambda: self._reset_seats(),
                   color="#777").pack(side="left", padx=8)

        tree_frame = tk.Frame(parent, bg=LIGHT)
        tree_frame.pack(fill="both", expand=True, pady=(10, 0))
        cols = ("name", "dept", "hall", "status")
        heads = ("Student", "Department", "Hall", "Status")
        tree = ttk.Treeview(tree_frame, columns=cols,
                            show="headings", height=14)
        for c, h in zip(cols, heads):
            tree.heading(c, text=h)
            tree.column(c, width=200 if c == "name" else 150,
                        anchor="w" if c == "name" else "center")
        tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(tree_frame, command=tree.yview)
        sb.pack(side="right", fill="y")
        tree.config(yscrollcommand=sb.set)

        for i, s in enumerate(STORE.students):
            tree.insert("", "end", iid=str(i),
                        values=(s["name"], s["dept"],
                                s["hall"], s["status"]))
            if s["status"] == "Seated":
                tree.item(str(i), tags=("ok",))
            elif s["status"] == "No space":
                tree.item(str(i), tags=("bad",))
        tree.tag_configure("ok", background="#e6f5ea")
        tree.tag_configure("bad", background="#fdecec")

    def _reset_seats(self):
        if not messagebox.askyesno("Start over",
                                   "Clear all seat assignments?"):
            return
        for h in STORE.halls:
            h["filled"] = 0
            h["status"] = "Empty"
        for s in STORE.students:
            s["hall"] = "—"
            s["status"] = "Waiting"
        self.show("seats")

    # ============================================================
    #  ASSIGN INVIGILATORS
    # ============================================================
    def screen_invig(self, parent):
        friendly_banner(parent, "Assign Invigilators",
                        "One invigilator per hall. Senior-most first. "
                        "Optionally match by department.", "👨‍🏫")

        form = card(parent, "Add an invigilator")
        f = tk.Frame(form, bg="white")
        f.pack(fill="x", padx=14, pady=(0, 14))
        self.i_name = tk.StringVar()
        self.i_dept = tk.StringVar()
        self.i_prio = tk.StringVar(value="3")

        for i, (label, var, w) in enumerate([
            ("Name", self.i_name, 20),
            ("Department", self.i_dept, 16),
            ("Seniority (1 = most senior)", self.i_prio, 6),
        ]):
            tk.Label(f, text=label, bg="white", fg="#333",
                     font=("Segoe UI", 10)).grid(row=0, column=i * 2,
                                                 padx=(6, 4), sticky="e")
            ttk.Entry(f, textvariable=var, width=w
                      ).grid(row=0, column=i * 2 + 1, padx=(0, 10))

        def add_inv():
            name = self.i_name.get().strip()
            if not name:
                messagebox.showerror("Missing name", "Enter a name.")
                return
            try:
                prio = int(self.i_prio.get())
                if prio <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid seniority",
                                     "Seniority must be a "
                                     "positive number.")
                return
            STORE.invigilators.append({
                "id": STORE.new_tid(), "name": name,
                "dept": self.i_dept.get().strip() or "—",
                "priority": prio, "hall": "—", "status": "Available"
            })
            self.i_name.set("")
            self.show("invig")

        ttk.Button(f, text="➕ Add", command=add_inv
                   ).grid(row=0, column=6)

        action = card(parent)
        a = tk.Frame(action, bg="white")
        a.pack(fill="x", padx=14, pady=14)

        self.match_dept_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            a,
            text="🚫  Prefer invigilators from a *different* department "
                 "than the students in that hall (fairer)",
            variable=self.match_dept_var,
            bg="white", fg="#333", activebackground="white",
            font=("Segoe UI", 10), anchor="w",
            justify="left", wraplength=750,
        ).pack(anchor="w", pady=(0, 10))

        def run_assign():
            if not STORE.invigilators:
                messagebox.showerror("No invigilators",
                                     "Add at least one invigilator first.")
                return
            if not any(h["filled"] > 0 for h in STORE.halls):
                messagebox.showinfo("Assign seats first",
                                    "Please assign students to halls "
                                    "before assigning invigilators.")
                return
            assigned, total = do_priority_assignment(
                match_department=self.match_dept_var.get())
            messagebox.showinfo("Done",
                                f"{assigned} of {total} halls got an "
                                f"invigilator.")
            self.show("invig")

        tk.Label(a,
                 text="Give each active hall its senior-most invigilator.",
                 bg="white", fg="#556677",
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 8))
        big_button(a, "▶  Assign invigilators now",
                   run_assign, color=GREEN).pack(anchor="w")

        tree_frame = tk.Frame(parent, bg=LIGHT)
        tree_frame.pack(fill="both", expand=True, pady=(10, 0))
        cols = ("name", "dept", "prio", "hall", "status")
        heads = ("Invigilator", "Department", "Seniority",
                 "Assigned Hall", "Status")
        tree = ttk.Treeview(tree_frame, columns=cols,
                            show="headings", height=12)
        for c, h in zip(cols, heads):
            tree.heading(c, text=h)
            tree.column(c, anchor="w" if c == "name" else "center",
                        width=180 if c == "name" else 130)
        tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(tree_frame, command=tree.yview)
        sb.pack(side="right", fill="y")
        tree.config(yscrollcommand=sb.set)

        for i, t in enumerate(STORE.invigilators):
            tree.insert("", "end", iid=str(i),
                        values=(t["name"], t["dept"], t["priority"],
                                t["hall"], t["status"]))
            if t["status"] == "On duty":
                tree.item(str(i), tags=("ok",))
        tree.tag_configure("ok", background="#e6f5ea")

    # ============================================================
    #  HALL LAYOUT
    # ============================================================
    def screen_layout(self, parent):
        friendly_banner(parent, "Hall Layout",
                        "Visual grid of who sits where. Green cells are "
                        "occupied. Print this page to stick on the wall.",
                        "🗺️")

        seated_halls = [h for h in STORE.halls if h["filled"] > 0]
        if not seated_halls:
            warn = card(parent, "No seats assigned yet")
            tk.Label(warn,
                     text="Go to 'Assign Seats' first, then come back.",
                     bg="white", fg="#333",
                     font=("Segoe UI", 10)).pack(anchor="w",
                                                 padx=14, pady=10)
            big_button(warn, "Go to Assign Seats",
                       lambda: self.show("seats")
                       ).pack(anchor="w", padx=14, pady=(0, 12))
            return

        opts = card(parent, "Grid shape")
        of = tk.Frame(opts, bg="white")
        of.pack(fill="x", padx=14, pady=(0, 12))

        self.cols_var = tk.StringVar(value="6")
        tk.Label(of, text="Columns per row:", bg="white", fg="#333",
                 font=("Segoe UI", 10)).pack(side="left", padx=(0, 6))
        ttk.Entry(of, textvariable=self.cols_var, width=4
                  ).pack(side="left", padx=(0, 10))
        ttk.Button(of, text="🔄 Refresh",
                   command=lambda: self.show("layout")
                   ).pack(side="left")

        try:
            cols = max(1, int(self.cols_var.get()))
        except ValueError:
            cols = 6

        palette = ["#d9ecff", "#d9f7d9", "#ffe9c7",
                   "#f0d9ff", "#ffd9e0", "#d9fff7"]

        for hall in seated_halls:
            students_here = [s for s in STORE.students
                             if s["hall"] == hall["name"]]
            box = card(parent,
                       f"🏛️  {hall['name']}  —  "
                       f"{len(students_here)}/{hall['capacity']} filled")
            bf = tk.Frame(box, bg="white")
            bf.pack(fill="x", padx=14, pady=(0, 14))

            rows_needed = math.ceil(len(students_here) / cols)
            canvas = tk.Canvas(bf, bg="white", highlightthickness=0,
                               height=max(120, rows_needed * 90 + 20))
            canvas.pack(fill="x", expand=True)

            def draw(_=None, canvas=canvas,
                     students_here=students_here, cols=cols,
                     palette=palette):
                canvas.delete("all")
                w = max(canvas.winfo_width(), 500)
                cell_w = w / cols
                cell_h = 80
                depts = sorted({s["dept"] for s in students_here})
                for i, s in enumerate(students_here):
                    r = i // cols
                    c = i % cols
                    x0 = c * cell_w + 4
                    y0 = r * cell_h + 4
                    x1 = x0 + cell_w - 8
                    y1 = y0 + cell_h - 8
                    idx = depts.index(s["dept"]) % len(palette)
                    fill = palette[idx]
                    canvas.create_rectangle(x0, y0, x1, y1,
                                            fill=fill, outline="#999")
                    canvas.create_text(x0 + 8, y0 + 8,
                                       text=s["seat"], anchor="nw",
                                       font=("Segoe UI", 8, "bold"),
                                       fill="#444")
                    canvas.create_text((x0 + x1) / 2, (y0 + y1) / 2,
                                       text=s["name"], anchor="center",
                                       font=("Segoe UI", 9), fill="#222",
                                       width=cell_w - 20)

            canvas.bind("<Configure>", draw)
            canvas.after(60, draw)

        # Legend
        leg = card(parent, "🎨 Department colours (in this view)")
        lf = tk.Frame(leg, bg="white")
        lf.pack(fill="x", padx=14, pady=(0, 12))
        all_depts = sorted({s["dept"] for s in STORE.students
                            if s["hall"] != "—"})
        for i, d in enumerate(all_depts):
            chip = tk.Label(lf, text=f"  {d}  ",
                            bg=palette[i % len(palette)], fg="#222",
                            font=("Segoe UI", 9, "bold"))
            chip.pack(side="left", padx=6, pady=4)

        big_button(parent, "🖨️  Print this layout as an HTML page",
                   self._print_layout, color=GREEN
                   ).pack(anchor="w", pady=(10, 0))

    def _print_layout(self):
        try:
            cols = max(1, int(self.cols_var.get()))
        except Exception:
            cols = 6

        palette = ["#d9ecff", "#d9f7d9", "#ffe9c7",
                   "#f0d9ff", "#ffd9e0", "#d9fff7"]
        all_depts = sorted({s["dept"] for s in STORE.students})
        dept_color = {d: palette[i % len(palette)]
                      for i, d in enumerate(all_depts)}

        html = ["<html><head><meta charset='utf-8'>",
                "<title>Hall Layout</title>",
                "<style>",
                "body{font-family:Arial;padding:20px}",
                "h1{color:#1f3a5f}",
                "h2{color:#1f3a5f;border-bottom:2px solid #1f3a5f;"
                "padding-bottom:4px;margin-top:30px}",
                "table{border-collapse:collapse;margin-top:8px}",
                "td{border:1px solid #999;padding:6px;width:140px;"
                "height:60px;vertical-align:top;font-size:12px}",
                ".seat{font-weight:bold;color:#444;font-size:10px}",
                "</style></head><body>",
                f"<h1>{STORE.exam['name']} — Hall Layout</h1>",
                f"<p>{STORE.exam['department']} &bull; "
                f"{STORE.exam['date']} at {STORE.exam['time']}</p>"]

        for hall in [h for h in STORE.halls if h["filled"] > 0]:
            students_here = [s for s in STORE.students
                             if s["hall"] == hall["name"]]
            html.append(f"<h2>🏛️ {hall['name']} "
                        f"({len(students_here)}/{hall['capacity']})</h2>")
            html.append("<table>")
            for i, s in enumerate(students_here):
                if i % cols == 0:
                    html.append("<tr>")
                bg = dept_color.get(s["dept"], "#fff")
                html.append(
                    f"<td style='background:{bg}'>"
                    f"<div class='seat'>Seat {s['seat']}</div>"
                    f"{s['name']}<br><i>{s['dept']}</i></td>"
                )
                if i % cols == cols - 1:
                    html.append("</tr>")
            leftover = len(students_here) % cols
            if leftover:
                html.append("<td style='background:#f5f5f5'>&nbsp;</td>"
                            * (cols - leftover) + "</tr>")
            html.append("</table>")

        html.append("</body></html>")
        text = "\n".join(html)

        path = os.path.join(tempfile.gettempdir(), "hall_layout.html")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        webbrowser.open(f"file://{path}")
        messagebox.showinfo("Opened in browser",
                            "The layout opened in your browser.\n"
                            "Use Ctrl+P there to print or save as PDF.")

    # ============================================================
    #  PRINT SEAT SLIPS
    # ============================================================
    def screen_slips(self, parent):
        friendly_banner(parent, "Print Seat Slips",
                        "One printable slip per desk. Print, cut, and "
                        "stick on each desk before the exam.", "🖨️")

        seated = [s for s in STORE.students if s["hall"] != "—"]
        if not seated:
            warn = card(parent, "No seats assigned yet")
            tk.Label(warn, text="Go to 'Assign Seats' first.",
                     bg="white", fg="#333",
                     font=("Segoe UI", 10)).pack(anchor="w",
                                                 padx=14, pady=10)
            big_button(warn, "Go to Assign Seats",
                       lambda: self.show("seats")
                       ).pack(anchor="w", padx=14, pady=(0, 12))
            return

        opts = card(parent, "What to include")
        of = tk.Frame(opts, bg="white")
        of.pack(fill="x", padx=14, pady=(0, 12))

        self.slip_hall_var = tk.StringVar(value="All halls")
        hall_names = ["All halls"] + [h["name"] for h in STORE.halls
                                      if h["filled"] > 0]
        tk.Label(of, text="Hall:", bg="white", fg="#333",
                 font=("Segoe UI", 10)).pack(side="left", padx=(0, 6))
        ttk.Combobox(of, textvariable=self.slip_hall_var,
                     values=hall_names, state="readonly", width=20
                     ).pack(side="left", padx=(0, 16))

        self.slip_size_var = tk.StringVar(value="3 per row")
        tk.Label(of, text="Slips per row:", bg="white", fg="#333",
                 font=("Segoe UI", 10)).pack(side="left", padx=(0, 6))
        ttk.Combobox(of, textvariable=self.slip_size_var,
                     values=["2 per row", "3 per row", "4 per row"],
                     state="readonly", width=12).pack(side="left")

        def make_slips():
            hall_choice = self.slip_hall_var.get()
            per_row = {"2 per row": 2, "3 per row": 3,
                       "4 per row": 4}.get(self.slip_size_var.get(), 3)

            if hall_choice == "All halls":
                slips = seated
                title = "All Halls"
            else:
                slips = [s for s in seated if s["hall"] == hall_choice]
                title = hall_choice

            html = ["<html><head><meta charset='utf-8'>",
                    "<title>Seat Slips</title>",
                    "<style>",
                    "body{font-family:Arial;padding:12px;margin:0}",
                    ".row{display:flex;flex-wrap:wrap}",
                    f".slip{{border:2px dashed #888;padding:10px;"
                    f"width:{100 // per_row}%;box-sizing:border-box;"
                    f"min-height:110px;text-align:center;"
                    f"page-break-inside:avoid}}",
                    ".hall{font-size:11px;color:#666;"
                    "letter-spacing:1px}",
                    ".seat{font-size:20px;font-weight:bold;"
                    "color:#1f3a5f;margin:4px 0}",
                    ".name{font-size:16px;margin:4px 0}",
                    ".dept{font-size:12px;color:#555}",
                    ".exam{font-size:10px;color:#999;margin-top:6px}",
                    "@media print{.slip{border:1px dashed #aaa}}",
                    "</style></head><body>",
                    f"<div style='font-size:13px;color:#666;"
                    f"margin-bottom:8px'>"
                    f"{STORE.exam['name']} &mdash; Seat Slips "
                    f"&mdash; {title}</div>",
                    "<div class='row'>"]
            for s in slips:
                html.append(
                    f"<div class='slip'>"
                    f"<div class='hall'>{s['hall']}</div>"
                    f"<div class='seat'>Seat {s['seat']}</div>"
                    f"<div class='name'>{s['name']}</div>"
                    f"<div class='dept'>{s['dept']}</div>"
                    f"<div class='exam'>{STORE.exam['name']}</div>"
                    f"</div>"
                )
            html.append("</div></body></html>")

            path = os.path.join(tempfile.gettempdir(), "seat_slips.html")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(html))
            webbrowser.open(f"file://{path}")
            messagebox.showinfo("Opened in browser",
                                "Seat slips opened in your browser.\n"
                                "Use Ctrl+P there to print or save "
                                "as PDF.")

        big_button(parent, "🖨️  Generate seat slips",
                   make_slips, color=GREEN).pack(anchor="w", pady=10)

        # Preview count
        prev = card(parent, "Preview")
        pv = tk.Frame(prev, bg="white")
        pv.pack(fill="x", padx=14, pady=(0, 12))
        tk.Label(pv,
                 text=f"{len(seated)} seat slip(s) will be generated.",
                 bg="white", fg="#333",
                 font=("Segoe UI", 10)).pack(anchor="w")

    # ============================================================
    #  CHECK FOR ISSUES
    # ============================================================
    def screen_check(self, parent):
        friendly_banner(parent, "Check for Issues",
                        "Run a quick check to make sure nothing is stuck "
                        "or double-booked.", "⚠️")

        action = card(parent)
        a = tk.Frame(action, bg="white")
        a.pack(fill="x", padx=14, pady=14)

        def run_check():
            conflicts = check_conflicts()
            if not conflicts:
                messagebox.showinfo(
                    "All good ✅",
                    "No problems detected.\n\n"
                    "Every student who needs a seat has one, and no "
                    "invigilator is double-booked."
                )
            else:
                messagebox.showwarning(
                    "Issues found ⚠️",
                    "The system found:\n\n• " + "\n• ".join(conflicts)
                )
            self.show("check")

        tk.Label(a, text="Click below to scan the whole plan.",
                 bg="white", fg="#556677",
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 8))
        big_button(a, "🔎  Check now",
                   run_check, color=AMBER).pack(anchor="w")

        if STORE.last_deadlock:
            r = card(parent, "Last check")
            g = tk.Frame(r, bg="white")
            g.pack(fill="x", padx=14, pady=(0, 12))
            tk.Label(g,
                     text=f"Checked at: "
                          f"{STORE.last_deadlock['checked_at']}",
                     bg="white", fg="#556677",
                     font=("Segoe UI", 9)).pack(anchor="w")
            if STORE.last_deadlock["conflicts"]:
                tk.Label(g, text="Issues:", bg="white", fg=RED,
                         font=("Segoe UI", 11, "bold")
                         ).pack(anchor="w", pady=(6, 2))
                for c in STORE.last_deadlock["conflicts"]:
                    tk.Label(g, text=f"• {c}", bg="white", fg="#333",
                             font=("Segoe UI", 10),
                             wraplength=800, justify="left"
                             ).pack(anchor="w")
            else:
                tk.Label(g, text="✓ Everything looks fine.",
                         bg="white", fg=GREEN,
                         font=("Segoe UI", 11, "bold")).pack(anchor="w")

            tk.Label(g,
                     text=f"Students still waiting: "
                          f"{STORE.last_deadlock['seats_needed']}   |   "
                          f"Free seats in halls: "
                          f"{STORE.last_deadlock['total_free']}",
                     bg="white", fg="#556677",
                     font=("Segoe UI", 10)
                     ).pack(anchor="w", pady=(8, 0))

    # ============================================================
    #  SAVE SEATING FILES
    # ============================================================
    def screen_files(self, parent):
        friendly_banner(parent, "Save Seating Files",
                        "Save the seating plan for each department as a "
                        "'file' on disk. Blocks must be consecutive.",
                        "💾")

        form = card(parent, "Create a seating file")
        f = tk.Frame(form, bg="white")
        f.pack(fill="x", padx=14, pady=(0, 14))

        self.f_name = tk.StringVar()
        self.f_dept = tk.StringVar()
        self.f_size = tk.StringVar(value="4")

        for i, (label, var, w) in enumerate([
            ("File name", self.f_name, 22),
            ("Department", self.f_dept, 16),
            ("Size (blocks)", self.f_size, 6),
        ]):
            tk.Label(f, text=label, bg="white", fg="#333",
                     font=("Segoe UI", 10)).grid(row=0, column=i * 2,
                                                 padx=(6, 4), sticky="e")
            ttk.Entry(f, textvariable=var, width=w
                      ).grid(row=0, column=i * 2 + 1, padx=(0, 10))

        BITMAP = STORE._bitmap

        def alloc():
            name = self.f_name.get().strip()
            dept = self.f_dept.get().strip()
            if not name or not dept:
                messagebox.showerror("Missing info",
                                     "Fill in file name and department.")
                return
            try:
                size = int(self.f_size.get())
                if size <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid size",
                                     "Size must be a positive integer.")
                return
            if any(x["name"] == name and x["dept"] == dept
                   for x in STORE.files):
                messagebox.showerror("Duplicate",
                                     "That file already exists for "
                                     "the department.")
                return
            run = 0
            for i in range(len(BITMAP)):
                if BITMAP[i] == 0:
                    run += 1
                    if run == size:
                        start = i - size + 1
                        for j in range(start, start + size):
                            BITMAP[j] = 1
                        STORE.files.append({
                            "id": STORE.new_fid(), "name": name,
                            "dept": dept, "start": start, "size": size
                        })
                        messagebox.showinfo(
                            "Saved",
                            f"File saved.\nBlocks {start} to "
                            f"{start + size - 1} on disk."
                        )
                        self.f_name.set("")
                        self.show("files")
                        return
                else:
                    run = 0
            messagebox.showerror(
                "Could not save",
                "There isn't a long enough continuous free space "
                "on disk.\n\nTry a smaller size or delete some "
                "files first."
            )

        ttk.Button(f, text="💾  Save file", command=alloc
                   ).grid(row=0, column=6, padx=6)

        tree_frame = tk.Frame(parent, bg=LIGHT)
        tree_frame.pack(fill="x", pady=(6, 10))
        cols = ("name", "dept", "start", "size")
        heads = ("File", "Department", "Starting Block",
                 "Size (blocks)")
        tree = ttk.Treeview(tree_frame, columns=cols,
                            show="headings", height=8)
        for c, h in zip(cols, heads):
            tree.heading(c, text=h)
            tree.column(c, anchor="center" if c != "name" else "w",
                        width=180)
        tree.pack(side="left", fill="x", expand=True)
        for i, x in enumerate(STORE.files):
            tree.insert("", "end", iid=str(i),
                        values=(x["name"], x["dept"],
                                x["start"], x["size"]))

        def del_file():
            sel = tree.selection()
            if not sel:
                return
            if not messagebox.askyesno(
                "Delete file",
                "Remove selected file(s)?\n"
                "Their blocks will become free again."
            ):
                return
            for iid in sorted((int(x) for x in sel), reverse=True):
                f_rec = STORE.files.pop(iid)
                for b in range(f_rec["start"],
                               f_rec["start"] + f_rec["size"]):
                    BITMAP[b] = 0
            self.show("files")

        bar = tk.Frame(parent, bg=LIGHT)
        bar.pack(fill="x")
        ttk.Button(bar, text="🗑  Delete selected", command=del_file
                   ).pack(side="left")

        vis = card(parent, "Disk map")
        v = tk.Frame(vis, bg="white")
        v.pack(fill="x", padx=14, pady=(0, 12))
        tk.Label(v, text="🟦 = used      ⬜ = free",
                 bg="white", fg="#556677",
                 font=("Segoe UI", 9)).pack(anchor="w")
        canvas = tk.Canvas(v, height=40, bg="white",
                           highlightthickness=0)
        canvas.pack(fill="x", pady=6)

        def draw_disk(_=None):
            canvas.delete("all")
            w = max(canvas.winfo_width(), 600)
            bw = w / len(BITMAP)
            for i, b in enumerate(BITMAP):
                color = "#2c5282" if b else "#e8edf3"
                canvas.create_rectangle(i * bw, 4, (i + 1) * bw, 36,
                                        fill=color, outline="")

        canvas.bind("<Configure>", draw_disk)
        canvas.after(50, draw_disk)

    # ============================================================
    #  DEPARTMENT RECORDS
    # ============================================================
    def screen_dirs(self, parent):
        friendly_banner(parent, "Department Records",
                        "Files are grouped by department — like folders "
                        "on your computer.", "📁")

        form = card(parent, "Add a department or file")
        f = tk.Frame(form, bg="white")
        f.pack(fill="x", padx=14, pady=(0, 14))

        self.d_dept = tk.StringVar()
        self.d_entry = tk.StringVar()

        tk.Label(f, text="Department", bg="white", fg="#333",
                 font=("Segoe UI", 10)).grid(row=0, column=0, padx=6)
        ttk.Entry(f, textvariable=self.d_dept, width=18
                  ).grid(row=0, column=1, padx=6)
        tk.Label(f, text="File name", bg="white", fg="#333",
                 font=("Segoe UI", 10)).grid(row=0, column=2, padx=6)
        ttk.Entry(f, textvariable=self.d_entry, width=22
                  ).grid(row=0, column=3, padx=6)

        def new_dept():
            d = self.d_dept.get().strip()
            if not d:
                messagebox.showerror("Missing name",
                                     "Enter a department.")
                return
            if d in STORE.folders:
                messagebox.showerror("Duplicate",
                                     "That department already exists.")
                return
            STORE.folders[d] = []
            self.d_dept.set("")
            self.show("dirs")

        def add_file():
            d = self.d_dept.get().strip()
            fn = self.d_entry.get().strip()
            if not d or not fn:
                messagebox.showerror("Missing info",
                                     "Enter department and file name.")
                return
            if d not in STORE.folders:
                messagebox.showerror("No such department",
                                     f"Add '{d}' first.")
                return
            if fn in STORE.folders[d]:
                messagebox.showerror("Duplicate file",
                                     "That file already exists here.")
                return
            STORE.folders[d].append(fn)
            self.d_entry.set("")
            self.show("dirs")

        ttk.Button(f, text="➕ New department", command=new_dept
                   ).grid(row=0, column=4, padx=6)
        ttk.Button(f, text="➕ Add file", command=add_file
                   ).grid(row=0, column=5, padx=6)

        box = card(parent)
        tree = ttk.Treeview(box, show="tree", height=14)
        tree.pack(fill="both", expand=True, padx=14, pady=12)
        root = tree.insert("", "end", iid="root",
                           text="📁 Exam Management", open=True)
        for dept, files in STORE.folders.items():
            dnode = tree.insert(root, "end", iid=f"d:{dept}",
                                text=f"📁 {dept}", open=True)
            for fn in files:
                tree.insert(dnode, "end",
                            iid=f"f:{dept}:{fn}", text=f"📄 {fn}")

        def del_entry():
            sel = tree.selection()
            if not sel:
                return
            iid = sel[0]
            if iid.startswith("d:"):
                dept = iid[2:]
                if messagebox.askyesno(
                    "Delete department",
                    f"Delete '{dept}' and all its files?"
                ):
                    STORE.folders.pop(dept, None)
            elif iid.startswith("f:"):
                _, dept, fn = iid.split(":", 2)
                if messagebox.askyesno("Delete file",
                                       f"Delete '{fn}'?"):
                    STORE.folders[dept] = [
                        x for x in STORE.folders[dept] if x != fn
                    ]
            self.show("dirs")

        bar = tk.Frame(parent, bg=LIGHT)
        bar.pack(fill="x")
        ttk.Button(bar, text="🗑  Delete selected", command=del_entry
                   ).pack(side="left")

    # ============================================================
    #  REPORTS
    # ============================================================
    def screen_reports(self, parent):
        friendly_banner(parent, "Reports",
                        "A complete summary of the exam plan — ready to "
                        "print or export.", "📊")

        box = card(parent)
        txt = tk.Text(box, wrap="word", bg="white", bd=0,
                      font=("Consolas", 10), height=22)
        txt.pack(fill="both", expand=True, padx=14, pady=14)

        def build():
            txt.delete("1.0", "end")
            w = txt.insert
            w("end", f"{STORE.exam['name']}\n")
            w("end", f"{STORE.exam['department']}  •  "
                     f"{STORE.exam['date']} at {STORE.exam['time']}\n")
            w("end", "=" * 68 + "\n\n")

            w("end", "SUMMARY\n")
            w("end", f"  Students       : {len(STORE.students)}\n")
            w("end", f"  Exam Halls     : {len(STORE.halls)}\n")
            w("end", f"  Invigilators   : {len(STORE.invigilators)}\n")
            seated = sum(1 for s in STORE.students
                         if s["status"] == "Seated")
            w("end", f"  Seated         : {seated}\n")
            w("end",
              f"  Waiting        : {len(STORE.students) - seated}\n\n")

            w("end", "SEATING PLAN\n")
            for s in STORE.students:
                w("end", f"  {s['name']:<20} {s['dept']:<12} "
                         f"Hall {s['hall']:<10} "
                         f"({s['status']})\n")

            w("end", "\nINVIGILATOR ASSIGNMENTS\n")
            for t in STORE.invigilators:
                w("end", f"  {t['name']:<16} Dept {t['dept']:<12} "
                         f"Hall {t['hall']:<10} "
                         f"({t['status']})\n")

            w("end", "\nSEATING FILES SAVED\n")
            for f_rec in STORE.files:
                w("end",
                  f"  {f_rec['name']:<24} {f_rec['dept']:<12} "
                  f"Blocks {f_rec['start']}–"
                  f"{f_rec['start'] + f_rec['size'] - 1}\n")

            w("end", "\nDEPARTMENT RECORDS\n")
            for d, files in STORE.folders.items():
                w("end", f"  📁 {d}\n")
                for fn in files:
                    w("end", f"      📄 {fn}\n")

            w("end", "\n" + "=" * 68 + "\n")
            w("end",
              f"Generated "
              f"{datetime.now().strftime('%d %b %Y %H:%M')}\n")

        build()

        bar = tk.Frame(parent, bg=LIGHT)
        bar.pack(fill="x", pady=(8, 0))

        def export():
            path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                initialfile=(
                    f"exam_report_"
                    f"{datetime.now():%Y%m%d}.txt"
                ),
                filetypes=[("Text", "*.txt")])
            if not path:
                return
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(txt.get("1.0", "end"))
            messagebox.showinfo("Saved", f"Report saved to:\n{path}")

        def export_csv():
            path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                initialfile=(
                    f"seating_plan_"
                    f"{datetime.now():%Y%m%d}.csv"
                ),
                filetypes=[("CSV", "*.csv")])
            if not path:
                return
            with open(path, "w", newline="",
                      encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["seat", "name", "dept", "hall",
                            "status"])
                for s in STORE.students:
                    w.writerow([s["seat"], s["name"], s["dept"],
                                s["hall"], s["status"]])
            messagebox.showinfo("Saved",
                                f"Seating plan CSV saved:\n{path}")

        big_button(bar, "💾  Save report (.txt)", export
                   ).pack(side="left")
        big_button(bar, "📄  Export seating plan (.csv)",
                   export_csv, color=GREEN).pack(side="left", padx=8)
        big_button(bar, "🔃  Refresh", build,
                   color="#777").pack(side="left", padx=8)


# ============================================================
if __name__ == "__main__":
    load_demo_data()
    App().mainloop()