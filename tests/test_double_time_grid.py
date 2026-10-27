"""Double-time grids (Ernest, 2026-10-15).

Shanice "I Love Your Smile" is gridded at 187.88 BPM, twice its real tempo.
Her real beats are her odd grid beats. Build started SWV "You're The One"
(94.0) on an even grid beat, an off-beat "and", and still said "matched":
the odd/even snare test on a double-time grid compares on-beats with
off-beats. Build now measures the real beats and aligns on them.
"""
import unittest

from brain.build_mix_plan import build_plan
from brain.onset_analysis import double_time_shifts, double_time_side, trust_real_beats

REAL = {"beat_phase": 1, "snare_parity": 1, "confidence": 0.9, "other_confidence": 0.1}


def _build(out_bpm, in_bpm, real_beat_phase=None, in_notes="cue_seconds=6.0"):
    tracks = [
        {"track_id": "/music/a.mp3", "artist": "A", "title": "Outgoing", "bpm": out_bpm,
         "key": "Am", "dj_notes": "cue_seconds=0; ride_beats=10"},
        {"track_id": "/music/b.mp3", "artist": "B", "title": "Incoming", "bpm": in_bpm,
         "key": "Am", "dj_notes": in_notes},
    ]
    phases = {
        "/music/a.mp3": {"snare_parity": 1, "confidence": 0.5, "bpm": out_bpm, "first_beat_seconds": 0.0},
        "/music/b.mp3": {"snare_parity": 1, "confidence": 0.5, "bpm": in_bpm, "first_beat_seconds": 0.0},
    }
    plan = build_plan(
        tracks, count=2, seconds_per_track=20.0, affinity_lookup={},
        beat_phase_lookup=phases, real_beat_phase=real_beat_phase,
    )
    body = next(e for e in plan["events"] if e["op"] == "play_body")
    load = next(e for e in plan["events"] if e.get("track_id") == "/music/b.mp3" and "cue_seconds" in e)
    return body, load


class DoubleTimeSideTest(unittest.TestCase):
    def test_sides(self) -> None:
        self.assertEqual(double_time_side(187.88, 94.0), "out")
        self.assertEqual(double_time_side(94.0, 187.88), "in")
        self.assertIsNone(double_time_side(94.0, 96.0))
        self.assertIsNone(double_time_side(None, 94.0))


class DoubleTimeShiftsTest(unittest.TestCase):
    def test_shanice_into_swv_starts_on_a_real_beat(self) -> None:
        # Plan anchored on grid beat 600, an off-beat. Real beats are odd
        # grid beats; SWV's beat 0 is not a snare, so the entry must be a
        # real non-snare beat that starts a bar: grid beat 601.
        shift, cue_shift = double_time_shifts(
            side="out", outgoing_anchor_beat_index=600, incoming_cue_beat_index=0,
            outgoing_read=REAL, incoming_read={"snare_parity": 1},
        )
        self.assertEqual((600 + shift, cue_shift), (601, 0))

    def test_incoming_cue_moves_onto_a_real_beat(self) -> None:
        shift, cue_shift = double_time_shifts(
            side="in", outgoing_anchor_beat_index=11, incoming_cue_beat_index=20,
            outgoing_read={"snare_parity": 1}, incoming_read=REAL,
        )
        self.assertEqual(cue_shift, 1)
        self.assertEqual(shift, -1)

    def test_trust_needs_a_clear_winner(self) -> None:
        self.assertTrue(trust_real_beats(REAL))
        self.assertFalse(trust_real_beats({**REAL, "other_confidence": 0.8}))
        self.assertFalse(trust_real_beats({**REAL, "confidence": 0.2, "other_confidence": 0.0}))
        self.assertFalse(trust_real_beats(None))


class BuildAlignsOnRealBeatsTest(unittest.TestCase):
    def test_outgoing_double_time_lands_on_a_real_beat(self) -> None:
        body, _ = _build(200.0, 100.0, lambda *_: REAL)
        backbeat = body["backbeat"]
        self.assertEqual(backbeat["status"], "matched")
        self.assertIn("double-time grid", backbeat["reason"])
        self.assertEqual(backbeat["double_time"]["side"], "out")
        # incoming cue = beat 10 (no snare). Anchor 11 -> 13: an odd grid
        # beat, real beat 6 (no snare, same bar position as beat 10).
        self.assertEqual(body["beats"], 12)
        self.assertEqual(body["phase_anchor"]["planned_anchor_beat_index"], 13)
        self.assertEqual(body["phase_anchor"]["target_beat_mod4"], 1)

    def test_incoming_double_time_cue_moves_one_grid_beat(self) -> None:
        body, load = _build(100.0, 200.0, lambda *_: REAL)
        self.assertEqual(body["backbeat"]["status"], "matched")
        self.assertEqual(load["cue_beat_index"], 21)
        self.assertAlmostEqual(load["cue_seconds"], 6.3, places=3)
        self.assertIn("+real_beat", load["cue_source"])
        self.assertEqual(body["backbeat"]["double_time"]["cue_shift_beats"], 1)
        self.assertEqual(body["beats"], 9)

    def test_without_a_real_beat_read_it_is_not_called_matched(self) -> None:
        body, _ = _build(200.0, 100.0)
        self.assertEqual(body["backbeat"]["status"], "unverified")
        self.assertIn("real beats not measured", body["backbeat"]["reason"])
        self.assertEqual(body["beats"], 10)

    def test_unclear_read_is_unverified_and_moves_nothing(self) -> None:
        body, load = _build(100.0, 200.0, lambda *_: {**REAL, "other_confidence": 0.85})
        self.assertEqual(body["backbeat"]["status"], "unverified")
        self.assertEqual(load["cue_beat_index"], 20)
        self.assertEqual(body["beats"], 10)

    def test_certified_incoming_cue_never_moves(self) -> None:
        body, load = _build(100.0, 200.0, lambda *_: REAL, in_notes="cue_seconds=6.0; trust_cue_seconds")
        self.assertEqual(load["cue_seconds"], 6.0)
        self.assertEqual(body["backbeat"]["status"], "unverified")
        self.assertIn("certified incoming cue", body["backbeat"]["reason"])


if __name__ == "__main__":
    unittest.main()
