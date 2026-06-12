"""
test_organizer.py
Unit tests for the Smart File Organizer back-end.

Run with:
    python -m pytest test_organizer.py -v
    # or
    python -m unittest test_organizer -v
"""
from __future__ import annotations
import os
import shutil
import tempfile
import unittest

from organizer.classifier import FileClassifier
from organizer.history    import MoveHistory, MoveRecord
from organizer.logger     import FileLogger
from organizer.organizer  import FileOrganizer


# ─────────────────────────────────────────────────────────────────────────────
class TestFileClassifier(unittest.TestCase):

    def setUp(self):
        self.clf = FileClassifier()

    def test_known_extensions(self):
        cases = {
            "photo.jpg":      "Images",
            "report.pdf":     "Documents",
            "song.mp3":       "Audio",
            "movie.mkv":      "Videos",
            "archive.zip":    "Archives",
            "script.py":      "Code",
            "sheet.xlsx":     "Spreadsheets",
            "slides.pptx":    "Presentations",
            "app.exe":        "Executables",
            "font.ttf":       "Fonts",
        }
        for filename, expected in cases.items():
            with self.subTest(filename=filename):
                self.assertEqual(self.clf.classify(filename), expected)

    def test_unknown_extension_returns_others(self):
        self.assertEqual(self.clf.classify("mystery.xyz123"), "Others")

    def test_case_insensitive(self):
        self.assertEqual(self.clf.classify("IMAGE.JPG"),  "Images")
        self.assertEqual(self.clf.classify("IMAGE.Jpg"),  "Images")

    def test_add_rule(self):
        self.clf.add_rule(".log", "Logs")
        self.assertEqual(self.clf.classify("app.log"), "Logs")

    def test_remove_rule(self):
        self.clf.add_rule(".log", "Logs")
        self.clf.remove_rule(".log")
        self.assertEqual(self.clf.classify("app.log"), "Others")

    def test_custom_rules_at_init(self):
        clf = FileClassifier(custom_rules={"Custom": {".foo", ".bar"}})
        self.assertEqual(clf.classify("x.foo"), "Custom")
        self.assertEqual(clf.classify("y.bar"), "Custom")

    def test_get_categories_includes_others(self):
        self.assertIn("Others", self.clf.get_categories())


# ─────────────────────────────────────────────────────────────────────────────
class TestMoveHistory(unittest.TestCase):

    def setUp(self):
        self.tmp  = tempfile.mkdtemp()
        self.hist = MoveHistory()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_record_and_length(self):
        self.hist.record("/a/b.txt", "/c/d.txt", "Docs", "d.txt")
        self.assertEqual(len(self.hist), 1)

    def test_pop_last_lifo_order(self):
        self.hist.record("/a/1.txt", "/dst/1.txt", "A", "1.txt")
        self.hist.record("/a/2.txt", "/dst/2.txt", "B", "2.txt")
        rec = self.hist.pop_last()
        self.assertEqual(rec.filename, "2.txt")
        self.assertEqual(len(self.hist), 1)

    def test_pop_last_on_empty_returns_none(self):
        self.assertIsNone(self.hist.pop_last())

    def test_clear(self):
        self.hist.record("/a/x.txt", "/b/x.txt", "X", "x.txt")
        self.hist.clear()
        self.assertEqual(len(self.hist), 0)

    def test_persistence(self):
        hist_file = os.path.join(self.tmp, "history.json")
        h1 = MoveHistory(history_file=hist_file)
        h1.record("/src/a.txt", "/dst/a.txt", "Docs", "a.txt")

        h2 = MoveHistory(history_file=hist_file)
        self.assertEqual(len(h2), 1)
        self.assertEqual(h2.last().filename, "a.txt")

    def test_move_record_defaults_timestamp(self):
        rec = MoveRecord(source="/s", destination="/d", category="C", filename="f")
        self.assertTrue(rec.timestamp)   # non-empty


# ─────────────────────────────────────────────────────────────────────────────
class TestFileOrganizer(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.logger = FileLogger(log_dir=os.path.join(self.tmp, "logs"))
        self.organizer = FileOrganizer(logger=self.logger)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ── helper ──────────────────────────────────────────────────────────

    def _touch(self, name: str) -> str:
        """Create an empty file in the temp dir and return its path."""
        path = os.path.join(self.tmp, name)
        open(path, "w").close()
        return path

    # ── scan ────────────────────────────────────────────────────────────

    def test_scan_returns_files(self):
        self._touch("a.txt")
        self._touch("b.pdf")
        files = self.organizer.scan(self.tmp)
        names = {os.path.basename(f) for f in files}
        self.assertIn("a.txt", names)
        self.assertIn("b.pdf", names)

    def test_scan_excludes_hidden(self):
        self._touch(".hidden")
        files = self.organizer.scan(self.tmp)
        names = {os.path.basename(f) for f in files}
        self.assertNotIn(".hidden", names)

    def test_scan_invalid_dir_raises(self):
        with self.assertRaises(NotADirectoryError):
            self.organizer.scan("/nonexistent_path_xyz")

    # ── organize ────────────────────────────────────────────────────────

    def test_organize_moves_files(self):
        self._touch("photo.jpg")
        self._touch("report.pdf")
        stats = self.organizer.organize(self.tmp)
        self.assertEqual(stats["moved"], 2)
        self.assertEqual(stats["errors"], 0)
        self.assertTrue(os.path.isfile(
            os.path.join(self.tmp, "Images", "photo.jpg")
        ))
        self.assertTrue(os.path.isfile(
            os.path.join(self.tmp, "Documents", "report.pdf")
        ))

    def test_organize_conflict_resolution(self):
        """Two files with the same name end up as file.ext and file_1.ext."""
        # Pre-create the destination so there is a conflict
        os.makedirs(os.path.join(self.tmp, "Images"), exist_ok=True)
        with open(os.path.join(self.tmp, "Images", "photo.jpg"), "w") as f:
            f.write("existing")
        self._touch("photo.jpg")
        self.organizer.organize(self.tmp)
        self.assertTrue(os.path.isfile(
            os.path.join(self.tmp, "Images", "photo_1.jpg")
        ))

    def test_organize_unknown_goes_to_others(self):
        self._touch("mystery.xyz")
        self.organizer.organize(self.tmp)
        self.assertTrue(os.path.isfile(
            os.path.join(self.tmp, "Others", "mystery.xyz")
        ))

    def test_organize_empty_folder(self):
        stats = self.organizer.organize(self.tmp)
        self.assertEqual(stats["moved"], 0)

    def test_organize_records_history(self):
        self._touch("song.mp3")
        self.organizer.organize(self.tmp)
        self.assertEqual(len(self.organizer.history), 1)

    # ── undo ────────────────────────────────────────────────────────────

    def test_undo_last_restores_file(self):
        self._touch("doc.docx")
        self.organizer.organize(self.tmp)
        self.organizer.undo_last()
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "doc.docx")))

    def test_undo_last_on_empty_history_returns_false(self):
        self.assertFalse(self.organizer.undo_last())

    def test_undo_all(self):
        self._touch("a.jpg")
        self._touch("b.mp3")
        self.organizer.organize(self.tmp)
        count = self.organizer.undo_all()
        self.assertEqual(count, 2)
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "a.jpg")))
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "b.mp3")))

    def test_undo_removes_empty_category_folder(self):
        self._touch("only.jpg")
        self.organizer.organize(self.tmp)
        self.organizer.undo_last()
        self.assertFalse(os.path.isdir(os.path.join(self.tmp, "Images")))

    # ── progress callback ───────────────────────────────────────────────

    def test_progress_callback_called(self):
        calls = []
        self._touch("x.txt")
        self._touch("y.pdf")
        self.organizer.organize(self.tmp, on_progress=lambda c, t, n: calls.append(c))
        self.assertEqual(len(calls), 2)


# ─────────────────────────────────────────────────────────────────────────────
class TestFileLogger(unittest.TestCase):

    def setUp(self):
        self.tmp    = tempfile.mkdtemp()
        self.logger = FileLogger(log_dir=self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_log_file_created(self):
        logs = [f for f in os.listdir(self.tmp) if f.endswith(".log")]
        self.assertEqual(len(logs), 1)

    def test_callback_invoked(self):
        received = []
        self.logger.add_callback(lambda lvl, msg: received.append((lvl, msg)))
        self.logger.log_info("hello")
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0][0], "INFO")

    def test_remove_callback(self):
        received = []
        cb = lambda lvl, msg: received.append(msg)
        self.logger.add_callback(cb)
        self.logger.remove_callback(cb)
        self.logger.log_info("should not appear")
        self.assertEqual(len(received), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)