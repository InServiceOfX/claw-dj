"""Scans one or more local music directories' tags into brain/library.py's crate
cache. Metadata only (title/artist/album/genre via mutagen) — no audio
analysis. BPM/key stay whatever Mixxx already produced if a prior crate row
exists for the same absolute path.

The cache (brain/data/crate.json) is gitignored — a personal media library's
track listing doesn't belong committed to a public repo.

Files still downloading or mid-copy are excluded: partial-download markers
(`song.mp3.part` next to `song.mp3`), zero-byte placeholders, and files whose
mtime is younger than --min-age-seconds. Skipped paths are written to
brain/data/scan_skipped.json so a later rescan can pick them up.

Usage:
    uv run python -m brain.scan_library /Volumes/USB322FD/Music/RnB \\
        /Volumes/USB322FD/Music/HipHop
    uv run python -m brain.scan_library ... --catalog   # also write slim agent catalog
"""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from mutagen import File as MutagenFile

from brain.library import DEFAULT_CRATE_CACHE
from brain.library_index import DEFAULT_INDEX, begin_scan, bootstrap_analysis, connect, export_records

AUDIO_EXTENSIONS = {".mp3", ".flac", ".m4a", ".wav", ".aiff"}

# Sibling suffixes download tools leave next to (or instead of) the final
# file while it is still transferring. Firefox writes a zero-byte final name
# plus `<name>.part`; qBittorrent uses `.!qB`; aria2 uses `.aria2`.
INCOMPLETE_MARKER_SUFFIXES = (".part", ".crdownload", ".!qB", ".aria2")

DEFAULT_SKIPPED_REPORT = DEFAULT_CRATE_CACHE.parent / "scan_skipped.json"


def _first(tags: dict, key: str) -> str | None:
    values = tags.get(key)
    return values[0] if values else None


def incomplete_reason(path: Path, *, min_age_seconds: float, now: float) -> str | None:
    """Why this audio file should be treated as still transferring, else None."""
    for marker in INCOMPLETE_MARKER_SUFFIXES:
        if path.with_name(path.name + marker).exists():
            return f"sibling {marker} marker"
    try:
        stat = path.stat()
    except OSError:
        return "unreadable (stat failed)"
    if stat.st_size == 0:
        return "zero-byte placeholder"
    if min_age_seconds > 0 and now - stat.st_mtime < min_age_seconds:
        return f"modified {int(now - stat.st_mtime)}s ago (< min age)"
    return None


def _read_record(
    path: Path, *, min_age_seconds: float, now: float
) -> tuple[str, dict] | None:
    reason = incomplete_reason(path, min_age_seconds=min_age_seconds, now=now)
    if reason is not None:
        return ("skip", {"track_id": str(path), "reason": reason})
    try:
        tagged = MutagenFile(path, easy=True)
    except Exception:
        return None
    size_bytes = path.stat().st_size
    duration = getattr(getattr(tagged, "info", None), "length", None)
    record = {
        "track_id": str(path),
        "title": path.stem,
        "artist": "Unknown Artist",
        "album": None,
        "genre": None,
        "duration_seconds": round(duration, 1) if duration else None,
        "size_bytes": size_bytes,
    }
    if tagged is not None:
        # Untagged audio still counts as available; name falls back to filename.
        tags = tagged.tags or {}
        record["title"] = _first(tags, "title") or path.stem
        record["artist"] = _first(tags, "artist") or "Unknown Artist"
        record["album"] = _first(tags, "album")
        record["genre"] = _first(tags, "genre")
    return ("ok", record)


def scan(
    root: Path,
    *,
    min_age_seconds: float = 300,
    skipped: list[dict] | None = None,
    workers: int = 8,
    progress_every: int = 500,
) -> list[dict]:
    """Read embedded tags only — no decoding. Tag reads run on a thread pool:
    on a contended USB drive the wall time is dominated by per-file I/O waits
    (observed ~1 s/file serial), and mutagen releases the GIL while blocked,
    so overlapping reads is what makes 10k+ files tractable."""
    paths = [
        path
        for path in sorted(root.rglob("*"))
        if path.suffix.lower() in AUDIO_EXTENSIONS and not path.name.startswith("._")
    ]
    records = []
    now = time.time()
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = pool.map(
            lambda p: _read_record(p, min_age_seconds=min_age_seconds, now=now),
            paths,
        )
        for i, result in enumerate(results, start=1):
            if progress_every and i % progress_every == 0:
                rate = i / (time.perf_counter() - started)
                remaining = (len(paths) - i) / rate if rate else 0
                print(
                    f"    {i}/{len(paths)} files ({rate:.0f}/s, ~{remaining:.0f}s left)",
                    flush=True,
                )
            if result is None:
                continue
            kind, payload = result
            if kind == "skip":
                if skipped is not None:
                    skipped.append(payload)
            else:
                records.append(payload)
    return records


def incremental_scan(
    roots: list[Path], *, index_path: Path = DEFAULT_INDEX,
    min_age_seconds: float = 300, workers: int = 8,
) -> dict:
    """Index only new/changed files and return a user-facing scan summary."""
    normalized = [root.expanduser().resolve() for root in roots]
    for root in normalized:
        if not root.exists():
            raise FileNotFoundError(f"scan root does not exist: {root}")
    paths_by_root: dict[str, Path] = {}
    for root in normalized:
        for path in root.rglob("*"):
            if path.suffix.lower() in AUDIO_EXTENSIONS and not path.name.startswith("._"):
                paths_by_root[str(path)] = root

    db = connect(index_path)
    started_at = begin_scan(db, len(paths_by_root))
    try:
        baseline_paths: set[str] = set()
        if DEFAULT_CRATE_CACHE.exists():
            try:
                baseline_paths = {
                    row["track_id"] for row in json.loads(DEFAULT_CRATE_CACHE.read_text())
                }
            except (OSError, json.JSONDecodeError, KeyError):
                baseline_paths = set()
        for root in normalized:
            db.execute(
                "INSERT INTO roots(path, added_at) VALUES (?, ?) "
                "ON CONFLICT(path) DO NOTHING", (str(root), started_at),
            )
        existing = {
            row["track_id"]: row for row in db.execute(
                "SELECT track_id,size_bytes,mtime_ns FROM tracks"
            )
        }
        changed: list[Path] = []
        unchanged = 0
        for raw_path in sorted(paths_by_root):
            path = Path(raw_path)
            try:
                stat = path.stat()
            except OSError:
                continue
            old = existing.get(raw_path)
            if old and old["size_bytes"] == stat.st_size and old["mtime_ns"] == stat.st_mtime_ns:
                unchanged += 1
                db.execute(
                    "UPDATE tracks SET available=1,last_seen_at=? WHERE track_id=?",
                    (started_at, raw_path),
                )
            else:
                changed.append(path)

        now = time.time()
        skipped: list[dict] = []
        records: list[dict] = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = pool.map(
                lambda p: _read_record(p, min_age_seconds=min_age_seconds, now=now), changed
            )
            for result in results:
                if result is None:
                    continue
                kind, payload = result
                (skipped if kind == "skip" else records).append(payload)

        new_count = changed_count = migrated_count = 0
        for record in records:
            track_id = record["track_id"]
            stat = Path(track_id).stat()
            is_new = track_id not in existing and track_id not in baseline_paths
            new_count += int(is_new)
            changed_count += int(track_id in existing)
            migrated_count += int(track_id not in existing and track_id in baseline_paths)
            tag_status = "ok"
            if record["artist"] == "Unknown Artist" or record["title"] == Path(track_id).stem:
                tag_status = "missing_tags"
            old_analysis = db.execute(
                "SELECT bpm,key,energy,first_seen_at FROM tracks WHERE track_id=?", (track_id,)
            ).fetchone()
            first_seen = old_analysis["first_seen_at"] if old_analysis else started_at
            db.execute(
                """INSERT OR REPLACE INTO tracks
                (track_id,root,size_bytes,mtime_ns,title,artist,album,genre,duration_seconds,
                 bpm,key,energy,first_seen_at,last_seen_at,available,tag_status)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?)""",
                (track_id, str(paths_by_root[track_id]), stat.st_size, stat.st_mtime_ns,
                 record["title"], record["artist"], record.get("album"), record.get("genre"),
                 record.get("duration_seconds"), old_analysis["bpm"] if old_analysis else None,
                 old_analysis["key"] if old_analysis else None,
                 old_analysis["energy"] if old_analysis else None, first_seen, started_at, tag_status),
            )

        present = set(paths_by_root)
        scoped = [row["track_id"] for row in db.execute(
            "SELECT track_id FROM tracks WHERE root IN (%s) AND available=1" %
            ",".join("?" * len(normalized)), tuple(map(str, normalized)),
        )] if normalized else []
        missing = [track_id for track_id in scoped if track_id not in present]
        db.executemany("UPDATE tracks SET available=0 WHERE track_id=?", ((p,) for p in missing))
        bootstrap_analysis(db)
        finished = time.time()
        db.execute(
            "UPDATE roots SET last_scan_at=? WHERE path IN (%s)" % ",".join("?" * len(normalized)),
            (finished, *map(str, normalized)),
        )
        db.execute(
            """UPDATE scan_state SET running=0,finished_at=?,processed=?,new_count=?,
            changed_count=?,unchanged_count=?,missing_count=?,skipped_count=? WHERE id=1""",
            (finished, len(paths_by_root), new_count, changed_count, unchanged + migrated_count,
             len(missing), len(skipped)),
        )
        db.commit()
        return {"tracks": len(paths_by_root), "new": new_count, "changed": changed_count,
                "unchanged": unchanged + migrated_count, "missing": len(missing), "skipped": len(skipped),
                "elapsed_seconds": round(finished - started_at, 2), "skipped_records": skipped}
    except Exception as error:
        db.execute(
            "UPDATE scan_state SET running=0,finished_at=?,error=? WHERE id=1",
            (time.time(), str(error)),
        )
        db.commit()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "roots", type=Path, nargs="+", help="directories to scan for audio files"
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_CRATE_CACHE)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument(
        "--catalog",
        action="store_true",
        help="also write brain/data/catalog.json (slim agent-facing index)",
    )
    parser.add_argument(
        "--min-age-seconds",
        type=float,
        default=300,
        help="treat files modified more recently than this as still copying (0 disables)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="parallel tag-read threads (I/O bound; raise on fast disks)",
    )
    args = parser.parse_args()

    started = time.perf_counter()
    try:
        summary = incremental_scan(
            args.roots, index_path=args.index, min_age_seconds=args.min_age_seconds,
            workers=args.workers,
        )
    except FileNotFoundError as error:
        raise SystemExit(str(error)) from error
    records = export_records(args.index)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(records, indent=2))
    elapsed = time.perf_counter() - started
    print(
        f"indexed {len(records)} tracks -> {args.out} ({elapsed:.1f}s; "
        f"{summary['new']} new, {summary['changed']} changed, "
        f"{summary['unchanged']} unchanged)"
    )

    skipped_report = args.out.parent / DEFAULT_SKIPPED_REPORT.name
    skipped_report.write_text(json.dumps(summary["skipped_records"], indent=2))
    print(f"skipped {summary['skipped']} incomplete/in-transfer files -> {skipped_report}")

    if args.catalog:
        from brain.catalog import write_catalog

        catalog_path = write_catalog(records, roots=[str(root) for root in args.roots])
        print(f"catalog -> {catalog_path}")


if __name__ == "__main__":
    main()
