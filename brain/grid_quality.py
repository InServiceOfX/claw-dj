"""Measure how truthful a track's Mixxx beatgrid actually is, from the audio.

Mixxx fits ONE constant BPM + one anchor point to a whole track. For
drum-machine music (G-funk, 2000s R&B/pop) that grid is exact for the whole
song, and beatsync against it sounds locked. For live drummers and vinyl
rips the real tempo wobbles — the constant grid is only right on average,
so two decks that are perfectly synced at the anchor moment audibly drift
apart within a bar or two of overlap. No cue-point or phase fix can help
when the grid itself is wrong; the honest answer is to KNOW which tracks
have trustworthy grids and plan short blends (or clean cuts) for the rest.

This measures, per track: what fraction of detected drum onsets land tight
on the beatgrid (within a small tolerance), both overall and per time
window, plus librosa's own independent tempo estimate as a cross-check.

Verdicts:
  rigid       -- onsets stay tight on the grid the whole way through:
                 long synced blends are safe
  drifty      -- tight in some windows, loose in others (live drummer /
                 vinyl wow): keep overlaps SHORT, or cut instead of blend
  misaligned  -- onsets never line up with the claimed grid (wrong bpm,
                 wrong phase, or too little percussion to tell): do not
                 trust sync at all on this track

Usage:
    uv run python -m brain.grid_quality <track_path> --bpm 94.0 --first-beat 0.476
"""
from __future__ import annotations

import argparse
import json

import librosa
import numpy as np

from brain.onset_analysis import DEFAULT_MAX_SECONDS, DEFAULT_SR, load_audio

# An onset within this distance of a grid line counts as "on the grid".
# ~35ms is roughly the edge of what reads as one hit rather than a flam.
TIGHT_TOLERANCE_S = 0.035
WINDOW_SECONDS = 30.0
RIGID_MIN_FRACTION = 0.6
MISALIGNED_MAX_FRACTION = 0.35


def onset_times(y: np.ndarray, sr: int) -> np.ndarray:
    return librosa.onset.onset_detect(y=y, sr=sr, units="time", backtrack=False)


def grid_line_gaps(
    onsets: np.ndarray, *, bpm: float, first_beat_seconds: float
) -> tuple[np.ndarray, np.ndarray]:
    """For each GRID LINE inside the onset span: distance to the nearest
    detected onset, capped at half a period.

    Direction matters. A first version measured onset→grid distances and
    drowned in legitimately off-beat onsets (hi-hats, syncopation, vocals)
    — real drum-machine tracks Ernest's ear certified as perfectly
    beat-matched scored no better than the problem tracks (survey,
    2026-07-19). Grid→onset asks the right question: if the grid is
    truthful, SOMETHING audible happens near every beat it claims.
    Returns (grid_times, gaps).
    """
    period = 60.0 / bpm
    if len(onsets) == 0:
        return np.array([]), np.array([])
    first = float(onsets[0])
    last = float(onsets[-1])
    k_start = int(np.ceil((first - first_beat_seconds) / period))
    k_end = int(np.floor((last - first_beat_seconds) / period))
    if k_end < k_start:
        return np.array([]), np.array([])
    grid = first_beat_seconds + np.arange(k_start, k_end + 1) * period
    idx = np.searchsorted(onsets, grid)
    left = onsets[np.clip(idx - 1, 0, len(onsets) - 1)]
    right = onsets[np.clip(idx, 0, len(onsets) - 1)]
    gaps = np.minimum(np.abs(grid - left), np.abs(right - grid))
    return grid, np.minimum(gaps, period / 2)


def windowed_tight_fractions(
    grid: np.ndarray,
    gaps: np.ndarray,
    *,
    window_seconds: float = WINDOW_SECONDS,
    tolerance_s: float = TIGHT_TOLERANCE_S,
) -> list[float]:
    """Fraction of grid lines with an onset within tolerance, per
    consecutive time window. A drifting tempo shows up as early windows
    tight and later windows loose (or oscillating), even when the overall
    average looks ok."""
    if len(grid) == 0:
        return []
    fractions = []
    end = float(grid[-1])
    start = float(grid[0])
    while start <= end:
        mask = (grid >= start) & (grid < start + window_seconds)
        if int(mask.sum()) >= 8:  # too few grid lines to say anything
            fractions.append(float((gaps[mask] <= tolerance_s).mean()))
        start += window_seconds
    return fractions


def measure_grid_quality(
    path: str,
    *,
    bpm: float,
    first_beat_seconds: float,
    sr: int = DEFAULT_SR,
    max_seconds: float = DEFAULT_MAX_SECONDS,
) -> dict:
    y = load_audio(path, sr=sr, max_seconds=max_seconds)
    onsets = onset_times(y, sr)
    grid, gaps = grid_line_gaps(onsets, bpm=bpm, first_beat_seconds=first_beat_seconds)
    tight = float((gaps <= TIGHT_TOLERANCE_S).mean()) if len(grid) else 0.0
    windows = windowed_tight_fractions(grid, gaps)
    min_window = min(windows) if windows else 0.0
    from librosa.feature.rhythm import tempo as rhythm_tempo

    tempo_estimate = float(np.atleast_1d(rhythm_tempo(y=y, sr=sr))[0]) if len(y) else 0.0

    if tight >= RIGID_MIN_FRACTION and min_window >= RIGID_MIN_FRACTION * 0.75:
        verdict = "rigid"
    elif tight <= MISALIGNED_MAX_FRACTION:
        verdict = "misaligned"
    else:
        verdict = "drifty"
    return {
        "tight_fraction": round(tight, 3),
        "min_window_fraction": round(min_window, 3),
        "window_fractions": [round(f, 3) for f in windows],
        "onset_count": int(len(onsets)),
        "tempo_estimate": round(tempo_estimate, 2),
        "verdict": verdict,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("track_id")
    parser.add_argument("--bpm", type=float, required=True)
    parser.add_argument("--first-beat", type=float, required=True, dest="first_beat")
    parser.add_argument("--max-seconds", type=float, default=DEFAULT_MAX_SECONDS)
    args = parser.parse_args()
    result = measure_grid_quality(
        args.track_id,
        bpm=args.bpm,
        first_beat_seconds=args.first_beat,
        max_seconds=args.max_seconds,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
