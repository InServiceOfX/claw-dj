"""Locates and opens Mixxx's own library database — the source of truth for
BPM/key/beatgrid once Mixxx has analyzed a track. Read-only: Mixxx holds this
file open while running, and we never want to risk writing to it.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

# macOS: Mixxx is sandboxed, so its data lives under ~/Library/Containers,
# not directly under ~/Library/Application Support. Confirmed against a real
# install; the other two are Mixxx's documented layout on Linux/Windows,
# unverified here.
CANDIDATE_PATHS = [
    Path.home()
    / "Library/Containers/org.mixxx.mixxx/Data/Library/Application Support/Mixxx/mixxxdb.sqlite",
    Path.home() / ".mixxx" / "mixxxdb.sqlite",  # Linux
    Path.home() / "AppData/Local/Mixxx/mixxxdb.sqlite",  # Windows
]


def find_mixxxdb() -> Path:
    for path in CANDIDATE_PATHS:
        if path.exists():
            return path
    raise FileNotFoundError(f"mixxxdb.sqlite not found in any of: {[str(p) for p in CANDIDATE_PATHS]}")


def connect_readonly(path: Path | None = None) -> sqlite3.Connection:
    db_path = path or find_mixxxdb()
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
