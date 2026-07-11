"""Playlist selection, seed matching, and Mixxx-compatible exports."""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

from brain.library import Track

DATA_DIR = Path(__file__).parent / "data"
DEFAULT_SELECTION = DATA_DIR / "playlist_selection.json"
DEFAULT_PLAYLIST_JSON = DATA_DIR / "playlist.json"
DEFAULT_PLAYLIST_M3U = DATA_DIR / "playlist.m3u8"
DEFAULT_SEED = Path(__file__).parent / "playlist_seeds" / "rnb_west_coast_hits.json"


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


@dataclass(frozen=True)
class SeedMatch:
    artist: str
    title: str
    source: str
    track: Track | None


def load_seed(path: Path = DEFAULT_SEED) -> list[dict]:
    return json.loads(path.read_text())


def _match_score(track: Track, artist: str, title: str) -> tuple[int, int, int] | None:
    wanted_artist = normalize(artist)
    wanted_title = normalize(title)
    actual_artist = normalize(track.artist)
    actual_title = normalize(track.title)
    path = normalize(track.track_id)
    filename = normalize(Path(track.track_id).stem)

    artist_match = wanted_artist in actual_artist or actual_artist in wanted_artist or wanted_artist in path
    title_match = wanted_title == actual_title or wanted_title in actual_title or wanted_title in filename
    if not artist_match or not title_match:
        return None

    exact_title = int(wanted_title == actual_title)
    exact_artist = int(wanted_artist == actual_artist)
    preferred_album = int(
        not any(
            word in path
            for word in ("compilation", "greatest hits", "remix", "single", "live", "bootleg", "dvd rip")
        )
    )
    return preferred_album, exact_title, exact_artist


def match_seed(tracks: list[Track], seed: list[dict]) -> list[SeedMatch]:
    matches = []
    for item in seed:
        ranked = [(_match_score(track, item["artist"], item["title"]), track) for track in tracks]
        candidates = [(score, track) for score, track in ranked if score is not None]
        track = max(candidates, key=lambda pair: pair[0])[1] if candidates else None
        matches.append(SeedMatch(item["artist"], item["title"], item["source"], track))
    return matches


def load_selection(path: Path = DEFAULT_SELECTION) -> list[str]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text())
    return payload["track_ids"] if isinstance(payload, dict) else payload


def save_selection(track_ids: list[str], path: Path = DEFAULT_SELECTION) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"track_ids": list(dict.fromkeys(track_ids))}, indent=2) + "\n")


def track_record(track: Track) -> dict:
    record = asdict(track)
    record["energy"] = track.energy.value
    return record


def export_playlist(
    tracks: list[Track],
    track_ids: list[str],
    *,
    json_path: Path = DEFAULT_PLAYLIST_JSON,
    m3u_path: Path = DEFAULT_PLAYLIST_M3U,
) -> list[Track]:
    by_id = {track.track_id: track for track in tracks}
    selected = [by_id[track_id] for track_id in track_ids if track_id in by_id]
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps([track_record(track) for track in selected], indent=2) + "\n")
    lines = ["#EXTM3U"]
    for track in selected:
        lines.extend((f"#EXTINF:-1,{track.artist} - {track.title}", track.track_id))
    m3u_path.write_text("\n".join(lines) + "\n")
    return selected
