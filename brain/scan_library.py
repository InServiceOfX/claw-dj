"""Scans one or more local music directories' tags into brain/library.py's crate
cache. Metadata only (title/artist/album/genre via mutagen) — no audio
analysis. BPM/key stay whatever Mixxx already produced if a prior crate row
exists for the same absolute path.

The cache (brain/data/crate.json) is gitignored — a personal media library's
track listing doesn't belong committed to a public repo.

Usage:
    uv run python -m brain.scan_library /Volumes/USB322FD/Music/RnB \\
        /Volumes/USB322FD/Music/HipHop
    uv run python -m brain.scan_library ... --catalog   # also write slim agent catalog
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from mutagen import File as MutagenFile

from brain.library import DEFAULT_CRATE_CACHE

AUDIO_EXTENSIONS = {".mp3", ".flac", ".m4a", ".wav", ".aiff"}


def _first(tags: dict, key: str) -> str | None:
    values = tags.get(key)
    return values[0] if values else None


def scan(root: Path) -> list[dict]:
    """Read embedded tags only — typically a few ms per file, no decoding."""
    records = []
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in AUDIO_EXTENSIONS or path.name.startswith("._"):
            continue
        try:
            tagged = MutagenFile(path, easy=True)
        except Exception:
            continue
        if tagged is None:
            # Untagged audio still counts as available; name falls back to filename.
            records.append(
                {
                    "track_id": str(path),
                    "title": path.stem,
                    "artist": "Unknown Artist",
                    "album": None,
                    "genre": None,
                }
            )
            continue
        tags = tagged.tags or {}
        records.append(
            {
                "track_id": str(path),
                "title": _first(tags, "title") or path.stem,
                "artist": _first(tags, "artist") or "Unknown Artist",
                "album": _first(tags, "album"),
                "genre": _first(tags, "genre"),
            }
        )
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
    args = parser.parse_args()

    previous = {}
    if args.out.exists():
        previous = {
            record["track_id"]: record for record in json.loads(args.out.read_text())
        }

    started = time.perf_counter()
    records_by_path: dict[str, dict] = {}
    for root in args.roots:
        if not root.exists():
            raise SystemExit(f"scan root does not exist: {root}")
        found = scan(root)
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

    if args.catalog:
        from brain.catalog import write_catalog

        catalog_path = write_catalog(records, roots=[str(root) for root in args.roots])
        print(f"catalog -> {catalog_path}")


if __name__ == "__main__":
    main()
