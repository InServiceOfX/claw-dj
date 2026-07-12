"""Curated track metadata the Brain picks from, sourced from local ID3 tags
(brain/scan_library.py writes the cache this reads). BPM/key aren't reliable
from tags on most rips, so beat-precise timing still comes from Mixxx's own
analyzed beatgrid once a track is loaded (hands/beatgrid.py) — bpm/key here
are best-effort hints for track selection, not what Hands schedules against.
`energy` isn't inferable from tags at all and defaults to MEDIUM until
hand-tuned for a set or inferred from audio.
"""
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

DEFAULT_CRATE_CACHE = Path(__file__).parent / "data" / "crate.json"


class Energy(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PEAK = "peak"


@dataclass(frozen=True)
class Track:
    track_id: str  # absolute file path — matches Mixxx's own library location
    title: str
    artist: str
    genre: str | None = None
    album: str | None = None
    bpm: float | None = None
    key: str | None = None
    energy: Energy = Energy.MEDIUM


def load_crate(path: Path = DEFAULT_CRATE_CACHE) -> list[Track]:
    if not path.exists():
        return []
    records = json.loads(path.read_text())
    return [
        Track(
            track_id=r["track_id"],
            title=r["title"],
            artist=r["artist"],
            genre=r.get("genre"),
            album=r.get("album"),
            bpm=r.get("bpm"),
            key=r.get("key"),
            energy=Energy(r.get("energy", Energy.MEDIUM.value)),
        )
        for r in records
    ]


CRATE: list[Track] = load_crate()


def find_next(current: Track | None, requested_energy: Energy) -> Track | None:
    candidates = [t for t in CRATE if t.energy == requested_energy]
    if current is not None:
        candidates = [t for t in candidates if t.track_id != current.track_id]
    return candidates[0] if candidates else None
