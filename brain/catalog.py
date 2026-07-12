"""Slim available-catalog for agent curation.

The full crate (brain/data/crate.json) keeps absolute paths for Mixxx. Agents
(and NemoClaw sandboxes) only need a compact index of what is *available* on
this machine: short id, artist, title, album, genre. No audio analysis.

Usage:
    uv run python -m brain.catalog
    uv run python -m brain.catalog --from-crate brain/data/crate.json
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from brain.library import DEFAULT_CRATE_CACHE, Track, load_crate

DATA_DIR = Path(__file__).parent / "data"
DEFAULT_CATALOG = DATA_DIR / "catalog.json"


def short_id(index: int) -> str:
    """Stable short id for agent prompts (t00001 …)."""
    return f"t{index:05d}"


def catalog_entry(index: int, track: Track | dict) -> dict:
    if isinstance(track, Track):
        return {
            "id": short_id(index),
            "artist": track.artist,
            "title": track.title,
            "album": track.album,
            "genre": track.genre,
            "track_id": track.track_id,
            "analyzed": track.bpm is not None,
        }
    return {
        "id": short_id(index),
        "artist": track.get("artist") or "Unknown Artist",
        "title": track.get("title") or "Unknown Title",
        "album": track.get("album"),
        "genre": track.get("genre"),
        "track_id": track["track_id"],
        "analyzed": track.get("bpm") is not None,
    }


_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")
_NOISE_RE = re.compile(
    r"\s*[(\[][^)\]]*(feat|ft\.|remaster|explicit|clean|album version|bonus)[^)\]]*[)\]]",
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    return _NORMALIZE_RE.sub(" ", _NOISE_RE.sub("", text).lower()).strip()


def find_duplicates(tracks: list[Track] | list[dict]) -> list[dict]:
    """Same normalized artist+title at different paths (scene rips, reissues)."""
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for track in tracks:
        row = track.__dict__ if isinstance(track, Track) else track
        key = (
            _normalize(row.get("artist") or "Unknown Artist"),
            _normalize(row.get("title") or ""),
        )
        if key[1]:
            groups[key].append(row["track_id"])
    return [
        {"artist": artist, "title": title, "track_ids": sorted(paths)}
        for (artist, title), paths in sorted(groups.items())
        if len(paths) > 1
    ]


def build_catalog(
    tracks: list[Track] | list[dict],
    *,
    roots: list[str] | None = None,
) -> dict:
    entries = [catalog_entry(i, track) for i, track in enumerate(tracks)]
    artists = Counter(entry["artist"] for entry in entries)
    genres = Counter(entry["genre"] or "unknown" for entry in entries)
    duplicates = find_duplicates(tracks)
    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "roots": roots or [],
        "track_count": len(entries),
        "analyzed_count": sum(1 for entry in entries if entry["analyzed"]),
        "artist_count": len(artists),
        "top_artists": [
            {"artist": artist, "count": count}
            for artist, count in artists.most_common(40)
        ],
        "genres": [
            {"genre": genre, "count": count} for genre, count in genres.most_common(30)
        ],
        "duplicate_group_count": len(duplicates),
        "duplicates": duplicates,
        "tracks": entries,
    }


def write_catalog(
    tracks: list[Track] | list[dict],
    *,
    path: Path = DEFAULT_CATALOG,
    roots: list[str] | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_catalog(tracks, roots=roots), indent=2) + "\n")
    return path


def load_catalog(path: Path = DEFAULT_CATALOG) -> dict:
    return json.loads(path.read_text())


def agent_view(
    catalog: dict,
    *,
    max_tracks: int | None = None,
    include_paths: bool = False,
) -> dict:
    """Drop absolute host paths by default (safe to hand a sandbox)."""
    tracks = catalog["tracks"]
    if max_tracks is not None:
        tracks = tracks[:max_tracks]
    slim_tracks = []
    for entry in tracks:
        row = {
            "id": entry["id"],
            "artist": entry["artist"],
            "title": entry["title"],
            "album": entry.get("album"),
            "genre": entry.get("genre"),
        }
        if include_paths:
            row["track_id"] = entry["track_id"]
        slim_tracks.append(row)
    return {
        "track_count": catalog["track_count"],
        "artist_count": catalog.get("artist_count"),
        "top_artists": catalog.get("top_artists", []),
        "genres": catalog.get("genres", []),
        "tracks": slim_tracks,
        "note": "Only pick tracks whose id appears in tracks[]. Paths are host-local.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-crate", type=Path, default=DEFAULT_CRATE_CACHE)
    parser.add_argument("--out", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument(
        "--agent-view",
        type=Path,
        default=None,
        help="also write a path-stripped copy suitable for NemoClaw upload",
    )
    args = parser.parse_args()

    if not args.from_crate.exists():
        raise SystemExit(
            f"no crate at {args.from_crate}; run brain.scan_library on your music dirs first"
        )
    tracks = load_crate(args.from_crate)
    path = write_catalog(tracks, path=args.out)
    catalog = load_catalog(path)
    print(
        f"catalog {catalog['track_count']} tracks "
        f"({catalog['artist_count']} artists) -> {path}"
    )
    if args.agent_view:
        args.agent_view.parent.mkdir(parents=True, exist_ok=True)
        args.agent_view.write_text(
            json.dumps(agent_view(catalog), indent=2) + "\n"
        )
        print(f"agent view -> {args.agent_view}")


if __name__ == "__main__":
    main()
