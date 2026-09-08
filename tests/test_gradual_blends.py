"""Listener regressions: uncertain evidence must not turn smooth blends into cuts."""
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from brain import rhythm
from hands import backbeat
from hands.run_mix_plan import perform_transition
from tests.test_backbeat import Clock, Transport, event, pattern


class GradualBlendTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        for item in (patch('hands.backbeat.time.monotonic', self.clock.monotonic),
                     patch('hands.backbeat.time.sleep', self.clock.sleep),
                     patch('hands.backbeat.identity_matches', return_value=True),
                     patch('hands.backbeat.wait_for_next_beat')):
            item.start()
            self.addCleanup(item.stop)

    def play(self, transition, *, transport=None):
        transport = transport or Transport(self.clock)
        output = io.StringIO()
        with redirect_stdout(output), patch('hands.backbeat.evidence') as log:
            perform_transition(transport, transition, port=9995)
        writes = [(value, at) for _, key, value, at in transport.writes if key == 'crossfader']
        return transport, writes, output.getvalue(), log

    def assert_gradual(self, writes, seconds):
        self.assertGreaterEqual(writes[-1][1] - writes[0][1], seconds - 0.12)
        self.assertLess(writes[-1][1] - writes[0][1], seconds + 0.5)
        self.assertGreater(len(writes), 30)
        direction = 1 if writes[-1][0] > writes[0][0] else -1
        self.assertTrue(all((b[0] - a[0]) * direction >= 0 for a, b in zip(writes, writes[1:])))
        self.assertLess(max(abs(b[0] - a[0]) for a, b in zip(writes, writes[1:])), .1)

    def test_weak_evidence_retains_planned_fade_on_both_reported_pairs(self):
        for outgoing, incoming in (('Aaliyah — Rock The Boat', 'Mario — Just a Friend'),
                                   ('Mario — Just a Friend', 'Young Buck — 2 Bricks'),
                                   ('G-Unit — Part 2 & Bump Heads', 'Barry White — Never Never Gonna Give Ya Up'),
                                   ('Barry White — Never Never Gonna Give Ya Up', "Biggie — You're Nobody"),
                                   ("Biggie — You're Nobody", 'Rick Ross — Nobody'),
                                   ('Rick Ross — Nobody', 'Keith Murray — Get Lifted'),
                                   ('Ja Rule — Put It On Me', 'Nick Jonas — Jealous'),
                                   ('Nick Jonas — Jealous', "Lil' Mo — Superwoman pt.2")):
            with self.subTest(pair=(outgoing, incoming)):
                transition = event(incoming=pattern(confidence=0.1))
                transition.update(from_track=outgoing, to_track=incoming, transition_beats=32)
                _, writes, output, log = self.play(transition)
                self.assert_gradual(writes, 16)
                self.assertIn('unverified', output)
                self.assertNotIn('2-beat landing', output)
                self.assertFalse(any(c.args[0] == 'position_verified' for c in log.call_args_list))

    def test_key_clash_filter_blend_retains_gradual_fader_and_filter(self):
        transition = event(incoming=pattern(confidence=.1))
        transition.update(technique='key_clash_blend', transition_beats=32,
                          from_track="It's All About The Benjamins", to_track='Put It On Me',
                          moves=['sync', 'filter_sweep_out', 'crossfade', 'filter_reset', 'eq_restore'])
        transport, writes, _, _ = self.play(transition)
        self.assert_gradual(writes, 16)
        sweep = [value for _, key, value, _ in transport.writes if key == 'super1']
        self.assertGreater(len(sweep), 30)

    def test_noisy_errors_and_late_drift_neither_reverse_nor_extend_either_direction(self):
        for from_deck, to_deck in ((1, 2), (2, 1)):
            for noise in (True, False):
                with self.subTest(direction=(from_deck, to_deck), noise=noise):
                    self.clock.now = 0
                    transport = Transport(self.clock)
                    transport.values[('[Master]', 'crossfader')] = -1 if from_deck == 1 else 1
                    transport.values[(f'[Channel{from_deck}]', 'play')] = 1
                    transport.values[(f'[Channel{to_deck}]', 'play')] = 0
                    transport.positions[from_deck], transport.positions[to_deck] = 8, 0
                    observed = []
                    def observe(stage):
                        if stage == 'before_fader':
                            return 0.0
                        observed.append(True)
                        if noise:
                            return .18 if len(observed) % 2 else -.18
                        return .18 if self.clock.now > 14 else 0.0
                    transition = event(from_deck=from_deck, to_deck=to_deck)
                    transition['transition_beats'] = 32
                    with patch.object(backbeat.Guard, 'observe', side_effect=observe):
                        _, writes, _, _ = self.play(transition, transport=transport)
                    self.assert_gradual(writes, 16)

    def test_one_stale_stopped_or_eof_read_cannot_slam_the_fader(self):
        for control, value in (('play', 0), ('playposition', 1), ('playposition', .999), ('playposition', .995)):
            with self.subTest(control=control):
                self.clock.now = 0
                transport = Transport(self.clock)
                original = transport.get
                injected = []
                def get(group, key):
                    if group == '[Channel1]' and key == control and self.clock.now > 5 and not injected:
                        injected.append(True)
                        return value
                    return original(group, key)
                transport.get = get
                transition = event()
                transition['transition_beats'] = 64
                _, writes, _, _ = self.play(transition, transport=transport)
                self.assert_gradual(writes, 32)
                self.assertLess(max(b[0] - a[0] for a, b in zip(writes, writes[1:])), .1)

    def test_half_double_grid_family_keeps_full_fade_when_evidence_is_weak(self):
        for native_out, native_in in ((85.0, 170.0), (170.0, 85.0)):
            with self.subTest(bpms=(native_out, native_in)):
                self.clock.now = 0
                transport = Transport(self.clock)
                rhythms = []
                for deck, native in ((1, native_out), (2, native_in)):
                    transport.values[(f'[Channel{deck}]', 'file_bpm')] = native
                    transport.values[(f'[Channel{deck}]', 'bpm')] = native
                    data = pattern(confidence=.1)
                    data['bpm'] = native
                    rhythms.append(data)
                transition = event(*rhythms)
                transition.update(transition_beats=32, incoming_bpm_target=native_in)
                with patch('hands.run_mix_plan.set_bpm_target'):
                    _, writes, output, _ = self.play(transition, transport=transport)
                self.assert_gradual(writes, 32 * 60 / native_out)
                self.assertNotIn('mismatch', output)

    def test_short_middle_track_uses_remaining_audio_without_cue_jump(self):
        transport = Transport(self.clock)
        transport.values[('[Channel2]', 'duration')] = 71
        transport.positions[2] = 38.38
        middle = pattern(confidence=.1)
        middle['duration_seconds'] = 71
        first = event(incoming=middle)
        first['transition_beats'] = 32
        self.play(first, transport=transport)
        transport.positions[1] = 0
        second = event(middle, pattern(confidence=.1), 2, 1)
        second['transition_beats'] = 32
        _, writes, output, _ = self.play(second, transport=transport)
        # Inspect only the reverse fade after the first transfer finished.
        peak = next(i for i, (v, _) in enumerate(writes) if v == 1)
        self.assertGreater(writes[-1][1] - writes[peak][1], 10)
        self.assertIn('remaining audio', output)
        self.assertFalse(any(w[1] == 'playposition' for w in transport.writes))

    def test_missing_position_verification_keeps_last_cue_preserving_launch(self):
        with patch.object(backbeat.Guard, 'observe', return_value=None):
            transport, writes, _, _ = self.play(event())
        self.assert_gradual(writes, 8)
        # One optional muted retry, never a second reset to an unrelated beat.
        seeks = [w for w in transport.writes if w[1] == 'playposition']
        self.assertLessEqual(len(seeks), 1)
        self.assertTrue(all(group == '[Channel2]' and value == 0 for group, _, value, _ in seeks))

    def test_borderline_opening_uses_multiple_samples_not_one_outlier(self):
        errors = iter([-.122, -.0625, -.052, -.049, -.044])
        with patch.object(backbeat.Guard, 'observe', side_effect=lambda stage: next(errors, -.050)):
            _, writes, _, log = self.play(event())
        self.assert_gradual(writes, 8)
        self.assertTrue(any(c.args[0] == 'position_verified' for c in log.call_args_list))

    def test_losing_local_evidence_mid_blend_does_not_rush_fader(self):
        def observe(stage):
            return -.05 if stage == 'before_fader' else None
        transition = event()
        transition.update(from_track='Young Buck — 2 Bricks', to_track='G-Unit — Stunt 101', transition_beats=32)
        with patch.object(backbeat.Guard, 'observe', side_effect=observe):
            _, writes, output, log = self.play(transition)
        self.assert_gradual(writes, 16)
        self.assertNotIn('short handoff', output)
        self.assertFalse(any(c.args[0] == 'fallback' for c in log.call_args_list))

    def test_sustained_measured_mismatch_keeps_planned_blend_and_honest_warning(self):
        with patch.object(backbeat.Guard, 'observe', return_value=.18):
            _, writes, output, log = self.play(event())
        self.assert_gradual(writes, 8)
        self.assertIn('mismatch', output)
        ends = [c.kwargs for c in log.call_args_list if c.args[0] == 'transition_end']
        self.assertAlmostEqual(ends[-1]['planned_beats'], 16)
        self.assertAlmostEqual(ends[-1]['executed_beats'], 16, delta=0.6)
        self.assertEqual(ends[-1]['verification'], 'mismatch')
        self.assertFalse(ends[-1]['fade_reasons'])

    def test_entire_chain_has_zero_evidence_triggered_short_handoffs(self):
        transport = Transport(self.clock)
        for index in range(35):
            with self.subTest(transition=index + 1):
                outgoing, incoming = (1, 2) if index % 2 == 0 else (2, 1)
                transport.positions[incoming] = 0  # Simulated preload of next track.
                transport.writes.clear()
                transition = event(from_deck=outgoing, to_deck=incoming)
                transition['transition_beats'] = 32
                transition['backbeat'].update(fade_policy_version=2, recovery_beats=8, fallback_beats=2)
                # Alternate unavailable evidence, confirmed mismatch and lost
                # verification. Old recovery metadata is deliberately retained.
                mode = index % 3
                def observe(stage):
                    return .18 if mode == 1 else (0.0 if mode == 2 and stage == 'before_fader' else None)
                with patch.object(backbeat.Guard, 'observe', side_effect=observe):
                    _, writes, _, log = self.play(transition, transport=transport)
                self.assert_gradual(writes, 16)
                self.assertFalse(any(c.args[0] == 'crossfade_recovery' for c in log.call_args_list))
                transport.positions[outgoing] = 0

    def test_compatible_long_blends_keep_32_and_64_beats(self):
        for beats in (32, 64):
            with self.subTest(beats=beats):
                transition = event()
                transition['transition_beats'] = beats
                _, writes, _, _ = self.play(transition)
                self.assert_gradual(writes, beats / 2)

    def test_actual_end_of_audio_limits_fade_and_is_reported(self):
        transport = Transport(self.clock)
        transport.positions[1] = 197.0
        _, writes, output, log = self.play(event(incoming=pattern(confidence=.1)), transport=transport)
        self.assertLess(writes[-1][1] - writes[0][1], 3)
        self.assertIn('remaining audio', output)
        self.assertTrue(any(c.args[0] == 'transition_end' and c.kwargs['executed_seconds'] < 3
                            for c in log.call_args_list))

    def test_intentional_hard_cut_is_not_forced_into_slow_blend(self):
        transition = event()
        transition['moves'] = ['hard_cut']
        transition.pop('backbeat')
        with patch('hands.run_mix_plan._wait_for_anchor_or_continue', return_value=True):
            _, writes, output, _ = self.play(transition)
        self.assertEqual(writes[-1][1] - writes[0][1], 0)
        self.assertIn('on-beat cut', output)


class FadePolicyTests(unittest.TestCase):
    def test_old_two_and_eight_beat_previews_are_rejected(self):
        from brain.preview_transitions import transition_specs
        from tests.test_backbeat import BuildEvidenceTests
        plan = BuildEvidenceTests().plan()
        rhythm.prepare_plan(plan, analyze=lambda *a, **k: pattern())
        transition = next(e for e in plan['events'] if e['op'] == 'transition')
        for version in (None, 1, 2):
            with self.subTest(version=version):
                transition['backbeat'].pop('fade_policy_version', None)
                if version is not None:
                    transition['backbeat']['fade_policy_version'] = version
                transition['backbeat']['preview']['overlap_seconds'] = 1
                with self.assertRaisesRegex(ValueError, 'retired short-handoff'):
                    transition_specs(plan['events'], {t['track_id']: t for t in plan['tracks']})

    def test_only_audio_limits_shorten_shared_fade_policy(self):
        self.assertEqual(rhythm.blend_seconds(40, 94), 40)
        self.assertEqual(rhythm.blend_seconds(2, 94), 2)
        self.assertEqual(rhythm.blend_seconds(40, 94, remaining_seconds=1.3), 1.3)

    def test_confident_incompatibility_does_not_shorten_build_preview(self):
        from tests.test_backbeat import BuildEvidenceTests
        plan = BuildEvidenceTests().plan()
        with patch('brain.rhythm.alignment', return_value={
                'status': 'incompatible', 'reason': 'conflicting local cadence',
                'delay_seconds': 0, 'cycle_seconds': 1}):
            rhythm.prepare_plan(plan, analyze=lambda *a, **k: pattern())
        for transition in (e for e in plan['events'] if e['op'] == 'transition'):
            self.assertEqual(transition['backbeat']['verification'], 'mismatch')
            self.assertEqual(transition['backbeat']['preview']['overlap_seconds'], 8)
            self.assertEqual(transition['backbeat']['automatic_short_handoffs'], 0)

    def test_retiming_never_extends_remaining_fade_or_reverses_direction(self):
        fade = backbeat.FadeEnvelope(0, 20)
        previous = fade.progress(18)
        fade.shorten(18, 8)
        self.assertEqual(fade.end_at, 20)
        fade.shorten(18, 1)
        self.assertEqual(fade.progress(18), previous)
        self.assertEqual(fade.progress(19), 1)


if __name__ == '__main__':
    unittest.main()
