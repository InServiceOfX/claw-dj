"""Grid-quality (beatgrid truthfulness) detection on synthetic click tracks.

Ground truth is engineered: a click pattern generated exactly on the claimed
grid must read as rigid; the same pattern generated at a tempo 1% off the
claimed grid (a constant grid fitted to a drifting live drummer) must not.
"""
import os
import tempfile
import unittest

import soundfile as sf

from brain.grid_quality import measure_grid_quality
from tests.test_onset_analysis import SR, build_click_track


def _write_wav(y) -> str:
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    sf.write(path, y, SR)
    return path


class GridQualityTests(unittest.TestCase):
    def test_exact_grid_reads_rigid(self) -> None:
        y = build_click_track(bpm=100.0, first_beat_seconds=0.3, bars=40, sr=SR)
        path = _write_wav(y)
        try:
            result = measure_grid_quality(path, bpm=100.0, first_beat_seconds=0.3, sr=SR)
        finally:
            os.remove(path)
        self.assertEqual(result["verdict"], "rigid")
        self.assertGreaterEqual(result["tight_fraction"], 0.9)
        self.assertGreaterEqual(result["min_window_fraction"], 0.9)

    def test_wrong_tempo_grid_is_not_rigid(self) -> None:
        # The audio's true tempo is 101bpm but the claimed grid says 100 --
        # the same failure mode as a constant Mixxx grid fitted to a live
        # drummer: right on average, wrong almost everywhere in time.
        y = build_click_track(bpm=101.0, first_beat_seconds=0.3, bars=40, sr=SR)
        path = _write_wav(y)
        try:
            result = measure_grid_quality(path, bpm=100.0, first_beat_seconds=0.3, sr=SR)
        finally:
            os.remove(path)
        self.assertNotEqual(result["verdict"], "rigid")
        self.assertLess(result["tight_fraction"], 0.5)

    def test_phase_shifted_grid_is_not_rigid(self) -> None:
        # Correct tempo, but the anchor is off by half a beat -- every onset
        # lands maximally far from the claimed grid lines.
        y = build_click_track(bpm=100.0, first_beat_seconds=0.3, bars=40, sr=SR)
        path = _write_wav(y)
        try:
            result = measure_grid_quality(
                path, bpm=100.0, first_beat_seconds=0.3 + 0.3, sr=SR
            )
        finally:
            os.remove(path)
        self.assertEqual(result["verdict"], "misaligned")


if __name__ == "__main__":
    unittest.main()
