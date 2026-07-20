"""Convert .m4a playlist tracks to .mp3 siblings and swap the playlist over.

Why: the Rust chroma fingerprinter (Symphonia) cannot decode some .m4a
channel layouts — a permanent per-file gap in enrichment. Converting to mp3
with ffmpeg fixes it at the source. The original .m4a is KEPT (the user can
delete it later); the mp3 lands next to it with the same basename and the
same embedded tags, and — because it is the same audio — every piece of
per-track knowledge (bpm/key, dj_notes, lyrics, timelines, beat-phase)
carries over to the new file's database rows verbatim.

Only runs if ffmpeg is on PATH. Skips files whose mp3 sibling already
exists (never overwrites). Re-running is a no-op.

Usage:
    uv run python -m brain.convert_m4a            # all .m4a in the playlist
    uv run python -m brain.convert_m4a --dry-run  # report only
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import time
from contextlib import closing
from pathlib import Path

from brain.library_index import DEFAULT_INDEX, connect
from brain.portable_library import _CACHE_TABLES, _TRACK_COLUMNS


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def convert_file(m4a: Path) -> Path:
    """Write an mp3 sibling with the same tags. Never overwrites."""
    mp3 = m4a.with_suffix(".mp3")
    if mp3.exists():
        return mp3
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error", "-i", str(m4a),
            "-codec:a", "libmp3lame", "-qscale:a", "0",
            "-map_metadata", "0", "-id3v2_version", "3",
            str(mp3),
        ],
        check=True, capture_output=True,
    )
    return mp3


def adopt_metadata(db, old_id: str, new_id: str) -> dict:
    """Copy everything known about the .m4a onto the new .mp3's rows.

    Same audio -> same analysis: bpm/key/energy, dj_notes, and every cache
    table row apply unchanged. Fill-missing only (an existing mp3 row's
    non-empty fields are left alone), so re-running is safe.
    """
    copied = {"track": 0, **{t: 0 for t in _CACHE_TABLES}}
    old = db.execute(
        f"SELECT {','.join(_TRACK_COLUMNS)} FROM tracks WHERE track_id=?", (old_id,)
    ).fetchone()
    if old is None:
        raise ValueError(f"no library row for {old_id}")
    existing = db.execute(
        "SELECT track_id FROM tracks WHERE track_id=?", (new_id,)
    ).fetchone()
    stat = Path(new_id).stat()
    if existing is None:
        values = dict(zip(_TRACK_COLUMNS, tuple(old)))
        values.update(track_id=new_id, size_bytes=stat.st_size, mtime_ns=stat.st_mtime_ns)
        db.execute(
            f"INSERT INTO tracks ({','.join(_TRACK_COLUMNS)}) "
            f"VALUES ({','.join('?' * len(_TRACK_COLUMNS))})",
            tuple(values[c] for c in _TRACK_COLUMNS),
        )
        copied["track"] = 1
    else:
        # mp3 row already scanned in: carry the human/expensive fields over
        # where the mp3 side is missing them.
        db.execute(
            """UPDATE tracks SET
               bpm=COALESCE(bpm, ?), key=COALESCE(key, ?), energy=COALESCE(energy, ?),
               dj_notes=CASE WHEN dj_notes='' THEN ? ELSE dj_notes END
               WHERE track_id=?""",
            (old["bpm"], old["key"], old["energy"], old["dj_notes"], new_id),
        )
    for table, columns in _CACHE_TABLES.items():
        have = db.execute(
            f"SELECT track_id FROM {table} WHERE track_id=?", (new_id,)
        ).fetchone()
        if have:
            continue
        row = db.execute(
            f"SELECT {','.join(columns)} FROM {table} WHERE track_id=?", (old_id,)
        ).fetchone()
        if row is None:
            continue
        values = dict(zip(columns, tuple(row)))
        values["track_id"] = new_id
        db.execute(
            f"INSERT INTO {table} ({','.join(columns)}) "
            f"VALUES ({','.join('?' * len(columns))})",
            tuple(values[c] for c in columns),
        )
        copied[table] += 1
    return copied


def convert_playlist(*, dry_run: bool = False) -> dict:
    from brain.mix_directives import apply_directives, load_playlist

    if not ffmpeg_available():
        raise RuntimeError("ffmpeg not found on PATH — cannot convert")
    tracks = load_playlist()
    m4as = [t for t in tracks if t["track_id"].lower().endswith(".m4a")]
    summary = {"converted": [], "skipped_existing": [], "dry_run": dry_run}
    if not m4as:
        return summary
    if dry_run:
        summary["converted"] = [t["track_id"] for t in m4as]
        return summary

    new_order = []
    updated = []
    with closing(connect(DEFAULT_INDEX)) as db:
        replacements: dict[str, str] = {}
        for track in tracks:
            tid = track["track_id"]
            if not tid.lower().endswith(".m4a"):
                new_order.append(tid)
                updated.append(track)
                continue
            mp3 = Path(tid).with_suffix(".mp3")
            already = mp3.exists()
            convert_file(Path(tid))
            adopt_metadata(db, tid, str(mp3))
            replacements[tid] = str(mp3)
            (summary["skipped_existing"] if already else summary["converted"]).append(str(mp3))
            new_track = dict(track)
            new_track["track_id"] = str(mp3)
            updated.append(new_track)
            new_order.append(str(mp3))
        db.commit()
    apply_directives(updated, {}, new_order)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    summary = convert_playlist(dry_run=args.dry_run)
    if args.dry_run:
        for tid in summary["converted"]:
            print(f"would convert: {tid}")
        return
    for path in summary["converted"]:
        print(f"converted -> {path}")
    for path in summary["skipped_existing"]:
        print(f"mp3 already existed, adopted metadata -> {path}")
    if not summary["converted"] and not summary["skipped_existing"]:
        print("no .m4a tracks in the playlist")
    else:
        print("playlist swapped to the mp3 copies; originals kept in place")


if __name__ == "__main__":
    main()
