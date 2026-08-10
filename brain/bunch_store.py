"""Reusable, library-scoped ordered track bunches."""
from __future__ import annotations

import time
import uuid
import builtins
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from brain import library_index
from brain.plan_types import Bunch

DEFAULT_INDEX = library_index.DEFAULT_INDEX
SCHEMA_ADDITIONS = """CREATE TABLE IF NOT EXISTS bunches (
 bunch_id TEXT PRIMARY KEY, label TEXT NOT NULL, ordered INTEGER NOT NULL DEFAULT 1,
 source TEXT NOT NULL DEFAULT 'human', notes TEXT NOT NULL DEFAULT '',
 created_at REAL NOT NULL, updated_at REAL NOT NULL, archived_at REAL);
CREATE TABLE IF NOT EXISTS bunch_members (
 bunch_id TEXT NOT NULL REFERENCES bunches(bunch_id) ON DELETE CASCADE,
 position INTEGER NOT NULL, track_id TEXT NOT NULL,
 PRIMARY KEY(bunch_id, position), UNIQUE(bunch_id, track_id));"""


@dataclass(frozen=True)
class MembersResult:
    bunch: Bunch
    auto_archived: bool
    member_count: int
    reason: str | None = None


@dataclass(frozen=True)
class ArchiveResult:
    bunch: Bunch
    auto_archived: bool
    member_count: int
    reason: str


def connect(db_path: Path | None = None):
    if db_path is None:
        db_path = (
            DEFAULT_INDEX
            if DEFAULT_INDEX != library_index.DEFAULT_INDEX
            else library_index.current_index_path()
        )
    db_path.parent.mkdir(parents=True, exist_ok=True)
    import sqlite3
    db = sqlite3.connect(db_path, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(SCHEMA_ADDITIONS)
    return db


def _ids(track_ids) -> list[str]:
    result = builtins.list(dict.fromkeys(str(item) for item in track_ids))
    return result


def _read(db, bunch_id: str) -> Bunch:
    row = db.execute("SELECT * FROM bunches WHERE bunch_id=?", (str(bunch_id),)).fetchone()
    if row is None:
        raise KeyError(bunch_id)
    members = tuple(r[0] for r in db.execute("SELECT track_id FROM bunch_members WHERE bunch_id=? ORDER BY position", (str(bunch_id),)))
    return Bunch(row["bunch_id"], row["label"], members, bool(row["ordered"]), row["source"], row["notes"], row["archived_at"] is not None)


def create(label, track_ids, ordered=True, source="human", notes="") -> Bunch:
    members = _ids(track_ids)
    if len(members) < 2:
        raise ValueError("a bunch requires at least 2 distinct tracks")
    if source not in {"human", "agent", "imported"}:
        raise ValueError(f"invalid bunch source: {source}")
    bunch_id, now = str(uuid.uuid4()), time.time()
    with closing(connect()) as db, db:
        db.execute("INSERT INTO bunches VALUES (?,?,?,?,?,?,?,NULL)", (bunch_id, str(label), int(bool(ordered)), source, str(notes), now, now))
        db.executemany("INSERT INTO bunch_members VALUES (?,?,?)", ((bunch_id, i, track_id) for i, track_id in enumerate(members)))
        return _read(db, bunch_id)


def get(bunch_id) -> Bunch:
    with closing(connect()) as db:
        return _read(db, str(bunch_id))


def list(include_archived=False) -> list[Bunch]:
    with closing(connect()) as db:
        query = "SELECT bunch_id FROM bunches" + ("" if include_archived else " WHERE archived_at IS NULL") + " ORDER BY created_at, bunch_id"
        return [_read(db, row[0]) for row in db.execute(query)]


def list_for_track(track_id: str) -> list[Bunch]:
    with closing(connect()) as db:
        rows = db.execute("SELECT b.bunch_id FROM bunches b JOIN bunch_members m USING(bunch_id) WHERE m.track_id=? AND b.archived_at IS NULL ORDER BY b.created_at", (track_id,))
        return [_read(db, row[0]) for row in rows]


def update_members(bunch_id, track_ids) -> MembersResult:
    members = _ids(track_ids)
    with closing(connect()) as db, db:
        _read(db, str(bunch_id))
        db.execute("DELETE FROM bunch_members WHERE bunch_id=?", (str(bunch_id),))
        db.executemany("INSERT INTO bunch_members VALUES (?,?,?)", ((str(bunch_id), i, track_id) for i, track_id in enumerate(members)))
        auto = len(members) < 2
        now = time.time()
        db.execute("UPDATE bunches SET updated_at=?, archived_at=CASE WHEN ? THEN coalesce(archived_at, ?) ELSE archived_at END WHERE bunch_id=?", (now, auto, now, str(bunch_id)))
        bunch = _read(db, str(bunch_id))
        return MembersResult(bunch, auto, len(members), "fewer_than_two_members" if auto else None)


def update(bunch_id, *, label=None, notes=None, ordered=None, track_ids=None) -> MembersResult:
    """Update a reusable bunch atomically, rewriting dense members if supplied."""
    members = None if track_ids is None else _ids(track_ids)
    with closing(connect()) as db, db:
        before = _read(db, str(bunch_id))
        if members is not None:
            db.execute("DELETE FROM bunch_members WHERE bunch_id=?", (str(bunch_id),))
            db.executemany(
                "INSERT INTO bunch_members VALUES (?,?,?)",
                ((str(bunch_id), i, track_id) for i, track_id in enumerate(members)),
            )
        else:
            members = list(before.track_ids)
        auto = len(members) < 2
        now = time.time()
        db.execute(
            "UPDATE bunches SET label=?, notes=?, ordered=?, updated_at=?, "
            "archived_at=CASE WHEN ? THEN coalesce(archived_at, ?) ELSE archived_at END "
            "WHERE bunch_id=?",
            (
                before.label if label is None else str(label),
                before.notes if notes is None else str(notes),
                int(before.ordered if ordered is None else bool(ordered)),
                now,
                auto,
                now,
                str(bunch_id),
            ),
        )
        bunch = _read(db, str(bunch_id))
        return MembersResult(
            bunch,
            auto,
            len(members),
            "fewer_than_two_members" if auto else None,
        )


def archive(bunch_id) -> ArchiveResult:
    with closing(connect()) as db, db:
        before = _read(db, str(bunch_id))
        db.execute("UPDATE bunches SET archived_at=coalesce(archived_at,?), updated_at=? WHERE bunch_id=?", (time.time(), time.time(), str(bunch_id)))
        return ArchiveResult(_read(db, str(bunch_id)), not before.archived, len(before.track_ids), "explicit_archive")
