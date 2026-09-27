"""Same-beat authoring arithmetic and measurement on synthetic drum loops."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from brain.performance_author import Grid
from shared.performance import validate

SR = 22050


def drum_loop(path, bpm, seconds, *, zero=0.0, voice=None):
    """Two-bar kick/snare/hat pattern with a 55 Hz bass on the kicks.

    Kicks on beats 1, 3, 3.5, 5, 7; snare on 2, 4, 6, 8 (the backbeat); hats on
    eighths. ``zero`` is where bar 1 beat 1 of the pattern first falls.
    ``voice`` = list of (start_s, seconds) tone bursts standing in for vocals."""
    import soundfile as sf
    t = np.arange(int(seconds * SR)) / SR
    x = np.zeros_like(t)
    beat = 60 / bpm
    rng = np.random.default_rng(7)
    noise = rng.standard_normal(len(t))
    n = int((seconds - zero) / beat) + 2
    for k in range(-8, n):
        at = zero + k * beat
        pos = k % 8
        for hit, kind in [(at, 'kick' if pos in (0, 2, 4, 6) else 'snare'), (at + beat / 2, 'hat')]:
            if not 0 <= hit < seconds:
                continue
            i = int(hit * SR); seg = slice(i, min(len(t), i + int(0.2 * SR))); tt = t[seg] - hit
            if kind == 'kick':
                x[seg] += np.exp(-tt / 0.08) * np.sin(2 * np.pi * 55 * tt)
            elif kind == 'snare':
                x[seg] += 0.6 * np.exp(-tt / 0.05) * noise[seg]
            else:
                x[seg] += 0.03 * np.exp(-tt / 0.015) * np.diff(noise[seg], prepend=0)
        if pos == 5:  # the "and" of 3 in bar 2 makes the 8-beat pattern two-bar asymmetric
            i = int((at + beat / 2) * SR)
            if 0 <= i < len(t) - SR // 10:
                x[i:i + SR // 10] += 0.8 * np.exp(-t[:SR // 10] / 0.08) * np.sin(2 * np.pi * 55 * t[:SR // 10])
    for start, dur in voice or []:
        seg = (t >= start) & (t < start + dur)
        x[seg] += 0.3 * np.sin(2 * np.pi * 440 * t[seg]) * np.sin(2 * np.pi * 3 * t[seg]) ** 2
    sf.write(path, (0.5 * x / np.max(np.abs(x))).astype('float32'), SR)


class AuthorGridTests(unittest.TestCase):
    def measure(self):
        return {'inst': {'track_id': 'inst.wav', 'bpm': 94.0, 'zero': 0.3},
                'song': {'track_id': 'song.wav', 'bpm': 90.0, 'zero': 1.1}}

    def test_clips_placed_by_the_grid_always_validate(self):
        g = Grid(92.0, self.measure(), anchor='song')
        a = g.clip('song', 'song', 0.0, g.pattern_point('song', 10), 0.0, fade_in=0, fade_out=2)
        loop = g.loop('inst', 2, beats=32)
        bed_at = g.aligned_start('inst', loop['source_start'], g.end(a) - 8)
        bed = g.bed('bed', 'inst', loop, bed_at, bed_at + 60, fade_in=2, fade_out=2,
                    support={'transition_seconds': 4.0, 'low_gain': 1.0, 'high_gain': 0.45, 'mid_gain': 0.6})
        again = g.clip('song-2', 'song', 30.0, 50.0, g.aligned_start('song', 30.0, g.end(a), side='after'),
                       fade_in=1, fade_out=1, eq=(0.4, 1, 1),
                       eq_automation=[{'at': 1.0, 'scale': [1, 1, 1]}, {'at': 3.0, 'scale': [0.5, 1, 1]}])
        validate(g.performance([a, bed, again], loop=loop))
        self.assertGreaterEqual(again['start'], g.end(a) - 1e-9)
        self.assertAlmostEqual((loop['source_end'] - loop['source_start']) / loop['rate'], 32 * g.beat, places=9)

    def test_a_clip_one_beat_late_is_rejected(self):
        g = Grid(92.0, self.measure(), anchor='song')
        a = g.clip('song', 'song', 0.0, 20.0, 0.0, fade_in=0, fade_out=1)
        late = g.clip('late', 'song', 0.0, 20.0, g.aligned_start('song', 0.0, 25.0) + g.beat, fade_in=1, fade_out=1)
        with self.assertRaisesRegex(ValueError, 'backbeat/pattern phase'):
            validate(g.performance([a, late]))

    def test_bed_must_start_on_a_pattern_point(self):
        g = Grid(92.0, self.measure(), anchor='song')
        loop = g.loop('inst', 1)
        with self.assertRaisesRegex(ValueError, 'pattern point'):
            g.bed('bed', 'inst', loop, g.zero + g.beat, g.zero + 40, fade_in=1, fade_out=1,
                  support={'transition_seconds': 1.0, 'low_gain': 1.0, 'high_gain': 0.3})


class MeasureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.TemporaryDirectory()
        d = Path(cls.dir.name)
        drum_loop(d / 'inst.wav', 94.0, 60, zero=0.25)
        drum_loop(d / 'song.wav', 90.0, 60, zero=0.9, voice=[(10, 3), (30, 3)])
        cls.spec = {'reference': 'inst', 'tempo_bpm': 92.0, 'sources': {
            'inst': {'track_id': str(d / 'inst.wav'), 'bpm': 94.3, 'spans': [[2, 58]]},
            'song': {'track_id': str(d / 'song.wav'), 'bpm': 89.6, 'spans': [[2, 58]]}}}
        from brain.performance_measure import fit
        cls.measure = fit(cls.spec)

    @classmethod
    def tearDownClass(cls):
        cls.dir.cleanup()

    def test_fit_recovers_tempo_and_the_shared_pattern_zero(self):
        m = self.measure
        self.assertAlmostEqual(m['inst']['bpm'], 94.0, delta=0.02)
        self.assertAlmostEqual(m['song']['bpm'], 90.0, delta=0.02)
        # Zeros name the SAME point of the shared pattern (the reference's phase),
        # so both sources sit at one pattern phase relative to their true bar 1.
        phase = lambda name, truth, bpm: ((m[name]['zero'] - truth) * bpm / 60) % 8
        diff = abs(phase('song', 0.9, 90.0) - phase('inst', 0.25, 94.0))
        self.assertLess(min(diff, 8 - diff) * 60 / 92.0, 0.012)
        drift = [w['offset_ms'] for w in m['song']['windows']]
        self.assertLess(max(map(abs, drift)), 15)

    def test_lag_zero_beats_wins_over_one_count_off(self):
        from brain.performance_measure import lags
        row = lags(self.spec, self.measure)['song']
        self.assertTrue(row['bass_onset']['backbeat_ok'] and row['backbeat_onset']['backbeat_ok'])
        self.assertTrue(row['bass_onset']['bar_aligned'])

    def test_verify_locks_a_render_built_from_the_grid(self):
        import soundfile as sf
        from brain.performance_measure import verify
        g = Grid(92.0, self.measure, anchor='inst')
        # A "render": the reference beat itself retimed onto the mix clock.
        x, sr = sf.read(self.spec['sources']['inst']['track_id'])
        rate = g.rate('inst')
        t_mix = np.arange(int(50 * sr)) / sr
        y = np.interp(t_mix * rate, np.arange(len(x)) / sr, x)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'render.wav'; sf.write(path, y.astype('float32'), sr)
            p = g.performance([g.clip('inst', 'inst', 0.0, 48.0, 0.0, fade_in=0, fade_out=0)])
            result = verify(p, self.measure, 'inst', str(path))
        self.assertTrue(result['all_lock_at_zero'])
        self.assertLessEqual(abs(result['offset_ms_median']), 11)

    def test_evidence_is_refused_inside_the_checkout(self):
        from brain.performance_measure import CHECKOUT, _out
        with self.assertRaisesRegex(ValueError, 'outside the checkout'):
            _out(CHECKOUT / 'evidence.json')


if __name__ == '__main__':
    unittest.main()
