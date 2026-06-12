"""
classifier.py
Classifies files into semantic categories based on their extension.
"""
from __future__ import annotations
import os


class FileClassifier:
    """
    Maps file extensions to human-readable categories.

    The default extension map covers the most common file types.
    Custom rules can be injected at construction time or added later via
    ``add_rule()``.
    """

    EXTENSION_MAP: dict[str, set[str]] = {
        "Images":        {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg",
                          ".webp", ".tiff", ".ico", ".raw", ".heic", ".avif"},
        "Documents":     {".pdf", ".doc", ".docx", ".txt", ".odt", ".rtf",
                          ".md", ".tex", ".epub", ".pages"},
        "Spreadsheets":  {".xls", ".xlsx", ".csv", ".ods", ".numbers"},
        "Presentations": {".ppt", ".pptx", ".odp", ".key"},
        "Videos":        {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv",
                          ".webm", ".m4v", ".3gp", ".ts"},
        "Audio":         {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a",
                          ".wma", ".opus", ".aiff"},
        "Archives":      {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2",
                          ".xz", ".zst", ".cab"},
        "Code":          {".py", ".js", ".ts", ".html", ".css", ".java",
                          ".cpp", ".c", ".h", ".hpp", ".php", ".json", ".xml",
                          ".yaml", ".yml", ".sh", ".bat", ".ps1", ".rb",
                          ".go", ".rs", ".swift", ".kt", ".lua", ".sql"},
        "Executables":   {".exe", ".msi", ".dmg", ".deb", ".rpm", ".appimage",
                          ".apk"},
        "Fonts":         {".ttf", ".otf", ".woff", ".woff2", ".eot"},
        "Design":        {".psd", ".ai", ".xd", ".fig", ".sketch", ".xcf",
                          ".blend", ".fbx", ".obj"},
    }

    def __init__(self, custom_rules: dict[str, set[str]] | None = None):
        """
        Args:
            custom_rules: Optional ``{category: {ext, ...}}`` to merge into the
                          default map.  Unknown categories are created on the fly.
        """
        # Deep-copy so instances are independent
        self._rules: dict[str, set[str]] = {
            cat: exts.copy() for cat, exts in self.EXTENSION_MAP.items()
        }
        if custom_rules:
            for category, extensions in custom_rules.items():
                self._rules.setdefault(category, set()).update(extensions)

        self._rebuild_index()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def classify(self, filename: str) -> str:
        """Return the category name for *filename*, or ``"Others"``."""
        _, ext = os.path.splitext(filename)
        return self._index.get(ext.lower(), "Others")

    def get_categories(self) -> list[str]:
        """Sorted list of all known categories, including ``"Others"``."""
        return sorted(self._rules.keys()) + ["Others"]

    def add_rule(self, extension: str, category: str) -> None:
        """Map *extension* (with or without leading dot) to *category*."""
        ext = self._normalise_ext(extension)
        self._rules.setdefault(category, set()).add(ext)
        self._index[ext] = category

    def remove_rule(self, extension: str) -> None:
        """Remove the mapping for *extension* (silent if absent)."""
        ext = self._normalise_ext(extension)
        category = self._index.pop(ext, None)
        if category:
            self._rules.get(category, set()).discard(ext)

    def rules_for(self, category: str) -> set[str]:
        """Return the set of extensions mapped to *category*."""
        return self._rules.get(category, set()).copy()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _rebuild_index(self) -> None:
        """Rebuild the fast extension → category reverse-lookup."""
        self._index: dict[str, str] = {}
        for category, extensions in self._rules.items():
            for ext in extensions:
                self._index[ext.lower()] = category

    @staticmethod
    def _normalise_ext(extension: str) -> str:
        ext = extension.lower().strip()
        return ext if ext.startswith(".") else f".{ext}"