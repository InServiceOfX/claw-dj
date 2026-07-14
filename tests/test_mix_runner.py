from unittest import TestCase
from unittest.mock import patch

from hands.run_mix_plan import perform_transition


class FakeMixxx:
    def __init__(self) -> None:
        self.values = {
            ("[Channel1]", "bpm"): 120.0,
            ("[Master]", "crossfader"): -1.0,
        }
        self.writes: list[tuple[str, str, float]] = []

    def get(self, group: str, key: str) -> float:
        return self.values.get((group, key), 0.0)

    def set(self, group: str, key: str, value: float) -> None:
        self.values[(group, key)] = value
        self.writes.append((group, key, value))


class MixRunnerTests(TestCase):
    @patch("hands.run_mix_plan.wait_for_next_beat")
    @patch("hands.run_mix_plan.time.sleep")
    @patch("hands.run_mix_plan.time.monotonic", side_effect=[0.0, 2.0])
    def test_key_blend_applies_then_restores_pitch(
        self, _monotonic, _sleep, _wait_for_next_beat
    ) -> None:
        mixxx = FakeMixxx()
        perform_transition(
            mixxx,
            {
                "from_deck": 1,
                "to_deck": 2,
                "transition_beats": 4,
                "technique": "key_adjusted_blend",
                "moves": ["key_blend", "sync", "crossfade"],
                "pitch_adjust_semitones": -1,
                "pitch_adjust_target": "F",
            },
            port=9995,
        )
        pitch_writes = [
            value for group, key, value in mixxx.writes
            if group == "[Channel2]" and key == "pitch_adjust"
        ]
        self.assertEqual(pitch_writes[0], -1.0)
        self.assertEqual(pitch_writes[-1], 0.0)

    def test_key_blend_rejects_excessive_shift(self) -> None:
        mixxx = FakeMixxx()
        with self.assertRaises(ValueError):
            perform_transition(
                mixxx,
                {
                    "from_deck": 1,
                    "to_deck": 2,
                    "technique": "key_adjusted_blend",
                    "moves": ["key_blend"],
                    "pitch_adjust_semitones": 3,
                },
                port=9995,
            )
