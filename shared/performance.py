"""Portable musical timeline and deterministic native-source live compiler.

No audio libraries, device calls, or writes. Seconds are explicit: source
positions are before rate conversion, clip positions are on the mix clock.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path

SCHEMA_VERSION = 1
LIVE_MODE = 'live_source_tracks'


def fingerprint(performance: dict) -> str:
    return hashlib.sha256(json.dumps(performance, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def smooth(value: float) -> float:
    value = min(1.0, max(0.0, value))
    return value * value * (3 - 2 * value)


def envelope(clip: dict, elapsed: float) -> float:
    if elapsed < 0 or elapsed >= clip['length']:
        return 0.0
    incoming = smooth(elapsed / clip['fade_in']) if clip['fade_in'] else 1.0
    outgoing = smooth((clip['length'] - elapsed) / clip['fade_out']) if clip['fade_out'] else 1.0
    return incoming * outgoing


def duration(performance: dict) -> float:
    return max(c['start'] + c['length'] for c in performance['clips'])


def _number(value, label, minimum=0.0, maximum=float('inf')) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f'{label}: invalid number {value!r}')
    return float(value)


def validate(performance: dict, limits: dict | None = None) -> None:
    if performance.get('schema_version') != SCHEMA_VERSION:
        raise ValueError('Unsupported performance schema version')
    _number(performance['tempo_bpm'], 'tempo', 20, 400)
    if performance['sample_rate'] not in (44100, 48000):
        raise ValueError('sample_rate must be 44100 or 48000')
    _number(performance['global_pattern_zero_seconds'], 'pattern zero', -1000, 1000)
    pattern = _number(performance.get('pattern_beats', 8), 'pattern beats', 1, 64)
    clips = performance.get('clips', [])
    if not clips or len({c['id'] for c in clips}) != len(clips):
        raise ValueError('Performance needs unique clip IDs')
    boundaries = performance.get('source_limits', {})
    def region(tid, start, end):
        _number(start, 'source start'); _number(end, 'source end')
        if end <= start: raise ValueError('Empty or reversed source span')
        for rule in (boundaries.get(tid, {}), (limits or {}).get(tid, {})):
            if start < rule.get('min', 0) - 1e-9 or end > rule.get('max', float('inf')) + 1e-9:
                raise ValueError(f'{tid}: source span violates mandatory boundary')
            for a, b in rule.get('exclude', []):
                if start < b and end > a:
                    raise ValueError(f'{tid}: source span overlaps excluded region')
    for c in clips:
        if not isinstance(c['track_id'], str) or not c['track_id']:
            raise ValueError('Missing source identity')
        for key in ('start', 'length', 'fade_in', 'fade_out'):
            _number(c[key], key)
        if c['length'] <= 0 or max(c['fade_in'], c['fade_out']) > c['length']:
            raise ValueError('Invalid clip duration/envelope')
        _number(c['rate'], 'playback rate', .25, 4)
        _number(c['gain_db'], 'gain', -90, 20*math.log10(4))
        _number(c['zero'], 'pattern anchor', -86400, 86400)
        _number(c.get('low_subtract', 0), 'low subtraction', 0, 1)
        if len(c.get('live_eq', [1,1,1])) != 3:
            raise ValueError('live_eq requires low/mid/high gains')
        for gain in c.get('live_eq', [1,1,1]): _number(gain, 'live EQ gain', 0, 4)
        phase=(c['start']+c['zero']-performance['global_pattern_zero_seconds'])*performance['tempo_bpm']/60 % pattern
        if min(phase, pattern-phase) > 1e-5:
            raise ValueError(f"{c['id']}: backbeat/pattern phase mismatch")
        if not c['segments'] or c['segments'][0]['local_start'] != 0:
            raise ValueError('Missing initial source segment')
        end_at = 0.0
        for s in c['segments']:
            region(c['track_id'], s['source_start'], s['source_end'])
            _number(s['local_start'], 'segment placement')
            end=s['local_start']+(s['source_end']-s['source_start'])/c['rate']
            if s['local_start'] < end_at-1e-5 or end > c['length']+2/performance['sample_rate']:
                raise ValueError('Segments overlap or exceed clip duration')
            skipped=(s['local_start']-(s['source_start']-c['segments'][0]['source_start'])/c['rate'])*performance['tempo_bpm']/60 % pattern
            if min(skipped,pattern-skipped)>1e-5:
                raise ValueError('Source skip changes the backbeat/pattern phase')
            end_at=end
        for g in c.get('skip_fills', []):
            if not 0 <= g['start'] <= g['end'] <= c['length']:
                raise ValueError('Invalid instrumental gap fill')
            edge=120/performance['tempo_bpm']
            if g['start'] < edge or g['end']+edge > c['length']:
                raise ValueError('Source skip lacks room for its instrumental cover')
        support=c.get('support')
        if support:
            for key in ('takeover_seconds','transition_seconds','low_gain','high_gain','pulse_gain','pulse_width_seconds'):
                _number(support[key], key)
            if support['transition_seconds'] <= 0 or support['pulse_width_seconds'] <= 0:
                raise ValueError('Invalid support envelope')
            if support['takeover_seconds']+support['transition_seconds'] > end_at+1e-5:
                raise ValueError('Instrumental source runs out before loop takeover')
            for anchor in support['pulse_times']: _number(anchor, 'support anchor')
    loop=performance.get('loop')
    if any(c.get('support') or c.get('skip_fills') for c in clips) and not loop:
        raise ValueError('Missing instrumental loop for support/fills')
    if loop:
        region(loop['track_id'],loop['source_start'],loop['source_end'])
        _number(loop['rate'],'loop rate',.25,4)
        _number(loop['gain_db'],'loop gain',-90,20*math.log10(4))
        beats=_number(loop['beats'],'loop beats',1,256)
        seconds=(loop['source_end']-loop['source_start'])/loop['rate']
        if abs(seconds-beats*60/performance['tempo_bpm']) > 2/performance['sample_rate']:
            raise ValueError('Loop length does not match tempo')
        for c in clips:
            if c.get('support') and (c['track_id'] != loop['track_id'] or abs(c['rate']-loop['rate'])>1e-8):
                raise ValueError('Support loop must belong to the same source and rate')
    expanded=live_clips(performance)
    if len({c['id'] for c in expanded}) != len(expanded):
        raise ValueError('Instrumental fill ID collides with a clip')
    # Reserve enough time to preload a replacement; reject rather than clip a live source.
    compile_events(performance, check=False)


def compile_events(performance: dict, *, check=True) -> list[dict]:
    if check: validate(performance)
    free=[-10.0]*4
    events=[]
    for c in sorted(live_clips(performance),key=lambda c:(c['start'],c['id'])):
        choices=[i for i,t in enumerate(free) if t+2.0 <= c['start']]
        if not choices: raise ValueError('Timeline exceeds four decks or leaves no preload window')
        deck=min(choices)+1
        load_at=max(0.0,free[deck-1]+.1)
        free[deck-1]=c['start']+c['length']
        common={'clip_id':c['id'],'deck':deck}
        events.extend([
            {'op':'load_clip','at':load_at,'source_track_id':c['track_id'],**common},
            {'op':'start_clip','at':c['start'],**common},
            {'op':'gain_envelope','at':c['start'],'fade_in':c['fade_in'],'fade_out':c['fade_out'],'length':c['length'],**common},
            {'op':'stop_clip','at':c['start']+c['length'],**common}])
        if c.get('support') and c['support']['takeover_seconds']>0:
            events.append({'op':'loop_clip','at':c['start']+c['support']['takeover_seconds'],'source_start':performance['loop']['source_start'],'source_end':performance['loop']['source_end'],**common})
        for seg in c['segments'][1:]:
            events.append({'op':'seek_clip','at':c['start']+seg['local_start'],'source_seconds':seg['source_start'],**common})
    priority={'stop_clip':0,'load_clip':1,'start_clip':2,'loop_clip':3,'seek_clip':3,'gain_envelope':4}
    return sorted(events,key=lambda e:(e['at'],priority[e['op']],e['deck']))


def validate_artifact(plan: dict, limits: dict | None = None) -> dict:
    if plan.get('execution_mode') != LIVE_MODE:
        raise ValueError('A performance must execute original live sources')
    p=plan['performance'];validate(p,limits)
    if plan.get('performance_sha256') != fingerprint(p):
        raise ValueError('Performance changed: compile the live plan again')
    if plan.get('events') != compile_events(p):
        raise ValueError('Live events do not match the musical plan; compile again')
    return p


def source_paths(performance: dict, source_map: dict | None = None) -> dict[str, Path]:
    ids={c['track_id'] for c in performance['clips']}
    if performance.get('loop'): ids.add(performance['loop']['track_id'])
    result={tid:Path((source_map or {}).get(tid,tid)).expanduser().resolve() for tid in ids}
    for tid,path in result.items():
        if not path.is_file(): raise ValueError(f'Missing source {tid}: {path}; supply a source map')
    return result


def live_clips(p):
    """Expand instrumental gap covers into real independent source decks."""
    import copy
    clips=copy.deepcopy(p['clips']);beat=60/p['tempo_bpm']
    for c in p['clips']:
        for i,gap in enumerate(c.get('skip_fills',[])):
            loop=p['loop'];edge=2*beat
            start=c['start']+gap['start']-edge
            length=gap['end']-gap['start']+2*edge
            clips.append({'id':f"{c['id']}-fill-{i}",'track_id':loop['track_id'],
                'artist':'Instrumental','title':'Source-skip cover','start':start,'length':length,
                'rate':loop['rate'],'gain_db':loop['gain_db'],'fade_in':edge,'fade_out':edge,
                'segments':[{'source_start':loop['source_start'],'source_end':loop['source_end'],'local_start':0}],
                'support':{'takeover_seconds':0,'transition_seconds':.001,'low_gain':1,'high_gain':1,'pulse_gain':0,'pulse_width_seconds':1,'pulse_times':[]},'skip_fills':[],'fill':True})
    return clips


def source_state(p,c,local):
    """Return source position and engine loop bounds for a point in the mix."""
    support=c.get('support')
    if support and local>=support['takeover_seconds']:
        l=p['loop'];span=l['source_end']-l['source_start']
        position=l['source_start']+((c['start']+local-p['global_pattern_zero_seconds'])*l['rate'])%span
        return position,l['source_start'],l['source_end'],'loop'
    for i,s in enumerate(c['segments']):
        length=(s['source_end']-s['source_start'])/c['rate']
        if s['local_start']<=local<s['local_start']+length:
            return s['source_start']+(local-s['local_start'])*c['rate'],s['source_start'],s['source_end'],str(i)
    return None


def live_envelope(p,c,local):
    value=envelope(c,local);edge=2*60/p['tempo_bpm']
    for gap in c.get('skip_fills',[]):
        cover=smooth((local-(gap['start']-edge))/edge)*smooth(((gap['end']+edge)-local)/edge)
        value*=1-cover
    return value
