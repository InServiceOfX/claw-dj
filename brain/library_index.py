"""Persistent incremental index for local music files.

SQLite is the source of scan state; crate.json remains the compatibility
export consumed by the existing curation pipeline.
"""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import closing
from pathlib import Path

from brain.library import DEFAULT_CRATE_CACHE

DEFAULT_INDEX = DEFAULT_CRATE_CACHE.parent / "library.sqlite3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS tracks (
    track_id TEXT PRIMARY KEY,
    root TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    mtime_ns INTEGER NOT NULL,
    title TEXT NOT NULL,
    artist TEXT NOT NULL,
    album TEXT,
    genre TEXT,
    duration_seconds REAL,
    bpm REAL,
    key TEXT,
    energy TEXT,
    first_seen_at REAL NOT NULL,
    last_seen_at REAL NOT NULL,
    available INTEGER NOT NULL DEFAULT 1,
    tag_status TEXT NOT NULL DEFAULT 'ok'
);
CREATE INDEX IF NOT EXISTS tracks_available ON tracks(available);
CREATE INDEX IF NOT EXISTS tracks_first_seen ON tracks(first_seen_at);
CREATE TABLE IF NOT EXISTS roots (
    path TEXT PRIMARY KEY,
    added_at REAL NOT NULL,
    last_scan_at REAL
);
-- Per-track enrichment, filled only for curated/finalized sets (never the
-- full crate) and only when missing — see brain/enrich_set.py.
CREATE TABLE IF NOT EXISTS lyrics (
    track_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    fetched_at REAL NOT NULL,
    synced INTEGER NOT NULL DEFAULT 0,
    lyrics TEXT
);
CREATE TABLE IF NOT EXISTS chroma (
    track_id TEXT PRIMARY KEY,
    computed_at REAL NOT NULL,
    fingerprint TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS phrases (
    track_id TEXT PRIMARY KEY,
    analyzed_at REAL NOT NULL,
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scan_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    running INTEGER NOT NULL DEFAULT 0,
    started_at REAL,
    finished_at REAL,
    discovered INTEGER NOT NULL DEFAULT 0,
    processed INTEGER NOT NULL DEFAULT 0,
    new_count INTEGER NOT NULL DEFAULT 0,
    changed_count INTEGER NOT NULL DEFAULT 0,
    unchanged_count INTEGER NOT NULL DEFAULT 0,
    missing_count INTEGER NOT NULL DEFAULT 0,
    skipped_count INTEGER NOT NULL DEFAULT 0,
    error TEXT
);
INSERT OR IGNORE INTO scan_state(id) VALUES (1);
"""


def connect(path: Path = DEFAULT_INDEX) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=30)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    return db


def configured_roots(path: Path = DEFAULT_INDEX) -> list[str]:
    with closing(connect(path)) as db:
        return [row["path"] for row in db.execute("SELECT path FROM roots ORDER BY path")]


def scan_status(path: Path = DEFAULT_INDEX) -> dict:
    with closing(connect(path)) as db:
        state = dict(db.execute("SELECT * FROM scan_state WHERE id = 1").fetchone())
        state["roots"] = [row["path"] for row in db.execute("SELECT path FROM roots ORDER BY path")]
        state["track_count"] = db.execute(
            "SELECT count(*) FROM tracks WHERE available = 1"
        ).fetchone()[0]
        state["untagged_count"] = db.execute(
            "SELECT count(*) FROM tracks WHERE available = 1 AND tag_status != 'ok'"
        ).fetchone()[0]
        state["new_since_last_scan"] = state["new_count"]
        return state


def export_records(path: Path = DEFAULT_INDEX) -> list[dict]:
    fields = (
        "track_id", "title", "artist", "album", "genre", "duration_seconds",
        "size_bytes", "bpm", "key", "energy",
    )
    with closing(connect(path)) as db:
        rows = db.execute(
            "SELECT * FROM tracks WHERE available = 1 ORDER BY track_id"
        ).fetchall()
    return [{field: row[field] for field in fields if row[field] is not None} for row in rows]


def bootstrap_analysis(db: sqlite3.Connection, crate_path: Path = DEFAULT_CRATE_CACHE) -> None:
    """Seed analysis fields from a pre-index crate during first migration."""
    if not crate_path.exists():
        return
    try:
        records = json.loads(crate_path.read_text())
    except (OSError, json.JSONDecodeError):
        return
    for record in records:
        db.execute(
            "UPDATE tracks SET bpm=coalesce(bpm, ?), key=coalesce(key, ?), "
            "energy=coalesce(energy, ?) WHERE track_id=?",
            (record.get("bpm"), record.get("key"), record.get("energy"), record["track_id"]),
        )


def begin_scan(db: sqlite3.Connection, discovered: int) -> float:
    now = time.time()
    db.execute(
        "UPDATE scan_state SET running=1, started_at=?, finished_at=NULL, "
        "discovered=?, processed=0, new_count=0, changed_count=0, "
        "unchanged_count=0, missing_count=0, skipped_count=0, error=NULL WHERE id=1",
        (now, discovered),
    )
    db.commit()
    return now
