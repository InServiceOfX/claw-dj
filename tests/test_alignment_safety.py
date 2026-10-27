"""2026-10-23: unresolved counts must not cause guessed beat jumps.

Strict cue checks are opt-in: existing heard plans keep their old controls.
All controls below are fake; no music, database or sockets are needed.
"""
import unittest
from unittest.mock import patch

from brain.build_mix_plan import build_plan
from hands import run_mix_plan as runner
from tests.test_blend_window import SONG, _tracks
from tests.test_double_time_grid import REAL, _build


class AlignmentSafetyTests(unittest.TestCase):
    def plan(self, out_parity=1, in_parity=0, confidence=.8, notes='', ride=10):
        tracks = _tracks()
        tracks[0]['dj_notes'] = f'cue_seconds=0; ride_beats={ride}'
        tracks[1]['dj_notes'] += notes
        return build_plan(tracks, count=2, seconds_per_track=20., affinity_lookup={},
            beat_phase_lookup={
                '/music/a.mp3': {**SONG, 'snare_parity': out_parity},
                '/music/b.mp3': {**SONG, 'snare_parity': in_parity, 'confidence': confidence}})

    def test_ambiguous_count_does_not_move_ride_or_invent_jump(self):
        p = self.plan()
        body = next(e for e in p['events'] if e['op'] == 'play_body')
        transition = next(e for e in p['events'] if e['op'] == 'transition')
        self.assertEqual(body['beats'], 10)
        self.assertEqual(body['backbeat']['status'], 'bar_guessed')
        self.assertFalse(body['backbeat']['count1_verified'])
        self.assertNotIn('nudged_beats', body['backbeat'])
        self.assertNotIn('snare_align', transition['moves'])

    def test_default_plus_one_guess_is_withheld(self):
        p = self.plan(ride=11)
        body = next(e for e in p['events'] if e['op'] == 'play_body')
        self.assertEqual(body['beats'], 11)
        self.assertEqual(body['backbeat']['status'], 'bar_guessed')
        self.assertNotIn('snare_align', next(e for e in p['events'] if e['op'] == 'transition')['moves'])

    def test_weak_read_does_not_move_ride(self):
        p = self.plan(in_parity=1, confidence=.04)
        body = next(e for e in p['events'] if e['op'] == 'play_body')
        self.assertEqual(body['beats'], 10)
        self.assertEqual(body['backbeat']['status'], 'unverified')
        self.assertFalse(body['backbeat']['count1_verified'])
        self.assertNotIn('snare_align', next(e for e in p['events'] if e['op'] == 'transition')['moves'])

    def test_explicit_human_snare_override_is_not_stripped(self):
        p = self.plan(notes='; snare_align')
        self.assertIn('snare_align', next(e for e in p['events'] if e['op'] == 'transition')['moves'])

    def test_ambiguous_double_time_read_does_not_move_cue_or_ride(self):
        for out_bpm, in_bpm in [(200., 100.), (100., 200.)]:
            with self.subTest(out=out_bpm):
                body, load = _build(out_bpm, in_bpm, lambda *_: {**REAL, 'snare_parity': 0})
                self.assertEqual(body['beats'], 10)
                self.assertEqual(load['cue_seconds'], 6.)
                self.assertEqual(body['backbeat']['status'], 'bar_guessed')
                self.assertFalse(body['backbeat']['count1_verified'])


class CueFake:
    def __init__(self, error_seconds=0., ignore_unquantized=False):
        self.position = 0.
        self.quantize = 1.
        self.error = error_seconds
        self.ignore_unquantized = ignore_unquantized
        self.writes = []

    def get(self, group, key):
        return {'duration': 300., 'playposition': self.position, 'quantize': self.quantize}.get(key, 0.)

    def set(self, group, key, value):
        self.writes.append((group, key, value))
        if key == 'quantize': self.quantize = value
        if key == 'playposition':
            error = self.error if self.quantize or self.ignore_unquantized else 0.
            self.position = value + error / 300.


class StrictCueTests(unittest.TestCase):
    def test_legacy_cue_behavior_is_unchanged_without_opt_in(self):
        fake = CueFake(.6)
        actual, _ = runner.cue_deck(fake, 1, cue_seconds=9.7274, duration=300., settle_s=0)
        self.assertAlmostEqual(actual * 300., 10.3274)
        self.assertFalse(any(key == 'quantize' for _, key, _ in fake.writes))

    @patch('hands.run_mix_plan.time.sleep')
    def test_strict_file_head_seek_temporarily_disables_quantize(self, _sleep):
        fake = CueFake(.132792)
        actual, _ = runner.cue_deck(fake, 1, cue_seconds=0., duration=300., settle_s=0,
                                    cue_tolerance_ms=20.)
        self.assertEqual(actual, 0.)
        self.assertEqual(fake.quantize, 1.)
        self.assertIn(('[Channel1]', 'quantize', 0), fake.writes)

    @patch('hands.run_mix_plan.time.sleep')
    def test_one_count_error_is_refused_and_quantize_restored(self, _sleep):
        fake = CueFake(.6, ignore_unquantized=True)
        with patch('hands.run_mix_plan.time.monotonic', side_effect=[0., 0., 1.]):
            with self.assertRaises(TimeoutError):
                runner.cue_deck(fake, 1, cue_seconds=9.7274, duration=300., settle_s=0,
                                timeout_s=.1, cue_tolerance_ms=20.)
        self.assertEqual(fake.quantize, 1.)
        self.assertFalse(any(key == 'play' and value == 1 for _, key, value in fake.writes))

    def test_invalid_tolerances_are_rejected_before_controls(self):
        for value in [0, -1, float('nan'), float('inf'), 251, True]:
            with self.subTest(value=value):
                fake = CueFake()
                with self.assertRaises(ValueError):
                    runner.cue_deck(fake, 1, cue_seconds=0., duration=300., cue_tolerance_ms=value)
                self.assertEqual(fake.writes, [])

    @patch('hands.run_mix_plan.load_deck')
    def test_explicit_load_event_carries_strict_tolerance(self, load):
        event = {'op': 'load', 'deck': 1, 'track_id': '/music/a.mp3',
                 'cue_seconds': 0., 'cue_tolerance_ms': 20.}
        runner._run_events(CueFake(), [event], {}, port=9995)
        self.assertEqual(load.call_args.kwargs['cue_tolerance_ms'], 20.)

    @patch('hands.run_mix_plan.time.sleep')
    def test_restoring_quantize_cannot_silently_snap_the_cue(self, _sleep):
        class RestoreSnap(CueFake):
            def set(self, group, key, value):
                super().set(group, key, value)
                if key == 'quantize' and value == 1:
                    self.position += .4 / 300.
        fake = RestoreSnap()
        with self.assertRaises(runner.CueVerificationError):
            runner.cue_deck(fake, 1, cue_seconds=0., duration=300., settle_s=0,
                            cue_tolerance_ms=20.)
        self.assertEqual(fake.quantize, 1.)

    @patch('hands.run_mix_plan.load_deck')
    def test_legacy_load_event_has_no_new_keyword(self, load):
        runner._run_events(CueFake(), [{'op': 'load', 'deck': 1,
            'track_id': '/music/a.mp3', 'cue_seconds': 0.}], {}, port=9995)
        self.assertEqual(load.call_args.kwargs, {})

    def test_strict_verification_refuses_a_playing_deck(self):
        class Playing(CueFake):
            def get(self, group, key):
                return 1. if key == 'play' else super().get(group, key)
        fake = Playing()
        with self.assertRaises(runner.CueVerificationError):
            runner.cue_deck(fake, 1, cue_seconds=0., duration=300., cue_tolerance_ms=20.)
        self.assertEqual(fake.writes, [])

    def test_invalid_event_is_rejected_before_connecting(self):
        with patch('hands.source_cutoffs.prepare_plan', side_effect=lambda plan, **kw: plan), \
             patch('hands.run_mix_plan.MixxxControl') as control:
            with self.assertRaises(ValueError):
                runner.run_plan({'tracks': [], 'events': [{'op': 'load', 'deck': 1,
                    'track_id': '/music/a.mp3', 'cue_tolerance_ms': float('nan')}]},
                    port=9995, dry_run=False, max_events=None)
            control.assert_not_called()

    def test_strict_failure_stops_both_decks(self):
        from unittest.mock import MagicMock
        fake = CueFake()
        context = MagicMock()
        context.__enter__.return_value = fake
        with patch('hands.source_cutoffs.prepare_plan', side_effect=lambda plan, **kw: plan), \
             patch('hands.run_mix_plan.MixxxControl', return_value=context), \
             patch('hands.run_mix_plan.load_deck', side_effect=runner.CueVerificationError('refused')), \
             patch('hands.run_mix_plan.neutralize_deck_effects') as neutralize:
            with self.assertRaises(runner.CueVerificationError):
                runner.run_plan({'tracks': [], 'events': [{'op': 'load', 'deck': 1,
                    'track_id': '/music/a.mp3', 'cue_tolerance_ms': 20.}]},
                    port=9995, dry_run=False, max_events=None)
        for deck in (1, 2):
            self.assertIn((f'[Channel{deck}]', 'play', 0), fake.writes)
        neutralize.assert_called_once()


if __name__ == '__main__':
    unittest.main()
