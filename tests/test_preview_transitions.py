"""Sequencing logic for the transition preview renderer (no ffmpeg needed)."""
import unittest

from brain.preview_transitions import transition_specs


def _plan_events() -> list[dict]:
    return [
        {"op": "load", "deck": 1, "track_id": "/m/a.mp3", "artist": "A",
         "title": "One", "cue_seconds": 10.0},
        {"op": "load", "deck": 2, "track_id": "/m/b.mp3", "artist": "B",
         "title": "Two", "cue_seconds": 20.0},
        {"op": "start", "deck": 1},
        {"op": "play_body", "deck": 1, "beats": 60, "track": "A — One"},
        {"op": "transition", "from_deck": 1, "to_deck": 2,
         "from_track": "A — One", "to_track": "B — Two",
         "technique": "standard_blend", "transition_beats": 20,
         "moves": ["sync", "crossfade"]},
    ]


class TransitionSpecTests(unittest.TestCase):
    def test_anchor_and_fade_math(self) -> None:
        tracks = {
            "/m/a.mp3": {"track_id": "/m/a.mp3", "bpm": 120.0, "dj_notes": ""},
            "/m/b.mp3": {"track_id": "/m/b.mp3", "bpm": 100.0, "dj_notes": ""},
        }
        (spec,) = transition_specs(_plan_events(), tracks)
        # Anchor: cue 10.0 + 60 beats at 120bpm (0.5s/beat) = 40.0s.
        # Outgoing plays at native rate, so the segment ends fade past 40.
        self.assertAlmostEqual(spec["out_start_s"], 40.0 - 12.0, places=3)
        # Fade: 20 beats at the outgoing's played 120bpm = 10s.
        self.assertAlmostEqual(spec["fade_wall_s"], 10.0, places=3)
        # Incoming has sync in moves and no bpm target: rendered at the
        # outgoing's live 120bpm over its own native 100 -> rate 1.2.
        self.assertAlmostEqual(spec["in_rate"], 1.2, places=3)
        self.assertAlmostEqual(spec["in_start_s"], 20.0, places=3)
        self.assertFalse(spec["hard_cut"])

    def test_incoming_bpm_target_overrides_sync_rate(self) -> None:
        events = _plan_events()
        events[-1]["incoming_bpm_target"] = 90.0
        tracks = {
            "/m/a.mp3": {"track_id": "/m/a.mp3", "bpm": 120.0, "dj_notes": ""},
            "/m/b.mp3": {"track_id": "/m/b.mp3", "bpm": 100.0, "dj_notes": ""},
        }
        (spec,) = transition_specs(events, tracks)
        self.assertAlmostEqual(spec["in_rate"], 0.9, places=3)

    def test_outgoing_play_bpm_hold_shifts_anchor_window_and_fade(self) -> None:
        tracks = {
            # play_bpm=132 on a 120bpm track: rate 1.1
            "/m/a.mp3": {"track_id": "/m/a.mp3", "bpm": 120.0,
                         "dj_notes": "play_bpm=132"},
            "/m/b.mp3": {"track_id": "/m/b.mp3", "bpm": 100.0, "dj_notes": ""},
        }
        (spec,) = transition_specs(_plan_events(), tracks)
        # File-position math still uses the native grid (beats consume file
        # time by the track's own bpm), but the 12s of wall-clock context
        # covers 12*1.1 file seconds, and the fade wall time shrinks.
        self.assertAlmostEqual(spec["out_rate"], 1.1, places=3)
        self.assertAlmostEqual(spec["out_start_s"], 40.0 - 12.0 * 1.1, places=3)
        self.assertAlmostEqual(spec["fade_wall_s"], 20 * 60.0 / 132.0, places=3)

    def test_hard_cut_renders_as_splice_not_fade(self) -> None:
        events = _plan_events()
        events[-1].update(technique="beat_drop_entry", moves=["brake_out", "hard_cut"])
        tracks = {
            "/m/a.mp3": {"track_id": "/m/a.mp3", "bpm": 120.0, "dj_notes": ""},
            "/m/b.mp3": {"track_id": "/m/b.mp3", "bpm": 100.0, "dj_notes": ""},
        }
        (spec,) = transition_specs(events, tracks)
        self.assertTrue(spec["hard_cut"])
        self.assertEqual(spec["fade_wall_s"], 0.0)
        # Hard cut means no sync either: incoming at its own native tempo.
        self.assertAlmostEqual(spec["in_rate"], 1.0, places=3)

    def test_missing_bpm_becomes_error_entry_not_crash(self) -> None:
        tracks = {
            "/m/a.mp3": {"track_id": "/m/a.mp3", "bpm": None, "dj_notes": ""},
            "/m/b.mp3": {"track_id": "/m/b.mp3", "bpm": 100.0, "dj_notes": ""},
        }
        (spec,) = transition_specs(_plan_events(), tracks)
        self.assertIn("error", spec)


if __name__ == "__main__":
    unittest.main()
