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
# Below this many measured beats an "alternating pattern" is not a claim
# worth making; report zero confidence and let the caller fall back.
MIN_BEATS_FOR_PARITY = 16
# Below this, a snare-parity read is a coin flip: the planner aligns bar
# counts only and must not nudge a ride by one beat on it.
SNARE_CONFIDENCE_GATE = 0.15


def load_audio(
    path: str,
    *,
    sr: int = DEFAULT_SR,
    max_seconds: float = DEFAULT_MAX_SECONDS,
    offset_seconds: float = 0.0,
) -> np.ndarray:
    y, _ = librosa.load(
        path, sr=sr, mono=True, duration=max_seconds, offset=max(0.0, offset_seconds)
    )
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


def per_beat_energies(
    envelope: np.ndarray,
    *,
    sr: int,
    hop_length: int,
    bpm: float,
    first_beat_seconds: float,
    window_seconds: float = 0.08,
    envelope_start_seconds: float = 0.0,
) -> dict[int, float]:
    """Snare-band onset energy at every individual beat, keyed by beat index.

    Same measurement as `beat_phase_energies`, but WITHOUT collapsing into
    four bar-slot buckets. Keeping the per-beat sequence is what lets
    `detect_snare_phase` ask whether the energy *alternates*, rather than
    only comparing two grand totals.

    `envelope_start_seconds` is where the envelope begins within the track,
    so beat indices stay ABSOLUTE (counted from the track's own first beat)
    even when only a later window was decoded. Parity is meaningless unless
    the index it refers to is the same one the planner uses.
    """
    period = 60.0 / bpm
    frame_seconds = hop_length / sr
    total_seconds = len(envelope) * frame_seconds
    half_window = max(1, int(round(window_seconds / frame_seconds)))
    energies: dict[int, float] = {}
    beat = max(0, int(np.ceil((envelope_start_seconds - first_beat_seconds) / period)))
    while True:
        t = first_beat_seconds + beat * period - envelope_start_seconds
        if t > total_seconds:
            break
        if t < 0:
            beat += 1
            continue
        center_frame = int(round(t / frame_seconds))
        lo = max(0, center_frame - half_window)
        hi = min(len(envelope), center_frame + half_window)
        if hi > lo:
            energies[beat] = float(np.sum(envelope[lo:hi]))
        beat += 1
    return energies


def detect_snare_phase(
    path: str,
    *,
    bpm: float,
    first_beat_seconds: float,
    sr: int = DEFAULT_SR,
    max_seconds: float = DEFAULT_MAX_SECONDS,
    offset_seconds: float = 0.0,
) -> dict:
    """Estimate the snare/backbeat's beat parity (even beats vs. odd beats).

    Pass `offset_seconds` (normally the track's planned cue) to measure the
    section that will actually be mixed. Analyzing from 0 measures whatever
    the first two minutes happen to contain, which for a track cued late is
    a different arrangement entirely -- Top Of The World, cued at 105s,
    reads 0.009 from the track top and 0.301 from its cue.

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
    `confidence` measures how strongly the per-beat energy ALTERNATES.

    Confidence is the normalized period-2 Fourier component of the per-beat
    energy sequence, i.e. the mean-removed sequence correlated against
    (+1, -1, +1, -1, ...). The earlier estimator compared the odd-beat sum
    against the even-beat sum and divided by the larger; on real records a
    hi-hat or shaker plays every beat, and that constant floor lands in BOTH
    sums, so a genuine backbeat showed up as a small margin on top of a big
    number. Subtly-mixed snares (soul, quiet-storm R&B, live drums) scored
    near zero and fell below the planner's trust gate, which silently
    downgraded those transitions to bar-count-only alignment -- bars matched
    while 2-and-4 did not. Removing the mean first makes any constant floor
    contribute exactly nothing, so the statistic answers "does this
    alternate?" instead of "which total is bigger?".

    Measured over the 18 tracks of the 2026-08-03 sample-lineage mix, every
    track's confidence roughly doubled, four tracks crossed the 0.15 gate for
    the first time (Groove Theory 0.051 -> 0.239, Keni Burke instrumental
    0.034 -> 0.273, Ice Cream 0.105 -> 0.370, Top Of The World 0.094 ->
    0.301), and the Keni Burke instrumental's parity came out INVERTED from
    the old read -- that track sat on both transitions Ernest called the
    worst in the set.
    """
    y = load_audio(path, sr=sr, max_seconds=max_seconds, offset_seconds=offset_seconds)
    envelope, hop_length = snare_band_onset_envelope(y, sr)
    slot_energies = beat_phase_energies(
        envelope, sr=sr, hop_length=hop_length, bpm=bpm,
        first_beat_seconds=first_beat_seconds - offset_seconds,
    )
    per_beat = per_beat_energies(
        envelope, sr=sr, hop_length=hop_length, bpm=bpm,
        first_beat_seconds=first_beat_seconds, envelope_start_seconds=offset_seconds,
    )
    beats = sorted(per_beat)
    parity, confidence = 0, 0.0
    # Too few beats to claim an alternating pattern exists at all.
    if len(beats) >= MIN_BEATS_FOR_PARITY:
        values = np.array([per_beat[b] for b in beats], dtype=float)
        values -= values.mean()
        signs = np.where(np.array(beats) % 2 == 0, 1.0, -1.0)
        component = float(np.dot(values, signs))
        spread = float(np.sum(np.abs(values)))
        if spread > 0:
            # component < 0 means the odd-indexed beats carry the accents.
            parity = 1 if component < 0 else 0
            confidence = abs(component) / spread
    return {
        "snare_parity": parity,
        "confidence": round(confidence, 3),
        "slot_energies": [round(e, 4) for e in slot_energies],
    }


def detect_snare_phase_percussive(
    path: str,
    *,
    bpm: float,
    first_beat_seconds: float,
    offset_seconds: float,
    window_seconds: float = 45.0,
    sr: int = DEFAULT_SR,
) -> dict:
    """`detect_snare_phase` on the percussive (drum) component of one window.

    Harmonic/percussive separation strips sustained vocals, pads and bass
    that smear the snare-band envelope on quiet-storm R&B and live-drum
    records. It is a cheap stand-in for a real drum stem, not a stem model.
    """
    y = load_audio(path, sr=sr, max_seconds=window_seconds, offset_seconds=offset_seconds)
    y = librosa.effects.percussive(y, margin=2.0)
    envelope, hop_length = snare_band_onset_envelope(y, sr)
    per_beat = per_beat_energies(
        envelope, sr=sr, hop_length=hop_length, bpm=bpm,
        first_beat_seconds=first_beat_seconds, envelope_start_seconds=offset_seconds,
    )
    beats = sorted(per_beat)
    parity, confidence = 0, 0.0
    if len(beats) >= MIN_BEATS_FOR_PARITY:
        values = np.array([per_beat[b] for b in beats], dtype=float)
        values -= values.mean()
        signs = np.where(np.array(beats) % 2 == 0, 1.0, -1.0)
        component = float(np.dot(values, signs))
        spread = float(np.sum(np.abs(values)))
        if spread > 0:
            parity = 1 if component < 0 else 0
            confidence = abs(component) / spread
    return {"snare_parity": parity, "confidence": round(confidence, 3), "offset_seconds": offset_seconds}


# Blend-window reads (2026-10-13). The song-wide read comes from the first
# minutes of the song; Mix to listen blends out near the end, where an extra
# half-bar in the arrangement or live drums drifting off Mixxx's constant grid
# can put the snare on the other beats. A drum-only read of the actual blend
# window outranks the song-wide read only when it is at least this sure:
# below it, today's behaviour (song-wide read, or bar count only) stands.
BLEND_WINDOW_GATE = 0.25
# Window length in beats and where it starts. Outgoing: a few bars before the
# fade starts through the blend. Incoming: from its cue through the blend.
BLEND_WINDOW_BEATS = 64
BLEND_WINDOW_LEAD_BEATS = 16


def blend_window_start_beat(beat_index: int) -> int:
    """Window start, rounded down to 8 beats so rebuilds reuse cached reads."""
    return max(0, (int(beat_index) // 8) * 8)


def measure_blend_window(
    path: str, *, bpm: float, first_beat_seconds: float, start_beat: int,
    beats: int = BLEND_WINDOW_BEATS,
) -> dict:
    """Drum-only snare parity of `beats` beats starting at global `start_beat`."""
    beat_seconds = 60.0 / float(bpm)
    return detect_snare_phase_percussive(
        path, bpm=bpm, first_beat_seconds=first_beat_seconds,
        offset_seconds=float(first_beat_seconds) + start_beat * beat_seconds,
        window_seconds=beats * beat_seconds,
    )


def fit_backbeat_timing(envelope, times, *, real_bpm: float) -> dict:
    """Fit actual transient timing, without declaring grid beat zero count one.

    The beat cadence is independently supplied, not selected from the largest
    autocorrelation peak (syncopated music often has a stronger dotted-beat peak).
    Absolute source seconds survive silent/late intros and double-time grids.
    Constant hats and weak/irregular evidence are refused, not called matched.
    """
    from shared.backbeat import positive_number

    bpm = positive_number(real_bpm, 'real BPM')
    env, clock = np.asarray(envelope, dtype=float), np.asarray(times, dtype=float)
    if (env.ndim != 1 or env.shape != clock.shape or len(env) < 3
            or not np.all(np.isfinite(env)) or not np.all(np.isfinite(clock))
            or np.any(np.diff(clock) <= 0)):
        raise ValueError('backbeat timing needs finite, increasing source times')
    period, cycle = 60 / bpm, 120 / bpm
    step = max(.002, min(.006, float(np.median(np.diff(clock)))))
    phases = np.arange(0, cycle, step)
    lo, hi = float(clock[0]) + .04, float(clock[-1]) - .04
    scores, rows = [], []
    for phase in phases:
        first = phase + np.ceil((lo - phase) / cycle) * cycle
        beats = np.arange(first, hi, cycle)
        # Small local envelope maximum avoids quantization of the analysis hop.
        values = np.max([np.interp(beats + d, clock, env) for d in (-.012, 0, .012)], axis=0)
        rows.append((beats, values))
        scores.append(float(np.median(values)) if len(values) >= 8 else 0.)
    best = int(np.argmax(scores))
    peak = scores[best]
    opposite = float(np.interp((phases[best] + period) % cycle, phases, scores, period=cycle))
    beats, values = rows[best]
    agreement = float(np.mean(values >= peak * .45)) if peak > 0 else 0.
    contrast = max(0., (peak - opposite) / max(peak, 1e-12))
    confidence = contrast * agreement
    if peak <= 1e-10 or confidence < .2 or len(beats) < 8:
        raise ValueError('no stable, contrasting snare cycle in this source window')
    # Refine the phase from observed peak times, not the broad search-window edge.
    residuals, observed = [], []
    for beat in beats:
        near = np.flatnonzero(np.abs(clock - beat) <= .025)
        if len(near):
            j = int(near[np.argmax(env[near])])
            if env[j] >= peak * .45:
                residuals.append(float(clock[j] - beat)); observed.append(float(clock[j]))
    phase = (float(phases[best]) + float(np.median(residuals))) % cycle
    residual = np.asarray([((t - phase + period) % cycle - period) for t in observed])
    jitter = float(np.median(np.abs(residual)))
    if jitter > .035:
        raise ValueError('snare timing wanders beyond the measured-start tolerance')
    return {'real_bpm': bpm, 'snare_phase_seconds': round(phase, 6),
            'confidence': round(confidence, 3), 'observed_hits': len(observed),
            'median_residual_ms': round(jitter * 1000, 3),
            'first_observed_hit_seconds': round(min(observed), 6),
            'window_start_seconds': float(clock[0]), 'window_end_seconds': float(clock[-1]),
            'count1_verified': False}


def measure_backbeat_timing(path: str, *, real_bpm: float, offset_seconds: float,
                            window_seconds: float = 32., sr: int = 11025) -> dict:
    """Short, read-only source-window measurement; never modifies grid/cache/audio."""
    from scipy.signal import stft

    if not 8 <= window_seconds <= 60 or not np.isfinite(offset_seconds) or offset_seconds < 0:
        raise ValueError('backbeat measurement requires a bounded source window')
    y = load_audio(path, sr=sr, offset_seconds=offset_seconds, max_seconds=window_seconds)
    _, times, spectrum = stft(y, fs=sr, nperseg=512, noverlap=448, boundary='zeros')
    freqs = np.fft.rfftfreq(512, 1 / sr)
    band = np.abs(spectrum[(freqs >= 700) & (freqs <= min(5000, sr / 2))])
    envelope = np.maximum(0., np.diff(band, axis=1, prepend=band[:, :1])).sum(axis=0)
    return fit_backbeat_timing(envelope, times + offset_seconds, real_bpm=real_bpm)


def prefer_blend_window(song_wide: dict, window: dict | None) -> tuple[dict, bool]:
    """Pick the snare read to align on: the blend window's when it is sure.

    Returns (phase, used_window). `phase` keeps the song's grid fields and
    takes the window's parity/confidence when the window clears
    BLEND_WINDOW_GATE.
    """
    if not window or float(window.get("confidence") or 0.0) < BLEND_WINDOW_GATE:
        return song_wide, False
    return {
        **song_wide,
        "snare_parity": int(window["snare_parity"]),
        "confidence": float(window["confidence"]),
    }, True


# Double-time grids (2026-10-15). Mixxx sometimes grids a ~94 BPM song at
# ~188, so every grid beat is an eighth note. Found live: Shanice "I Love
# Your Smile" (187.88) -> SWV "You're The One" (94.0) came in off by a count.
# On such a grid the odd/even test above compares on-beats with off-beats,
# not kick with snare, and grid beat 0 can sit on an "and": Shanice's real
# beats are her ODD grid beats, and Build started SWV on an even one.
# A pair is mixed when one grid counts about twice as fast as the other.
DOUBLE_TIME_RATIO = (1.8, 2.2)
# Window in grid beats: 64 real beats on a double-time grid.
REAL_BEAT_WINDOW_BEATS = 128
# Trust the real-beat read only when one starting position clearly wins.
REAL_BEAT_MARGIN = 0.15


def double_time_side(outgoing_bpm: float | None, incoming_bpm: float | None) -> str | None:
    """'out' or 'in' when that side's grid counts twice per beat of the other."""
    if not outgoing_bpm or not incoming_bpm:
        return None
    ratio = float(outgoing_bpm) / float(incoming_bpm)
    low, high = DOUBLE_TIME_RATIO
    if low <= ratio <= high:
        return "out"
    if low <= 1.0 / ratio <= high:
        return "in"
    return None


def _alternation(per_beat: dict[int, float]) -> tuple[int, float]:
    """(parity of the accented beats, how strongly they alternate)."""
    beats = sorted(per_beat)
    if len(beats) < MIN_BEATS_FOR_PARITY:
        return 0, 0.0
    values = np.array([per_beat[b] for b in beats], dtype=float)
    values -= values.mean()
    signs = np.where(np.array(beats) % 2 == 0, 1.0, -1.0)
    component = float(np.dot(values, signs))
    spread = float(np.sum(np.abs(values)))
    if spread <= 0:
        return 0, 0.0
    return (1 if component < 0 else 0), abs(component) / spread


def measure_real_beats(
    path: str, *, bpm: float, first_beat_seconds: float, start_beat: int,
    beats: int = REAL_BEAT_WINDOW_BEATS, sr: int = DEFAULT_SR,
) -> dict:
    """Find the real beats and the snare on a double-time grid.

    Reads the drums at half the grid tempo twice: once counting from grid
    beat 0, once from grid beat 1. Counted on the real beats, kick and snare
    alternate strongly; counted on the "and"s, they barely do. Shanice's
    blend window reads 0.95 from grid beat 1 and 0.13 from grid beat 0.

    Returns {"beat_phase": grid-beat parity of the real beats,
    "snare_parity": parity of the snare in real-beat index r, where grid
    beat = 2r + beat_phase, "confidence", "other_confidence"}.
    """
    beat_seconds = 60.0 / float(bpm)
    offset_seconds = float(first_beat_seconds) + start_beat * beat_seconds
    y = load_audio(path, sr=sr, max_seconds=beats * beat_seconds, offset_seconds=offset_seconds)
    y = librosa.effects.percussive(y, margin=2.0)
    envelope, hop_length = snare_band_onset_envelope(y, sr)
    reads = []
    for phase in (0, 1):
        per_beat = per_beat_energies(
            envelope, sr=sr, hop_length=hop_length, bpm=float(bpm) / 2.0,
            first_beat_seconds=float(first_beat_seconds) + phase * beat_seconds,
            envelope_start_seconds=offset_seconds,
        )
        parity, confidence = _alternation(per_beat)
        reads.append((confidence, phase, parity))
    (confidence, phase, parity), (other, _, _) = sorted(reads, reverse=True)
    return {
        "beat_phase": phase,
        "snare_parity": parity,
        "confidence": round(confidence, 3),
        "other_confidence": round(other, 3),
    }


def trust_real_beats(read: dict | None) -> bool:
    """A real-beat read is usable when it is sure and one position clearly wins."""
    if not read:
        return False
    confidence = float(read.get("confidence") or 0.0)
    return (
        confidence >= BLEND_WINDOW_GATE
        and confidence - float(read.get("other_confidence") or 0.0) >= REAL_BEAT_MARGIN
    )


def double_time_shifts(
    *, side: str, outgoing_anchor_beat_index: int, incoming_cue_beat_index: int,
    outgoing_read: dict, incoming_read: dict,
) -> tuple[int, int]:
    """(outgoing ride shift, incoming cue shift), both in that deck's grid beats.

    `side` is the double-time deck. Its read carries "beat_phase" and the
    snare parity in real beats; the other read is an ordinary snare read.

    Outgoing double: the incoming enters on grid beat A of the outgoing, and
    every incoming beat after it lands two outgoing grid beats later. A must
    be a real beat (A = 2r + phase), then the usual snare + bar-count rule
    applies in real beats. Incoming double: its cue moves one grid beat onto
    a real beat when needed, then the rule applies to its real-beat index.
    """
    anchor, cue = int(outgoing_anchor_beat_index), int(incoming_cue_beat_index)
    if side == "out":
        phase = int(outgoing_read["beat_phase"])
        best = None
        for fix in ([0] if (anchor - phase) % 2 == 0 else [-1, 1]):
            real = count_shift_beats(
                outgoing_snare_parity=int(outgoing_read["snare_parity"]),
                outgoing_anchor_beat_index=(anchor + fix - phase) // 2,
                incoming_snare_parity=int(incoming_read["snare_parity"]),
                incoming_cue_beat_index=cue,
            )
            total = fix + 2 * real
            if best is None or abs(total) < abs(best):
                best = total
        return best, 0
    phase = int(incoming_read["beat_phase"])
    cue_shift = 0 if (cue - phase) % 2 == 0 else 1
    shift = count_shift_beats(
        outgoing_snare_parity=int(outgoing_read["snare_parity"]),
        outgoing_anchor_beat_index=anchor,
        incoming_snare_parity=int(incoming_read["snare_parity"]),
        incoming_cue_beat_index=(cue + cue_shift - phase) // 2,
    )
    return shift, cue_shift


def agree_on_parity(windows: list[dict], *, gate: float, min_agreeing: int = 2) -> dict | None:
    """Combine per-window reads without inflating confidence.

    Accept only when at least `min_agreeing` windows clear `gate` AND every
    window that clears it names the same parity. The stored confidence is
    the weakest passing window, never the best one — picking the maximum of
    several tries would manufacture confidence out of noise. Returns None
    when the windows disagree or too few pass (the original read stands).
    """
    passing = [w for w in windows if float(w.get("confidence") or 0.0) >= gate]
    if len(passing) < min_agreeing:
        return None
    parities = {int(w["snare_parity"]) for w in passing}
    if len(parities) != 1:
        return None
    return {
        "snare_parity": parities.pop(),
        "confidence": min(float(w["confidence"]) for w in passing),
        "windows": len(windows),
        "agreeing": len(passing),
    }


def remeasure_snare_phase(
    path: str,
    *,
    bpm: float,
    first_beat_seconds: float,
    duration_seconds: float | None,
    gate: float,
    window_seconds: float = 45.0,
    windows: int = 4,
) -> dict | None:
    """Re-read a weak snare phase from several drum-only windows.

    Windows are spread across the body of the song (skipping the first and
    last 10%, where intros and outros are often drumless). Snare parity is
    defined on the global beat index, so any window measures the same
    quantity the planner needs.
    """
    total = float(duration_seconds or 0.0) or (window_seconds * (windows + 1))
    start = total * 0.10
    end = max(start + window_seconds, total * 0.90 - window_seconds)
    step = (end - start) / max(1, windows - 1)
    reads = []
    for i in range(windows):
        offset = start + i * step
        try:
            reads.append(
                detect_snare_phase_percussive(
                    path, bpm=bpm, first_beat_seconds=first_beat_seconds,
                    offset_seconds=offset, window_seconds=window_seconds,
                )
            )
        except Exception:
            continue
    result = agree_on_parity(reads, gate=gate)
    if result is not None:
        result["reads"] = reads
    return result


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

    This is legacy arithmetic, NOT a verified musical downbeat detector.
    Callers must check bar_count_guessed before applying its result; the
    planner withholds ambiguous corrections rather than choosing +1 by fiat.

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


def bar_count_guessed(
    outgoing_snare_parity: int,
    outgoing_anchor_beat_index: int,
    incoming_snare_parity: int,
    incoming_cue_beat_index: int,
) -> bool:
    """True when `count_shift_beats` had to drop the bar assumption.

    Then one grid's beat 0 is not count 1, and +1 and -1 both match the
    snares: one lands count 1 on count 1, the other lands it on count 3.
    `count_shift_beats` always picks +1, so the count is a coin flip.
    Found 2026-10-21: 99 of 269 vol-02 blends took this branch, including
    SWV "You're The One" remix -> "I'm So Into You" (+1 to beat 421) and
    four of the six "off by 1 count" blends from 2026-10-15. The pilot
    suggested 419, but Ernest later rejected BOTH 419 and 421 and approved
    the 420 bar phase (subsequently a longer blend beginning at 400).
    A count-1 detector (kick, snare and chord changes
    folded per beat-in-bar) agreed with Ernest's ear on only 9 of 14
    approved blends, so the planner cannot resolve the flip yet. It marks
    the blend "bar_guessed" so the listener knows to check the count.
    Since 2026-10-23 the planner also withholds the guessed shift and any
    inferred snare jump; the label alone was not an execution safeguard.
    """
    parity_shift = phase_shift_beats(
        outgoing_snare_parity, outgoing_anchor_beat_index,
        incoming_snare_parity, incoming_cue_beat_index,
    )
    bar_shift = (incoming_cue_beat_index - outgoing_anchor_beat_index) % 4
    mapped = bar_shift if bar_shift <= 2 else bar_shift - 4
    return mapped % 2 != parity_shift % 2


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
