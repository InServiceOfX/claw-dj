"""Center hold: both songs at full for part of a blend (Ernest, 2026-10-21).

On SWV remix -> "I'm So Into You" the backbeats line up, so he wanted a longer
blend with both songs up together for a while. Mixxx's additive crossfader
plays both decks at full gain at center; ``center_hold_beats`` parks it there.
"""
import unittest

from hands.run_mix_plan import center_hold_fraction, held_fader_position


class CenterHoldFractionTest(unittest.TestCase):
    def test_no_hold_by_default(self) -> None:
        self.assertEqual(center_hold_fraction({"transition_beats": 32}), 0.0)

    def test_hold_is_a_share_of_the_blend(self) -> None:
        self.assertEqual(center_hold_fraction({"transition_beats": 64, "center_hold_beats": 32}), 0.5)

    def test_ramps_keep_gentle_faders(self) -> None:
        # 32-beat blend, 32-beat hold: the ramps still get 16 beats in all
        self.assertEqual(center_hold_fraction({"transition_beats": 32, "center_hold_beats": 32}), 0.5)


class HeldFaderPositionTest(unittest.TestCase):
    def test_without_hold_the_ramp_is_steady(self) -> None:
        self.assertEqual(held_fader_position(0.25, -1.0, 1.0, 0.0), -0.5)

    def test_hold_parks_at_center(self) -> None:
        positions = [held_fader_position(p, -1.0, 1.0, 0.5) for p in (0.0, 0.125, 0.25, 0.5, 0.75, 0.875, 1.0)]
        self.assertEqual(positions, [-1.0, -0.5, 0.0, 0.0, 0.0, 0.5, 1.0])

    def test_hold_works_right_to_left(self) -> None:
        self.assertEqual(held_fader_position(0.5, 1.0, -1.0, 0.5), 0.0)
        self.assertEqual(held_fader_position(1.0, 1.0, -1.0, 0.5), -1.0)


if __name__ == "__main__":
    unittest.main()
