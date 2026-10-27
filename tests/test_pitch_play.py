"""Synthetic pitch-play boundaries and lifecycle; never touches live Mixxx/library."""
import copy
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest
from contextlib import closing, redirect_stdout
from unittest.mock import patch, Mock

from hands import pitch_play as p


def score():
    return dict(deck=3, bpm=120., cue_seconds=10., source_end_seconds=12.,
        duration_seconds=100., sample_rate=44100., prepare_seconds=.1, max_late_seconds=.05,
        notes=[dict(beat=i*2., semitones=v, gate_beats=.5) for i, v in enumerate([0., 1., 2., 0.])])


class Fake:
    def __init__(self):
        self.values = {(g, k): .7 for g, k, _ in p.settings(3)}
        self.values.update({(f'[Channel{d}]', 'play'): 0 for d in range(1, 5)})
        self.values.update({('[Channel3]', 'track_loaded'): 0, ('[Channel3]', 'loop_enabled'): 0,
                            ('[Channel3]', 'duration'): 100, ('[Channel3]', 'track_samplerate'): 44100,
                            ('[Channel3]', 'playposition'): 0, ('[Channel3]', 'loop_start_position'): -1,
                            ('[Channel3]', 'loop_end_position'): -1})
        self.initial = self.values.copy()
        self.writes = []
        self.loads = []
        self.closed = False
        self.broken = False

    def get(self, g, k):
        if self.broken:
            raise ConnectionError('disconnected')
        return self.values.get((g, k), 0)

    def set(self, g, k, v):
        if self.broken:
            raise ConnectionError('disconnected')
        self.writes.append((g, k, v))
        self.values[g, k] = v
        if k == 'eject' and v == 1:
            self.values[g, 'track_loaded'] = 0

    def load(self, d, path, play=False):
        assert play is False
        self.loads.append((d, path))
        self.values[f'[Channel{d}]', 'track_loaded'] = 1

    def close(self):
        self.closed = True


class PitchPlay(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.source = self.root / 'original.wav'
        self.source.write_bytes(b'not decoded by synthetic test')
        self.index = self.root / 'library.sqlite3'
        with closing(sqlite3.connect(self.index)) as db, db:
            db.execute('CREATE TABLE tracks(track_id TEXT, dj_notes TEXT, available INTEGER)')
            db.execute('INSERT INTO tracks VALUES(?,?,1)', (str(self.source), ''))
        self.binary = self.root / 'fake-clawdj'
        self.binary.write_text('synthetic; subprocess is mocked')
        guard = patch.object(p, 'active_runners', return_value=[])
        self.guard = guard.start()
        self.addCleanup(guard.stop)

    def notes(self, text):
        with closing(sqlite3.connect(self.index)) as db, db:
            db.execute('UPDATE tracks SET dj_notes=?', (text,))

    def perform(self, fake, **kw):
        with patch.object(p.subprocess, 'run'):
            return p.perform(self.source, score(), index=self.index, binary=self.binary,
                             api_factory=lambda **_: fake, **kw)

    def assert_restored(self, fake):
        for g, k, _ in p.settings(3):
            self.assertEqual(fake.values[g, k], fake.initial[g, k], (g, k))
        self.assertEqual(fake.values['[Channel3]', 'play'], 0)
        self.assertEqual(fake.values['[Channel3]', 'track_loaded'], 0)
        self.assertEqual(fake.values['[Channel3]', 'loop_enabled'], 0)
        for key in ('playposition', 'loop_start_position', 'loop_end_position'):
            self.assertEqual(fake.values['[Channel3]', key], fake.initial['[Channel3]', key])
        self.assertTrue(fake.closed)

    def test_dry_run_has_no_connection_or_writes_and_is_deterministic(self):
        factory = Mock(side_effect=AssertionError('must not connect'))
        outputs = []
        for _ in range(2):
            out = io.StringIO()
            with redirect_stdout(out):
                p.perform(self.source, score(), index=self.index, api_factory=factory)
            outputs.append(out.getvalue())
        factory.assert_not_called()
        self.assertEqual(outputs[0], outputs[1])
        result = json.loads(outputs[0])
        self.assertEqual(result['mode'], 'dry_run')
        self.assertEqual(result['attacks'][1]['on_seconds'], 1.1)
        self.assertEqual(len(list(self.root.iterdir())), 3)

    def test_math_different_tempos_and_no_accumulated_offsets(self):
        for bpm in [60, 90, 120, 180]:
            s = score(); s['bpm'] = bpm
            a = p.compile_score(s)
            self.assertAlmostEqual(a[1]['on_seconds'], .1+120/bpm)
            self.assertEqual(a[-1]['semitones'], 0)
            self.assertAlmostEqual(a[2]['frequency_ratio'], 2**(2/12))

    def test_invalid_score_before_connect(self):
        for field, value in [('bpm', float('nan')), ('deck', True), ('deck', 5),
                             ('cue_seconds', -1), ('source_end_seconds', 1000),
                             ('prepare_seconds', 0), ('max_late_seconds', float('inf'))]:
            s = score(); s[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                p.perform(self.source, s, api_factory=Mock(side_effect=AssertionError('connect')))
        for change in ['overlap', 'pitch', 'gate', 'boundary', 'count']:
            s = score()
            if change == 'overlap': s['notes'][1]['beat'] = 0
            if change == 'pitch': s['notes'][0]['semitones'] = 4
            if change == 'gate': s['notes'][0]['gate_beats'] = float('nan')
            if change == 'boundary': s['source_end_seconds'] = 10.25
            if change == 'count': s['notes'] = []
            with self.subTest(change=change), self.assertRaises(ValueError): p.compile_score(s)

    def test_current_source_boundaries_and_skips_before_connect(self):
        for note in ['mandatory_end_seconds=11', 'mandatory_start_seconds=11',
                     'mandatory_skip skip_from_seconds=11 skip_to_seconds=13',
                     'mandatory_skip skip_from_seconds=11', 'mandatory_end_seconds=nan',
                     'mandatory_end_seconds=92 mandatory_end_seconds=11', 'mandatory_end_seconds=']:
            self.notes(note)
            with self.subTest(note=note), self.assertRaises(ValueError):
                p.perform(self.source, score(), index=self.index,
                          api_factory=Mock(side_effect=AssertionError('connect')))
        p.validate_region(10, 12, 'mandatory_start_seconds=10 mandatory_end_seconds=12')
        p.validate_region(10, 12, 'mandatory_skip skip_from_seconds=12 skip_to_seconds=13')

    def test_unknown_source_or_missing_index_refuses(self):
        with self.assertRaises(ValueError): p.source_notes(self.source, self.root / 'missing')
        self.assertFalse((self.root / 'missing').exists())
        with closing(sqlite3.connect(self.index)) as db, db: db.execute('DELETE FROM tracks')
        with self.assertRaises(ValueError): self.perform(Fake(), live=True)

    def test_busy_or_nonempty_deck_no_mutations(self):
        for control in [('track_loaded', '[Channel3]'), ('play', '[Channel2]'),
                        ('loop_enabled', '[Channel3]'), ('enabled', '[AutoDJ]')]:
            f = Fake(); f.values[control[1], control[0]] = 1
            with self.assertRaises(ValueError): self.perform(f, live=True)
            self.assertEqual(f.writes, []); self.assertEqual(f.loads, [])
            self.assertTrue(f.closed)

    def test_active_runner_refuses_before_connect(self):
        self.guard.return_value = ['pid synthetic: mix runner']
        factory = Mock(side_effect=AssertionError('must not connect'))
        with patch.object(p.subprocess, 'run'), self.assertRaisesRegex(ValueError, 'runner is active'):
            p.perform(self.source, score(), index=self.index, binary=self.binary,
                      live=True, api_factory=factory)
        factory.assert_not_called()

    def test_snapshot_failure_no_mutations(self):
        f = Fake(); f.values['[Channel3]', 'volume'] = float('nan')
        with self.assertRaises(ValueError): self.perform(f, live=True)
        self.assertEqual(f.writes, [])

    def test_success_original_load_guard_and_restore(self):
        f = Fake(); received = []
        def runner(binary, port, s):
            received.append(s)
            self.assertEqual(f.values['[Channel3]', 'loop_start_position'], 10*44100*2)
            self.assertEqual(f.values['[Channel3]', 'loop_end_position'], 12*44100*2)
            self.assertEqual(f.values['[Channel3]', 'loop_enabled'], 1)
            self.assertEqual(f.values['[Channel3]', 'keylock'], 1)
            self.assertEqual(f.values['[Channel3]', 'rate_ratio'], 1)
        self.perform(f, live=True, runner=runner)
        self.assertEqual(len(received), 1)
        self.assertEqual(f.loads, [(3, str(self.source))])
        self.assert_restored(f)
        self.assertFalse(any('hotcue' in k or k in ['cue_set', 'cue_point'] for _, k, _ in f.writes))
        self.assertEqual(self.source.read_bytes(), b'not decoded by synthetic test')

    def test_error_and_ctrl_c_restore(self):
        for exc in [RuntimeError('scheduler failed'), KeyboardInterrupt()]:
            f = Fake()
            def fail(*_): raise exc
            with self.assertRaises(type(exc)): self.perform(f, live=True, runner=fail)
            self.assert_restored(f)

    def test_source_changes_during_load_refuse_and_cleanup(self):
        f = Fake(); original = f.load
        def load(*a, **kw):
            original(*a, **kw)
            self.source.write_bytes(b'changed')
        f.load = load
        runner = Mock()
        with self.assertRaisesRegex(ValueError, 'Source changed'):
            self.perform(f, live=True, runner=runner)
        runner.assert_not_called(); self.assert_restored(f)

    def test_reconnect_for_disconnect_cleanup(self):
        f = Fake(); recovery = Fake()
        recovery.values = f.values  # same server, separate stream
        def runner(*_):
            f.broken = True
            raise ConnectionError('scheduler disconnect')
        factory = Mock(side_effect=[f, recovery])
        with patch.object(p.subprocess, 'run'), self.assertRaises(ConnectionError):
            p.perform(self.source, score(), index=self.index, binary=self.binary, live=True,
                      api_factory=factory, runner=runner)
        self.assert_restored(recovery)
        self.assertEqual(factory.call_count, 2)

    def test_cleanup_failure_does_not_unmute_unverified_voice(self):
        f = Fake(); f.values['[Channel3]', 'track_loaded'] = 1
        original = f.set
        def no_eject(g, k, v):
            if k == 'eject': raise ConnectionError('eject failed')
            original(g, k, v)
        f.set = no_eject
        with patch.object(p, 'wait_loaded', side_effect=RuntimeError('still loaded')):
            with self.assertRaisesRegex(RuntimeError, 'Cleanup incomplete'):
                p.cleanup(f, '[Channel3]', [('[Channel3]', 'mute', 0)])
        self.assertEqual(f.values['[Channel3]', 'mute'], 1)
        self.assertEqual(f.values['[Channel3]', 'play'], 0)
        self.assertFalse(any(k == 'loop_enabled' for _, k, _ in f.writes))

    def test_current_notes_changed_after_loading_aborts_before_scheduler(self):
        f = Fake(); original = f.load
        def load(*a, **kw):
            original(*a, **kw)
            self.notes('mandatory_end_seconds=11')
        f.load = load
        runner = Mock()
        with self.assertRaisesRegex(ValueError, 'mandatory source boundary'):
            self.perform(f, live=True, runner=runner)
        runner.assert_not_called(); self.assert_restored(f)

    def test_fractional_cue_rounds_inward(self):
        f = Fake(); s = score(); s['cue_seconds'] = 10.000001
        received = []
        with patch.object(p.subprocess, 'run'):
            p.perform(self.source, s, index=self.index, binary=self.binary, live=True,
                      api_factory=lambda **_: f, runner=lambda *a: received.append(a[-1]))
        self.assertGreaterEqual(received[0]['cue_seconds'], s['cue_seconds'])
        self.assert_restored(f)

    def test_child_terminated_and_joined_on_interruption(self):
        child = Mock(); child.communicate.side_effect = KeyboardInterrupt(); child.poll.return_value = None
        with patch.object(p.subprocess, 'Popen', return_value=child), self.assertRaises(KeyboardInterrupt):
            p.child_execute(self.binary, 9995, score())
        child.terminate.assert_called_once(); child.wait.assert_called_once()

    def test_child_killed_if_termination_times_out(self):
        child = Mock(); child.communicate.side_effect = RuntimeError('input failed'); child.poll.return_value = None
        child.wait.side_effect = [subprocess.TimeoutExpired('pitch-play', 3), None]
        with patch.object(p.subprocess, 'Popen', return_value=child), self.assertRaises(RuntimeError):
            p.child_execute(self.binary, 9995, score())
        child.kill.assert_called_once(); self.assertEqual(child.wait.call_count, 2)

    def test_cli_default_is_dry_and_exposes_parameters(self):
        with patch.object(p, 'probe_source', return_value=(100, 44100)), patch.object(p, 'perform') as perform:
            p.main(['--source', str(self.source), '--cue-seconds', '10', '--source-end-seconds', '12'])
        self.assertFalse(perform.call_args.kwargs['live'])
        self.assertEqual([n['semitones'] for n in perform.call_args.args[1]['notes']], [0,0,0,1,2,0])


if __name__ == '__main__': unittest.main()
