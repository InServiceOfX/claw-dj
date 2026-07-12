"""Provisional BPM estimates for the lineage set, computed with librosa so
track selection can proceed before Mixxx has analyzed anything. Mixxx's own
beatgrid remains the timing authority (hands/beatgrid.py) — rerun
brain.sync_mixxx_analysis after importing/analyzing in Mixxx to overwrite
these with Mixxx's values.

librosa is not a project dependency; run with an ephemeral install:
    uv run --with librosa python -m brain.analyze_bpm
"""
from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
SET_JSON = DATA_DIR / "lineage_set.json"


def estimate_bpm(path: str) -> float | None:
    import librosa
    import numpy as np

    try:
        # 90 seconds from 30s in: past the intro, enough bars to be stable.
        y, sr = librosa.load(path, mono=True, offset=30.0, duration=90.0)
        tempo = librosa.feature.tempo(y=y, sr=sr, aggregate=np.median)
        bpm = float(tempo[0] if hasattr(tempo, "__len__") else tempo)
    except Exception as e:
        print(f"    FAILED: {e}")
        return None
    # Fold octave errors into the plausible hip-hop/RnB range.
    while bpm > 160:
        bpm /= 2
    while bpm < 60:
        bpm *= 2
    return round(bpm, 1)


def main() -> None:
    records = json.loads(SET_JSON.read_text())
    for r in records:
        if r.get("bpm"):
            continue
        print(f"{r['artist']} - {r['title']}")
        r["bpm"] = estimate_bpm(r["track_id"])
        print(f"    bpm ~ {r['bpm']}")
    SET_JSON.write_text(json.dumps(records, indent=2))
    done = sum(1 for r in records if r.get("bpm"))
    print(f"\n{done}/{len(records)} tracks have BPM -> {SET_JSON}")


if __name__ == "__main__":
    main()
