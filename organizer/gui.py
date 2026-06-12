"""
gui.py
tkinter-based graphical front-end for the Smart File Organizer.

Layout
------
  ┌─────────────────────────── Header ──────────────────────────────┐
  │              Smart File Organizer                               │
  ├──── Folder picker ──────────────────────────────────────────────┤
  │  [path entry ___________________________] [Browse…]             │
  ├──── Controls ───────────────────────────────────────────────────┤
  │  [▶ Start]  [⏹ Stop]  [↩ Undo Last]  [↩↩ Undo All]  [🗑Clear] │
  ├──── Progress ───────────────────────────────────────────────────┤
  │  ████████████████░░░░  72 %  – processing report.pdf            │
  ├──── History (scrollable list) ──────────────────────────────────┤
  │  Moved: 14 files                                                │
  │  ▸ report.pdf  →  Documents/                                    │
  │  ▸ photo.jpg   →  Images/                                       │
  │  …                                                              │
  ├──── Activity log ───────────────────────────────────────────────┤
  │  [dark terminal-style scrolled text]                            │
  └──── Status bar ─────────────────────────────────────────────────┘
"""
from __future__ import annotations
import os
import threading
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, scrolledtext, ttk

from .classifier import FileClassifier
from .history    import MoveHistory
from .logger     import FileLogger
from .organizer  import FileOrganizer


# ─────────────────────────── colour palette ────────────────────────────────
PALETTE = {
    "bg":       "#f5f5f5",
    "header":   "#1a1a2e",
    "accent":   "#16213e",
    "green":    "#2ecc71",
    "red":      "#e74c3c",
    "orange":   "#e67e22",
    "crimson":  "#c0392b",
    "steel":    "#7f8c8d",
    "blue":     "#3498db",
    "log_bg":   "#1e1e1e",
    "log_fg":   "#d4d4d4",
    "info_fg":  "#4ec9b0",
    "warn_fg":  "#dcdcaa",
    "err_fg":   "#f48771",
    "ts_fg":    "#569cd6",
    "move_fg":  "#9cdcfe",
}


class OrganizerGUI:
    """Main application window."""

    APP_TITLE   = "Smart File Organizer"
    WINDOW_SIZE = "860x680"
    MIN_SIZE    = (640, 520)

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self._configure_root()

        # State
        self._folder_var   = tk.StringVar()
        self._status_var   = tk.StringVar(value="Ready.")
        self._progress_var = tk.IntVar(value=0)
        self._pct_var      = tk.StringVar(value="0 %")

        # Back-end objects
        self._classifier: FileClassifier | None = None
        self._history:    MoveHistory    | None = None
        self._file_logger: FileLogger    | None = None
        self._organizer:  FileOrganizer  | None = None
        self._organize_thread: threading.Thread | None = None

        self._setup_backend()
        self._build_ui()

    # ──────────────────────── window setup ────────────────────────────────

    def _configure_root(self) -> None:
        self.root.title(self.APP_TITLE)
        self.root.geometry(self.WINDOW_SIZE)
        self.root.minsize(*self.MIN_SIZE)
        self.root.configure(bg=PALETTE["bg"])
        try:
            self.root.tk.call("tk", "scaling", 1.2)
        except tk.TclError:
            pass

    # ──────────────────────── back-end wiring ─────────────────────────────

    def _setup_backend(self) -> None:
        base = os.path.join(os.path.expanduser("~"), ".file_organizer")
        log_dir      = os.path.join(base, "logs")
        history_file = os.path.join(base, "history.json")

        self._classifier  = FileClassifier()
        self._history     = MoveHistory(history_file=history_file)
        self._file_logger = FileLogger(log_dir=log_dir)
        self._file_logger.add_callback(self._on_log_callback)

        self._organizer = FileOrganizer(
            classifier=self._classifier,
            history=self._history,
            logger=self._file_logger,
        )

    # ──────────────────────────── UI build ────────────────────────────────

    def _build_ui(self) -> None:
        self._build_header()
        self._build_folder_section()
        self._build_controls()
        self._build_progress()
        self._build_history_panel()
        self._build_log_area()
        self._build_status_bar()

    # ── header ──────────────────────────────────────────────────────────

    def _build_header(self) -> None:
        f = tk.Frame(self.root, bg=PALETTE["header"], pady=14)
        f.pack(fill="x")
        tk.Label(
            f, text="📁  Smart File Organizer",
            font=("Segoe UI", 17, "bold"),
            bg=PALETTE["header"], fg="white",
        ).pack()
        tk.Label(
            f, text="Automatically sort your files by type — with full undo",
            font=("Segoe UI", 9),
            bg=PALETTE["header"], fg="#a0a8b8",
        ).pack()

    # ── folder picker ───────────────────────────────────────────────────

    def _build_folder_section(self) -> None:
        lf = tk.LabelFrame(
            self.root, text="  📂  Target Folder  ",
            font=("Segoe UI", 10, "bold"),
            bg=PALETTE["bg"], padx=10, pady=8,
        )
        lf.pack(fill="x", padx=16, pady=(12, 0))

        entry = tk.Entry(
            lf, textvariable=self._folder_var,
            font=("Segoe UI", 10), relief="solid", bd=1,
        )
        entry.pack(side="left", expand=True, fill="x", padx=(0, 8))

        self._btn(lf, "Browse…", self._browse_folder,
                  PALETTE["blue"]).pack(side="left")

    # ── control buttons ─────────────────────────────────────────────────

    def _build_controls(self) -> None:
        f = tk.Frame(self.root, bg=PALETTE["bg"])
        f.pack(fill="x", padx=16, pady=8)

        self._btn_start = self._btn(f, "▶  Start",     self._start_organize, PALETTE["green"])
        self._btn_stop  = self._btn(f, "⏹  Stop",      self._stop_organize,  PALETTE["red"],
                                    state="disabled")
        self._btn_undo  = self._btn(f, "↩  Undo Last", self._undo_last,      PALETTE["orange"])
        self._btn_undo_all = self._btn(f, "↩↩  Undo All", self._undo_all,    PALETTE["crimson"])

        for b in (self._btn_start, self._btn_stop, self._btn_undo, self._btn_undo_all):
            b.pack(side="left", padx=(0, 6))

        self._btn(f, "🗑  Clear Log", self._clear_log, PALETTE["steel"]).pack(side="right")

    # ── progress ────────────────────────────────────────────────────────

    def _build_progress(self) -> None:
        f = tk.Frame(self.root, bg=PALETTE["bg"])
        f.pack(fill="x", padx=16, pady=(0, 6))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Org.Horizontal.TProgressbar",
            troughcolor="#dde", background=PALETTE["green"],
            thickness=18,
        )
        self._progress_bar = ttk.Progressbar(
            f, variable=self._progress_var, maximum=100,
            style="Org.Horizontal.TProgressbar",
        )
        self._progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 8))

        tk.Label(f, textvariable=self._pct_var,
                 font=("Segoe UI", 9, "bold"),
                 bg=PALETTE["bg"], width=5).pack(side="left")

    # ── history panel ───────────────────────────────────────────────────

    def _build_history_panel(self) -> None:
        lf = tk.LabelFrame(
            self.root, text="  🗂  Move History  ",
            font=("Segoe UI", 10, "bold"),
            bg=PALETTE["bg"], padx=6, pady=4,
        )
        lf.pack(fill="x", padx=16, pady=(0, 4))

        self._history_text = scrolledtext.ScrolledText(
            lf, state="disabled", font=("Segoe UI", 9),
            bg="#eef2f7", fg="#2c3e50", height=5,
            wrap="none", relief="flat",
        )
        self._history_text.pack(fill="both", expand=True)
        self._history_text.tag_config("arrow",    foreground=PALETTE["blue"])
        self._history_text.tag_config("category", foreground=PALETTE["orange"],
                                      font=("Segoe UI", 9, "bold"))
        self._history_text.tag_config("path",     foreground="#555")

        self._refresh_history_panel()

    # ── log area ────────────────────────────────────────────────────────

    def _build_log_area(self) -> None:
        lf = tk.LabelFrame(
            self.root, text="  📋  Activity Log  ",
            font=("Segoe UI", 10, "bold"),
            bg=PALETTE["bg"], padx=6, pady=4,
        )
        lf.pack(fill="both", expand=True, padx=16, pady=(0, 4))

        self._log_text = scrolledtext.ScrolledText(
            lf, state="disabled", font=("Courier New", 9),
            bg=PALETTE["log_bg"], fg=PALETTE["log_fg"],
            insertbackground="white", wrap="word", height=8, relief="flat",
        )
        self._log_text.pack(fill="both", expand=True)

        self._log_text.tag_config("TS",      foreground=PALETTE["ts_fg"])
        self._log_text.tag_config("INFO",    foreground=PALETTE["info_fg"])
        self._log_text.tag_config("WARNING", foreground=PALETTE["warn_fg"])
        self._log_text.tag_config("ERROR",   foreground=PALETTE["err_fg"])
        self._log_text.tag_config("MOVE",    foreground=PALETTE["move_fg"])

    # ── status bar ──────────────────────────────────────────────────────

    def _build_status_bar(self) -> None:
        f = tk.Frame(self.root, bg=PALETTE["accent"], pady=5)
        f.pack(fill="x", side="bottom")
        tk.Label(
            f, textvariable=self._status_var,
            font=("Segoe UI", 9), bg=PALETTE["accent"], fg="#ecf0f1",
        ).pack(side="left", padx=10)

    # ──────────────────────────── callbacks ───────────────────────────────

    def _browse_folder(self) -> None:
        folder = filedialog.askdirectory(title="Select folder to organise")
        if folder:
            self._folder_var.set(folder)

    def _start_organize(self) -> None:
        folder = self._folder_var.get().strip()
        if not folder:
            messagebox.showwarning("No folder", "Please select a folder first.")
            return
        if not os.path.isdir(folder):
            messagebox.showerror("Invalid folder", f"'{folder}' is not a valid directory.")
            return

        self._btn_start.config(state="disabled")
        self._btn_stop.config(state="normal")
        self._progress_var.set(0)
        self._pct_var.set("0 %")
        self._set_status("Organising…")

        self._organize_thread = threading.Thread(
            target=self._run_organize, args=(folder,), daemon=True
        )
        self._organize_thread.start()

    def _run_organize(self, folder: str) -> None:
        def on_progress(current: int, total: int, filename: str) -> None:
            pct = int((current / total) * 100) if total else 0
            self.root.after(0, self._update_progress, pct, current, total, filename)

        stats = self._organizer.organize(folder, on_progress=on_progress)
        self.root.after(0, self._organize_done, stats)

    def _update_progress(self, pct: int, current: int, total: int, filename: str) -> None:
        self._progress_var.set(pct)
        self._pct_var.set(f"{pct} %")
        self._set_status(f"Processing {current}/{total}: {filename}")

    def _organize_done(self, stats: dict) -> None:
        self._btn_start.config(state="normal")
        self._btn_stop.config(state="disabled")
        self._progress_var.set(100)
        self._pct_var.set("100 %")
        self._set_status(
            f"Done ✔  –  Moved: {stats['moved']} | "
            f"Skipped: {stats['skipped']} | Errors: {stats['errors']}"
        )
        self._refresh_history_panel()

    def _stop_organize(self) -> None:
        self._organizer.stop()
        self._btn_stop.config(state="disabled")
        self._set_status("Stopping after current file…")

    def _undo_last(self) -> None:
        ok = self._organizer.undo_last()
        self._set_status("Last move undone." if ok else "Nothing to undo.")
        self._refresh_history_panel()

    def _undo_all(self) -> None:
        if not self._history:
            messagebox.showinfo("Nothing to undo", "The history is already empty.")
            return
        if not messagebox.askyesno(
            "Undo All",
            f"Undo all {len(self._history)} recorded move(s)?\n\n"
            "Files will be moved back to their original locations.",
        ):
            return
        count = self._organizer.undo_all()
        self._set_status(f"Undone {count} move(s).")
        self._refresh_history_panel()

    def _clear_log(self) -> None:
        self._log_text.config(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.config(state="disabled")

    # ──────────────────── log / history display ───────────────────────────

    def _on_log_callback(self, level: str, message: str) -> None:
        """Called from any thread; delegate to main thread."""
        self.root.after(0, self._append_log, level, message)

    def _append_log(self, level: str, message: str) -> None:
        ts  = datetime.now().strftime("%H:%M:%S")
        tag = level if level in ("INFO", "WARNING", "ERROR") else "INFO"
        move_line = "MOVE" in message

        self._log_text.config(state="normal")
        self._log_text.insert("end", f"[{ts}] ", "TS")
        self._log_text.insert("end", f"[{level:<7}] ", tag)
        self._log_text.insert("end", f"{message}\n", "MOVE" if move_line else "")
        self._log_text.see("end")
        self._log_text.config(state="disabled")

    def _refresh_history_panel(self) -> None:
        """Rebuild the history panel from current MoveHistory contents."""
        records = self._history.all()
        self._history_text.config(state="normal")
        self._history_text.delete("1.0", "end")

        if not records:
            self._history_text.insert("end", "  No moves recorded yet.\n", "path")
        else:
            self._history_text.insert(
                "end", f"  {len(records)} file(s) moved\n", "category"
            )
            for rec in reversed(records):   # most recent first
                self._history_text.insert("end", f"  ▸ ", "arrow")
                self._history_text.insert("end", f"{rec.filename}", "path")
                self._history_text.insert("end", "  →  ", "arrow")
                self._history_text.insert("end", f"{rec.category}/\n", "category")

        self._history_text.config(state="disabled")

    # ──────────────────────────── helpers ─────────────────────────────────

    def _set_status(self, text: str) -> None:
        self._status_var.set(text)

    @staticmethod
    def _btn(
        parent, text: str, command,
        bg: str, state: str = "normal",
    ) -> tk.Button:
        return tk.Button(
            parent, text=text, command=command,
            bg=bg, fg="white",
            font=("Segoe UI", 9, "bold"),
            relief="flat", padx=14, pady=6,
            cursor="hand2", state=state,
            activebackground=bg, activeforeground="white",
        )