from unittest import TestCase

from brain.library import Track
from brain.mix_graph import (
    bpm_compatibility,
    greedy_mix_order,
    key_compatibility,
    pair_score,
    parse_key,
)


class MixGraphTest(TestCase):
    def test_parse_key_musical_and_camelot(self) -> None:
        self.assertEqual(parse_key("Am"), (8, "A"))
        self.assertEqual(parse_key("C"), (8, "B"))
        self.assertEqual(parse_key("8A"), (8, "A"))

    def test_bpm_near_and_double_time(self) -> None:
        score, _ = bpm_compatibility(92.0, 94.0)
        self.assertGreaterEqual(score, 0.9)
        score_half, reason = bpm_compatibility(90.0, 180.0)
        self.assertGreaterEqual(score_half, 0.9)
        self.assertIn("bpm", reason or "")

    def test_key_relative_major_minor(self) -> None:
        score, reason = key_compatibility("Am", "C")
        self.assertGreaterEqual(score, 0.9)
        self.assertIn("relative", reason or "")

    def test_greedy_prefers_compatible_neighbor(self) -> None:
        tracks = [
            Track("/a.mp3", "A", "Artist", bpm=90.0, key="Am"),
            Track("/b.mp3", "B", "Artist", bpm=140.0, key="F#"),
            Track("/c.mp3", "C", "Artist", bpm=92.0, key="C"),
        ]
        order = greedy_mix_order(tracks, start=tracks[0])
        self.assertEqual(order[0].title, "A")
        # C is the natural second hop from A (close BPM + relative key)
        self.assertEqual(order[1].title, "C")
        edge = pair_score(order[0], order[1])
        self.assertGreater(edge.score, pair_score(tracks[0], tracks[1]).score)
