"""Placement arithmetic for authoring a same-beat live performance.

Pure math, no audio. Input is the measurement JSON from
``brain.performance_measure fit``: for each named source its measured tempo
(``bpm``) and 8-beat pattern zero (``zero``, source seconds), all fitted
against one reference template, so every ``zero`` names the same musical
point of the shared beat.

The mix clock runs at one ``tempo``. A clip that plays a source at
``rate = tempo / bpm`` (turntable style, keylock off) is phase-correct when
its source pattern zero lands on a mix pattern point; ``aligned_start``
returns only such times, so ``shared.performance.validate`` accepts every clip
built here and the backbeat cannot be one count off by construction.
"""
from __future__ import annotations


class Grid:
    """Common mix clock anchored so ``anchor`` plays source ``anchor_source``
    at mix time ``anchor_mix``."""

    def __init__(self, tempo: float, measure: dict, *, anchor: str, anchor_source: float = 0.0,
                 anchor_mix: float = 0.0, pattern_beats: int = 8):
        self.tempo, self.m, self.pattern_beats = float(tempo), measure, pattern_beats
        self.beat = 60 / self.tempo
        self.pattern = pattern_beats * self.beat
        z = measure[anchor]['zero']
        self.zero = anchor_mix + (z - anchor_source) / self.rate(anchor)

    def rate(self, name: str) -> float:
        return self.tempo / self.m[name]['bpm']

    def pattern_point(self, name: str, k: int) -> float:
        """Source seconds of the k-th pattern start (bar 1 of the 8-beat pattern)."""
        v = self.m[name]
        return v['zero'] + k * self.pattern_beats * 60 / v['bpm']

    def beat_point(self, name: str, k: int) -> float:
        v = self.m[name]
        return v['zero'] + k * 60 / v['bpm']

    def aligned_start(self, name: str, source_start: float, near: float, side: str = 'nearest') -> float:
        """Mix start for a clip entering at ``source_start``, on the shared pattern phase.

        ``side='after'`` returns the earliest aligned time at or after ``near``
        (for re-entries that must not overlap an excluded region)."""
        base = self.zero - (self.m[name]['zero'] - source_start) / self.rate(name)
        n = round((near - base) / self.pattern)
        cands = [base + (n + d) * self.pattern for d in (-1, 0, 1, 2)]
        if side == 'after':
            return min(c for c in cands if c >= near - 1e-6)
        if side != 'nearest':
            raise ValueError("side must be 'nearest' or 'after'")
        return min(cands, key=lambda c: abs(c - near))

    def clip(self, cid: str, name: str, source_start: float, source_end: float, start: float, *,
             fade_in: float, fade_out: float, gain_db: float = 0.0, eq=(1.0, 1.0, 1.0), **extra) -> dict:
        """Single-span clip. ``start`` must come from ``aligned_start`` (or an
        earlier clip's ``mix_time``); ``shared.performance.validate`` rechecks."""
        v, r = self.m[name], self.rate(name)
        return {'id': cid, 'track_id': v['track_id'], 'source_bpm': v['bpm'], 'rate': r,
                'zero': (v['zero'] - source_start) / r, 'start': start,
                'length': (source_end - source_start) / r,
                'segments': [{'source_start': source_start, 'source_end': source_end, 'local_start': 0.0}],
                'skip_fills': [], 'fade_in': fade_in, 'fade_out': fade_out, 'gain_db': gain_db,
                'live_eq': list(eq), **extra}

    @staticmethod
    def mix_time(clip: dict, source_seconds: float) -> float:
        """Mix time at which a single-span clip plays ``source_seconds``."""
        return clip['start'] + (source_seconds - clip['segments'][0]['source_start']) / clip['rate']

    @staticmethod
    def end(clip: dict) -> float:
        return clip['start'] + clip['length']

    def loop(self, name: str, pattern_k: int, *, beats: int = 32, gain_db: float = 0.0) -> dict:
        """Loop region starting on a pattern point; its length is exact at the mix tempo."""
        s0, r = self.pattern_point(name, pattern_k), self.rate(name)
        return {'track_id': self.m[name]['track_id'], 'source_start': s0,
                'source_end': s0 + beats * self.beat * r, 'beats': beats, 'rate': r, 'gain_db': gain_db}

    def bed(self, cid: str, name: str, loop: dict, start: float, end: float, *, support: dict,
            fade_in: float, fade_out: float, gain_db: float | None = None, **extra) -> dict:
        """Support deck looping ``loop`` on the common clock from ``start`` (a
        mix pattern point) to ``end``. ``support`` holds takeover/transition,
        low/mid/high gains and pulses; see docs/SAME_BEAT_CONTINUOUS_MIX.md."""
        offset = (start - self.zero) / self.pattern
        if abs(offset - round(offset)) > 1e-6:
            raise ValueError('A bed must start on a mix pattern point')
        v = self.m[name]
        return {'id': cid, 'track_id': loop['track_id'], 'source_bpm': v['bpm'], 'rate': loop['rate'],
                'zero': (v['zero'] - loop['source_start']) / loop['rate'], 'start': start, 'length': end - start,
                'segments': [{'source_start': loop['source_start'], 'source_end': loop['source_end'], 'local_start': 0.0}],
                'skip_fills': [], 'fade_in': fade_in, 'fade_out': fade_out,
                'gain_db': loop['gain_db'] if gain_db is None else gain_db, 'live_eq': [1.0, 1.0, 1.0],
                'support': {'takeover_seconds': 0.0, 'pulse_gain': 0.0, 'pulse_width_seconds': 2 * self.beat,
                            'pulse_times': [], **support}, **extra}

    def performance(self, clips: list[dict], *, loop: dict | None = None, source_limits: dict | None = None,
                    sample_rate: int = 44100) -> dict:
        p = {'schema_version': 1, 'tempo_bpm': self.tempo, 'sample_rate': sample_rate,
             'pattern_beats': self.pattern_beats, 'global_pattern_zero_seconds': self.zero,
             'clips': clips, 'source_limits': source_limits or {}}
        if loop:
            p['loop'] = loop
        return p
