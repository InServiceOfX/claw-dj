"""Source-time backbeat coordinates, independent of Mixxx grid beat numbering.

A two-beat snare cycle establishes 2/4 parity, not musical count one.
Explicitly measured starts opt in; existing approved recipes stay unchanged.
"""
from __future__ import annotations

import math


def approved_launch_delay(spec: dict) -> int:
    """A heard launch adjustment is distinct from a detected snare phase."""
    approval = spec.get('approved_launch_delay')
    if approval is None:
        return 0
    if (not isinstance(approval, dict) or type(approval.get('beats')) is not int
            or approval['beats'] != 1 or approval.get('author') != 'human'
            or approval.get('approved') is not True
            or not isinstance(approval.get('quote'), str) or not approval['quote'].strip()):
        raise ValueError('one-beat launch delay requires explicit human listening approval')
    return 1


def positive_number(value, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite positive number")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be a finite positive number") from error
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{label} must be a finite positive number")
    return number


def validate_backbeat_start(spec: dict) -> dict:
    if not isinstance(spec, dict) or type(spec.get('version')) is not int or spec['version'] != 1:
        raise ValueError('backbeat_start requires version 1')
    result = {'version': 1}
    for side in ('outgoing', 'incoming'):
        source = spec.get(side)
        if not isinstance(source, dict):
            raise ValueError(f'backbeat_start missing {side}')
        model = dict(source)
        for key in ('grid_bpm', 'real_bpm'):
            model[key] = positive_number(source.get(key), f'{side}.{key}')
        try:
            first = float(source['first_beat_seconds'])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f'{side} measured start needs its exact first grid beat') from error
        if not math.isfinite(first):
            raise ValueError(f'{side} first grid beat must be finite')
        model['first_beat_seconds'] = first
        phase = float(source['snare_phase_seconds'])
        if not math.isfinite(phase) or not 0 <= phase < 120 / model['real_bpm']:
            raise ValueError(f'{side} snare phase must be within one two-beat cycle')
        model['snare_phase_seconds'] = phase
        confidence = float(source.get('confidence', 0))
        if not math.isfinite(confidence) or not .2 <= confidence <= 1:
            raise ValueError(f'{side} has no usable measured backbeat')
        result[side] = model
    cue = float(spec['cue_seconds'])
    if not math.isfinite(cue) or cue < 0:
        raise ValueError('backbeat_start cue must be finite and nonnegative')
    tolerance = positive_number(spec.get('tolerance_ms', 30), 'backbeat tolerance')
    if tolerance > 50:
        raise ValueError('backbeat tolerance must not exceed 50 ms')
    result.update(cue_seconds=cue, tolerance_ms=tolerance)
    if approved_launch_delay(spec):
        result['approved_launch_delay'] = dict(spec['approved_launch_delay'])
    return result


def target_grid_bpm(spec: dict, outgoing_live_grid_bpm: float) -> float:
    """Keep real musical beats equal even when one grid counts eighth notes."""
    out, inc = spec['outgoing'], spec['incoming']
    return (positive_number(outgoing_live_grid_bpm, 'live BPM') / out['grid_bpm']
            * out['real_bpm'] / inc['real_bpm'] * inc['grid_bpm'])


def phase_error_ms(spec: dict, out_seconds: float, in_seconds: float,
                   outgoing_live_grid_bpm: float) -> float:
    """Residual against measured cycles plus any explicitly heard launch delay."""
    out, inc = spec['outgoing'], spec['incoming']
    a = (out_seconds - out['snare_phase_seconds']) * out['real_bpm'] / 60
    a -= approved_launch_delay(spec)
    b = (in_seconds - inc['snare_phase_seconds']) * inc['real_bpm'] / 60
    real_live_bpm = outgoing_live_grid_bpm / out['grid_bpm'] * out['real_bpm']
    return ((a - b + 1) % 2 - 1) * 60000 / real_live_bpm


def next_start_source(spec: dict, out_seconds: float, cue_seconds: float) -> float:
    """Next outgoing source position whose backbeat matches the untouched cue.

    Wait on the outgoing record; never seek across the incoming intro.
    A small lead permits issuing the start before a source-clock deadline.
    """
    out, inc = spec['outgoing'], spec['incoming']
    a = (out_seconds - out['snare_phase_seconds']) * out['real_bpm'] / 60
    b = (cue_seconds - inc['snare_phase_seconds']) * inc['real_bpm'] / 60
    distance = (b - a) % 2
    if distance * 60 / out['real_bpm'] < .04:
        distance += 2
    return out_seconds + (distance + approved_launch_delay(spec)) * 60 / out['real_bpm']
