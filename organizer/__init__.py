"""
Smart File Organizer – organizer package.

Core exports (no GUI dependency):
  FileClassifier  – extension-to-category classification
  MoveHistory     – LIFO undo history with optional JSON persistence
  FileLogger      – file + console + callback logging
  FileOrganizer   – core engine (scan / move / undo)

GUI import (requires tkinter):
  from organizer.gui import OrganizerGUI
"""
from .classifier import FileClassifier
from .history    import MoveHistory, MoveRecord
from .logger     import FileLogger
from .organizer  import FileOrganizer

__all__ = [
    "FileClassifier",
    "MoveHistory",
    "MoveRecord",
    "FileLogger",
    "FileOrganizer",
]