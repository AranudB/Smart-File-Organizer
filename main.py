"""
main.py
Entry point for the Smart File Organizer.

Usage
-----
    python main.py           # launch the GUI (default)
    python main.py --cli     # future: headless CLI mode
"""
from __future__ import annotations
import sys
import tkinter as tk

from organizer.gui import OrganizerGUI


def launch_gui() -> None:
    root = tk.Tk()
    _app = OrganizerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    if "--cli" in sys.argv:
        print("CLI mode not yet implemented – launching GUI.")
    launch_gui()