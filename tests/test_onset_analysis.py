"""Regression tests for brain.onset_analysis against synthetic drum patterns.

No real MP3 fixtures are bundled -- these build a fake click-track signal
with a known kick-on-1&3 / snare-on-2&4 pattern in-memory and verify the
detector recovers the correct snare parity, so the module is validated
without depending on any specific song being present in a music library.
"""
from unittest import TestCase

import numpy as np

from brain.onset_analysis import (
    beat_phase_energies,
    count_shift_beats,
    detect_snare_phase,
    phase_shift_beats,
    snare_band_onset_envelope,
)

SR = 22050


def _tone_burst(duration_s: float, freq_hz: float, sr: int) -> np.ndarray:
    n = int(round(duration_s * sr))
    t = np.arange(n) / sr
    envelope = np.exp(-t * 40.0)  # fast decay, percussive
    return (np.sin(2 * np.pi * freq_hz * t) * envelope).astype(np.float32)


def _noise_burst(duration_s: float, sr: int, *, seed: int) -> np.ndarray:
    n = int(round(duration_s * sr))
    t = np.arange(n) / sr
    envelope = np.exp(-t * 25.0)
    rng = np.random.default_rng(seed)
    return (rng.standard_normal(n).astype(np.float32) * envelope)


def build_click_track(*, bpm: float, first_beat_seconds: float, bars: int, sr: int = SR) -> np.ndarray:
    """A synthetic 4/4 pattern: low kick thump on beats 0 & 2, broadband
    snare-like noise burst on beats 1 & 3 (0-indexed, i.e. musical 1 & 3
    for the kick, 2 & 4 for the snare)."""
    period = 60.0 / bpm
    total_beats = bars * 4
    total_seconds = first_beat_seconds + total_beats * period + 1.0
    y = np.zeros(int(round(total_seconds * sr)), dtype=np.float32)
    for beat in range(total_beats):
        start_s = first_beat_seconds + beat * period
        start_i = int(round(start_s * sr))
        if beat % 4 in (0, 2):
            hit = _tone_burst(0.15, 90.0, sr)  # kick: low frequency thump
        else:
            hit = _noise_burst(0.15, sr, seed=beat)  # snare: broadband noise
        end_i = min(len(y), start_i + len(hit))
        y[start_i:end_i] += hit[: end_i - start_i]
    return y


class SnarePhaseDetectionTests(TestCase):
    def test_detects_snare_on_the_backbeat_slots(self) -> None:
        bpm = 94.0
        first_beat = 0.2
        y = build_click_track(bpm=bpm, first_beat_seconds=first_beat, bars=20)
        envelope, hop_length = snare_band_onset_envelope(y, SR)
        energies = beat_phase_energies(
            envelope, sr=SR, hop_length=hop_length, bpm=bpm, first_beat_seconds=first_beat
        )
        # Slots 1 and 3 (0-indexed) carry the noise-burst "snare" and must
        # clearly outscore slots 0 and 2 (the low-frequency "kick").
        self.assertGreater(energies[1], energies[0])
        self.assertGreater(energies[1], energies[2])
        self.assertGreater(energies[3], energies[0])
        self.assertGreater(energies[3], energies[2])

    def test_detect_snare_phase_end_to_end_on_a_synthetic_file(self) -> None:
        import soundfile as sf
        import tempfile
        import os

        bpm = 100.0
        first_beat = 0.3
        y = build_click_track(bpm=bpm, first_beat_seconds=first_beat, bars=16, sr=SR)
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            sf.write(path, y, SR)
            result = detect_snare_phase(path, bpm=bpm, first_beat_seconds=first_beat, sr=SR)
        finally:
            os.remove(path)
        # Snare is on beats 1 & 3 (0-indexed) -> odd parity.
        self.assertEqual(result["snare_parity"], 1)
        self.assertGreater(result["confidence"], 0.0)

    def test_kick_on_backbeat_flips_parity_to_even(self) -> None:
        """Swap which beats carry the noise burst -- the detector must
        follow the actual audio, not default to "odd" as a hardcoded guess."""
        import soundfile as sf
        import tempfile
        import os

        bpm = 100.0
        first_beat = 0.3
        period = 60.0 / bpm
        total_beats = 16 * 4
        total_seconds = first_beat + total_beats * period + 1.0
        y = np.zeros(int(round(total_seconds * SR)), dtype=np.float32)
        for beat in range(total_beats):
            start_i = int(round((first_beat + beat * period) * SR))
            # Inverted from build_click_track: snare on 0 & 2 this time.
            hit = _noise_burst(0.15, SR, seed=beat) if beat % 4 in (0, 2) else _tone_burst(0.15, 90.0, SR)
            end_i = min(len(y), start_i + len(hit))
            y[start_i:end_i] += hit[: end_i - start_i]

        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            sf.write(path, y, SR)
            result = detect_snare_phase(path, bpm=bpm, first_beat_seconds=first_beat, sr=SR)
        finally:
            os.remove(path)
        self.assertEqual(result["snare_parity"], 0)
        self.assertGreater(result["confidence"], 0.0)


class PhaseShiftBeatsTests(TestCase):
    def test_zero_shift_when_already_aligned(self) -> None:
        # Outgoing anchor at beat 8 (even), snare parity 1 (odd) -> target parity (8+1)%2=1.
        # Incoming cue at beat 5 (odd), snare parity 0 -> current parity (5+0)%2=1. Matches.
        shift = phase_shift_beats(
            outgoing_snare_parity=1,
            outgoing_anchor_beat_index=8,
            incoming_snare_parity=0,
            incoming_cue_beat_index=5,
        )
        self.assertEqual(shift, 0)

    def test_nonzero_shift_when_misaligned(self) -> None:
        # Target parity = (8 + 1) % 2 = 1. Incoming cue at beat 4 (even), snare parity 0 -> current parity 0.
        shift = phase_shift_beats(
            outgoing_snare_parity=1,
            outgoing_anchor_beat_index=8,
            incoming_snare_parity=0,
            incoming_cue_beat_index=4,
        )
        self.assertEqual(shift, 1)

    def test_matching_snare_parities_at_matching_cue_parity_needs_no_shift(self) -> None:
        # Both tracks have snare on odd beats, both anchor/cue on even beat
        # indices -- already aligned (this is the Run It!/Keni Burke case
        # found live: both land on the same, non-snare parity).
        shift = phase_shift_beats(
            outgoing_snare_parity=1,
            outgoing_anchor_beat_index=118,
            incoming_snare_parity=1,
            incoming_cue_beat_index=160,
        )
        self.assertEqual(shift, 0)


class CountShiftBeatsTests(TestCase):
    def test_bar_offset_with_matching_parity_shifts_two(self) -> None:
        # Snare parity already matches, but the incoming enters on "the 3"
        # relative to the outgoing's count (anchor 10 vs cue 12: 2 apart mod
        # 4) -- live feedback 2026-07-19: parity-only alignment still left
        # the counts sounding off. A +2 shift fixes the bar and preserves
        # parity.
        shift = count_shift_beats(
            outgoing_snare_parity=1,
            outgoing_anchor_beat_index=10,
            incoming_snare_parity=1,
            incoming_cue_beat_index=12,
        )
        self.assertEqual(shift, 2)

    def test_fully_aligned_needs_nothing(self) -> None:
        shift = count_shift_beats(
            outgoing_snare_parity=1,
            outgoing_anchor_beat_index=8,
            incoming_snare_parity=1,
            incoming_cue_beat_index=16,
        )
        self.assertEqual(shift, 0)

    def test_bar_shift_three_maps_to_minus_one(self) -> None:
        # cue 11 vs anchor 8: 3 apart mod 4 -> -1 is the smaller move, and
        # (-1 % 2 == 1) matches the required parity flip.
        shift = count_shift_beats(
            outgoing_snare_parity=0,
            outgoing_anchor_beat_index=8,
            incoming_snare_parity=0,
            incoming_cue_beat_index=11,
        )
        self.assertEqual(shift, -1)

    def test_measured_parity_wins_over_bar_assumption(self) -> None:
        # Bar arithmetic says "already aligned" (cue ≡ anchor mod 4), but
        # the MEASURED snare parities disagree (one track's grid anchor is
        # off by an odd count). Trust the measurement: shift by 1.
        shift = count_shift_beats(
            outgoing_snare_parity=1,
            outgoing_anchor_beat_index=8,
            incoming_snare_parity=0,
            incoming_cue_beat_index=8,
        )
        self.assertEqual(shift, 1)
