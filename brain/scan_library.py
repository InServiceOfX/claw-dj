"""Scans a local music directory's ID3 tags into brain/library.py's crate
cache. The cache (brain/data/crate.json) is gitignored — a personal media
library's track listing doesn't belong committed to a public repo.

Usage: uv run python -m brain.scan_library /path/to/music/dir [more/dirs...]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mutagen import File as MutagenFile

from brain.library import DEFAULT_CRATE_CACHE

AUDIO_EXTENSIONS = {".mp3", ".flac", ".m4a", ".wav", ".aiff"}


def _first(tags: dict, key: str) -> str | None:
    values = tags.get(key)
    return values[0] if values else None


def scan(root: Path) -> list[dict]:
    records = []
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in AUDIO_EXTENSIONS or path.name.startswith("._"):
            continue
        try:
            tagged = MutagenFile(path, easy=True)
        except Exception:
            continue
        if tagged is None or not tagged.tags:
            continue
        records.append(
            {
                "track_id": str(path),
                "title": _first(tagged.tags, "title") or path.stem,
                "artist": _first(tagged.tags, "artist") or "Unknown Artist",
                "genre": _first(tagged.tags, "genre"),
            }
        )
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "roots", type=Path, nargs="+", help="directories to scan for audio files"
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_CRATE_CACHE)
    args = parser.parse_args()

    previous = {}
    if args.out.exists():
        previous = {
            record["track_id"]: record for record in json.loads(args.out.read_text())
        }

    records_by_path = {}
    for root in args.roots:
        found = scan(root)
        print(f"  {root}: {len(found)} tracks")
        records_by_path.update({record["track_id"]: record for record in found})

    records = []
    for track_id in sorted(records_by_path):
        record = records_by_path[track_id]
        old = previous.get(track_id, {})
        for field in ("bpm", "key", "energy"):
            if old.get(field) is not None:
                record[field] = old[field]
        records.append(record)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(records, indent=2))
    print(f"scanned {len(records)} tracks -> {args.out}")


if __name__ == "__main__":
    main()
