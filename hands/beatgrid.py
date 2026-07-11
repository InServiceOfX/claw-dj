"""Reads BPM / beatgrid data Mixxx already computed on track analysis, from
its own library database, so Hands doesn't need its own beat-detection pass.
Schema confirmed against a real Mixxx install (see shared/mixxx_db.py) —
`library.location` is an integer FK into `track_locations.id`, and a track
only has a usable bpm once Mixxx has actually analyzed it (bpm stays 0
otherwise; Mixxx analyzes lazily, not automatically on library scan).
"""
from dataclasses import dataclass

from shared.mixxx_db import connect_readonly


@dataclass(frozen=True)
class Beatgrid:
    track_id: str  # absolute file path — matches track_locations.location
    bpm: float
    first_beat_sec: float


def load_beatgrid(track_id: str) -> Beatgrid:
    conn = connect_readonly()
    try:
        row = conn.execute(
            """
            SELECT library.bpm
            FROM library
            JOIN track_locations ON library.location = track_locations.id
            WHERE track_locations.location = ?
            """,
            (track_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise ValueError(f"{track_id!r} is not in Mixxx's library")
    bpm = row[0]
    if not bpm:
        raise ValueError(f"{track_id!r} is in Mixxx's library but not yet analyzed (bpm=0)")
    # TODO: parse the `beats` BLOB (protobuf) for first_beat_sec instead of
    # assuming 0.0 — Mixxx's beatgrid isn't always anchored at track start.
    return Beatgrid(track_id=track_id, bpm=bpm, first_beat_sec=0.0)


def beat_to_seconds(grid: Beatgrid, beat: float) -> float:
    return grid.first_beat_sec + beat * (60.0 / grid.bpm)
