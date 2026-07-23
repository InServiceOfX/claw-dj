from unittest import TestCase
from unittest.mock import MagicMock, patch

from hands.run_mix_plan import (
    _run_events,
    load_deck,
    perform_juggle_brake_intro,
    perform_juggle_intro,
    perform_transition,
    ramp_bpm_target,
    run_plan,
    set_bpm_target,
)


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
