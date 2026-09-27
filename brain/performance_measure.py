"""Measure and verify a same-beat live performance from the original audio.

Read-only on originals; JSON evidence goes outside the checkout. Every source
is measured against ONE reference template (ideally a clean instrumental of the
shared beat), so each ``zero`` names the same musical point. Numbers are
evidence for placement and review, never a listening verdict.

Spec JSON (``--spec``)::

    {"reference": "inst", "tempo_bpm": 91.68,
     "sources": {"inst":  {"track_id": "/path/instrumental.mp3", "bpm": 94.66, "spans": [[20, 180]]},
                 "album": {"track_id": "/path/album.mp3", "bpm": 91.67, "spans": [[4, 203.5], [224.5, 300]]}}}

``bpm`` is a guess (the fit searches +/-1.2); ``spans`` are musical source
windows that avoid excluded regions, skits and DJ talk.

Subcommands (see docs/SAME_BEAT_CONTINUOUS_MIX.md for the workflow):
  fit     tempo + pattern zero per source, per-window drift (ms), backbeat
          one-beat margin, band shares and loudness -> measure.json
  pitch   tuning residual (cents) after turntable rate to the mix tempo
  lags    independent check: lag 0 must beat +/-1 (off by one); also reports bar alignment
  vocals  bar-by-bar vocal presence map (voice band over the beat's own ratio)
  hooks   where a query region's vocal (e.g. a chorus) recurs in every source
  align   fine vocal offset between two hook copies on the mix clock
  verify  rendered mix: snare/hat-band (5-10 kHz) lock per window and per clip
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

import numpy as np
from scipy import ndimage, signal

from brain.audio_patterns import FEATURE_RATE, envelopes, features, fold, match, template

BINS = 512
CHECKOUT = Path(__file__).resolve().parents[1]


def decode(path, sample_rate, start=None, seconds=None):
    command = ['ffmpeg', '-v', 'error', '-nostdin']
    if start is not None:
        command += ['-ss', str(start)]
    if seconds is not None:
        command += ['-t', str(seconds)]
    command += ['-i', str(path), '-ac', '1', '-ar', str(sample_rate), '-f', 'f32le', '-']
    return np.frombuffer(subprocess.check_output(command), dtype='<f4')


def loudness_lufs(path, a, b):
    """Integrated loudness of a source window (ffmpeg ebur128)."""
    out = subprocess.run(['ffmpeg', '-nostdin', '-ss', str(a), '-t', str(b - a), '-i', str(path),
                          '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    return float(re.findall(r'I:\s+(-?[\d.]+) LUFS', out)[-1])


def _spans_features(env, spans):
    end = len(env['bass_onset']) / FEATURE_RATE - 0.1
    parts = [features(env, a, min(b, end)) for a, b in spans]
    return np.concatenate([t for t, _ in parts]), np.concatenate([c for _, c in parts], axis=1)


def _xcorr(a, b):
    return np.fft.irfft(np.fft.rfft(a) * np.conj(np.fft.rfft(b)), n=len(a))


def refine_zero(t, c, ref, bpm):
    """Pattern zero with sub-bin (parabolic) peak interpolation; ``match``
    alone quantizes to 1/512 of the pattern (~10 ms at 92 BPM)."""
    cc = sum(_xcorr(f, r) for f, r in zip(fold(t, c, bpm, 0.0, bins=BINS), ref))
    k = int(np.argmax(cc))
    y0, y1, y2 = cc[k - 1], cc[k], cc[(k + 1) % BINS]
    den = y0 - 2 * y1 + y2
    frac = 0.5 * (y0 - y2) / den if den else 0.0
    return ((k + frac) / BINS * 8 * 60 / bpm) % (8 * 60 / bpm)


def sharpest_tempo(t, c, guess, span=1.5):
    """Tempo whose 8-beat fold is sharpest (a wrong tempo smears the pattern).

    Independent of any template, so a rough guess cannot bias the reference."""
    def score(bpm):
        return float(sum(np.var(f) for f in fold(t, c, bpm, 0.0, bins=BINS)))
    coarse = np.linspace(guess - span, guess + span, 601)
    best = max(coarse, key=score)
    step = coarse[1] - coarse[0]
    return float(max(np.linspace(best - step, best + step, 41), key=score))


def reference_template(spec):
    ref = spec['sources'][spec['reference']]
    env = envelopes(ref['track_id'])
    t, c = features(env, *ref['spans'][0])
    bpm = sharpest_tempo(t, c, float(ref['bpm']))
    first = match(t, c, template(t, c, bpm, 0.0, bins=BINS), bpm, span=0.02)
    return template(t, c, first['bpm'], first['pattern_zero_seconds'], bins=BINS), first['bpm'], env


def fit(spec, window=16.0, hop=8.0):
    """Per source: bpm, zero, correlations, per-window residual offset/score/backbeat margin."""
    ref, _, ref_env = reference_template(spec)
    beat_bins = BINS // 8
    out = {}
    for name, s in spec['sources'].items():
        env = ref_env if name == spec['reference'] else envelopes(s['track_id'])
        t, c = _spans_features(env, s['spans'])
        found = match(t, c, ref, float(s['bpm']), span=1.2)
        bpm = found['bpm']
        zero = refine_zero(t, c, ref, bpm)
        windows = []
        for a, b in s['spans']:
            at = a
            while at + window <= b:
                wt, wc = features(env, at, at + window)
                f = fold(wt, wc, bpm, zero, bins=BINS)
                cc = sum(_xcorr(x, y) for x, y in zip(f, ref))
                k = int(np.argmax(cc))
                y0, y1, y2 = cc[k - 1], cc[k], cc[(k + 1) % BINS]
                den = y0 - 2 * y1 + y2
                pos = ((k + (0.5 * (y0 - y2) / den if den else 0) + BINS / 2) % BINS) - BINS / 2
                bb = _xcorr(f[1], ref[1])
                margin = (bb[k] - max(bb[(k + beat_bins) % BINS], bb[(k - beat_bins) % BINS])) / BINS
                windows.append({'t': round(at + window / 2, 2), 'offset_ms': round(pos / BINS * 8 * 60 / bpm * 1000, 1),
                                'score': round(float(y1) / BINS, 3), 'backbeat_margin': round(float(margin), 3)})
                at += hop
        x = decode(s['track_id'], 11025)
        freqs, power = signal.welch(x, fs=11025, nperseg=8192)
        total = power[(freqs > 30) & (freqs < 5000)].sum()
        a, b = s['spans'][0]
        out[name] = {'track_id': s['track_id'], 'spans': s['spans'], 'bpm': bpm, 'zero': zero,
                     'correlation_bass_backbeat': found['correlation_bass_backbeat'], 'windows': windows,
                     'sub_40_100_share': float(power[(freqs >= 40) & (freqs < 100)].sum() / total),
                     'low_100_250_share': float(power[(freqs >= 100) & (freqs < 250)].sum() / total),
                     'lufs': loudness_lufs(s['track_id'], a, min(b, a + 180))}
    return out


def drift_summary(measure):
    rows = {}
    for name, v in measure.items():
        offs = np.array([w['offset_ms'] for w in v['windows'] if w['score'] > 0.15])
        rows[name] = {'bpm': round(v['bpm'], 4), 'zero': round(v['zero'], 4),
                      'drift_ms_p5_p95': [round(float(np.percentile(offs, q)), 1) for q in (5, 95)] if len(offs) else None,
                      'jumps_over_100ms': [w['t'] for w in v['windows'] if abs(w['offset_ms']) > 100],
                      'backbeat_margin_median': round(float(np.median([w['backbeat_margin'] for w in v['windows']])), 3)
                      if v['windows'] else None}
    return rows


def pitch(spec, measure, anchor=None, seconds=80.0):
    """Cents each source sits from ``anchor`` after rate = tempo / bpm (keylock off)."""
    tempo, sr = float(spec['tempo_bpm']), 22050
    grid = np.arange(np.log2(40), np.log2(1200), 1 / 1200)
    anchor = anchor or next(n for n in spec['sources'] if n != spec['reference'])
    names = [anchor] + [n for n in spec['sources'] if n != anchor]
    out, ref = {}, None
    for name in names:
        s, v = spec['sources'][name], measure[name]
        a = s['spans'][0][0]
        f, p = signal.welch(decode(s['track_id'], sr, a, seconds), fs=sr, nperseg=1 << 16)
        rate = tempo / v['bpm']
        spec_ = np.interp(grid, np.log2(f[1:] * rate), np.log(p[1:] + 1e-14))
        spec_ -= signal.medfilt(spec_, 301)
        if ref is None:
            ref = spec_
        cc = [np.dot(ref[200 + d:len(ref) - 200 + d], spec_[200:len(spec_) - 200]) for d in range(-150, 151)]
        out[name] = {'rate': rate, 'rate_cents': round(1200 * float(np.log2(rate)), 1),
                     'residual_cents': int(np.argmax(cc)) - 150}
    return out


def _mapped(env, key, bpm, zero, a, b, tempo, fs=400.0):
    rate = tempo / bpm
    src = np.arange(len(env[key])) / FEATURE_RATE
    grid = np.arange((a - zero) / rate, (b - zero) / rate, 1 / fs)
    return grid, np.interp(grid, (src - zero) / rate, env[key])


def lags(spec, measure):
    """Onset cross-correlation vs the reference at whole-beat lags on one 8-beat cycle."""
    tempo = float(spec['tempo_bpm']); beat = 60 / tempo; fs = 400.0
    period = 8 * beat; n = int(period * fs)
    ref_name = spec['reference']
    ref_env = envelopes(spec['sources'][ref_name]['track_id'])

    def cycle(grid, vals):
        idx = ((grid % period) * fs).astype(int) % n
        s = np.bincount(idx, vals, n) / np.maximum(np.bincount(idx, None, n), 1)
        return (s - s.mean()) / (s.std() + 1e-12)
    out = {}
    for name, s in spec['sources'].items():
        if name == ref_name:
            continue
        env = envelopes(s['track_id']); v, r = measure[name], measure[ref_name]
        row = {}
        for key in ('bass_onset', 'backbeat_onset'):
            a = cycle(*_mapped(env, key, v['bpm'], v['zero'], *s['spans'][0], tempo))
            b = cycle(*_mapped(ref_env, key, r['bpm'], r['zero'], *spec['sources'][ref_name]['spans'][0], tempo))
            cc = _xcorr(a, b) / n
            at = lambda k: round(float(cc[int(round(k * beat * fs)) % n]), 3)
            row[key] = {f'{k:+d}' if k else '0': at(k) for k in (0, 1, -1, 2, 4)}
            # Odd shifts put kick on snare (one count off); even shifts keep 2-and-4.
            row[key]['backbeat_ok'] = row[key]['0'] > max(row[key]['+1'], row[key]['-1'])
            row[key]['bar_aligned'] = row[key]['0'] >= max(row[key]['+2'], row[key]['+4'])
        out[name] = row
    return out


def _band_power(x, sr, lo, hi):
    return signal.sosfilt(signal.butter(4, [lo, hi], btype='bandpass', fs=sr, output='sos'), x) ** 2


def vocals(spec, measure):
    """One char per bar: '#' strong voice, '+' some, '.' beat only, '_' beat drop."""
    sr = 11025
    ref = spec['sources'][spec['reference']]
    maps = {}

    def bars(name, x):
        v = measure[name]; bar = 4 * 60 / v['bpm']; voice, bass = _band_power(x, sr, 300, 3000), _band_power(x, sr, 40, 150)
        rows, t = [], v['zero'] % bar
        while t + bar < len(x) / sr:
            a, b = int(t * sr), int((t + bar) * sr)
            rows.append((t, 10 * np.log10(voice[a:b].mean() + 1e-12), 10 * np.log10(bass[a:b].mean() + 1e-12)))
            t += bar
        return rows
    inst = bars(spec['reference'], decode(ref['track_id'], sr))
    base = float(np.median([vo - ba for _, vo, ba in inst[4:36]]))
    for name, s in spec['sources'].items():
        rows = bars(name, decode(s['track_id'], sr))
        med = float(np.median([ba for _, _, ba in rows]))
        maps[name] = [{'t': round(t, 2), 'c': '_' if ba < med - 12 else '#' if (vo - ba) - base > 6 else '+' if (vo - ba) - base > 3 else '.'}
                      for t, vo, ba in rows]
    return maps


def _bar_features(name, x, measure, sr=11025):
    v = measure[name]; bar = 4 * 60 / v['bpm']
    f, t, z = signal.stft(x, fs=sr, nperseg=1024, noverlap=512)
    power = np.abs(z) ** 2
    edges = np.geomspace(250, 4000, 25)
    log_bands = np.log(np.array([power[(f >= a) & (f < b)].sum(0) for a, b in zip(edges[:-1], edges[1:])]) + 1e-9)
    starts = np.arange(v['zero'] % bar, len(x) / sr - bar, bar)
    rows = [np.concatenate([q.mean(1) for q in np.array_split(log_bands[:, (t >= s) & (t < s + bar)], 4, axis=1)])
            for s in starts]
    return starts, np.array(rows)


def hooks(spec, measure, query, query_start, bars=8, top=4):
    """Best matches (score, source seconds) of the query's vocal bars in every source."""
    feats = {n: _bar_features(n, decode(s['track_id'], 11025), measure) for n, s in spec['sources'].items()}
    ref_starts, ref_f = feats[spec['reference']]
    beat_only = np.median(ref_f[8:60], axis=0)
    feats = {n: (s, f - beat_only) for n, (s, f) in feats.items()}
    starts, f = feats[query]
    q0 = int(np.argmin(abs(starts - query_start)))
    q = f[q0:q0 + bars]; q = (q - q.mean()) / q.std()
    out = {}
    for name, (s, f) in feats.items():
        if name == spec['reference']:
            continue
        scores = sorted(((float((((w := f[i:i + bars]) - w.mean()) / (w.std() + 1e-9) * q).mean()), float(s[i]))
                         for i in range(len(f) - bars)), reverse=True)
        best = []
        for sc, t in scores:
            if all(abs(t - u) > 12 for _, u in best):
                best.append((round(sc, 3), round(t, 2)))
            if len(best) == top:
                break
        out[name] = best
    return out


def align(spec, measure, a_name, a_start, b_name, b_start, seconds=21.0):
    """Fine vocal offset of B vs A on the common beat frame (+ms: B later).

    A true same-take double shows a high correlation at ~0 ms; a different
    vocal shows a low correlation or an inconsistent offset."""
    tempo, sr, hop = float(spec['tempo_bpm']), 11025, 22
    rate_hz = sr / hop

    def env(name, a):
        x = decode(spec['sources'][name]['track_id'], sr, a, seconds)
        y = signal.sosfilt(signal.butter(4, [300, 3000], btype='bandpass', fs=sr, output='sos'), x)
        e = np.log(np.sqrt(np.mean(y[:len(y) // hop * hop].reshape(-1, hop) ** 2, axis=1)) + 1e-6)
        d = np.maximum(0, np.diff(ndimage.uniform_filter1d(e, 3), prepend=e[0]))
        v = measure[name]
        beats = (a + np.arange(len(d)) / rate_hz - v['zero']) * v['bpm'] / 60
        grid = np.arange(np.ceil(beats[0] * 100) / 100, beats[-1], 0.01)
        return grid, np.interp(grid, beats, d)
    ga, ea = env(a_name, a_start); gb, eb = env(b_name, b_start)
    best = (-2.0, 0, 0)
    for shift in range(-40, 41):
        for lag in range(-200, 201, 2):
            off = shift * 8 + lag / 100
            lo, hi = max(ga[0], gb[0] - off), min(ga[-1], gb[-1] - off)
            if hi - lo < 16:
                continue
            g = np.arange(lo, hi, 0.01)
            corr = np.corrcoef(np.interp(g, ga, ea), np.interp(g + off, gb, eb))[0, 1]
            if corr > best[0]:
                best = (float(corr), shift, lag)
    corr, shift, lag = best
    return {'correlation': round(corr, 3), 'pattern_shift': shift, 'beats': lag / 100,
            'offset_ms': round(lag / 100 * 60 / tempo * 1000, 1), 'same_take_likely': corr >= 0.5 and abs(lag) <= 2}


def verify(performance, measure, reference, render, window_beats=16):
    """Snare/hat-band pattern of a rendered mix vs the reference, per window.

    Vocals rarely repeat periodically in 5-10 kHz, so the 8-beat fold isolates
    the drum loop. Each window reports correlation at lag 0, margin over +/-1
    beat (one count off), margin over a 4-beat bar swap, and the peak offset."""
    sr, hop = 22050, 110
    rate_hz = sr / hop
    tempo, zero = performance['tempo_bpm'], performance['global_pattern_zero_seconds']

    def onset(path):
        x = decode(path, sr)
        y = signal.sosfilt(signal.butter(4, [5000, 10000], btype='bandpass', fs=sr, output='sos'), x)
        e = np.sqrt(np.mean(y[:len(y) // hop * hop].reshape(-1, hop) ** 2, axis=1))
        return np.maximum(0, e - ndimage.uniform_filter1d(e, 9))

    def folded(e, a, b, bpm, z):
        lo, hi = int(a * rate_hz), int(b * rate_hz)
        t = np.arange(lo, hi) / rate_hz
        vals = np.minimum(e[lo:hi], np.percentile(e[lo:hi], 97))
        idx = np.floor(((t - z) * bpm / 60 % 8) / 8 * BINS).astype(int) % BINS
        f = np.bincount(idx, vals, BINS) / np.maximum(np.bincount(idx, None, BINS), 1)
        f = ndimage.gaussian_filter1d(f, 1, mode='wrap')
        return (f - f.mean()) / (f.std() + 1e-12)
    r = measure[reference]
    ref = folded(onset(r['track_id']), *r['spans'][0], r['bpm'], r['zero'])
    e = onset(render)
    beat = BINS // 8; win = window_beats * 60 / tempo; rows = []
    at = 1.0
    while at + win < len(e) / rate_hz - 1:
        cc = _xcorr(folded(e, at, at + win, tempo, zero), ref) / BINS
        k = int(np.argmax(cc))
        y0, y1, y2 = cc[k - 1], cc[k], cc[(k + 1) % BINS]
        frac = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2) if (y0 - 2 * y1 + y2) else 0.0
        rows.append({'t': round(at, 2), 'corr0': round(float(cc[0]), 3),
                     'margin_one_beat': round(float(cc[0] - max(cc[beat], cc[-beat])), 3),
                     'margin_bar_swap': round(float(cc[0] - cc[4 * beat]), 3),
                     'offset_ms': round(((k + frac + BINS / 2) % BINS - BINS / 2) / BINS * 8 * 60 / tempo * 1000, 1)})
        at += win / 2
    sections = {}
    for c in performance['clips']:
        inside = [x for x in rows if c['start'] <= x['t'] and x['t'] + win <= c['start'] + c['length']]
        if inside:
            sections[c['id']] = {'windows': len(inside),
                                 'corr0_median': round(float(np.median([x['corr0'] for x in inside])), 3),
                                 'margin_one_beat_min': min(x['margin_one_beat'] for x in inside),
                                 'offset_ms_median': float(np.median([x['offset_ms'] for x in inside]))}
    return {'windows': rows, 'by_clip': sections,
            'all_lock_at_zero': all(x['margin_one_beat'] > 0 for x in rows),
            'offset_ms_median': float(np.median([x['offset_ms'] for x in rows])) if rows else None}


def _out(path):
    out = Path(path).expanduser().resolve()
    if out.is_relative_to(CHECKOUT):
        raise ValueError('Measurement evidence belongs outside the checkout')
    out.parent.mkdir(parents=True, exist_ok=True)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('fit', 'pitch', 'lags', 'vocals', 'hooks', 'align', 'verify'):
        p = sub.add_parser(name)
        p.add_argument('--spec', required=name != 'verify')
        p.add_argument('--out', required=True)
        if name != 'fit':
            p.add_argument('--measure', required=True, help='JSON written by fit')
    sub.choices['pitch'].add_argument('--anchor', help='source the others are tuned against (default: first non-reference)')
    sub.choices['hooks'].add_argument('--query', required=True, help='NAME:SECONDS, e.g. album:224.3')
    sub.choices['hooks'].add_argument('--bars', type=int, default=8)
    sub.choices['align'].add_argument('--a', required=True, help='NAME:SECONDS'); sub.choices['align'].add_argument('--b', required=True)
    sub.choices['verify'].add_argument('--plan', required=True, help='mix_plan.json with a performance')
    sub.choices['verify'].add_argument('--render', required=True, help='rendered mix (hands.offline_mix)')
    sub.choices['verify'].add_argument('--reference', required=True, help='measure name of the clean instrumental')
    args = parser.parse_args(argv)
    out = _out(args.out)
    spec = json.loads(Path(args.spec).read_text()) if args.spec else None
    measure = json.loads(Path(args.measure).read_text()) if getattr(args, 'measure', None) else None
    if args.command == 'fit':
        result = fit(spec)
        print(json.dumps(drift_summary(result), indent=1))
    elif args.command == 'pitch':
        result = pitch(spec, measure, args.anchor)
    elif args.command == 'lags':
        result = lags(spec, measure)
    elif args.command == 'vocals':
        result = vocals(spec, measure)
        for name, row in result.items():
            text = ''.join(x['c'] for x in row)
            print(f'\n{name}')
            for i in range(0, len(text), 16):
                print(f"  {row[i]['t']:7.2f}s  {text[i:i + 16]}")
    elif args.command == 'hooks':
        name, at = args.query.rsplit(':', 1)
        result = hooks(spec, measure, name, float(at), bars=args.bars)
    elif args.command == 'align':
        (an, at), (bn, bt) = (x.rsplit(':', 1) for x in (args.a, args.b))
        result = align(spec, measure, an, float(at), bn, float(bt))
    else:
        plan = json.loads(Path(args.plan).read_text())
        result = verify(plan.get('performance', plan), measure, args.reference, args.render)
        print(json.dumps({k: v for k, v in result.items() if k != 'windows'}, indent=1))
    if args.command in ('pitch', 'lags', 'hooks', 'align'):
        print(json.dumps(result, indent=1))
    out.write_text(json.dumps(result, indent=1))


if __name__ == '__main__':
    main()
