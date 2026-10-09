# College Exam Hall Management System

Tkinter desktop app simulating OS concepts on a college examination scenario.

## Run on Windows
1. Install Python 3.8+ (from python.org, tick "Add to PATH").
2. Double-click **exam_hall_app.py**, or run:
   ```
   python exam_hall_app.py
   ```
No extra installs needed. (Optional: `pip install psutil` to see memory info.)

## Module ↔ CO mapping
| Section | CO | OS Concept |
|---|---|---|
| Dashboard | CO1 | System info + Batch OS classification |
| Students & Processes | CO2 | Processes & threads (many-to-one) |
| Hall Allocation (FCFS) | CO3 | First-Come-First-Serve scheduling |
| Invigilator Scheduling | CO3 | Priority scheduling (min-heap) |
| Deadlock Detection | CO3 | RAG cycle / safe-sequence test |
| Memory (LRU) | CO4 | LRU page replacement |
| File Allocation | CO4 | Contiguous allocation + bitmap |
| Department Directories | CO5 | Tree-structured directory |
| Reports | all | Summary + CSV/TXT export |

## How to demo
1. **Load Sample Data** (Examination Setup) — or add your own.
2. **Students & Processes** → add students (or use sample).
3. **Examination Halls** → add halls with capacities.
4. **Hall Allocation (FCFS)** → Run. See students placed / waiting.
5. **Invigilator Scheduling** → Run. Highest priority assigned first.
6. **Deadlock Detection** → click Demo 1 (safe) then Demo 2 (deadlock).
7. **Memory (LRU)** → Run. See step-by-step frames & hit ratio.
8. **File Allocation** → allocate files, watch bitmap fill.
9. **Department Directories** → tree of dept folders and files.
10. **Reports & Summary** → Generate, export TXT/CSV.
