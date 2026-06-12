"""
logger.py
Centralised logging for the organizer.

Every log entry is written to a timestamped log file **and** forwarded to
any registered callbacks (e.g. the tkinter GUI log panel).
"""
from __future__ import annotations
import logging
import os
from datetime import datetime
from typing import Callable


LogCallback = Callable[[str, str], None]   # (level, message)


class FileLogger:
    """
    Thin wrapper around :mod:`logging` that also fans out log entries to
    arbitrary callbacks – useful for live GUI log panels.

    Log levels used:
    - INFO    – normal operations (moves, start/end summary, undo)
    - WARNING – non-fatal issues (nothing to undo, skipped files)
    - ERROR   – failures (permission denied, shutil errors)
    """

    _FMT  = "%(asctime)s | %(levelname)-8s | %(message)s"
    _DATEFMT = "%Y-%m-%d %H:%M:%S"

    def __init__(
        self,
        log_dir:   str = ".",
        log_level: int = logging.INFO,
    ) -> None:
        os.makedirs(log_dir, exist_ok=True)

        timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_path = os.path.join(log_dir, f"organizer_{timestamp}.log")

        self._callbacks: list[LogCallback] = []

        # Build a dedicated logger so we don't pollute the root logger
        self._log = logging.getLogger(f"FileOrganizer.{id(self)}")
        self._log.setLevel(log_level)
        self._log.propagate = False
        self._log.handlers.clear()

        formatter = logging.Formatter(self._FMT, datefmt=self._DATEFMT)

        fh = logging.FileHandler(self.log_path, encoding="utf-8")
        fh.setFormatter(formatter)
        self._log.addHandler(fh)

        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        self._log.addHandler(ch)

    # ------------------------------------------------------------------ #
    # Callback management
    # ------------------------------------------------------------------ #

    def add_callback(self, cb: LogCallback) -> None:
        """Register a callback ``fn(level_str, message)`` for live updates."""
        self._callbacks.append(cb)

    def remove_callback(self, cb: LogCallback) -> None:
        self._callbacks = [c for c in self._callbacks if c is not cb]

    # ------------------------------------------------------------------ #
    # Semantic log methods
    # ------------------------------------------------------------------ #

    def log_start(self, folder: str) -> None:
        self._emit("INFO", f"{'='*20} Organisation started – {folder} {'='*20}")

    def log_end(self, moved: int, skipped: int, errors: int) -> None:
        self._emit(
            "INFO",
            f"{'='*20} Done | Moved: {moved}  Skipped: {skipped}  Errors: {errors} {'='*20}",
        )

    def log_move(self, source: str, destination: str, category: str) -> None:
        self._emit("INFO", f"MOVE  [{category}]  {source}  →  {destination}")

    def log_undo(self, source: str, destination: str) -> None:
        self._emit("INFO", f"UNDO  {destination}  →  {source}")

    def log_skip(self, filename: str, reason: str) -> None:
        self._emit("WARNING", f"SKIP  {filename}  ({reason})")

    def log_error(self, message: str) -> None:
        self._emit("ERROR", message)

    def log_warning(self, message: str) -> None:
        self._emit("WARNING", message)

    def log_info(self, message: str) -> None:
        self._emit("INFO", message)

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _emit(self, level: str, message: str) -> None:
        getattr(self._log, level.lower())(message)
        for cb in self._callbacks:
            try:
                cb(level, message)
            except Exception:
                pass