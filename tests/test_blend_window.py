"""Blend-window snare reads (Ernest, 2026-10-13).

Mix to listen blends late in the song. On a few songs the snare had moved to
the other beats by the blend while the song-wide read (first minutes) still
said "matched". Build now measures the drums in the actual blend window and
aligns on that read when it is sure.
"""
import tempfile
import unittest
from unittest import mock

from brain.build_mix_plan import BlendWindowReader, build_plan
from brain.onset_analysis import (
    BLEND_WINDOW_GATE,
    blend_window_start_beat,
    prefer_blend_window,
)

SONG = {"snare_parity": 1, "confidence": 0.5, "bpm": 100.0, "first_beat_seconds": 0.0}


def _tracks():
    return [
        {
            "track_id": "/music/a.mp3", "artist": "A", "title": "Outgoing",
            "bpm": 100.0, "key": "Am", "dj_notes": "cue_seconds=0; ride_beats=10",
        },
        {
            "track_id": "/music/b.mp3", "artist": "B", "title": "Incoming",
            "bpm": 100.0, "key": "Am", "dj_notes": "cue_seconds=6.0",
        },
    ]


def _build(window_phase=None):
    plan = build_plan(
        _tracks(), count=2, seconds_per_track=20.0, affinity_lookup={},
        beat_phase_lookup={"/music/a.mp3": dict(SONG), "/music/b.mp3": dict(SONG)},
        window_phase=window_phase,
    )
    return next(event for event in plan["events"] if event["op"] == "play_body")


class PreferBlendWindowTest(unittest.TestCase):
    def test_sure_window_read_wins(self) -> None:
        phase, used = prefer_blend_window(SONG, {"snare_parity": 0, "confidence": 0.41})
        self.assertTrue(used)
        self.assertEqual(phase["snare_parity"], 0)
        self.assertEqual(phase["bpm"], 100.0)

    def test_unsure_window_read_keeps_song_read(self) -> None:
        phase, used = prefer_blend_window(
            SONG, {"snare_parity": 0, "confidence": BLEND_WINDOW_GATE - 0.01}
        )
        self.assertFalse(used)
        self.assertIs(phase, SONG)

    def test_missing_window_read_keeps_song_read(self) -> None:
        self.assertEqual(prefer_blend_window(SONG, None), (SONG, False))

    def test_window_start_rounds_down_to_eight_beats(self) -> None:
        self.assertEqual(blend_window_start_beat(421), 416)
        self.assertEqual(blend_window_start_beat(-5), 0)


class BuildUsesBlendWindowTest(unittest.TestCase):
    def test_without_reader_the_song_read_aligns(self) -> None:
        body = _build()
        self.assertEqual(body["beats"], 9)
        self.assertNotIn("blend_window", body["backbeat"])

    def test_flipped_outgoing_window_changes_the_alignment(self) -> None:
        calls = []

        def reader(track_id, grid, beat_index):
            calls.append((track_id, beat_index))
            if track_id == "/music/a.mp3":
                return {"snare_parity": 0, "confidence": 0.41}
            return {"snare_parity": 1, "confidence": 0.6}

        body = _build(reader)
        backbeat = body["backbeat"]
        # the two parities disagree, so +1 and -1 both match the snares and
        # the bar count is a guess (bar_count_guessed, 2026-10-21)
        self.assertEqual(backbeat["status"], "bar_guessed")
        self.assertIn("blend-window read", backbeat["reason"])
        self.assertTrue(backbeat["blend_window"]["out"]["flipped"])
        self.assertFalse(backbeat["blend_window"]["in"]["flipped"])
        self.assertNotEqual(body["beats"], 9)
        # outgoing measured from 16 beats before the anchor (beat 11), incoming at its cue
        self.assertIn(("/music/a.mp3", 11 - 16), calls)
        self.assertIn(("/music/b.mp3", 10), calls)

    def test_unsure_window_reads_change_nothing(self) -> None:
        body = _build(lambda *_: {"snare_parity": 0, "confidence": 0.2})
        self.assertEqual(body["beats"], 9)
        self.assertFalse(body["backbeat"]["blend_window"]["out"]["used"])
        self.assertNotIn("blend-window", body["backbeat"]["reason"])


class WeakSongReadUpgradeTest(unittest.TestCase):
    def test_sure_windows_upgrade_a_bar_count_only_blend(self) -> None:
        weak = {**SONG, "confidence": 0.04}
        plan = build_plan(
            _tracks(), count=2, seconds_per_track=20.0, affinity_lookup={},
            beat_phase_lookup={"/music/a.mp3": weak, "/music/b.mp3": dict(SONG)},
            window_phase=lambda *_: {"snare_parity": 1, "confidence": 0.3},
        )
        backbeat = next(e for e in plan["events"] if e["op"] == "play_body")["backbeat"]
        self.assertEqual(backbeat["status"], "matched")
        self.assertTrue(backbeat["blend_window"]["out"]["upgraded"])
        self.assertIn("blend-window read", backbeat["reason"])


class BlendWindowReaderTest(unittest.TestCase):
    def test_collect_only_records_windows_for_files_on_disk(self) -> None:
        reader = BlendWindowReader(collect_only=True)
        with tempfile.NamedTemporaryFile(suffix=".mp3") as song, \
                mock.patch.object(BlendWindowReader, "_load"):
            self.assertIsNone(reader(song.name, SONG, 421))
            self.assertIsNone(reader("/not/on/disk.mp3", SONG, 421))
        self.assertEqual(list(reader.pending), [(song.name, 416, reader.beats)])

    def test_cached_read_is_reused_only_on_the_same_grid(self) -> None:
        reader = BlendWindowReader(collect_only=True)
        with tempfile.NamedTemporaryFile(suffix=".mp3") as song, \
                mock.patch.object(BlendWindowReader, "_load"):
            reader.cache[(song.name, 416, reader.beats)] = {
                "bpm": 100.0, "first_beat_seconds": 0.0, "snare_parity": 0, "confidence": 0.4,
            }
            self.assertEqual(reader(song.name, SONG, 421), {"snare_parity": 0, "confidence": 0.4})
            moved = {**SONG, "first_beat_seconds": 0.3}
            self.assertIsNone(reader(song.name, moved, 421))
        self.assertEqual(len(reader.pending), 1)


if __name__ == "__main__":
    unittest.main()
