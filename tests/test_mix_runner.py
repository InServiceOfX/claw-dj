from unittest import TestCase
from unittest.mock import MagicMock, patch

from brain.plan_paths import PlanNotFound
from hands.run_mix_plan import (
    _run_events,
    _safe_body_beats,
    default_plan_path,
    load_deck,
    load_executable_plan,
    perform_juggle_brake_intro,
    perform_juggle_intro,
    perform_transition,
    ramp_bpm_target,
    resolve_plan_argument,
    run_plan,
    set_bpm_target,
)
from hands.transition import _phase_corrected_beat_count


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
    def test_runtime_phase_correction_preserves_full_bar_position(self) -> None:
        # Parity-only correction would choose 111 (11 + 111 is even) but that
        # lands on beat index 2 within the bar. The planned bar position is 0,
        # so the nearest safe reduction is 109 (11 + 109 == 120).
        self.assertEqual(
            _phase_corrected_beat_count(
                112,
                first_counted_beat_index=11,
                target_beat_mod4=0,
            ),
            109,
        )

    @patch(
        "hands.run_mix_plan.wait_for_next_beat",
        side_effect=TimeoutError("deck is not playing"),
    )
    def test_dead_outgoing_anchor_continues_on_incoming_deck(self, _wait) -> None:
        mixxx = FakeMixxx()
        perform_transition(  # type: ignore[arg-type]
            mixxx,
            {
                "from_deck": 1,
                "to_deck": 2,
                "transition_beats": 32,
                "technique": "smooth_blend",
                "moves": ["sync", "crossfade"],
            },
            port=9995,
        )

        self.assertIn(("[Channel2]", "play", 1), mixxx.writes)
        self.assertIn(("[Master]", "crossfader", 1.0), mixxx.writes)
        self.assertIn(("[Channel1]", "play", 0), mixxx.writes)

    def test_safe_body_beats_reserves_anchor_and_next_transition(self) -> None:
        mixxx = FakeMixxx()
        mixxx.values[("[Channel1]", "duration")] = 60.0
        mixxx.values[("[Channel1]", "playposition")] = 0.5
        mixxx.values[("[Channel1]", "bpm")] = 120.0

        # 30 seconds = 60 beats remain. Reserve 32 transition beats, one
        # anchor beat, and four safety beats. Preserve the requested mod-4
        # count, so 40 clamps to 20 rather than overrunning the file.
        self.assertEqual(
            _safe_body_beats(mixxx, 1, 40, next_transition_beats=32),
            20,
        )

    def test_safe_body_beats_leaves_a_safe_ride_unchanged(self) -> None:
        mixxx = FakeMixxx()
        mixxx.values[("[Channel1]", "duration")] = 180.0
        mixxx.values[("[Channel1]", "playposition")] = 0.25
        mixxx.values[("[Channel1]", "bpm")] = 100.0

        self.assertEqual(
            _safe_body_beats(mixxx, 1, 40, next_transition_beats=32),
            40,
        )

    @patch("hands.run_mix_plan.wait_for_beats")
    def test_play_body_forwards_the_planned_phase_anchor(self, wait) -> None:
        mixxx = FakeMixxx()
        mixxx.values[("[Channel1]", "play")] = 1.0
        anchor = {
            "grid_bpm": 120.0,
            "first_beat_seconds": 0.0,
            "planned_anchor_beat_index": 9,
            "target_beat_mod4": 1,
            "target_beat_parity": 1,
        }

        _run_events(
            mixxx,
            [{"op": "play_body", "deck": 1, "beats": 8, "phase_anchor": anchor}],
            {},
            port=9995,
        )

        wait.assert_called_once_with(
            9995,
            "[Channel1]",
            8,
            timeout_s=90.0,
            phase_anchor=anchor,
        )

    @patch("hands.run_mix_plan.plan_paths.resolve")
    def test_default_plan_path_uses_active_gui_plan(self, resolve) -> None:
        expected = MagicMock()
        resolve.return_value.mix_plan = expected

        self.assertIs(default_plan_path(), expected)
        resolve.assert_called_once_with()

    @patch(
        "hands.run_mix_plan.plan_paths.resolve",
        side_effect=PlanNotFound(None),
    )
    def test_default_plan_path_refuses_to_guess_when_no_plan_is_active(self, _resolve) -> None:
        with self.assertRaisesRegex(SystemExit, "no active named mix plan"):
            default_plan_path()

    def test_resolve_plan_argument_accepts_directory_and_mix_plan_file(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mix = root / "mix_plan.json"
            mix.write_text('{"events": []}\n')
            self.assertEqual(resolve_plan_argument(root), mix.resolve())
            self.assertEqual(resolve_plan_argument(mix), mix.resolve())
            with self.assertRaisesRegex(SystemExit, "missing built mix plan"):
                resolve_plan_argument(root / "missing-plan-dir")

    def test_load_executable_plan_rejects_metadata_and_playlist(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_meta = root / "plan.json"
            plan_meta.write_text('{"slug": "demo"}\n')
            with self.assertRaisesRegex(SystemExit, "plan metadata"):
                load_executable_plan(plan_meta)

            playlist = root / "playlist.json"
            playlist.write_text("[]\n")
            with self.assertRaisesRegex(SystemExit, "playlist.json"):
                load_executable_plan(playlist)

            good = root / "mix_plan.json"
            good.write_text('{"events": [{"op": "start"}]}\n')
            payload = load_executable_plan(good)
            self.assertEqual(payload["events"][0]["op"], "start")

    @patch("hands.run_mix_plan.wait_for_next_beat")
    @patch("hands.run_mix_plan.time.sleep")
    @patch("hands.run_mix_plan.time.monotonic", side_effect=[0.0, 16.0])
    def test_strict_intro_loop_jumps_loops_and_enters_together(
        self, _monotonic, _sleep, _wait_for_next_beat
    ) -> None:
        mixxx = FakeMixxx()
        mixxx.values[("[Channel1]", "duration")] = 240.0
        perform_transition(
            mixxx,
            {
                "from_deck": 1,
                "to_deck": 2,
                "transition_beats": 32,
                "technique": "dj_format_intro_loop_under_entry",
                "moves": [
                    "outgoing_intro_loop_8_bars",
                    "sync",
                    "crossfade",
                ],
                "outgoing_loop_seconds": 24.0,
                "outgoing_loop_beats": 32,
            },
            port=9995,
        )
        self.assertIn(("[Channel1]", "playposition", 0.1), mixxx.writes)
        self.assertIn(("[Channel1]", "beatloop_32_activate", 1), mixxx.writes)
        self.assertIn(("[Channel2]", "play", 1), mixxx.writes)
        self.assertIn(("[Channel2]", "beatsync", 1), mixxx.writes)
        self.assertIn(("[Channel1]", "reloop_toggle", 1), mixxx.writes)
        self.assertEqual(mixxx.get("[Channel1]", "play"), 0)

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

    @patch("hands.run_mix_plan.time.sleep")
    def test_playing_tempo_ramp_reaches_target_without_recueing(self, _sleep) -> None:
        class RampMixxx(FakeMixxx):
            def __init__(self) -> None:
                super().__init__()
                self.values[("[Channel1]", "bpm")] = 92.86
                self.values[("[Channel1]", "rate")] = 0.0
                self.values[("[Channel1]", "rateRange")] = 0.08

            def get(self, group: str, key: str) -> float:
                if (group, key) == ("[Channel1]", "bpm"):
                    return 92.86 * (
                        1.0
                        + self.values[(group, "rate")]
                        * self.values[(group, "rateRange")]
                    )
                return super().get(group, key)

        mixxx = RampMixxx()
        ramp_bpm_target(
            mixxx, 1, native_bpm=92.86, target_bpm=100.0, beats=8
        )
        self.assertAlmostEqual(mixxx.get("[Channel1]", "bpm"), 100.0, delta=0.1)
        self.assertFalse(any(key == "playposition" for _, key, _ in mixxx.writes))

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


class IncomingBpmTargetMixxx(FakeMixxx):
    """Deck 2's readback bpm tracks its rate, like a real Mixxx deck would."""

    def __init__(self, *, outgoing_bpm: float = 6000.0, native_incoming_bpm: float = 96.8) -> None:
        super().__init__()
        self.values[("[Channel1]", "bpm")] = outgoing_bpm
        self.values[("[Channel2]", "rate")] = 0.0
        self.values[("[Channel2]", "rateRange")] = 0.08
        self._native_incoming_bpm = native_incoming_bpm

    def get(self, group: str, key: str) -> float:
        if (group, key) == ("[Channel2]", "bpm"):
            rate = self.values[("[Channel2]", "rate")]
            rate_range = self.values[("[Channel2]", "rateRange")]
            return self._native_incoming_bpm * (1.0 + rate * rate_range)
        return super().get(group, key)


class IncomingBpmTargetTests(TestCase):
    @patch("hands.run_mix_plan.wait_for_next_beat")
    @patch("hands.run_mix_plan.time.sleep")
    def test_incoming_bpm_target_survives_the_sync_move(self, _sleep, _wait_for_next_beat) -> None:
        # Regression for 2026-07-16: a play_bpm bridge target set via
        # set_bpm_target was getting silently overwritten by a later
        # beatsync call when "sync" was also in the technique's moves,
        # snapping the incoming deck back toward the outgoing deck's
        # tempo. transition_beats=1 with a very high outgoing bpm keeps
        # the crossfade loop's real elapsed time negligible.
        mixxx = IncomingBpmTargetMixxx()
        perform_transition(
            mixxx,
            {
                "from_deck": 1,
                "to_deck": 2,
                "transition_beats": 1,
                "technique": "standard_blend",
                "moves": ["sync", "eq_dip_out_mid", "crossfade", "eq_restore"],
                "incoming_bpm_target": 103.0,
            },
            port=9995,
        )
        self.assertNotIn(("[Channel2]", "beatsync", 1), mixxx.writes)
        self.assertAlmostEqual(mixxx.get("[Channel2]", "bpm"), 103.0, delta=0.5)

    @patch("hands.run_mix_plan.wait_for_next_beat")
    @patch("hands.run_mix_plan.time.sleep")
    def test_incoming_bpm_target_still_gets_a_phase_only_sync(self, _sleep, _wait_for_next_beat) -> None:
        # Found 2026-07-17: a play_bpm hold skipping "sync" entirely meant
        # tempo was correct but the incoming deck's PHASE never actually
        # locked to the outgoing deck's beat -- half this mix's transitions
        # had a play_bpm hold, and beat-matching suffered for it compared
        # to a set that used real sync almost everywhere. beatsync_phase
        # snaps phase without touching tempo, so it can run alongside a
        # play_bpm hold instead of trading phase-lock away entirely.
        mixxx = IncomingBpmTargetMixxx()
        perform_transition(
            mixxx,
            {
                "from_deck": 1,
                "to_deck": 2,
                "transition_beats": 1,
                "technique": "standard_blend",
                "moves": ["sync", "eq_dip_out_mid", "crossfade", "eq_restore"],
                "incoming_bpm_target": 103.0,
            },
            port=9995,
        )
        self.assertIn(("[Channel2]", "beatsync_phase", 1), mixxx.writes)
        # Tempo must still hold at the target -- phase-only sync must not
        # touch it.
        self.assertAlmostEqual(mixxx.get("[Channel2]", "bpm"), 103.0, delta=0.5)

    @patch("hands.run_mix_plan.wait_for_next_beat")
    @patch("hands.run_mix_plan.time.sleep")
    def test_half_time_or_cut_gets_no_phase_only_sync_either(self, _sleep, _wait_for_next_beat) -> None:
        mixxx = IncomingBpmTargetMixxx()
        perform_transition(
            mixxx,
            {
                "from_deck": 1,
                "to_deck": 2,
                "transition_beats": 1,
                "technique": "half_time_or_cut",
                "moves": ["sync", "hard_cut"],
                "incoming_bpm_target": 103.0,
            },
            port=9995,
        )
        self.assertNotIn(("[Channel2]", "beatsync_phase", 1), mixxx.writes)
        self.assertNotIn(("[Channel2]", "beatsync", 1), mixxx.writes)

    @patch("hands.run_mix_plan.wait_for_next_beat")
    @patch("hands.run_mix_plan.time.sleep")
    def test_sync_move_still_fires_without_a_bpm_target(self, _sleep, _wait_for_next_beat) -> None:
        mixxx = IncomingBpmTargetMixxx()
        perform_transition(
            mixxx,
            {
                "from_deck": 1,
                "to_deck": 2,
                "transition_beats": 1,
                "technique": "standard_blend",
                "moves": ["sync", "eq_dip_out_mid", "crossfade", "eq_restore"],
            },
            port=9995,
        )
        self.assertIn(("[Channel2]", "beatsync", 1), mixxx.writes)


class JuggleBrakeIntroTests(TestCase):
    @patch("hands.run_mix_plan.rust_gesture", return_value=True)
    @patch("hands.run_mix_plan.time.sleep")
    def test_brakes_and_rewinds_to_the_original_cue(self, _sleep, _rust_gesture) -> None:
        mixxx = FakeMixxx()
        mixxx.values[("[Channel1]", "playposition")] = 0.0
        # No track_id -> skips the juggle-against-a-second-copy step (that
        # part is unmodified perform_juggle_intro code); this isolates the
        # new brake + rewind-to-cue behavior.
        perform_juggle_brake_intro(mixxx, {"deck": 1}, port=9995)
        self.assertAlmostEqual(mixxx.get("[Channel1]", "playposition"), 0.0)
        self.assertEqual(mixxx.get("[Channel1]", "volume"), 1.0)
        # Resumes immediately -- no dead pause waiting for a later `start`.
        self.assertEqual(mixxx.get("[Channel1]", "play"), 1)
        self.assertEqual(mixxx.writes[-1], ("[Channel1]", "play", 1))

    @patch("hands.run_mix_plan.rust_gesture", return_value=False)
    @patch("hands.run_mix_plan.time.sleep")
    def test_falls_back_to_manual_fade_without_clawdj_binary(self, _sleep, _rust_gesture) -> None:
        mixxx = FakeMixxx()
        mixxx.values[("[Channel1]", "playposition")] = 0.3
        perform_juggle_brake_intro(mixxx, {"deck": 1}, port=9995)
        # Fallback fade ramps volume down to 0 and stops the deck itself
        # (rust_gesture unavailable means brake() never sets play=0 for us),
        # but playback still resumes immediately after the rewind.
        self.assertIn(("[Channel1]", "play", 0), mixxx.writes)
        volume_writes = [v for g, k, v in mixxx.writes if (g, k) == ("[Channel1]", "volume")]
        self.assertIn(0.0, volume_writes)
        self.assertEqual(volume_writes[-1], 1.0)
        self.assertAlmostEqual(mixxx.get("[Channel1]", "playposition"), 0.3)
        self.assertEqual(mixxx.get("[Channel1]", "play"), 1)
        self.assertEqual(mixxx.writes[-1], ("[Channel1]", "play", 1))


class JuggleIntroTests(TestCase):
    @patch("hands.run_mix_plan.load_deck")
    @patch("hands.run_mix_plan.time.sleep")
    def test_repeats_cue_drops_then_replays_cleanly(self, _sleep, load) -> None:
        mixxx = FakeMixxx()
        mixxx.values[("[Channel1]", "playposition")] = 0.08
        perform_juggle_intro(
            mixxx,
            {
                "deck": 1,
                "track": "Nas — If I Ruled The World",
                "track_id": "/music/nas.mp3",
                "cue_fraction": 0.08,
                "juggle_chops": 4,
            },
        )

        load.assert_called_once_with(
            mixxx, 2, "/music/nas.mp3",
            cue_fraction=0.08, cue_seconds=None, expected_bpm=120.0,
        )
        deck_one_drops = [
            value for group, key, value in mixxx.writes
            if (group, key) == ("[Channel1]", "playposition")
        ]
        deck_two_drops = [
            value for group, key, value in mixxx.writes
            if (group, key) == ("[Channel2]", "playposition")
        ]
        self.assertGreaterEqual(deck_one_drops.count(0.08), 3)
        self.assertGreaterEqual(deck_two_drops.count(0.08), 3)
        self.assertAlmostEqual(mixxx.get("[Channel1]", "playposition"), 0.08)
        self.assertEqual(mixxx.get("[Channel1]", "play"), 1)
        self.assertEqual(mixxx.get("[Channel2]", "play"), 0)
        self.assertEqual(mixxx.get("[Master]", "crossfader"), -1.0)


class VerseLandingMissTests(TestCase):
    @patch("hands.run_mix_plan.wait_for_next_beat")
    @patch("hands.run_mix_plan.time.sleep")
    def test_missed_landing_snaps_and_continues_instead_of_crashing(self, _sleep, _wait) -> None:
        # Seen live 2026-07-19: a track whose grid Mixxx re-analyzed into a
        # different tempo family made the pre-roll run short; the old hard
        # RuntimeError killed the whole set mid-mix, twice. Must recover.
        mixxx = FakeMixxx()
        mixxx.values[("[Channel2]", "duration")] = 268.0
        mixxx.values[("[Channel2]", "playposition")] = 76.6 / 268.0  # short of 84.27
        perform_transition(
            mixxx,
            {
                "from_deck": 1, "to_deck": 2, "transition_beats": 1,
                "technique": "verse_landing_blend",
                "moves": ["crossfade"],
                "landing_seconds": 84.27,
                "landing_tolerance_seconds": 1.0,
            },
            port=9995,
        )
        self.assertIn(
            ("[Channel2]", "playposition", 84.27 / 268.0), mixxx.writes
        )


class EchoOutExitTests(TestCase):
    @patch("hands.run_mix_plan.wait_for_next_beat")
    @patch("hands.run_mix_plan.time.sleep")
    def test_echo_out_uses_the_reserved_echo_unit_when_loaded(self, _sleep, _wait) -> None:
        mixxx = FakeMixxx()
        mixxx.values[("[EffectRack1_EffectUnit2_Effect3]", "loaded")] = 1.0
        perform_transition(
            mixxx,
            {
                "from_deck": 1, "to_deck": 2, "transition_beats": 4,
                "technique": "echo_out_exit", "moves": ["echo_out_exit"],
            },
            port=9995,
        )
        self.assertIn(("[EffectRack1_EffectUnit2_Effect3]", "enabled", 1), mixxx.writes)
        self.assertIn(("[EffectRack1_EffectUnit2]", "group_[Channel1]_enable", 1), mixxx.writes)
        self.assertIn(("[EffectRack1_EffectUnit2_Effect3]", "parameter1", 0.5), mixxx.writes)
        self.assertIn(("[EffectRack1_EffectUnit2_Effect3]", "parameter2", 0.68), mixxx.writes)
        self.assertIn(("[EffectRack1_EffectUnit2_Effect3]", "parameter4", 0.75), mixxx.writes)
        self.assertIn(("[EffectRack1_EffectUnit2_Effect3]", "button_parameter1", 1), mixxx.writes)
        # Outgoing stopped, incoming started clean; no sync of any kind.
        self.assertEqual(mixxx.get("[Channel1]", "play"), 0)
        self.assertEqual(mixxx.get("[Channel2]", "play"), 1)
        self.assertNotIn(("[Channel2]", "beatsync", 1), mixxx.writes)
        self.assertNotIn(("[Channel2]", "beatsync_phase", 1), mixxx.writes)

    @patch("hands.run_mix_plan.wait_for_next_beat")
    @patch("hands.run_mix_plan.time.sleep")
    def test_echo_out_falls_back_to_plain_fade_without_echo_loaded(self, _sleep, _wait) -> None:
        mixxx = FakeMixxx()  # ECHO_SLOT loaded reads 0.0
        perform_transition(
            mixxx,
            {
                "from_deck": 1, "to_deck": 2, "transition_beats": 4,
                "technique": "echo_out_exit", "moves": ["echo_out_exit"],
            },
            port=9995,
        )
        volume_writes = [v for g, k, v in mixxx.writes if (g, k) == ("[Channel1]", "volume")]
        self.assertIn(0.0, volume_writes)
        self.assertEqual(volume_writes[-1], 1.0)  # restored after the stop
        self.assertEqual(mixxx.get("[Channel1]", "play"), 0)
        self.assertEqual(mixxx.get("[Channel2]", "play"), 1)

    @patch("hands.run_mix_plan.wait_for_next_beat")
    @patch("hands.run_mix_plan.time.sleep")
    def test_echo_out_never_leaves_a_silent_gap(self, _sleep, _wait) -> None:
        # Found live 2026-07-19: the original sequential version (ramp the
        # outgoing deck fully to silence, THEN stop it, THEN start the
        # incoming one) left real dead air -- the opposite of "keep the
        # beat going". The incoming deck must start playing WHILE the
        # outgoing deck is still audible, not after.
        mixxx = FakeMixxx()
        mixxx.values[("[EffectRack1_EffectUnit2_Effect3]", "loaded")] = 1.0
        perform_transition(
            mixxx,
            {
                "from_deck": 1, "to_deck": 2, "transition_beats": 4,
                "technique": "echo_out_exit", "moves": ["echo_out_exit"],
            },
            port=9995,
        )
        play_index = mixxx.writes.index(("[Channel2]", "play", 1))
        # Every volume write on the outgoing deck strictly before the
        # incoming deck starts must still be audible (> 0) -- there is no
        # point in the sequence where both decks are silent at once.
        for group, key, value in mixxx.writes[:play_index]:
            if (group, key) == ("[Channel1]", "volume"):
                self.assertGreater(value, 0.0)
        # And the incoming starts before the outgoing deck is stopped.
        stop_index = mixxx.writes.index(("[Channel1]", "play", 0))
        self.assertLess(play_index, stop_index)
        # The delay stays routed after the dry deck stops, so Mixxx can
        # render its buffered repeats instead of cutting the tail off.
        unroute_index = mixxx.writes.index(
            ("[EffectRack1_EffectUnit2]", "group_[Channel1]_enable", 0)
        )
        self.assertLess(stop_index, unroute_index)
        _sleep.assert_any_call(2.0)  # four beats at FakeMixxx's 120 BPM


class FilterDropExitTests(TestCase):
    @patch("hands.run_mix_plan.wait_for_next_beat")
    @patch("hands.run_mix_plan.time.sleep")
    def test_filter_drop_cuts_on_phrase_without_echo_or_sync(self, _sleep, _wait) -> None:
        mixxx = FakeMixxx()
        perform_transition(
            mixxx,
            {
                "from_deck": 1, "to_deck": 2, "transition_beats": 4,
                "technique": "filter_drop_exit", "moves": ["filter_drop_exit"],
            },
            port=9995,
        )
        self.assertEqual(mixxx.get("[Channel1]", "play"), 0)
        self.assertEqual(mixxx.get("[Channel2]", "play"), 1)
        self.assertEqual(mixxx.get("[Master]", "crossfader"), 1.0)
        self.assertIn(("[QuickEffectRack1_[Channel1]]", "super1", 0.5), mixxx.writes)
        self.assertFalse(any(group.startswith("[EffectRack1") for group, _, _ in mixxx.writes))
        self.assertNotIn(("[Channel2]", "beatsync", 1), mixxx.writes)


class RunPlanInterruptTests(TestCase):
    @patch("hands.run_mix_plan._run_events", side_effect=KeyboardInterrupt)
    @patch("hands.run_mix_plan.MixxxControl")
    def test_ctrl_c_stops_both_decks_instead_of_leaving_them_playing(
        self, mock_mixxx_control, _run_events
    ) -> None:
        mixxx = FakeMixxx()
        mock_mixxx_control.return_value.__enter__ = MagicMock(return_value=mixxx)
        mock_mixxx_control.return_value.__exit__ = MagicMock(return_value=False)

        # Should not raise -- KeyboardInterrupt is caught and handled, not
        # left to unwind as a bare traceback.
        run_plan({"events": []}, port=9995, dry_run=False, max_events=None)

        self.assertIn(("[Channel1]", "play", 0), mixxx.writes)
        self.assertIn(("[Channel2]", "play", 0), mixxx.writes)


class StartEventBpmTargetTests(TestCase):
    @patch("hands.run_mix_plan.time.sleep")
    def test_start_event_bpm_target_applies_before_play(self, _sleep) -> None:
        class RateMixxx(FakeMixxx):
            def __init__(self) -> None:
                super().__init__()
                self.values[("[Channel1]", "rate")] = 0.0
                self.values[("[Channel1]", "rateRange")] = 0.08

            def get(self, group: str, key: str) -> float:
                if (group, key) == ("[Channel1]", "bpm"):
                    rate = self.values[("[Channel1]", "rate")]
                    rate_range = self.values[("[Channel1]", "rateRange")]
                    return 100.0 * (1.0 + rate * rate_range)
                return super().get(group, key)

        mixxx = RateMixxx()
        _run_events(mixxx, [{"op": "start", "deck": 1, "bpm_target": 103.0}], {}, port=9995)
        self.assertAlmostEqual(mixxx.get("[Channel1]", "bpm"), 103.0, delta=0.5)
        # The rate bump must land before play=1, not after (no audible jump).
        rate_writes = [i for i, w in enumerate(mixxx.writes) if w[1] == "rate" and w[2] != 0.0]
        play_writes = [i for i, w in enumerate(mixxx.writes) if w[1] == "play" and w[2] == 1]
        self.assertTrue(rate_writes and play_writes)
        self.assertLess(min(rate_writes), min(play_writes))

    @patch("hands.run_mix_plan.time.sleep")
    def test_start_event_without_bpm_target_is_unaffected(self, _sleep) -> None:
        mixxx = FakeMixxx()
        _run_events(mixxx, [{"op": "start", "deck": 1}], {}, port=9995)
        self.assertIn(("[Channel1]", "play", 1), mixxx.writes)


class LoadDeckBpmTimeoutTests(TestCase):
    @patch("hands.run_mix_plan.LOAD_TIMEOUT_S", 0.02)
    @patch("hands.run_mix_plan.time.sleep")
    def test_bpm_confirmation_timeout_does_not_crash_the_set(self, _sleep) -> None:
        # A newly-added track whose analysis hasn't settled into Mixxx's own
        # cache yet can report a bpm that never matches the plan's expected
        # value -- confirmed live, 2026-07-16 (a track added earlier the
        # same session). One track's slow/flaky analysis must not raise
        # and crash the whole live set.
        class StubbornBpmMixxx(FakeMixxx):
            def __init__(self) -> None:
                super().__init__()
                # Starts unloaded so the eject-wait (v < 0.5) resolves
                # immediately; .load() below flips it, same as a real deck.
                self.values[("[Channel1]", "track_loaded")] = 0.0
                self.values[("[Channel1]", "duration")] = 200.0
                self.values[("[Channel1]", "bpm")] = 200.0  # never near expected_bpm
                self.values[("[Channel1]", "playposition")] = 0.0

            def load(self, deck: int, path: str, play: bool = False) -> None:
                self.values[("[Channel1]", "track_loaded")] = 1.0

        mixxx = StubbornBpmMixxx()
        load_deck(mixxx, 1, "/music/new_track.mp3", expected_bpm=103.176)
        # Must have proceeded past the bpm wait (cue_deck ran) rather than
        # raising TimeoutError.
        self.assertIn(("[Channel1]", "volume", 1.0), mixxx.writes)


class WaitForBeatsResubscribeTests(TestCase):
    def test_runtime_phase_guard_corrects_a_delayed_body_start(self) -> None:
        """A variable preload must not move the planned bar position.

        The plan expects the transition anchor at beat 0 modulo four. By the
        time the body counter subscribes, the live deck's first counted edge
        is beat 11. Counting 112 edges would anchor on beat 123 (position 3),
        so the live counter must stop after 109 and anchor on beat 120.
        """
        from hands.transition import wait_for_beats

        class GridAwareMixxx:
            emitted = 0

            def __init__(self, *args, **kwargs) -> None:
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args) -> None:
                return None

            def get(self, group: str, key: str) -> float:
                if key == "bpm":
                    return 120.0
                if key == "play":
                    return 1.0
                if key == "duration":
                    return 120.0
                if key == "playposition":
                    # Beat 11 on a 120 BPM grid whose first beat is at 0.
                    return 5.5 / 120.0
                return 0.0

            def subscribe(self, *args) -> None:
                return None

            def events(self):
                for _ in range(112):
                    yield {"value": 0.0}
                    type(self).emitted += 1
                    yield {"value": 1.0}

        GridAwareMixxx.emitted = 0
        with patch("hands.transition.MixxxControl", GridAwareMixxx):
            wait_for_beats(
                9995,
                "[Channel1]",
                beats=112,
                timeout_s=180.0,
                phase_anchor={
                    "grid_bpm": 120.0,
                    "first_beat_seconds": 0.0,
                    "target_beat_mod4": 0,
                    "target_beat_parity": 0,
                },
            )

        self.assertEqual(GridAwareMixxx.emitted, 109)

    @patch("hands.transition.time.sleep")
    def test_resubscribes_after_mid_ride_stream_gap(self, _sleep) -> None:
        from hands.transition import wait_for_beats

        class ProbeMixxx:
            def __init__(self, *args, **kwargs) -> None:
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args) -> None:
                return None

            def get(self, group: str, key: str) -> float:
                if key == "bpm":
                    return 120.0
                if key == "play":
                    return 1.0
                return 0.0

            def set(self, *args) -> None:
                return None

        class GapThenRecoverEvents:
            instances = 0
            subscribes = 0

            def __init__(self, *args, **kwargs) -> None:
                type(self).instances += 1
                self._n = type(self).instances

            def __enter__(self):
                return self

            def __exit__(self, *args) -> None:
                return None

            def subscribe(self, group: str, key: str) -> None:
                type(self).subscribes += 1

            def events(self):
                if self._n == 1:
                    # First subscription dies after a few beats.
                    yield {"value": 0.0}
                    yield {"value": 1.0}
                    yield {"value": 0.0}
                    yield {"value": 1.0}
                    raise TimeoutError("stream quiet")
                # Second subscription finishes the ride.
                for _ in range(4):
                    yield {"value": 0.0}
                    yield {"value": 1.0}

        GapThenRecoverEvents.instances = 0
        GapThenRecoverEvents.subscribes = 0

        class Factory:
            n = 0

            def __call__(self, *args, **kwargs):
                type(self).n += 1
                # wait_for_beats alternates probe connections and event streams.
                if type(self).n % 2 == 1:
                    return ProbeMixxx()
                return GapThenRecoverEvents()

        Factory.n = 0
        with patch("hands.transition.MixxxControl", side_effect=Factory()):
            wait_for_beats(9995, "[Channel1]", beats=4, timeout_s=30.0)

        self.assertGreaterEqual(GapThenRecoverEvents.subscribes, 2)

    @patch("hands.transition.time.sleep")
    def test_raises_if_deck_stays_stopped_after_stream_gap(self, _sleep) -> None:
        from hands.transition import wait_for_beats

        class AliveThenDead:
            calls = 0

            def __init__(self, *args, **kwargs) -> None:
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args) -> None:
                return None

            def get(self, group: str, key: str) -> float:
                if key == "bpm":
                    return 120.0
                if key == "play":
                    type(self).calls += 1
                    # Initial probe only: playing. After the stream gap, stay dead.
                    return 1.0 if type(self).calls == 1 else 0.0
                return 0.0

            def set(self, *args) -> None:
                return None

            def subscribe(self, *args) -> None:
                return None

            def events(self):
                yield {"value": 1.0}
                raise TimeoutError("stream quiet")

        AliveThenDead.calls = 0
        with patch("hands.transition.MixxxControl", AliveThenDead):
            with self.assertRaisesRegex(TimeoutError, "stopped during ride"):
                wait_for_beats(9995, "[Channel1]", beats=8, timeout_s=10.0)

class SettleBpmTests(TestCase):
    """A track can be entered sped up and then ridden somewhere in between."""

    @patch("hands.run_mix_plan.time.sleep")
    def test_settle_bpm_stops_the_glide_part_way_home(self, _sleep) -> None:
        from hands.run_mix_plan import settle_rate

        mixxx = FakeMixxx()
        # Luchini's real case: native 83, dragged up to Keni Burke's 94 by the
        # blend, asked to ride at 90 rather than snapping all the way back.
        mixxx.values[("[Channel2]", "rate")] = 0.40
        mixxx.values[("[Channel2]", "bpm")] = 94.0
        settle_rate(mixxx, 2, steps=4, settle_bpm=90.0, native_bpm=83.0)
        rates = [value for group, key, value in mixxx.writes if key == "rate"]
        # (90-83)/(94-83) = 0.636 of the way up, so 0.40 * 0.636 = 0.2545.
        self.assertAlmostEqual(rates[-1], 0.2545, places=3)
        # Monotonic downward, never overshooting past the target.
        self.assertTrue(all(a >= b for a, b in zip(rates, rates[1:])), rates)
        self.assertGreater(rates[-1], 0.0)

    @patch("hands.run_mix_plan.time.sleep")
    def test_without_settle_bpm_it_still_goes_all_the_way_to_native(self, _sleep) -> None:
        from hands.run_mix_plan import settle_rate

        mixxx = FakeMixxx()
        mixxx.values[("[Channel2]", "rate")] = 0.40
        mixxx.values[("[Channel2]", "bpm")] = 94.0
        settle_rate(mixxx, 2, steps=4)
        rates = [value for group, key, value in mixxx.writes if key == "rate"]
        self.assertAlmostEqual(rates[-1], 0.0, places=6)

    @patch("hands.run_mix_plan.time.sleep")
    def test_a_settle_target_above_the_blend_tempo_never_speeds_up(self, _sleep) -> None:
        from hands.run_mix_plan import settle_rate

        mixxx = FakeMixxx()
        mixxx.values[("[Channel2]", "rate")] = 0.40
        mixxx.values[("[Channel2]", "bpm")] = 94.0
        # Asking for 120 on a deck already at 94 must clamp, not accelerate.
        settle_rate(mixxx, 2, steps=4, settle_bpm=120.0, native_bpm=83.0)
        rates = [value for group, key, value in mixxx.writes if key == "rate"]
        self.assertLessEqual(max(rates), 0.40 + 1e-9)
