"""Carry the library index (sqlite) between machines on the USB stick itself.

The library database (`brain/data/library.sqlite3`) is gitignored — it holds
personal-media metadata plus everything expensive or impossible to
regenerate elsewhere: Mixxx-analyzed bpm/key, human `dj_notes`, cached
lyrics/chroma/phrases/lyric-timelines, and beat-phase analysis. A fresh
clone on another machine starts empty; a stale clone diverges. Rather than
re-analyzing thousands of tracks per machine, keep a copy of the database
ON the music USB stick and merge it into whatever state the local machine
happens to be in.

Track identity is the absolute file path, and macOS mounts the same USB
volume at the same `/Volumes/<name>` on every Mac — so rows carry over
between Macs as-is. That makes the volume LABEL part of the collection
contract: a replacement drive must be named identically, or every track_id
(and every human dj_notes annotation keyed to one) orphans.

Linux mounts elsewhere (`/media/<user>/<label>`), so rows do not carry over
to Linux while identity is the absolute path. Where the database itself
lives is no longer hardcoded — see `brain/collection.py`, which records the
collection's id and this machine's mount base in the index — but making the
track rows themselves portable across platforms is a separate, deferred
change (see tests/test_music_collection_identity.py for what would have to
move atomically).

Usage (see docs/SETUP_NEW_MACHINE.md for the full walkthrough):

    # Once per machine: record where the collection is mounted here. Derives
    # the location from the configured scan roots when given no argument.
    uv run python -m brain.collection register

    # Machine A (source of truth), before unplugging the stick:
    uv run python -m brain.portable_library export

    # Machine B, after plugging the stick in:
    uv run python -m brain.portable_library import

Import is a MERGE, safe against any local state (empty, stale, diverged):
  - tracks missing locally are inserted whole
  - existing tracks only have NULL bpm/key/energy/duration filled in
  - dj_notes: imported only where the local note is empty; a local
    non-empty note is NEVER overwritten — conflicts are printed instead
  - lyrics/chroma/phrases/lyric_timelines/beat_phase rows are added only
    for tracks that have none locally
  - scan roots are unioned; scan_state is never touched
Running import twice is a no-op the second time.
"""
from __future__ import annotations

import argparse
import sqlite3
from contextlib import closing
from pathlib import Path

from brain.collection import CollectionNotConfiguredError, resolve_portable_db
from brain.library_index import DEFAULT_INDEX, connect

# No hardcoded volume label: the portable database's location is derived from
# the collection registered in the index (brain/collection.py), resolved at
# call time so a differently-mounted drive or a different machine works.

_TRACK_COLUMNS = (
    "track_id", "root", "size_bytes", "mtime_ns", "title", "artist", "album",
    "genre", "duration_seconds", "bpm", "key", "energy", "first_seen_at",
    "last_seen_at", "available", "tag_status", "dj_notes",
)
_FILL_IF_NULL = ("bpm", "key", "energy", "duration_seconds")

# Per-track cache tables that are expensive to regenerate: copied only for
# tracks that have no local row at all (fill-missing — no cross-machine
# clock trust needed, and a second import is a no-op).
_CACHE_TABLES = {
    "lyrics": ("track_id", "source", "fetched_at", "synced", "lyrics"),
    "chroma": ("track_id", "computed_at", "fingerprint"),
    "phrases": ("track_id", "analyzed_at", "payload"),
    "lyric_timelines": ("track_id", "computed_at", "source", "lrc", "segments"),
    "beat_phase": (
        "track_id", "analyzed_at", "snare_parity", "confidence", "bpm",
        "first_beat_seconds",
    ),
}


def export_db(local: Path = DEFAULT_INDEX, usb: Path | None = None) -> Path:
    """Copy the local index onto the USB stick (sqlite backup API — safe
    even while the playlist-editor GUI holds the database open).

    `usb` defaults to the registered collection's portable-database path,
    resolved at call time rather than from a hardcoded volume label.
    """
    if not local.exists():
        raise FileNotFoundError(f"no local library index at {local} — nothing to export")
    usb = usb if usb is not None else resolve_portable_db(local)
    usb.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(local)) as src, closing(sqlite3.connect(usb)) as dst:
        src.backup(dst)
    return usb


def import_db(usb: Path | None = None, local: Path = DEFAULT_INDEX) -> dict:
    """Merge the USB copy into the local index. Fill-missing only — see
    module docstring for the exact per-table policy.

    `usb` defaults to the registered collection's portable-database path,
    resolved at call time rather than from a hardcoded volume label.
    """
    usb = usb if usb is not None else resolve_portable_db(local)
    if not usb.exists():
        raise FileNotFoundError(
            f"no database on the USB stick at {usb} — run "
            "`uv run python -m brain.portable_library export` on the other "
            "machine first (or pass --usb-db if the volume name differs)"
        )
    # connect() creates/migrates schema on BOTH sides, so an old export or a
    # brand-new local clone both end up at the current schema before merging.
    summary = {
        "tracks_added": 0, "fields_filled": 0, "notes_imported": 0,
        "note_conflicts": [], "roots_added": 0,
        **{f"{table}_added": 0 for table in _CACHE_TABLES},
    }
    with closing(connect(usb)) as src, closing(connect(local)) as dst:
        src_tracks = src.execute(
            f"SELECT {','.join(_TRACK_COLUMNS)} FROM tracks"
        ).fetchall()
        local_rows = {
            row["track_id"]: row
            for row in dst.execute(f"SELECT {','.join(_TRACK_COLUMNS)} FROM tracks")
        }
        for row in src_tracks:
            local_row = local_rows.get(row["track_id"])
            if local_row is None:
                dst.execute(
                    f"INSERT INTO tracks ({','.join(_TRACK_COLUMNS)}) "
                    f"VALUES ({','.join('?' * len(_TRACK_COLUMNS))})",
                    tuple(row),
                )
                summary["tracks_added"] += 1
                continue
            for field in _FILL_IF_NULL:
                if local_row[field] is None and row[field] is not None:
                    dst.execute(
                        f"UPDATE tracks SET {field}=? WHERE track_id=?",
                        (row[field], row["track_id"]),
                    )
                    summary["fields_filled"] += 1
            incoming_note = (row["dj_notes"] or "").strip()
            local_note = (local_row["dj_notes"] or "").strip()
            if incoming_note and not local_note:
                dst.execute(
                    "UPDATE tracks SET dj_notes=? WHERE track_id=?",
                    (row["dj_notes"], row["track_id"]),
                )
                summary["notes_imported"] += 1
            elif incoming_note and local_note and incoming_note != local_note:
                # Never silently clobber a human note in either direction —
                # surface it and keep the local one.
                summary["note_conflicts"].append(row["track_id"])

        for table, columns in _CACHE_TABLES.items():
            have = {r[0] for r in dst.execute(f"SELECT track_id FROM {table}")}
            for row in src.execute(f"SELECT {','.join(columns)} FROM {table}"):
                if row["track_id"] in have:
                    continue
                dst.execute(
                    f"INSERT INTO {table} ({','.join(columns)}) "
                    f"VALUES ({','.join('?' * len(columns))})",
                    tuple(row),
                )
                summary[f"{table}_added"] += 1

        have_roots = {r[0] for r in dst.execute("SELECT path FROM roots")}
        for row in src.execute("SELECT path, added_at FROM roots"):
            if row["path"] not in have_roots:
                dst.execute(
                    "INSERT INTO roots(path, added_at) VALUES (?,?)",
                    (row["path"], row["added_at"]),
                )
                summary["roots_added"] += 1
        dst.commit()
    return summary


def _refresh_crate(local: Path = DEFAULT_INDEX) -> int:
    """Rewrite crate.json from the merged index so the GUI/curation pipeline
    sees the imported rows (crate.json is a lazily-synced export and would
    otherwise stay stale until the next scan)."""
    import json

    from brain.library import DEFAULT_CRATE_CACHE
    from brain.library_index import export_records

    records = export_records(local)
    DEFAULT_CRATE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_CRATE_CACHE.write_text(json.dumps(records, indent=2))
    return len(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("export", "import"))
    parser.add_argument("--usb-db", type=Path, default=None,
                        help="database path on the USB stick; defaults to the "
                             "registered collection's location")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX,
                        help="local library index path")
    args = parser.parse_args()

    try:
        usb_db = (
            args.usb_db if args.usb_db is not None
            else resolve_portable_db(args.index)
        )
    except CollectionNotConfiguredError as error:
        raise SystemExit(str(error)) from None

    if args.action == "export":
        destination = export_db(args.index, usb_db)
        print(f"exported {args.index} -> {destination}")
        return

    summary = import_db(usb_db, args.index)
    count = _refresh_crate(args.index)
    print(
        f"merged {usb_db} -> {args.index}: "
        f"{summary['tracks_added']} tracks added, "
        f"{summary['fields_filled']} missing bpm/key/energy/duration filled, "
        f"{summary['notes_imported']} dj_notes imported, "
        f"{summary['roots_added']} roots added"
    )
    for table in _CACHE_TABLES:
        added = summary[f"{table}_added"]
        if added:
            print(f"  {table}: {added} rows added")
    if summary["note_conflicts"]:
        print(
            f"  WARNING: {len(summary['note_conflicts'])} dj_notes conflict(s) "
            "-- local notes kept, imported versions ignored:"
        )
        for track_id in summary["note_conflicts"]:
            print(f"    {track_id}")
    print(f"crate.json refreshed ({count} tracks)")
    print("next: run the scan to reconcile availability -- see docs/SETUP_NEW_MACHINE.md")


if __name__ == "__main__":
    main()
