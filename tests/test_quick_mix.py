import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from brain.quick_mix import (
    cue_position,
    parse_agent_order,
    resolve_demo_tracks,
    transition_settings,
)


class QuickMixTest(TestCase):
    def test_resolve_demo_tracks_keeps_private_path_out_of_seed(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            seed = root / "seed.json"
            tracks = root / "tracks.json"
            seed.write_text(
                json.dumps(
                    [
                        {
                            "id": "one",
                            "artist": "Artist",
                            "title": "Song",
                            "cue_seconds": 3.0,
                            "sample_artist": "Source",
                            "sample_title": "Source Song",
                            "sample_element": "loop",
                            "hook_phrase": "short hook",
                            "research_url": "https://example.com",
                        }
                    ]
                )
            )
            tracks.write_text(
                json.dumps(
                    [
                        {
                            "artist": "Artist feat. Guest",
                            "title": "Song (Album Version)",
                            "track_id": "/private/music/song.mp3",
                            "bpm": 94.0,
                        }
                    ]
                )
            )
            resolved = resolve_demo_tracks(seed, tracks)
        self.assertEqual(resolved[0].track_id, "/private/music/song.mp3")
        self.assertEqual(resolved[0].bpm_hint, 94.0)

    def test_parse_agent_order_accepts_explanation_around_array(self) -> None:
        answer = 'Order: ["b", "a"]\nI put the related pair together.'
        self.assertEqual(parse_agent_order(answer, ["a", "b"]), ["b", "a"])

    def test_parse_agent_order_rejects_missing_track(self) -> None:
        with self.assertRaises(ValueError):
            parse_agent_order('["a"]', ["a", "b"])

    def test_cue_position_is_normalized_and_clamped(self) -> None:
        self.assertEqual(cue_position(25, 100), 0.25)
        self.assertEqual(cue_position(-3, 100), 0.0)
        self.assertEqual(cue_position(200, 100), 0.99)

    def test_large_tempo_gap_uses_cut_without_sync(self) -> None:
        self.assertEqual(transition_settings(86, 96, 4), (1, False))
        self.assertEqual(transition_settings(94, 96, 4), (4, True))
