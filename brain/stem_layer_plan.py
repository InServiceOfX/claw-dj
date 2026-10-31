"""Measure and plan one vocal-over-instrumental layer (two decks, live).

An acapella has no drums, so its backbeat cannot be read from its own audio.
Its vocal take is the same one heard on the full mix of the same song, so we
cross-correlate the two vocal-band onset envelopes. The offset transfers the
full mix's measured snare timing and tempo onto the acapella. That makes
snare-on-2-and-4 exact on both sides. Which snare cycle holds count 1 is
still not measurable (brain.onset_analysis.bar_count_guessed, detector
agreed with Ernest on 9 of 14). So count 1 is labeled "guessed" and the
alternative is a whole snare cycle (2 beats), never a 1-beat shift, which
would put a snare on 1 and 3.

Everything here is read-only analysis of the original files (nothing is
rendered). hands.stem_layer performs the plan live in Mixxx.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
from contextlib import closing
from pathlib import Path
from typing import Any

import numpy as np

from brain import library_index
from brain.library import DEFAULT_CRATE_CACHE
from brain.stems import classify_track, core_title, is_clean_version

CACHE_PATH = DEFAULT_CRATE_CACHE.parent / "stem_layers.json"
ANALYSIS_SR = 11025
HOP = 110                      # about 10 ms per envelope frame at 11025 Hz
VOICE_BAND_HZ = (300.0, 3400.0)
MIN_ALIGN_CONFIDENCE = 1.6     # peak over the best rival peak (>0.5 s away)
MAX_HALF_DISAGREEMENT_S = 0.02 # first and second halves must give one offset
TOLERANCE_MS = 30.0            # same start guard as the measured backbeat path
DEFAULT_LEAD_BARS = 8          # instrumental alone before the vocal comes in
PREROLL_BEATS = 4              # vocal deck starts one bar early, in its silence
# Ear-first levels. Mixxx ReplayGain is on in Ernest's mixxx.cfg, so analyzed
# tracks already play at a common loudness; these keep the voice in front.
BED_PREGAIN = 0.8              # about -2 dB under the vocal
BED_MID_INSTRUMENTAL = 0.8     # leave room for the voice
BED_MID_FULL_MIX = 0.35        # push the bed's own singer back (same as the runner)
BED_HIGH_FULL_MIX = 0.7


class LayerPlanError(ValueError):
    pass


# --------------------------------------------------------------------------
# library lookups


def library_row(track_id: str, index_path: Path | None = None) -> dict[str, Any]:
    with closing(library_index.connect(index_path or library_index.current_index_path())) as db:
        row = db.execute(
            "SELECT track_id, title, artist, album, duration_seconds, bpm, key, dj_notes "
            "FROM tracks WHERE track_id = ? AND available = 1",
            (track_id,),
        ).fetchone()
    if row is None:
        raise LayerPlanError(f"not an available library track: {track_id}")
    return dict(row)


def _artist_tokens(artist: str) -> set[str]:
    stop = {"feat", "ft", "featuring", "with", "and", "the", "x", "vs"}
    return {w for w in re.findall(r"[a-z0-9]+", (artist or "").lower()) if w not in stop and len(w) > 1}


def find_siblings(vocal: dict, index_path: Path | None = None) -> list[dict[str, Any]]:
    """Full mixes of the same song (same core title, overlapping artist).

    Explicit/album versions first: a clean edit mutes words, which weakens
    the alignment, and Ernest prefers the dirty vocal anyway.
    """
    wanted = core_title(vocal.get("title") or "")
    if not wanted:
        return []
    first = wanted.split()[0]
    artists = _artist_tokens(vocal.get("artist") or "")
    with closing(library_index.connect(index_path or library_index.current_index_path())) as db:
        rows = db.execute(
            "SELECT track_id, title, artist, duration_seconds, bpm, key, dj_notes FROM tracks "
            "WHERE available = 1 AND lower(title) LIKE ?",
            (f"%{first}%",),
        ).fetchall()
    found = []
    for row in map(dict, rows):
        if row["track_id"] == vocal["track_id"] or core_title(row["title"]) != wanted:
            continue
        if artists and not (artists & _artist_tokens(row["artist"])):
            continue
        if classify_track(row["title"], row["track_id"], row.get("dj_notes") or "")["kind"] != "full_mix":
            continue
        found.append(row)
    found.sort(key=lambda r: (is_clean_version(r["title"]), r["track_id"]))
    return found


# --------------------------------------------------------------------------
# audio measurements (pure numpy on decoded audio, so tests can feed signals)


def load_mono(path: str, *, sr: int = ANALYSIS_SR) -> np.ndarray:
    import librosa

    y, _ = librosa.load(path, sr=sr, mono=True)
    return y.astype(np.float32)


def voice_onset_envelope(y: np.ndarray, *, sr: int = ANALYSIS_SR, hop: int = HOP) -> np.ndarray:
    """Positive spectral flux in the voice band, one value per hop."""
    from scipy.signal import stft

    _, _, spectrum = stft(y, fs=sr, nperseg=512, noverlap=512 - hop, boundary=None, padded=False)
    freqs = np.fft.rfftfreq(512, 1 / sr)
    band = np.abs(spectrum[(freqs >= VOICE_BAND_HZ[0]) & (freqs <= VOICE_BAND_HZ[1])])
    band = np.log1p(100.0 * band)
    flux = np.maximum(0.0, np.diff(band, axis=1, prepend=band[:, :1])).sum(axis=0)
    flux -= flux.mean()
    return flux / (flux.std() + 1e-9)


def _xcorr(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Full cross-correlation; index k <-> lag (k - (len(b) - 1)) of a against b."""
    n = len(a) + len(b) - 1
    size = 1 << (n - 1).bit_length()
    spectrum = np.fft.rfft(a, size) * np.conj(np.fft.rfft(b, size))
    full = np.fft.irfft(spectrum, size)
    # irfft of A*conj(B) gives circular lags; unwrap to linear order
    return np.concatenate([full[-(len(b) - 1):], full[: len(a)]]) if len(b) > 1 else full[: len(a)]


def align_offset(vocal_env: np.ndarray, full_env: np.ndarray, *, frame_seconds: float) -> dict[str, float]:
    """Offset (seconds) with full_time = vocal_time + offset, and confidence."""
    corr = _xcorr(full_env, vocal_env)
    lags = np.arange(-(len(vocal_env) - 1), len(full_env))
    best = int(np.argmax(corr))
    guard = max(1, int(round(0.5 / frame_seconds)))
    rival_mask = np.abs(lags - lags[best]) > guard
    floor = float(np.median(corr))
    rival = float(np.max(corr[rival_mask])) if rival_mask.any() else floor
    peak = float(corr[best])
    confidence = (peak - floor) / max(rival - floor, 1e-9)
    # parabolic refinement
    shift = 0.0
    if 0 < best < len(corr) - 1:
        left, mid, right = corr[best - 1], corr[best], corr[best + 1]
        denom = left - 2 * mid + right
        if denom < 0:
            shift = 0.5 * (left - right) / denom
    return {"offset_seconds": float((lags[best] + shift) * frame_seconds), "confidence": float(confidence)}


def align_to_sibling(vocal_y: np.ndarray, full_y: np.ndarray, *, sr: int = ANALYSIS_SR) -> dict[str, Any]:
    """Whole-file offset plus a check that both halves agree (same tempo, no edit)."""
    frame = HOP / sr
    v_env, f_env = voice_onset_envelope(vocal_y, sr=sr), voice_onset_envelope(full_y, sr=sr)
    whole = align_offset(v_env, f_env, frame_seconds=frame)
    half = len(v_env) // 2
    first = align_offset(v_env[:half], f_env, frame_seconds=frame)
    second = align_offset(v_env[half:], f_env, frame_seconds=frame)
    second_offset = second["offset_seconds"] - half * frame
    disagreement = abs(first["offset_seconds"] - second_offset)
    usable = whole["confidence"] >= MIN_ALIGN_CONFIDENCE and disagreement <= MAX_HALF_DISAGREEMENT_S
    return {
        "offset_seconds": round(whole["offset_seconds"], 4),
        "confidence": round(whole["confidence"], 3),
        "half_disagreement_ms": round(disagreement * 1000, 1),
        "usable": bool(usable),
    }


def rms_db_frames(y: np.ndarray, *, sr: int = ANALYSIS_SR, frame_seconds: float = 0.05) -> list[float]:
    frame = max(1, int(sr * frame_seconds))
    count = len(y) // frame
    rms = np.sqrt(np.mean(y[: count * frame].reshape(count, frame) ** 2, axis=1) + 1e-12)
    return [round(float(v), 1) for v in 20 * np.log10(rms)]


def vocal_span(rms_db: list[float], *, start_seconds: float = 0.0, end_seconds: float | None = None,
               frame_seconds: float = 0.05) -> dict[str, float]:
    """First and last sustained vocal sound (seconds) inside [start, end]."""
    db = np.asarray(rms_db, dtype=float)
    if len(db) < 3:
        raise LayerPlanError("vocal file is too short to measure")
    lo = max(0, int(start_seconds / frame_seconds))
    hi = len(db) if end_seconds is None else min(len(db), int(end_seconds / frame_seconds) + 1)
    if hi - lo < 3:
        raise LayerPlanError("the chosen vocal section is too short")
    threshold = max(float(np.max(db)) - 30.0, -45.0)
    window = db[lo:hi] >= threshold
    run = np.convolve(window.astype(int), np.ones(3, dtype=int), mode="valid") == 3
    hits = np.flatnonzero(run)
    if not len(hits):
        raise LayerPlanError("no sustained vocal found in the chosen section")
    return {"first_seconds": round(float((lo + hits[0]) * frame_seconds), 3),
            "last_seconds": round(float((lo + hits[-1] + 3) * frame_seconds), 3)}


def refine_tempo(envelope: np.ndarray, *, frame_seconds: float, coarse_bpm: float,
                 span: float = 0.03, step: float = 0.004) -> float:
    """Tempo to a few thousandths of a BPM: the peak of the onset envelope's
    spectrum near `coarse_bpm`, over the whole file (phase-independent).
    A long layer drifts audibly with a 0.1% tempo error, so a rough tag BPM
    is not enough.
    """
    env = np.asarray(envelope, dtype=float)
    env = env - env.mean()
    times = np.arange(len(env)) * frame_seconds
    candidates = np.arange(coarse_bpm * (1 - span), coarse_bpm * (1 + span), coarse_bpm * step / 100)
    power = np.empty(len(candidates))
    for start in range(0, len(candidates), 64):
        chunk = candidates[start:start + 64]
        phases = np.exp(-2j * np.pi * np.outer(chunk / 60.0, times))
        power[start:start + 64] = np.abs(phases @ env)
    best = int(np.argmax(power))
    shift = 0.0
    if 0 < best < len(power) - 1:
        left, mid, right = power[best - 1], power[best], power[best + 1]
        denom = left - 2 * mid + right
        if denom < 0:
            shift = 0.5 * (left - right) / denom
    return float(candidates[best] + shift * (candidates[1] - candidates[0]))


def estimate_tempo(y: np.ndarray, *, sr: int = ANALYSIS_SR, prior_bpm: float | None = None) -> float:
    """Precise tempo of a drummed recording (an instrumental or a full mix)."""
    import librosa

    envelope = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP)
    frame = HOP / sr
    if prior_bpm:
        coarse = float(prior_bpm)
    else:
        coarse = float(np.atleast_1d(librosa.feature.tempo(onset_envelope=envelope, sr=sr, hop_length=HOP))[0])
    # real beats, not eighth notes: the snare must fall on every other beat
    while coarse >= 140:
        coarse /= 2
    while coarse < 65:
        coarse *= 2
    return round(refine_tempo(envelope, frame_seconds=frame, coarse_bpm=coarse), 4)


def gated_loudness_db(y: np.ndarray, *, sr: int = ANALYSIS_SR) -> float:
    """Mean energy of the frames within 20 dB of the loudest (silences excluded)."""
    frame = max(1, int(sr * 0.4))
    count = len(y) // frame
    if not count:
        return -70.0
    energy = np.mean(y[: count * frame].reshape(count, frame) ** 2, axis=1) + 1e-12
    db = 10 * np.log10(energy)
    kept = energy[db >= float(np.max(db)) - 20.0]
    return round(float(10 * np.log10(np.mean(kept))), 2)


# --------------------------------------------------------------------------
# beat maps: where every beat really falls, in source seconds


class BeatMap:
    """Beat times of one recording (source seconds), possibly unevenly spaced.

    Live-drummed and tape-era records drift (Wham! "Careless Whisper
    (Instrumental)" wanders about +/-200 ms around any fixed tempo), so a
    constant grid cannot hold a long layer. Index k is a beat; `snare_parity`
    is the index parity the snare falls on (k % 2), or None if unmeasured.
    """

    def __init__(self, beats, snare_parity: int | None = None) -> None:
        self.beats = np.asarray(beats, dtype=float)
        if len(self.beats) < 8 or np.any(np.diff(self.beats) <= 0):
            raise LayerPlanError("a beat map needs at least 8 increasing beats")
        self.snare_parity = snare_parity
        self._index = np.arange(len(self.beats), dtype=float)

    def index_at(self, seconds: float) -> float:
        """Fractional beat index at a source time (linear past either end)."""
        b = self.beats
        if seconds < b[0]:
            return (seconds - b[0]) / (b[1] - b[0])
        if seconds > b[-1]:
            return len(b) - 1 + (seconds - b[-1]) / (b[-1] - b[-2])
        return float(np.interp(seconds, b, self._index))

    def time_at(self, index: float) -> float:
        b = self.beats
        if index < 0:
            return float(b[0] + index * (b[1] - b[0]))
        if index > len(b) - 1:
            return float(b[-1] + (index - len(b) + 1) * (b[-1] - b[-2]))
        return float(np.interp(index, self._index, b))

    def period_at(self, index: float) -> float:
        i = int(min(max(0, math.floor(index)), len(self.beats) - 2))
        return float(self.beats[i + 1] - self.beats[i])

    def kick_index_at_or_after(self, seconds: float) -> int:
        """First beat at or after `seconds` that is NOT a snare (count 1 or 3)."""
        k = max(0, math.ceil(self.index_at(seconds) - 1e-6))
        if self.snare_parity is not None and k % 2 == self.snare_parity:
            k += 1
        return k

    def to_dict(self) -> dict:
        return {"beats": [round(float(t), 4) for t in self.beats], "snare_parity": self.snare_parity}

    @classmethod
    def from_dict(cls, data: dict) -> "BeatMap":
        return cls(data["beats"], data.get("snare_parity"))

    def shifted(self, offset_seconds: float, duration: float) -> "BeatMap":
        """The same beats in another file's time (t - offset), inside [0, duration]."""
        times = self.beats - offset_seconds
        keep = np.flatnonzero((times >= 0) & (times <= duration))
        if len(keep) < 8:
            raise LayerPlanError("the full mix and the vocal share too few beats")
        first = int(keep[0])
        parity = None if self.snare_parity is None else (self.snare_parity - first) % 2
        return BeatMap(times[keep], parity)


def phase_track(envelope: np.ndarray, *, frame_seconds: float, bpm: float,
                window_seconds: float = 12.0, hop_seconds: float = 3.0) -> dict[str, np.ndarray]:
    """Beat phase of the onset envelope in sliding windows (phase-of-fundamental)."""
    env = np.asarray(envelope, dtype=float)
    times = np.arange(len(env)) * frame_seconds
    period = 60.0 / bpm
    centers, phases, strengths = [], [], []
    for start in np.arange(0.0, max(0.0, times[-1] - window_seconds) + 1e-9, hop_seconds):
        mask = (times >= start) & (times < start + window_seconds)
        e = env[mask] - env[mask].mean()
        z = np.sum(e * np.exp(-2j * np.pi * times[mask] / period))
        centers.append(start + window_seconds / 2)
        phases.append((-np.angle(z) / (2 * np.pi) * period) % period)
        strengths.append(abs(z) / (np.sum(np.abs(e)) + 1e-12))
    centers, phases, strengths = map(np.asarray, (centers, phases, strengths))
    unwrapped = np.unwrap(phases * 2 * np.pi / period) * period / (2 * np.pi)
    return {"centers": centers, "phases": unwrapped, "strengths": strengths}


def build_beat_map(envelope: np.ndarray, *, frame_seconds: float, bpm: float, duration: float) -> tuple[BeatMap, dict]:
    """Beats from a phase track: t_k = phase(t_k) + k * period, solved per beat.

    Windows whose beat is weak (a breakdown, an intro pad) are dropped and the
    drift is interpolated across them.
    """
    track = phase_track(envelope, frame_seconds=frame_seconds, bpm=bpm)
    strong = track["strengths"] >= 0.5 * float(np.median(track["strengths"]))
    if strong.sum() < 3:
        raise LayerPlanError("no steady beat found")
    centers, phases = track["centers"][strong], track["phases"][strong]
    # re-unwrap after dropping windows so the curve stays continuous
    period = 60.0 / bpm
    phases = np.unwrap(phases * 2 * np.pi / period) * period / (2 * np.pi)
    phase_at = lambda t: np.interp(t, centers, phases)  # noqa: E731 (flat outside)
    env = envelope
    k0 = math.ceil((0.0 - phase_at(0.0)) / period)
    k1 = math.floor((duration - phase_at(duration)) / period)
    ks = np.arange(k0, k1 + 1)
    beats = ks * period + phase_at(ks * period)
    for _ in range(3):
        beats = ks * period + phase_at(beats)
    beats = snap_to_onsets(beats, env=np.asarray(envelope, dtype=float), frame_seconds=frame_seconds, period=period)
    trend = np.polyfit(centers, phases, 1)
    residual = phases - np.polyval(trend, centers)
    info = {"drift_ms": round(float(np.ptp(residual)) * 1000, 1),
            "mean_bpm": round(60.0 / float(np.median(np.diff(beats))), 4)}
    return BeatMap(beats), info


def snap_to_onsets(beats: np.ndarray, *, env: np.ndarray, frame_seconds: float, period: float,
                   reach: float = 0.06, smooth_beats: int = 9) -> np.ndarray:
    """Move each beat onto its drum hit, smoothed over neighbouring beats.

    The windowed phase sits at the centre of the beat's onset energy, a little
    before the hit, and averages over 12 s. Here each beat finds its strongest
    onset within +/-60 ms; a running median over 9 beats ignores missed or
    extra hits (hi-hats, fills) and keeps the map musical.
    """
    reach_frames = max(1, int(round(min(reach, period / 4) / frame_seconds)))
    threshold = float(np.percentile(env, 75))
    offsets = np.full(len(beats), np.nan)
    for k, t in enumerate(beats):
        i = int(round(t / frame_seconds))
        lo, hi = max(0, i - reach_frames), min(len(env), i + reach_frames + 1)
        if hi - lo < 3:
            continue
        j = lo + int(np.argmax(env[lo:hi]))
        if env[j] >= threshold and lo < j < hi - 1:
            left, mid, right = env[j - 1], env[j], env[j + 1]
            denom = left - 2 * mid + right
            frac = 0.5 * (left - right) / denom if denom < 0 else 0.0
            offsets[k] = (j + frac - t / frame_seconds) * frame_seconds
    if np.count_nonzero(~np.isnan(offsets)) < len(beats) // 3:
        return beats
    half = smooth_beats // 2
    smoothed = np.array([
        np.nanmedian(offsets[max(0, k - half):k + half + 1]) if np.any(~np.isnan(offsets[max(0, k - half):k + half + 1]))
        else np.nan for k in range(len(beats))
    ])
    good = ~np.isnan(smoothed)
    smoothed = np.interp(np.arange(len(beats)), np.flatnonzero(good), smoothed[good])
    snapped = beats + smoothed
    return snapped if np.all(np.diff(snapped) > 0) else beats


def band_flux(y: np.ndarray, *, sr: int, low: float, high: float) -> np.ndarray:
    from scipy.signal import stft

    _, _, spectrum = stft(y, fs=sr, nperseg=512, noverlap=512 - HOP, boundary=None, padded=False)
    freqs = np.fft.rfftfreq(512, 1 / sr)
    band = np.abs(spectrum[(freqs >= low) & (freqs <= high)])
    return np.maximum(0.0, np.diff(band, axis=1, prepend=band[:, :1])).sum(axis=0)


def snare_parity(y: np.ndarray, beats: np.ndarray, *, sr: int = ANALYSIS_SR) -> tuple[int | None, float]:
    """Which beat parity holds the snare: snare-band hits up, kick-band hits down."""
    frame = HOP / sr
    snare = band_flux(y, sr=sr, low=700.0, high=5000.0)
    kick = band_flux(y, sr=sr, low=30.0, high=150.0)

    def at(env: np.ndarray) -> np.ndarray:
        idx = np.clip(np.round(beats / frame).astype(int), 2, len(env) - 3)
        return np.max(np.stack([env[idx + d] for d in range(-2, 3)]), axis=0)

    s, k = at(snare), at(kick)
    even, odd = np.arange(len(beats)) % 2 == 0, np.arange(len(beats)) % 2 == 1
    s_contrast = (s[even].mean() - s[odd].mean()) / (s.mean() + 1e-12)
    k_contrast = (k[even].mean() - k[odd].mean()) / (k.mean() + 1e-12)
    score = s_contrast - k_contrast          # >0: snare on even beats
    confidence = round(float(min(1.0, abs(score) / 2)), 3)
    if confidence < 0.05:
        return None, confidence
    return (0 if score > 0 else 1), confidence


def fold_tempo(bed_bpm: float, vocal_bpm: float) -> float:
    """The bed's real tempo nearest the vocal's (half/double grids)."""
    return min((bed_bpm * f for f in (0.5, 1.0, 2.0)), key=lambda b: abs(math.log(b / vocal_bpm)))


def choose_vocal_anchor(vocal_map: BeatMap, first_word: float, count_shift_beats: int = 0) -> int:
    """The vocal's count-1 candidate: the first kick beat at or after (first
    word - 1 beat), so a short pickup lands just before it. `count_shift_beats`
    must be a whole snare cycle (multiple of 2).
    """
    if count_shift_beats % 2:
        raise LayerPlanError("a count shift must be a whole snare cycle (2 beats): "
                             "1 beat would put the snare on 1 and 3")
    period = vocal_map.period_at(vocal_map.index_at(first_word))
    return vocal_map.kick_index_at_or_after(first_word - period) + count_shift_beats


def choose_bed_entry(bed_map: BeatMap, bed_cue: float, lead_bars: int) -> int:
    """A kick beat `lead_bars` whole bars after the first kick beat past the cue."""
    return bed_map.kick_index_at_or_after(bed_cue) + 4 * lead_bars


# --------------------------------------------------------------------------
# cache


def _fingerprint(path: str) -> str:
    stat = os.stat(path)
    return hashlib.sha256(f"{path}|{stat.st_size}|{stat.st_mtime_ns}".encode()).hexdigest()[:16]


def _cache_get(key: str) -> dict | None:
    try:
        return json.loads(CACHE_PATH.read_text()).get(key)
    except (OSError, ValueError):
        return None


def _cache_put(key: str, value: dict) -> None:
    try:
        data = json.loads(CACHE_PATH.read_text()) if CACHE_PATH.exists() else {}
    except (OSError, ValueError):
        data = {}
    data[key] = value
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(data, indent=1, sort_keys=True))


# --------------------------------------------------------------------------
# measurements of whole files (cached by path, size and mtime)


def measure_drums(path: str, *, prior_bpm: float | None = None) -> dict[str, Any]:
    """Beat map, snare parity, drift and loudness of a drummed recording."""
    import librosa

    key = f"drums|v5|{_fingerprint(path)}|{prior_bpm or 0:.2f}"
    cached = _cache_get(key)
    if cached:
        return cached
    y = load_mono(path)
    duration = len(y) / ANALYSIS_SR
    envelope = librosa.onset.onset_strength(y=y, sr=ANALYSIS_SR, hop_length=HOP)
    bpm = estimate_tempo(y, prior_bpm=prior_bpm)
    beat_map, info = build_beat_map(envelope, frame_seconds=HOP / ANALYSIS_SR, bpm=bpm, duration=duration)
    parity, confidence = snare_parity(y, beat_map.beats)
    beat_map.snare_parity = parity
    result = {**beat_map.to_dict(), "bpm": info["mean_bpm"], "drift_ms": info["drift_ms"],
              "snare_confidence": confidence, "loudness_db": gated_loudness_db(y),
              "duration_seconds": round(duration, 2)}
    _cache_put(key, result)
    return result


def measure_bed(path: str, *, bpm: float | None = None, cue_seconds: float = 0.0) -> dict[str, Any]:
    return measure_drums(path, prior_bpm=bpm)


def measure_vocal(path: str, *, sibling: dict | None, sibling_bpm: float | None) -> dict[str, Any]:
    """Vocal span and loudness; beat map and snare through its full mix."""
    key = f"vocal|v5|{_fingerprint(path)}|{(sibling or {}).get('track_id', '')}|{sibling_bpm or 0:.3f}"
    cached = _cache_get(key)
    if cached:
        return cached
    y = load_mono(path)
    rms_db = rms_db_frames(y)
    duration = len(y) / ANALYSIS_SR
    result: dict[str, Any] = {**vocal_span(rms_db), "rms_db_50ms": rms_db, "loudness_db": gated_loudness_db(y),
                              "duration_seconds": round(duration, 2), "backbeat": "unverified",
                              "real_bpm": None, "beats": None, "snare_parity": None}
    if sibling:
        full = load_mono(sibling["track_id"])
        aligned = align_to_sibling(y, full)
        result["sibling"] = {"track_id": sibling["track_id"], "title": sibling["title"], **aligned}
        if aligned["usable"]:
            drums = measure_drums(sibling["track_id"], prior_bpm=sibling_bpm)
            mapped = BeatMap.from_dict(drums).shifted(aligned["offset_seconds"], duration)
            result.update(mapped.to_dict(), real_bpm=drums["bpm"], drift_ms=drums["drift_ms"],
                          snare_confidence=drums["snare_confidence"],
                          backbeat="measured_via_full_mix" if mapped.snare_parity is not None else "unverified")
    _cache_put(key, result)
    return result


# --------------------------------------------------------------------------
# the plan


def plan_layer(
    vocal_id: str,
    bed_id: str,
    *,
    vocal_bpm: float | None = None,
    bed_bpm: float | None = None,
    bed_cue_seconds: float = 0.0,
    vocal_from_seconds: float = 0.0,
    vocal_to_seconds: float | None = None,
    lead_bars: int = DEFAULT_LEAD_BARS,
    count_shift_beats: int = 0,
    index_path: Path | None = None,
    mixxx_db: Path | None = None,
    measure=None,
) -> dict[str, Any]:
    """A two-deck layer plan: bed alone for `lead_bars`, then the vocal for its
    whole length over it, then a gentle bed fade. No rendering.

    Both sides carry beat maps, so hands.stem_layer can ride the instrumental's
    tempo beat by beat under a vocal that plays at its own speed. `measure`
    ((kind, path, **kw) -> dict) is injectable for tests.
    """
    from brain.stem_crate import _mixxx_analysis

    if count_shift_beats % 2:
        raise LayerPlanError("a count shift must be a whole snare cycle (2 beats): "
                             "1 beat would put the snare on 1 and 3")
    vocal_row, bed_row = library_row(vocal_id, index_path), library_row(bed_id, index_path)
    vocal_kind = classify_track(vocal_row["title"], vocal_id, vocal_row.get("dj_notes") or "")
    bed_kind = classify_track(bed_row["title"], bed_id, bed_row.get("dj_notes") or "")
    if vocal_kind["kind"] != "vocals_only":
        raise LayerPlanError(f"{vocal_row['title']} is not marked vocals-only (it is {vocal_kind['kind']}); "
                             "mark it by hand if the name hides it")
    if bed_kind["kind"] == "vocals_only":
        raise LayerPlanError("the bed must have a beat: choose an instrumental (or a full mix)")
    siblings = find_siblings(vocal_row, index_path)
    analysis = _mixxx_analysis([vocal_id, bed_id, *[s["track_id"] for s in siblings]], mixxx_db)
    sibling = next((s for s in siblings if (analysis.get(s["track_id"]) or {}).get("bpm")), None) or (
        siblings[0] if siblings else None)
    sibling_prior = ((analysis.get(sibling["track_id"]) or {}).get("bpm") or sibling.get("bpm")) if sibling else None
    measure = measure or _measure
    vocal = dict(measure("vocal", vocal_id, sibling=sibling, sibling_bpm=sibling_prior))
    vocal.update(vocal_span(vocal["rms_db_50ms"], start_seconds=vocal_from_seconds, end_seconds=vocal_to_seconds))
    bed_prior = bed_bpm or (analysis.get(bed_id) or {}).get("bpm") or bed_row.get("bpm")
    if vocal.get("real_bpm") and bed_prior:
        bed_prior = fold_tempo(float(bed_prior), float(vocal["real_bpm"]))
    bed = measure("bed", bed_id, bpm=bed_prior, cue_seconds=bed_cue_seconds)
    bed_map = BeatMap.from_dict(bed)
    if bed_map.snare_parity is None:
        raise LayerPlanError("could not tell the instrumental's snare from its kick; choose a bed with a clear backbeat")
    if vocal.get("beats"):
        vocal_map = BeatMap.from_dict(vocal)
        backbeat = "measured" if vocal_map.snare_parity is not None else "unverified"
    else:
        tempo = vocal_bpm or (analysis.get(vocal_id) or {}).get("bpm") or vocal_row.get("bpm")
        if not tempo:
            raise LayerPlanError("the vocal's tempo is unknown: no full mix of the same song lines up with it "
                                 "and there is no BPM for the acapella; pass --vocal-bpm")
        tempo = fold_tempo(float(tempo), float(bed["bpm"]))
        period = 60.0 / tempo
        start = vocal["first_seconds"] % period
        vocal_map = BeatMap(np.arange(start, float(vocal["duration_seconds"]), period), None)
        backbeat = "unverified"
    if vocal_map.snare_parity is None and backbeat == "unverified":
        anchor_index = max(0, round(vocal_map.index_at(vocal["first_seconds"]))) + count_shift_beats
    else:
        anchor_index = choose_vocal_anchor(vocal_map, vocal["first_seconds"], count_shift_beats)
    entry_index = choose_bed_entry(bed_map, bed_cue_seconds, lead_bars)
    vocal_period = vocal_map.period_at(anchor_index)
    bed_period = bed_map.period_at(entry_index)
    rate = bed_period / vocal_period             # bed source seconds per real second
    vocal_bpm_here, bed_bpm_here = 60.0 / vocal_period, 60.0 / bed_period
    if not 0.92 <= rate <= 1.08:
        raise LayerPlanError(f"tempos too far apart for a clean layer: vocal {vocal_bpm_here:.1f} vs "
                             f"instrumental {bed_bpm_here:.1f} BPM ({(rate - 1) * 100:+.1f}%); pick a closer bed")
    anchor = vocal_map.time_at(anchor_index)
    cue = max(0.0, vocal_from_seconds, vocal_map.time_at(anchor_index - PREROLL_BEATS))
    if cue > vocal["first_seconds"]:
        cue = max(0.0, vocal["first_seconds"] - 0.05)
    end_index = vocal_map.index_at(vocal["last_seconds"]) + 4          # one bar after the last word
    bed_last_needed = entry_index + (end_index - anchor_index) + 16
    bed_duration = float(bed.get("duration_seconds") or bed_row.get("duration_seconds") or 0)
    warnings = []
    if bed_last_needed > len(bed_map.beats) - 1:
        warnings.append(f"the instrumental runs out {bed_last_needed - len(bed_map.beats) + 1:.0f} beats before "
                        "the vocal does; the layer fades with the instrumental's last 16 beats")
    if float(bed.get("drift_ms") or 0) > 60:
        warnings.append(f"the instrumental's tempo drifts about {bed['drift_ms']:.0f} ms over the song (live or "
                        "tape-era drums); its deck rides the pitch to keep the snares on the vocal's")
    if backbeat == "unverified":
        warnings.append("no full mix of this song lines up with the acapella: the vocal's snare is not measured, "
                        "so the backbeat is unverified (the instrumental's is); listen for the count")
    levels = _levels(vocal, bed, bed_kind["kind"], analysis.get(vocal_id), analysis.get(bed_id))
    return {
        "version": 2,
        "kind": "vocal_over_instrumental",
        "vocal": {
            "track_id": vocal_id, "label": f"{vocal_row['artist']} — {vocal_row['title']}",
            "bpm": round(vocal_bpm_here, 4), "tempo_source": "full_mix" if vocal.get("beats") else "mixxx_or_tags",
            "from_seconds": vocal_from_seconds, "to_seconds": vocal_to_seconds,
            "cue_seconds": round(cue, 4), "anchor_index": int(anchor_index), "anchor_seconds": round(anchor, 4),
            "first_word_seconds": vocal["first_seconds"], "last_word_seconds": vocal["last_seconds"],
            "end_index": round(end_index, 3), "beat_map": vocal_map.to_dict(), "sibling": vocal.get("sibling"),
            "drift_ms": vocal.get("drift_ms"),
        },
        "bed": {
            "track_id": bed_id, "label": f"{bed_row['artist']} — {bed_row['title']}", "kind": bed_kind["kind"],
            "bpm": round(bed_bpm_here, 4), "mean_bpm": bed.get("bpm"),
            "mixxx_bpm": (analysis.get(bed_id) or {}).get("bpm"),
            "cue_seconds": bed_cue_seconds, "entry_index": int(entry_index),
            "entry_seconds": round(bed_map.time_at(entry_index), 4),
            "snare_confidence": bed.get("snare_confidence"), "drift_ms": bed.get("drift_ms"),
            "duration_seconds": bed_duration or None, "beat_map": bed_map.to_dict(),
        },
        "tempo": {"bed_rate": round(rate, 5),
                  "note": "the vocal plays at its own speed; the instrumental's deck follows it beat by beat (keylock on)"},
        "alignment": {"backbeat": backbeat, "count1": "guessed", "count_shift_beats": count_shift_beats,
                      "alternatives": [count_shift_beats - 2, count_shift_beats + 2],
                      "tolerance_ms": TOLERANCE_MS, "lead_bars": lead_bars},
        "levels": levels,
        "layer_seconds": round(vocal["last_seconds"] - anchor, 2),
        "fade_beats": 16,
        "warnings": warnings,
    }


def _levels(vocal: dict, bed: dict, bed_kind: str, vocal_mixxx: dict | None, bed_mixxx: dict | None) -> dict:
    replaygain = bool((vocal_mixxx or {}).get("replaygain") and (bed_mixxx or {}).get("replaygain"))
    bed_pregain = BED_PREGAIN
    vocal_pregain = 1.0
    if not replaygain:
        # No ReplayGain on both: equalize from our own gated loudness, by
        # turning the louder one down (never boosting into clipping).
        diff = float(vocal["loudness_db"]) - float(bed["loudness_db"])
        if diff > 0:
            vocal_pregain = round(10 ** (-diff / 20), 3)
        else:
            bed_pregain = round(BED_PREGAIN * 10 ** (diff / 20), 3)
        vocal_pregain = max(0.25, vocal_pregain)
        bed_pregain = max(0.25, bed_pregain)
    full = bed_kind == "full_mix"
    return {
        "method": "mixxx_replaygain" if replaygain else "measured_gated_loudness",
        "vocal_pregain": vocal_pregain, "bed_pregain": bed_pregain,
        "bed_eq": {"low": 1.0, "mid": BED_MID_FULL_MIX if full else BED_MID_INSTRUMENTAL,
                   "high": BED_HIGH_FULL_MIX if full else 1.0},
        "note": "bed a little under the vocal; a full-mix bed also dips its mids and highs so its own singer steps back",
    }


def _measure(kind: str, path: str, **kwargs) -> dict:
    if kind == "vocal":
        return measure_vocal(path, **kwargs)
    return measure_bed(path, **kwargs)


def describe(plan: dict) -> list[str]:
    v, b, a, t, lv = plan["vocal"], plan["bed"], plan["alignment"], plan["tempo"], plan["levels"]
    lines = [
        f"vocal:        {v['label']}  ({v['bpm']} BPM, timing from {v['tempo_source']})",
        f"instrumental: {b['label']}  ({b['bpm']} BPM here; deck starts at x{t['bed_rate']} and follows the vocal)",
        f"backbeat:     {a['backbeat']}; count 1 {a['count1']} (A/B: count shift {a['alternatives'][0]} or {a['alternatives'][1]})",
        f"instrumental alone for {a['lead_bars']} bars, then the vocal's {v['anchor_seconds']:.2f}s lands on the "
        f"instrumental's {b['entry_seconds']:.2f}s (both kick beats); the vocal deck starts at {v['cue_seconds']:.2f}s",
        f"layer {plan['layer_seconds']:.0f}s (to the last word at {v['last_word_seconds']:.1f}s), then a "
        f"{plan['fade_beats']}-beat fade of the instrumental",
        f"levels ({lv['method']}): vocal gain {lv['vocal_pregain']}, instrumental gain {lv['bed_pregain']}, "
        f"instrumental EQ mid {lv['bed_eq']['mid']} high {lv['bed_eq']['high']}",
    ]
    if v.get("sibling"):
        s = v["sibling"]
        lines.append(f"timing source: {s['title']} (offset {s['offset_seconds']:+.3f}s, confidence {s['confidence']}, "
                     f"halves agree within {s['half_disagreement_ms']} ms, {'used' if s['usable'] else 'NOT used'})")
    lines += [f"warning: {w}" for w in plan["warnings"]]
    return lines
