"""
history.py
Tracks every file move so operations can be undone.
History is optionally persisted to a JSON file across sessions.
"""
from __future__ import annotations
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class MoveRecord:
    """Immutable snapshot of a single file-move operation."""
    source:      str
    destination: str
    category:    str
    filename:    str
    timestamp:   str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat(timespec="seconds")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "MoveRecord":
        return cls(**data)

    def __str__(self) -> str:
        return (
            f"[{self.timestamp}]  {self.filename}  "
            f"{self.source!r}  →  {self.destination!r}"
        )


class MoveHistory:
    """
    Ordered list of :class:`MoveRecord` objects, with optional JSON persistence.

    The most-recently added record is always popped first (LIFO), making
    ``undo_last`` reverse operations in the correct order.
    """

    def __init__(self, history_file: str | None = None) -> None:
        """
        Args:
            history_file: If given, load existing history from this path on
                          startup and save after every mutation.
        """
        self._records: list[MoveRecord] = []
        self._history_file = history_file

        if history_file:
            os.makedirs(os.path.dirname(history_file), exist_ok=True)
            self._load()

    # ------------------------------------------------------------------ #
    # Write operations
    # ------------------------------------------------------------------ #

    def record(self, source: str, destination: str,
               category: str, filename: str) -> MoveRecord:
        """Append a new move record and persist if a history file is set."""
        rec = MoveRecord(source=source, destination=destination,
                         category=category, filename=filename)
        self._records.append(rec)
        self._save()
        return rec

    def pop_last(self) -> MoveRecord | None:
        """Remove and return the most-recent record, or *None* if empty."""
        if not self._records:
            return None
        rec = self._records.pop()
        self._save()
        return rec

    def clear(self) -> None:
        """Delete all records."""
        self._records.clear()
        self._save()

    # ------------------------------------------------------------------ #
    # Read operations
    # ------------------------------------------------------------------ #

    def all(self) -> list[MoveRecord]:
        """Snapshot of all records (oldest first)."""
        return list(self._records)

    def last(self) -> MoveRecord | None:
        """Peek at the most-recent record without removing it."""
        return self._records[-1] if self._records else None

    def __len__(self) -> int:
        return len(self._records)

    def __bool__(self) -> bool:
        return bool(self._records)

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #

    def _save(self) -> None:
        if not self._history_file:
            return
        try:
            with open(self._history_file, "w", encoding="utf-8") as fh:
                json.dump([r.to_dict() for r in self._records], fh, indent=2)
        except OSError as exc:
            print(f"[MoveHistory] Warning – could not save history: {exc}")

    def _load(self) -> None:
        if not self._history_file or not os.path.exists(self._history_file):
            return
        try:
            with open(self._history_file, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            self._records = [MoveRecord.from_dict(d) for d in raw]
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            print(f"[MoveHistory] Warning – could not load history: {exc}")
            self._records = []