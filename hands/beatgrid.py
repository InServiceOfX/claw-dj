"""Reads BPM / beatgrid data Mixxx already computed on track import, from
mixxxdb.sqlite, so Hands doesn't need its own beat-detection pass.

Default DB location: ~/.mixxx/mixxxdb.sqlite (macOS/Linux).
"""
import sqlite3
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MIXXXDB_PATH = Path.home() / ".mixxx" / "mixxxdb.sqlite"


@dataclass(frozen=True)
class Beatgrid:
    track_id: str
    bpm: float
    first_beat_sec: float


def load_beatgrid(track_id: str, db_path: Path = DEFAULT_MIXXXDB_PATH) -> Beatgrid:
    conn = sqlite3.connect(db_path)
    try:
        # TODO: confirm exact column names against the installed Mixxx schema
        # version before the hackathon — this varies across Mixxx releases.
        row = conn.execute(
            "SELECT bpm, beats FROM library WHERE id = ?", (track_id,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise ValueError(f"no track {track_id!r} in {db_path}")
    bpm, _beats_blob = row
    # TODO: parse Mixxx's serialized beatgrid blob for first_beat_sec instead
    # of assuming 0.0.
    return Beatgrid(track_id=track_id, bpm=bpm, first_beat_sec=0.0)


def beat_to_seconds(grid: Beatgrid, beat: float) -> float:
    return grid.first_beat_sec + beat * (60.0 / grid.bpm)
