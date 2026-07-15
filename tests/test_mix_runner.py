from unittest import TestCase
from unittest.mock import patch

from hands.run_mix_plan import perform_transition, set_bpm_target


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
    @patch("hands.run_mix_plan.time.sleep")
    def test_bpm_target_uses_rate_readback(self, _sleep) -> None:
        class RateMixxx(FakeMixxx):
            def __init__(self) -> None:
                super().__init__()
                self.values[("[Channel2]", "rate")] = 0.0
                self.values[("[Channel2]", "rateRange")] = 0.08

            def get(self, group: str, key: str) -> float:
                if (group, key) == ("[Channel2]", "bpm"):
                    rate = self.values[(group, "rate")]
                    rate_range = self.values[(group, "rateRange")]
                    return 124.5 * (1.0 + rate * rate_range)
                return super().get(group, key)

        mixxx = RateMixxx()
        set_bpm_target(mixxx, 2, 100.0)
        self.assertAlmostEqual(mixxx.get("[Channel2]", "bpm"), 100.0, delta=0.5)

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


class RecordingMixxx(FakeMixxx):
    """Simulates Mixxx flipping [Recording],status after toggle_recording."""

    def __init__(self, *, starts_recording: bool = True, initial_status: float = 0.0) -> None:
        super().__init__()
        self.values[("[Recording]", "status")] = initial_status
        self._starts_recording = starts_recording

    def set(self, group: str, key: str, value: float) -> None:
        super().set(group, key, value)
        if (group, key) == ("[Recording]", "toggle_recording") and self._starts_recording:
            current = self.values[("[Recording]", "status")]
            self.values[("[Recording]", "status")] = 0.0 if current >= 1.0 else 1.0


class RecordingControlTests(TestCase):
    @patch("hands.run_mix_plan.time.sleep")
    def test_start_recording_toggles_and_confirms(self, _sleep) -> None:
        from hands.run_mix_plan import start_recording

        mixxx = RecordingMixxx(initial_status=0.0)
        started = start_recording(mixxx)
        self.assertTrue(started)
        self.assertEqual(mixxx.get("[Recording]", "status"), 1.0)
        self.assertIn(("[Recording]", "toggle_recording", 1), mixxx.writes)

    @patch("hands.run_mix_plan.time.sleep")
    def test_start_recording_leaves_existing_recording_alone(self, _sleep) -> None:
        from hands.run_mix_plan import start_recording

        mixxx = RecordingMixxx(initial_status=1.0)
        started = start_recording(mixxx)
        self.assertFalse(started)
        self.assertNotIn(
            ("[Recording]", "toggle_recording", 1),
            mixxx.writes,
            "must never toggle a recording that was already running",
        )

    @patch("hands.run_mix_plan.time.sleep")
    @patch("hands.run_mix_plan.time.monotonic", side_effect=[0.0, 0.0, 10.0])
    def test_start_recording_times_out_without_crashing(self, _monotonic, _sleep) -> None:
        from hands.run_mix_plan import start_recording

        mixxx = RecordingMixxx(starts_recording=False, initial_status=0.0)
        started = start_recording(mixxx, timeout_s=5.0)
        self.assertFalse(started)

    @patch("hands.run_mix_plan.time.sleep")
    def test_stop_recording_toggles_and_confirms(self, _sleep) -> None:
        from hands.run_mix_plan import stop_recording

        mixxx = RecordingMixxx(initial_status=1.0)
        stop_recording(mixxx)
        self.assertEqual(mixxx.get("[Recording]", "status"), 0.0)
        self.assertIn(("[Recording]", "toggle_recording", 1), mixxx.writes)
