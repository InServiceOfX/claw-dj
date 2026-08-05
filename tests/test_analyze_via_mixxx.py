import unittest
from unittest.mock import patch

from brain.analyze_via_mixxx import analyze_tracks


class FakeMixxx:
    last_instance: "FakeMixxx | None" = None

    def __init__(self, *args, **kwargs) -> None:
        self.loads = []
        type(self).last_instance = self

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        return None

    def set(self, *_args) -> None:
        return None

    def get(self, _group, key):
        return 1.0 if key == "key" else 0.0

    def load(self, deck, track_id) -> None:
        self.loads.append((deck, track_id))


class AnalyzeViaMixxxTests(unittest.TestCase):
    @patch("brain.analyze_via_mixxx.pending_grid_ids", side_effect=[[], []])
    @patch("brain.analyze_via_mixxx._flush_track_id", return_value="/music/flush.mp3")
    @patch("brain.analyze_via_mixxx.wait_for_bpm", return_value=93.0)
    @patch("brain.analyze_via_mixxx.time.sleep")
    @patch("brain.analyze_via_mixxx.MixxxControl", FakeMixxx)
    def test_single_target_loads_different_track_to_persist_final_grid(
        self, _sleep, _wait, _flush, _pending
    ) -> None:
        rows = analyze_tracks(
            [{"track_id": "/music/target.mp3", "artist": "A", "title": "T"}],
            deck=4,
            timeout_s=0,
        )

        self.assertTrue(rows[0]["ok"])
        instance = FakeMixxx.last_instance
        self.assertIsNotNone(instance)
        assert instance is not None
        self.assertEqual(
            instance.loads,
            [(4, "/music/target.mp3"), (4, "/music/flush.mp3")],
        )


if __name__ == "__main__":
    unittest.main()