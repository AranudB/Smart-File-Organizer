# Smart File Organizer

Automatically sort files in a folder into category subfolders — with
full undo, structured logging, and a tkinter GUI.

---

## Features

| Feature | Details |
|---|---|
| **Auto-classification** | 11 built-in categories (Images, Documents, Audio, Video, Code, …) |
| **Custom rules** | Add / remove extension→category mappings at runtime |
| **Conflict resolution** | `report.pdf` → `report_1.pdf` → `report_2.pdf` … |
| **Undo** | Undo the last move, or undo everything at once |
| **Persistent history** | Moves are saved to `~/.file_organizer/history.json` |
| **Logging** | Timestamped log file in `~/.file_organizer/logs/` + console output |
| **GUI** | tkinter window with folder picker, progress bar, live log, history panel |
| **Stoppable** | Click Stop to abort mid-run gracefully |
| **Fully tested** | 29 unit tests covering all core classes |

---

## Requirements

- Python ≥ 3.10
- Standard library only (`tkinter`, `shutil`, `logging`, `json`, `threading`, …)
- No external packages required

---

## Installation

```bash
git clone https://github.com/yourname/smart-file-organizer.git
cd smart-file-organizer
python main.py
```

---

## Usage

### GUI (default)

```bash
python main.py
```

1. Click **Browse…** and choose the folder you want to organise.
2. Click **▶ Start** — files are moved into subfolders immediately.
3. Click **↩ Undo Last** to reverse the most-recent move.
4. Click **↩↩ Undo All** to restore every file to its original location.
5. Click **⏹ Stop** to abort a running job after the current file.

### Programmatic (headless)

```python
from organizer import FileClassifier, FileOrganizer, MoveHistory, FileLogger

logger    = FileLogger(log_dir="/tmp/logs")
history   = MoveHistory(history_file="/tmp/history.json")
organizer = FileOrganizer(logger=logger, history=history)

stats = organizer.organize("/home/user/Downloads")
print(stats)          # {'moved': 42, 'skipped': 0, 'errors': 0}

organizer.undo_last() # reverse the last move
organizer.undo_all()  # reverse everything
```

### Custom classification rules

```python
from organizer import FileClassifier, FileOrganizer

clf = FileClassifier(custom_rules={"Configs": {".env", ".ini", ".toml"}})
organizer = FileOrganizer(classifier=clf)
organizer.organize("/home/user/Projects")
```

---

## Project Structure

```
smart_file_organizer/
├── main.py                  ← entry point (launches GUI)
├── test_organizer.py        ← 29 unit tests
└── organizer/
    ├── __init__.py          ← core package exports
    ├── classifier.py        ← FileClassifier
    ├── history.py           ← MoveHistory + MoveRecord
    ├── logger.py            ← FileLogger
    ├── organizer.py         ← FileOrganizer (core engine)
    └── gui.py               ← OrganizerGUI (tkinter)
```

---

## Architecture

All classes follow **single-responsibility** and are injected into each other
via constructor parameters (dependency injection), making them independently
testable.

```
                    ┌──────────────┐
                    │ OrganizerGUI │   tkinter front-end
                    └──────┬───────┘
                           │ owns
                    ┌──────▼───────┐
                    │ FileOrganizer│   core engine
                    └──┬────┬────┬─┘
                       │    │    │
            ┌──────────┘    │    └──────────┐
            ▼               ▼               ▼
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │FileClassifier│  │ MoveHistory  │  │  FileLogger  │
  └──────────────┘  └──────────────┘  └──────────────┘
```

### Class Overview

#### `FileClassifier`
- Holds an `EXTENSION_MAP: dict[str, set[str]]` of category → extensions.
- `classify(filename) → str` — O(1) reverse-lookup via a pre-built index.
- `add_rule` / `remove_rule` — dynamic rule management.

#### `MoveRecord` (dataclass)
- Immutable snapshot: `source`, `destination`, `category`, `filename`, `timestamp`.

#### `MoveHistory`
- LIFO stack of `MoveRecord` objects.
- `record()` appends; `pop_last()` removes from the top.
- Optionally serialises/deserialises the stack to a JSON file.

#### `FileLogger`
- Wraps Python's `logging` module with two handlers (file + console).
- Supports arbitrary callback functions — the GUI uses this to stream log
  lines into the dark log panel in real time.

#### `FileOrganizer`
- `scan(folder)` — lists top-level, non-hidden files.
- `organize(folder, on_progress)` — classify → create dir → `shutil.move()`.
  Runs safely in a background thread; `stop()` signals early exit via
  `threading.Event`.
- `undo_last()` / `undo_all()` — calls `shutil.move()` in reverse; cleans up
  empty category folders automatically.
- `_resolve_conflict(path)` — appends `_N` to the stem if the destination
  already exists.

---

## Running the Tests

```bash
python -m unittest test_organizer -v
```

Expected output: **29 tests, 0 failures**.

Test coverage includes:

- `FileClassifier` — known extensions, case-insensitivity, custom rules, add/remove
- `MoveHistory` — LIFO order, persistence, clear, empty-pop guard
- `FileOrganizer` — scan, organize, conflict resolution, unknown→Others,
                    progress callback, undo last/all, empty-folder cleanup
- `FileLogger` — log-file creation, callback fan-out, callback removal

---

## Default Categories

| Category | Example extensions |
|---|---|
| Images | `.jpg` `.png` `.gif` `.svg` `.webp` `.heic` |
| Documents | `.pdf` `.docx` `.txt` `.md` `.epub` |
| Spreadsheets | `.xlsx` `.csv` `.ods` |
| Presentations | `.pptx` `.odp` `.key` |
| Videos | `.mp4` `.mkv` `.mov` `.avi` |
| Audio | `.mp3` `.flac` `.wav` `.ogg` |
| Archives | `.zip` `.7z` `.tar` `.gz` `.rar` |
| Code | `.py` `.js` `.ts` `.go` `.rs` `.sql` |
| Executables | `.exe` `.dmg` `.deb` `.apk` |
| Fonts | `.ttf` `.otf` `.woff2` |
| Design | `.psd` `.ai` `.fig` `.blend` |
| Others | *(everything else)* |