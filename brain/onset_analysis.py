"""Real onset/transient detection to locate snare-drum hits in a track.

Mixxx's own beatgrid (and this project's `phrase_analysis.py`) only marks
generic, evenly-spaced quarter-note beats -- it has no notion of which beat
in a bar carries the kick vs. the snare. Two tracks can be tempo- and
phase-locked on Mixxx's beatgrid and still have their *drum hits* land on
the wrong beat relative to each other (a kick landing where a snare should
be), which reads as "the beats don't match" even though the generic
beatgrid sync looks correct on paper.

This module estimates, per track, the snare/backbeat's beat PARITY (does it
fall on even-indexed or odd-indexed beats, 0-indexed from the track's own
first-beat) from broadband high-frequency transient energy, since a kick
drum's energy is concentrated in the low end and a snare's is a sharp
broadband snap. A standard 4/4 backbeat puts the snare on every other beat
(musically "2 and 4"), so parity -- not "which single one of 4 beats-in-a-
bar" -- is the physically meaningful question; treating it as a 4-way pick
produced noisy, low-confidence results because the two real backbeat
positions legitimately tie for the top spot. That lets
`hands.run_mix_plan`/`brain.build_mix_plan` pick cue points and transition
anchors that line up snare-to-snare, not just beat-to-beat.

Usage:
    uv run python -m brain.onset_analysis <track_id> --bpm 94.0 --first-beat 0.476
"""
from __future__ import annotations

import argparse
import json

import librosa
import numpy as np

DEFAULT_SR = 22050
# Snare energy lives mostly in the snap/rattle, well above a kick's thump.
SNARE_HIGHPASS_HZ = 1500.0
DEFAULT_MAX_SECONDS = 120.0


def load_audio(path: str, *, sr: int = DEFAULT_SR, max_seconds: float = DEFAULT_MAX_SECONDS) -> np.ndarray:
    y, _ = librosa.load(path, sr=sr, mono=True, duration=max_seconds)
    return y


def snare_band_onset_envelope(y: np.ndarray, sr: int) -> tuple[np.ndarray, int]:
    """Onset-strength envelope of the high-passed (snare-emphasized) signal.

    Returns (envelope, hop_length) -- hop_length is needed to convert
    envelope frame indices back to seconds.
    """
    y_high = _highpass(y, sr, SNARE_HIGHPASS_HZ)
    hop_length = 512
    envelope = librosa.onset.onset_strength(y=y_high, sr=sr, hop_length=hop_length)
    return envelope, hop_length


def _highpass(y: np.ndarray, sr: int, cutoff_hz: float) -> np.ndarray:
    from scipy.signal import butter, sosfilt

    sos = butter(4, cutoff_hz, btype="highpass", fs=sr, output="sos")
    return sosfilt(sos, y).astype(np.float32)


def beat_phase_energies(
    envelope: np.ndarray,
    *,
    sr: int,
    hop_length: int,
    bpm: float,
    first_beat_seconds: float,
    window_seconds: float = 0.08,
) -> list[float]:
    """Aggregate snare-band onset energy at each of the 4 beat-in-bar slots.

    For every beat in the track (from `first_beat_seconds` on, at the
    track's own bpm), sums the envelope energy in a small window centered
    on that beat, and accumulates the total into `beat % 4`'s bucket.
    """
    period = 60.0 / bpm
    frame_seconds = hop_length / sr
    total_seconds = len(envelope) * frame_seconds
    energies = [0.0, 0.0, 0.0, 0.0]
    counts = [0, 0, 0, 0]
    beat = 0
    while True:
        t = first_beat_seconds + beat * period
        if t > total_seconds:
            break
        center_frame = int(round(t / frame_seconds))
        half_window = max(1, int(round(window_seconds / frame_seconds)))
        lo = max(0, center_frame - half_window)
        hi = min(len(envelope), center_frame + half_window)
        if hi > lo:
            slot = beat % 4
            energies[slot] += float(np.sum(envelope[lo:hi]))
            counts[slot] += 1
        beat += 1
    return [e / c if c else 0.0 for e, c in zip(energies, counts)]


def detect_snare_phase(
    path: str,
    *,
    bpm: float,
    first_beat_seconds: float,
    sr: int = DEFAULT_SR,
    max_seconds: float = DEFAULT_MAX_SECONDS,
) -> dict:
    """Estimate the snare/backbeat's beat parity (even beats vs. odd beats).

    A standard 4/4 backbeat puts the snare on every OTHER beat (musically
    "2 and 4"), not on one specific beat-in-bar -- so beats 1&3 (0-indexed:
    slots 1 and 3) should carry near-equal, elevated snare-band energy, and
    beats 0&2 should both be low. The physically meaningful question is
    therefore odd-vs-even parity, not "which single one of 4 slots wins" --
    an early version of this function ranked individual slots and got very
    low, noisy confidence scores precisely because two of them (the real
    backbeat pair) legitimately tie for the top spot.

    Returns {"snare_parity": 0 or 1, "confidence": float, "slot_energies": [...]}.
    `snare_parity` is `beat_index % 2` for the beats that carry the snare.
    `confidence` is the normalized margin between odd-sum and even-sum
    energy -- low confidence means no clear, consistent backbeat pattern
    was found (or the read is unreliable).
    """
    y = load_audio(path, sr=sr, max_seconds=max_seconds)
    envelope, hop_length = snare_band_onset_envelope(y, sr)
    energies = beat_phase_energies(
        envelope, sr=sr, hop_length=hop_length, bpm=bpm, first_beat_seconds=first_beat_seconds
    )
    even_energy = energies[0] + energies[2]
    odd_energy = energies[1] + energies[3]
    top = max(even_energy, odd_energy)
    confidence = 0.0 if top <= 0 else abs(odd_energy - even_energy) / top
    return {
        "snare_parity": 1 if odd_energy >= even_energy else 0,
        "confidence": round(confidence, 3),
        "slot_energies": [round(e, 4) for e in energies],
    }


def phase_shift_beats(
    outgoing_snare_parity: int,
    outgoing_anchor_beat_index: int,
    incoming_snare_parity: int,
    incoming_cue_beat_index: int,
) -> int:
    """Beats to shift the incoming cue so its snare lines up with the outgoing's.

    At the anchor moment the outgoing deck sits at beat
    `outgoing_anchor_beat_index`; its snare falls on beats whose index is
    congruent to `outgoing_snare_parity mod 2`. For the incoming deck's
    snare to land on the same beats as playback continues forward, its own
    cue beat index must match that same parity. Returns 0 (already aligned)
    or 1 (shift the incoming cue by one beat, either direction -- +1 and -1
    are equivalent mod 2, so there's no "smaller" choice to make here).
    """
    target_parity = (outgoing_anchor_beat_index + outgoing_snare_parity) % 2
    current_parity = (incoming_cue_beat_index + incoming_snare_parity) % 2
    return 0 if target_parity == current_parity else 1


def count_shift_beats(
    outgoing_snare_parity: int,
    outgoing_anchor_beat_index: int,
    incoming_snare_parity: int,
    incoming_cue_beat_index: int,
) -> int:
    """Beats to shift the outgoing ride so the incoming enters on the same
    COUNT-IN-BAR (the 1-2-3-4), not just the same snare parity.

    Snare parity (mod 2) is measured from real audio and always wins. The
    bar position (mod 4) additionally assumes both tracks' Mixxx beatgrids
    anchor beat 0 on a downbeat — usually true, and the same assumption the
    hand-tuned "multiple of 4" fixes (2026-07-16/17, several confirmed by
    ear) already relied on. When the two constraints disagree (a grid whose
    anchor is off by an odd count), the measured parity is trusted and the
    bar assumption is dropped. Returns a shift in {-1, 0, 1, 2}.

    Added after live feedback 2026-07-19: parity-only alignment left two
    transitions entering on the wrong count ("just make sure the counts
    match") even though kick/snare parity was correct.
    """
    parity_shift = phase_shift_beats(
        outgoing_snare_parity, outgoing_anchor_beat_index,
        incoming_snare_parity, incoming_cue_beat_index,
    )
    bar_shift = (incoming_cue_beat_index - outgoing_anchor_beat_index) % 4
    mapped = bar_shift if bar_shift <= 2 else bar_shift - 4
    if mapped % 2 == parity_shift % 2:
        return mapped
    return parity_shift


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("track_id")
    parser.add_argument("--bpm", type=float, required=True)
    parser.add_argument("--first-beat", type=float, required=True, dest="first_beat")
    parser.add_argument("--max-seconds", type=float, default=DEFAULT_MAX_SECONDS)
    args = parser.parse_args()

    result = detect_snare_phase(
        args.track_id,
        bpm=args.bpm,
        first_beat_seconds=args.first_beat,
        max_seconds=args.max_seconds,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
