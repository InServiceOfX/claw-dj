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

from brain import collection_registry
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
    dj_notes TEXT NOT NULL DEFAULT '',
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
-- The music collection (normally one external drive) and where it is mounted
-- on THIS machine. `collection_id` is a UUID carried in a marker file on the
-- collection itself, so every machine derives the same id for the same drive
-- -- it is deliberately not the volume label, which is renameable. Recorded
-- as data so the portable-database location is re-derivable without reading
-- code. See brain/collection.py and docs/SETUP_NEW_MACHINE.md.
CREATE TABLE IF NOT EXISTS collections (
    collection_id TEXT PRIMARY KEY,
    mount_base TEXT NOT NULL,
    data_dir TEXT NOT NULL,
    volume_label TEXT,
    created_at REAL NOT NULL,
    last_seen_at REAL
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
-- Cached real onset/waveform analysis (brain.onset_analysis): which beat
-- parity (even/odd, mod 2) carries the snare/backbeat, so build_mix_plan
-- can pick cue points and ride lengths that land actual drum hits
-- together, not just generic beatgrid ticks. See docs/DJ_STYLE_GUIDE.md.
CREATE TABLE IF NOT EXISTS beat_phase (
    track_id TEXT PRIMARY KEY,
    analyzed_at REAL NOT NULL,
    snare_parity INTEGER NOT NULL,
    confidence REAL NOT NULL,
    bpm REAL NOT NULL,
    first_beat_seconds REAL NOT NULL
);
-- Synced-lyric timeline: raw LRC plus detected verse/chorus segments with
-- vocal-start times snapped to the Mixxx beatgrid — the cut points the
-- verse-tour / lyric-aware transitions build on. See brain/lyric_timeline.py.
CREATE TABLE IF NOT EXISTS lyric_timelines (
    track_id TEXT PRIMARY KEY,
    computed_at REAL NOT NULL,
    source TEXT NOT NULL,
    lrc TEXT,
    segments TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bunches (
    bunch_id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    ordered INTEGER NOT NULL DEFAULT 1,
    source TEXT NOT NULL DEFAULT 'human',
    notes TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    archived_at REAL
);
CREATE TABLE IF NOT EXISTS bunch_members (
    bunch_id TEXT NOT NULL REFERENCES bunches(bunch_id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    track_id TEXT NOT NULL,
    PRIMARY KEY (bunch_id, position),
    UNIQUE (bunch_id, track_id)
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


def current_index_path(path: Path | None = None) -> Path:
    """Resolve the active SQLite at call time unless a caller chose a path."""
    if path is not None:
        return Path(path)
    return collection_registry.active_index_path(
        registry_path=collection_registry.DEFAULT_REGISTRY,
        fallback=DEFAULT_INDEX,
    )


# Paths that already received SCHEMA + additive migrations in this process.
# Re-running executescript(SCHEMA) on every GUI poll (/api/ingest every ~750ms)
# contending with a long incremental_scan write is what produced
# "database is locked" traceback storms during "Check for new music".
_SCHEMA_READY: set[str] = set()


def _path_key(path: Path) -> str:
    try:
        return str(path.expanduser().resolve())
    except OSError:
        return str(path.expanduser())


def _apply_schema(db: sqlite3.Connection) -> None:
    """Create tables and run additive migrations (write-heavy; call sparingly)."""
    db.executescript(SCHEMA)
    # Additive migration for indexes created before human DJ annotations.
    columns = {row[1] for row in db.execute("PRAGMA table_info(tracks)")}
    if "dj_notes" not in columns:
        db.execute("ALTER TABLE tracks ADD COLUMN dj_notes TEXT NOT NULL DEFAULT ''")
    # Additive migration for non-fatal scan warnings. Distinct from `error`,
    # which means the scan failed: a warning means the scan finished and
    # deliberately skipped something (e.g. a suspect availability flip), so
    # the GUI can surface it without reporting a failure.
    scan_columns = {row[1] for row in db.execute("PRAGMA table_info(scan_state)")}
    if "warnings" not in scan_columns:
        db.execute("ALTER TABLE scan_state ADD COLUMN warnings TEXT NOT NULL DEFAULT ''")
    # Additive migration for indexes whose `collections` table predates the
    # separately-recorded data directory. Defaults to empty rather than to
    # `<mount_base>/clawdj`, so a stale row can never silently point the
    # portable database at the wrong place — re-register to repopulate it.
    collection_columns = {row[1] for row in db.execute("PRAGMA table_info(collections)")}
    if collection_columns and "data_dir" not in collection_columns:
        db.execute("ALTER TABLE collections ADD COLUMN data_dir TEXT NOT NULL DEFAULT ''")
    db.commit()


def connect(
    path: Path | None = None,
    *,
    ensure_schema: bool = True,
    timeout: float = 60.0,
) -> sqlite3.Connection:
    """Open the library index.

    ``ensure_schema=True`` (default) applies CREATE/migrations once per path
    per process. Pass ``ensure_schema=False`` for hot read paths (scan status
    polls) so they do not take a schema write lock while a scan is running.
    """
    path = current_index_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    key = _path_key(path)
    db = sqlite3.connect(path, timeout=timeout)
    db.row_factory = sqlite3.Row
    # Milliseconds. Independent of the connect() timeout (seconds spent waiting
    # for a locked database before OperationalError).
    db.execute("PRAGMA busy_timeout = 60000")
    # Per-connection and ineffective once a transaction has begun.
    db.execute("PRAGMA foreign_keys = ON")
    # Concurrent readers during a long scan. Harmless no-op if the volume
    # cannot support WAL (some network mounts); ignore failures.
    try:
        db.execute("PRAGMA journal_mode=WAL")
    except sqlite3.Error:
        pass
    if key not in _SCHEMA_READY:
        if ensure_schema:
            _apply_schema(db)
            _SCHEMA_READY.add(key)
        else:
            # Hot read path (status polls): never rewrite schema if the writer
            # already created tables. Only CREATE when the file is brand new.
            try:
                db.execute("SELECT 1 FROM scan_state WHERE id = 1").fetchone()
            except sqlite3.Error:
                _apply_schema(db)
            _SCHEMA_READY.add(key)
    return db


def configured_roots(path: Path | None = None) -> list[str]:
    with closing(connect(path)) as db:
        return [row["path"] for row in db.execute("SELECT path FROM roots ORDER BY path")]


def _locked_scan_status_placeholder() -> dict:
    """Safe payload when the index is briefly unreadable during a write."""
    return {
        "running": 1,
        "started_at": None,
        "finished_at": None,
        "discovered": 0,
        "processed": 0,
        "new_count": 0,
        "changed_count": 0,
        "unchanged_count": 0,
        "missing_count": 0,
        "skipped_count": 0,
        "error": None,
        "warnings": "",
        "roots": [],
        "track_count": 0,
        "untagged_count": 0,
        "new_since_last_scan": 0,
        "locked": True,
    }


def scan_status(path: Path | None = None) -> dict:
    """Read scan progress without taking a schema write lock.

    GUI polls this every ~750ms during "Check for new music". Competing with
    the scan writer's commits used to raise sqlite3.OperationalError and
    dump ThreadingHTTPServer tracebacks in the start.sh terminal.
    """
    index = current_index_path(path)
    try:
        with closing(connect(index, ensure_schema=False, timeout=5.0)) as db:
            row = db.execute("SELECT * FROM scan_state WHERE id = 1").fetchone()
            if row is None:
                return _locked_scan_status_placeholder()
            state = dict(row)
            state["roots"] = [
                r["path"] for r in db.execute("SELECT path FROM roots ORDER BY path")
            ]
            state["track_count"] = db.execute(
                "SELECT count(*) FROM tracks WHERE available = 1"
            ).fetchone()[0]
            state["untagged_count"] = db.execute(
                "SELECT count(*) FROM tracks WHERE available = 1 AND tag_status != 'ok'"
            ).fetchone()[0]
            state["new_since_last_scan"] = state["new_count"]
            state["locked"] = False
            return state
    except sqlite3.OperationalError as error:
        message = str(error).lower()
        if "locked" in message or "busy" in message:
            return _locked_scan_status_placeholder()
        raise


def export_records(path: Path | None = None) -> list[dict]:
    fields = (
        "track_id", "title", "artist", "album", "genre", "duration_seconds",
        "size_bytes", "bpm", "key", "energy",
        "dj_notes",
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
