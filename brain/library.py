"""Curated track metadata the Brain picks from. Kept separate from Mixxx's
own library DB — this is the subset of tags (energy, role in a set) Mixxx
doesn't track natively.
"""
from dataclasses import dataclass
from enum import Enum


class Energy(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PEAK = "peak"


@dataclass(frozen=True)
class Track:
    track_id: str
    title: str
    artist: str
    bpm: float
    key: str
    energy: Energy


# TODO: replace with real crate before the hackathon — one curated hip-hop
# crate, BPM-matched, per ARCHITECTURE.md's MVP cut-list.
CRATE: list[Track] = []


def find_next(current: Track | None, requested_energy: Energy) -> Track | None:
    candidates = [t for t in CRATE if t.energy == requested_energy]
    if current is not None:
        candidates = [t for t in candidates if t.track_id != current.track_id]
    return candidates[0] if candidates else None
