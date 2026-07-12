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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "roots", type=Path, nargs="+", help="directories to scan for audio files"
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_CRATE_CACHE)
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

    previous = {}
    if args.out.exists():
        previous = {
            record["track_id"]: record for record in json.loads(args.out.read_text())
        }

    started = time.perf_counter()
    records_by_path: dict[str, dict] = {}
    skipped: list[dict] = []
    for root in args.roots:
        if not root.exists():
            raise SystemExit(f"scan root does not exist: {root}")
        found = scan(
            root,
            min_age_seconds=args.min_age_seconds,
            skipped=skipped,
            workers=args.workers,
        )
        print(f"  {root}: {len(found)} tracks")
        records_by_path.update({record["track_id"]: record for record in found})

    records = []
    for track_id in sorted(records_by_path):
        record = records_by_path[track_id]
        old = previous.get(track_id, {})
        # Carry analysis forward; never invent bpm/key here.
        for field in ("bpm", "key", "energy"):
            if old.get(field) is not None:
                record[field] = old[field]
        if record.get("album") is None and old.get("album") is not None:
            record["album"] = old["album"]
        records.append(record)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(records, indent=2))
    elapsed = time.perf_counter() - started
    print(f"scanned {len(records)} tracks -> {args.out} ({elapsed:.1f}s, metadata only)")

    skipped_report = args.out.parent / DEFAULT_SKIPPED_REPORT.name
    skipped_report.write_text(json.dumps(skipped, indent=2))
    print(f"skipped {len(skipped)} incomplete/in-transfer files -> {skipped_report}")

    if args.catalog:
        from brain.catalog import write_catalog

        catalog_path = write_catalog(records, roots=[str(root) for root in args.roots])
        print(f"catalog -> {catalog_path}")


if __name__ == "__main__":
    main()
