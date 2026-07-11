"""Builds a curated demo subset from the scanned crate (brain/data/crate.json)
and writes both a JSON snapshot and an .m3u playlist. Mixxx can import the
.m3u directly as one action regardless of subset size, so `holo` doesn't need
to click through the library track by track.

Usage: uv run python -m brain.build_demo_subset
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from brain.library import Track, load_crate

DATA_DIR = Path(__file__).parent / "data"
DEMO_SET_JSON = DATA_DIR / "demo_set.json"
DEMO_SET_M3U = DATA_DIR / "demo_set.m3u"

SKIP_TITLE_KEYWORDS = ("interlude", "skit", "intro", "outro")


def select(
    tracks: list[Track],
    *,
    artists: tuple[str, ...],
    path_include: str,
    path_exclude: tuple[str, ...],
    per_album_cap: int,
    total_cap: int,
) -> list[Track]:
    candidates = [
        t
        for t in tracks
        if t.artist in artists
        and path_include in t.track_id
        and not any(exc in t.track_id for exc in path_exclude)
        and not any(kw in t.title.lower() for kw in SKIP_TITLE_KEYWORDS)
    ]
    by_album: dict[str, list[Track]] = defaultdict(list)
    for t in candidates:
        by_album[Path(t.track_id).parent.name].append(t)
    for album_tracks in by_album.values():
        album_tracks.sort(key=lambda t: t.track_id)

    selected: list[Track] = []
    album_iters = {album: iter(ts) for album, ts in by_album.items()}
    while len(selected) < total_cap and album_iters:
        for album in list(album_iters):
            per_album_count = sum(1 for s in selected if Path(s.track_id).parent.name == album)
            if per_album_count >= per_album_cap:
                del album_iters[album]
                continue
            try:
                selected.append(next(album_iters[album]))
            except StopIteration:
                del album_iters[album]
                continue
            if len(selected) >= total_cap:
                break
    return selected


def write_m3u(tracks: list[Track], path: Path) -> None:
    lines = ["#EXTM3U"]
    for t in tracks:
        lines.append(f"#EXTINF:-1,{t.artist} - {t.title}")
        lines.append(t.track_id)
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    tracks = load_crate()
    selected = select(
        tracks,
        artists=("Snoop Dogg", "Snoop Doggy Dogg"),
        path_include="/1. Albums/",
        path_exclude=("(Remastered)",),
        per_album_cap=2,
        total_cap=30,
    )
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    records = [
        {
            "track_id": t.track_id,
            "title": t.title,
            "artist": t.artist,
            "genre": t.genre,
            "bpm": t.bpm,
            "key": t.key,
            "energy": t.energy.value,
        }
        for t in selected
    ]
    DEMO_SET_JSON.write_text(json.dumps(records, indent=2))
    write_m3u(selected, DEMO_SET_M3U)
    print(f"selected {len(selected)} tracks -> {DEMO_SET_JSON}, {DEMO_SET_M3U}")
    for t in selected:
        print(" -", t.title, "|", Path(t.track_id).parent.name)


if __name__ == "__main__":
    main()
