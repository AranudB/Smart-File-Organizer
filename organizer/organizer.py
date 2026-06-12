"""
organizer.py
Core engine: scans a folder, classifies files, moves them into subfolders,
and supports full undo via MoveHistory.
"""
from __future__ import annotations
import os
import shutil
import threading
from pathlib import Path
from typing import Callable

from .classifier import FileClassifier
from .history    import MoveHistory
from .logger     import FileLogger

# Callback signature: (current_index, total, current_filename)
ProgressCallback = Callable[[int, int, str], None]


class FileOrganizer:
    """
    High-level orchestrator that ties together :class:`FileClassifier`,
    :class:`MoveHistory`, and :class:`FileLogger`.

    Thread-safety
    -------------
    ``organize()`` is designed to be called from a background thread.
    ``stop()`` can be called from any thread to request an early exit.
    """

    def __init__(
        self,
        classifier: FileClassifier | None = None,
        history:    MoveHistory    | None = None,
        logger:     FileLogger     | None = None,
    ) -> None:
        self.classifier = classifier or FileClassifier()
        self.history    = history    or MoveHistory()
        self.logger     = logger     or FileLogger()

        self._stop_event = threading.Event()
        self._lock       = threading.Lock()
        self._running    = False

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def scan(self, folder: str) -> list[str]:
        """
        Return absolute paths of all top-level files in *folder*.
        Hidden files (dot-prefixed) are excluded.

        Raises
        ------
        NotADirectoryError
            If *folder* does not exist or is not a directory.
        """
        path = Path(folder)
        if not path.is_dir():
            raise NotADirectoryError(f"'{folder}' is not a valid directory.")
        return [
            str(p) for p in path.iterdir()
            if p.is_file() and not p.name.startswith(".")
        ]

    def organize(
        self,
        folder:      str,
        on_progress: ProgressCallback | None = None,
    ) -> dict[str, int]:
        """
        Classify and move every top-level file in *folder*.

        Parameters
        ----------
        folder:
            Path of the directory to organise.
        on_progress:
            Optional callback invoked for each file:
            ``fn(current_index, total, filename)``.

        Returns
        -------
        dict with keys ``moved``, ``skipped``, ``errors``.
        """
        stats = {"moved": 0, "skipped": 0, "errors": 0}

        try:
            files = self.scan(folder)
        except NotADirectoryError as exc:
            self.logger.log_error(str(exc))
            return stats

        if not files:
            self.logger.log_info(f"No files found in '{folder}'.")
            return stats

        self._stop_event.clear()
        with self._lock:
            self._running = True

        self.logger.log_start(folder)
        total = len(files)

        try:
            for idx, file_path in enumerate(files, start=1):
                if self._stop_event.is_set():
                    self.logger.log_info("Stopped by user request.")
                    break

                filename = os.path.basename(file_path)
                if on_progress:
                    on_progress(idx, total, filename)

                category = self.classifier.classify(filename)
                dest_dir  = os.path.join(folder, category)
                dest_path = self._resolve_conflict(os.path.join(dest_dir, filename))

                try:
                    os.makedirs(dest_dir, exist_ok=True)
                    shutil.move(file_path, dest_path)

                    self.history.record(
                        source=file_path,
                        destination=dest_path,
                        category=category,
                        filename=os.path.basename(dest_path),
                    )
                    self.logger.log_move(file_path, dest_path, category)
                    stats["moved"] += 1

                except PermissionError:
                    self.logger.log_error(f"Permission denied – '{filename}'")
                    stats["errors"] += 1
                except shutil.Error as exc:
                    self.logger.log_error(f"Move failed for '{filename}': {exc}")
                    stats["errors"] += 1
                except OSError as exc:
                    self.logger.log_error(f"OS error for '{filename}': {exc}")
                    stats["errors"] += 1
        finally:
            with self._lock:
                self._running = False
            self.logger.log_end(stats["moved"], stats["skipped"], stats["errors"])

        return stats

    def undo_last(self) -> bool:
        """
        Reverse the most-recent move.

        Returns
        -------
        ``True`` on success, ``False`` if history is empty or the move failed.
        """
        record = self.history.pop_last()
        if record is None:
            self.logger.log_warning("Nothing to undo – history is empty.")
            return False
        return self._do_undo(record)

    def undo_all(self) -> int:
        """
        Reverse all recorded moves (newest first).

        Returns
        -------
        Number of successful undo operations.
        """
        count = 0
        while self.history:
            record = self.history.pop_last()
            if record and self._do_undo(record):
                count += 1
        return count

    def stop(self) -> None:
        """Signal ``organize()`` to abort after the current file."""
        self._stop_event.set()

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    def _do_undo(self, record) -> bool:
        """Physically move the file back to its original location."""
        if not os.path.exists(record.destination):
            self.logger.log_error(
                f"Undo failed – '{record.destination}' no longer exists."
            )
            return False
        try:
            src_dir = os.path.dirname(record.source)
            if src_dir:
                os.makedirs(src_dir, exist_ok=True)
            shutil.move(record.destination, record.source)
            self.logger.log_undo(record.source, record.destination)

            # Clean up empty category folder
            dest_dir = os.path.dirname(record.destination)
            try:
                if os.path.isdir(dest_dir) and not os.listdir(dest_dir):
                    os.rmdir(dest_dir)
            except OSError:
                pass

            return True
        except (PermissionError, OSError, shutil.Error) as exc:
            self.logger.log_error(f"Undo failed: {exc}")
            return False

    @staticmethod
    def _resolve_conflict(path: str) -> str:
        """
        If *path* already exists, append ``_1``, ``_2``, … to the stem until a
        free slot is found.

        ``document.pdf`` → ``document_1.pdf`` → ``document_2.pdf`` …
        """
        if not os.path.exists(path):
            return path
        base, ext = os.path.splitext(path)
        counter = 1
        while True:
            candidate = f"{base}_{counter}{ext}"
            if not os.path.exists(candidate):
                return candidate
            counter += 1