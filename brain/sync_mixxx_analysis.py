"""Pulls BPM/key that Mixxx has already analyzed out of its own library
database and merges them into brain/data/crate.json (matched by absolute
file path). Mixxx is the source of truth for BPM/key, not us — this just
snapshots it locally so track-selection doesn't need a live DB read on every
decision. Re-run after (re-)analyzing tracks in Mixxx.

Usage: uv run python -m brain.sync_mixxx_analysis
"""
from __future__ import annotations

import json

from brain.library import DEFAULT_CRATE_CACHE, load_crate
from shared.mixxx_db import connect_readonly


def fetch_analyzed() -> dict[str, dict]:
    """{absolute file path: {"bpm": float, "key": str}} for tracks Mixxx has analyzed (bpm > 0)."""
    conn = connect_readonly()
    try:
        rows = conn.execute(
            """
            SELECT track_locations.location, library.bpm, library.key
            FROM library
            JOIN track_locations ON library.location = track_locations.id
            WHERE library.bpm > 0
            """
        ).fetchall()
    finally:
        conn.close()
    return {location: {"bpm": bpm, "key": key or None} for location, bpm, key in rows}


def main() -> None:
    analyzed = fetch_analyzed()
    tracks = load_crate()
    if not tracks:
        raise SystemExit(f"no crate at {DEFAULT_CRATE_CACHE} — run `brain.scan_library` first")

    matched = 0
    records = []
    for track in tracks:
        hit = analyzed.get(track.track_id)
        if hit:
            matched += 1
        records.append(
            {
                "track_id": track.track_id,
                "title": track.title,
                "artist": track.artist,
                "genre": track.genre,
                "bpm": hit["bpm"] if hit else track.bpm,
                "key": hit["key"] if hit else track.key,
                "energy": track.energy.value,
            }
        )

    DEFAULT_CRATE_CACHE.write_text(json.dumps(records, indent=2))
    print(f"{matched}/{len(tracks)} tracks matched Mixxx's analyzed library -> {DEFAULT_CRATE_CACHE}")
    print(f"{len(analyzed)} analyzed tracks total in Mixxx's library (including ones outside this crate)")


if __name__ == "__main__":
    main()
