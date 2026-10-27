"""Opt-in, original-source monophonic cue experiment. No rendered music.

python -m hands.pitch_play --help
Python owns source checks/setup/cleanup; Rust schedules; Mixxx owns pitch DSP.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
import subprocess
import time

from hands.mixxx_control import MixxxControl

ROOT = Path(__file__).resolve().parents[1]


def number(value, label, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{label}: invalid number {value!r}')
    return float(value)


def compile_score(score):
    """Pure dry-run schedule, mirrored and revalidated in Rust."""
    if type(score['deck']) is not int or not 1 <= score['deck'] <= 4:
        raise ValueError('deck must be 1..4')
    beat = 60 / number(score['bpm'], 'bpm', 40, 200)
    duration = number(score['duration_seconds'], 'duration', 0, float('inf'))
    if duration <= 0:
        raise ValueError('duration must be positive')
    number(score['sample_rate'], 'sample rate', 8000, 192000)
    cue = number(score['cue_seconds'], 'cue', 0, duration)
    end = number(score['source_end_seconds'], 'source end', cue, duration)
    if end <= cue:
        raise ValueError('empty source region')
    prepare = number(score['prepare_seconds'], 'preparation', .05, 1)
    late = number(score['max_late_seconds'], 'lateness', .001, .1)
    if not 1 <= len(score['notes']) <= 64:
        raise ValueError('need 1..64 notes')
    attacks, previous_off = [], -1
    for note in score['notes']:
        on = prepare + number(note['beat'], 'note beat', 0, 128) * beat
        gate = number(note['gate_beats'], 'gate', 0, float('inf')) * beat
        pitch = number(note['semitones'], 'pitch', -3, 3)
        off = on + gate
        if gate <= 0 or off > 200 or on - prepare < previous_off:
            raise ValueError('invalid/overlapping notes or insufficient preparation gap')
        if cue + gate + late >= end:
            raise ValueError('gate reaches source boundary')
        attacks.append(dict(on_seconds=on, off_seconds=off, prepare_seconds=on-prepare,
                            semitones=pitch, frequency_ratio=2**(pitch/12), cue_seconds=cue))
        previous_off = off
    return attacks


def validate_region(cue, end, notes):
    """Fail closed on malformed hard directives; never silently ignore a limit."""
    def directive(key):
        occurrences = re.findall(r'\b' + key + r'\s*=\s*([^\s;,]+)', notes, re.I)
        assignments = re.findall(r'\b' + key + r'\s*=', notes, re.I)
        if len(assignments) != len(occurrences):
            raise ValueError(f'Malformed {key} in current DJ notes')
        values = []
        for raw in occurrences:
            try:
                values.append(number(float(raw), key, 0, float('inf')))
            except (ValueError, TypeError) as exc:
                raise ValueError(f'Malformed {key} in current DJ notes') from exc
        return values
    starts, ends = directive('mandatory_start_seconds'), directive('mandatory_end_seconds')
    if starts and cue < max(starts) or ends and end > min(ends):
        raise ValueError('cue region violates mandatory source boundary')
    if re.search(r'\bmandatory_skip\b', notes, re.I):
        a, b = directive('skip_from_seconds'), directive('skip_to_seconds')
        if len(a) != 1 or len(b) != 1 or b[0] <= a[0]:
            raise ValueError('ambiguous mandatory skip; review source notes')
        if cue < b[0] and end > a[0]:
            raise ValueError('cue region overlaps mandatory source skip')


def source_notes(source, index=None):
    if index is None:
        from brain.library_index import current_index_path
        index = current_index_path()
    index = Path(index).resolve()
    if not index.is_file():
        raise ValueError('Library index missing; cannot verify current source restrictions')
    with closing(sqlite3.connect(index.as_uri() + '?mode=ro', uri=True)) as db:
        row = db.execute('SELECT dj_notes FROM tracks WHERE track_id=? AND available=1', (str(source),)).fetchone()
    if row is None:
        raise ValueError('Source must be the exact available original path in the library index')
    return row[0] or ''


def probe_source(source):
    result = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0',
        '-show_entries', 'stream=sample_rate:format=duration', '-of', 'json', str(source)],
        capture_output=True, text=True, check=True, timeout=30)
    data = json.loads(result.stdout)
    return float(data['format']['duration']), float(data['streams'][0]['sample_rate'])


def digest(source):
    with source.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def child_execute(binary, port, score):
    child = subprocess.Popen([str(binary), 'pitch-play', '--live', '--port', str(port)],
                             stdin=subprocess.PIPE, text=True)
    try:
        child.communicate(json.dumps(score, allow_nan=False))
        if child.returncode:
            raise RuntimeError(f'Pitch-play scheduler exited {child.returncode}')
    finally:
        # Join before mixer cleanup: no orphan can restart a restored deck.
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


def wait_loaded(api, group, loaded, *, timeout=10):
    deadline = time.monotonic() + timeout
    while bool(api.get(group, 'track_loaded') > .5) != loaded:
        if time.monotonic() >= deadline:
            raise RuntimeError('Mixxx load/eject timed out')
        time.sleep(.02)


def settings(deck):
    g = f'[Channel{deck}]'
    result = [(g, k, v) for k, v in [('mute', 1), ('volume', .3), ('orientation', 1),
        ('sync_enabled', 0), ('quantize', 0), ('keylock', 1), ('rate_ratio', 1), ('pitch_adjust', 0),
        ('pregain', 1), ('reverse', 0), ('reverseroll', 0), ('slip_enabled', 0),
        ('scratch2_enable', 0), ('vinylcontrol_enabled', 0)]]
    result += [(f'[QuickEffectRack1_{g}]', 'enabled', 0)]
    result += [(f'[EffectRack1_EffectUnit{unit}]', f'group_{g}_enable', 0) for unit in range(1, 5)]
    for band in range(1, 4):
        result += [(f'[EqualizerRack1_{g}_Effect1]', f'parameter{band}', 1),
                   (f'[EqualizerRack1_{g}_Effect1]', f'button_parameter{band}', 0)]
    return result


def cleanup(api, group, saved):
    errors = []
    # Keep the source guard active until the original has been ejected. If
    # mute/stop requests fail, disabling it could expose a forbidden tail.
    for key, value in [('mute', 1), ('play', 0), ('eject', 1), ('eject', 0)]:
        try:
            api.set(group, key, value)
        except Exception as exc:
            errors.append(f'{key}: {exc}')
    try:
        wait_loaded(api, group, False, timeout=3)
        if api.get(group, 'play') != 0:
            raise RuntimeError('deck did not stop')
    except Exception as exc:
        # Do not reopen the fader/unmute a voice not proven empty and stopped.
        raise RuntimeError(f'Cleanup incomplete; keep deck muted and stop it manually: {exc}; {errors}') from exc
    try:
        api.set(group, 'loop_enabled', 0)
    except Exception as exc:
        errors.append(f'loop_enabled: {exc}')
    for g, key, value in reversed(saved):
        try:
            api.set(g, key, value)
        except Exception as exc:
            errors.append(f'{g},{key}: {exc}')
    if errors:
        raise RuntimeError(f'Cleanup had control errors: {errors}')


def active_runners():
    # Shared read-only process guard, also used by transition auditions.
    from hands.audition_transition import running_mix_processes
    return running_mix_processes()


def perform(source, score, *, live=False, port=9995, binary=None, api_factory=MixxxControl,
            runner=child_execute, index=None):
    """Connection-free dry run; explicit live setup has zero writes on refusal."""
    score = copy.deepcopy(score)
    attacks = compile_score(score)
    source = Path(source).expanduser().resolve()
    if not source.is_file():
        raise ValueError('Original source file missing')
    validate_region(score['cue_seconds'], score['source_end_seconds'], source_notes(source, index))
    if not live:
        print(json.dumps({'mode': 'dry_run', 'source': str(source), 'deck': score['deck'],
            'guard_source_seconds': [score['cue_seconds'], score['source_end_seconds']],
            'setup': settings(score['deck']), 'attacks': attacks,
            'note_controls': ['pitch_adjust=absolute semitones', 'playposition=cue/duration',
                              'mute=0; play=1', 'mute=1; play=0'],
            'cleanup': 'join child, mute, stop, eject with guard retained, verify empty, disable loop, restore settings'}, indent=2))
        return
    if binary is None:
        binary = ROOT / 'core-rust/target/release/clawdj'
    binary = Path(binary)
    if not binary.is_file():
        raise ValueError('Build executor first: cd core-rust && cargo build --release -p clawdj-cli')
    subprocess.run([str(binary), 'pitch-play', '--help'], check=True, capture_output=True)
    if active_runners():
        raise ValueError('A mix/audition runner is active; stop it before this experiment')
    before = digest(source)
    # Recheck current durable restrictions immediately before connecting.
    validate_region(score['cue_seconds'], score['source_end_seconds'], source_notes(source, index))
    g = f"[Channel{score['deck']}]"
    api = api_factory(port=port, timeout_s=1)
    saved, owned = [], False
    try:
        if api.get('[AutoDJ]', 'enabled') != 0:
            raise ValueError('Disable AutoDJ before this standalone experiment')
        for d in range(1, 5):
            if api.get(f'[Channel{d}]', 'play') != 0:
                raise ValueError('Stop all decks before this standalone experiment')
        if api.get(g, 'track_loaded') != 0 or api.get(g, 'loop_enabled') != 0:
            raise ValueError('Reserved deck must be empty with looping disabled; no takeover')
        # Snapshot every required setting before the first mutation.
        saved = [(g, key, api.get(g, key)) for key in
                 ('playposition', 'loop_start_position', 'loop_end_position')]
        saved += [(group, key, api.get(group, key)) for group, key, _ in settings(score['deck'])]
        if any(not math.isfinite(v) for _, _, v in saved):
            raise ValueError('Invalid control readback')
        owned = True
        for group, key, value in settings(score['deck']):
            api.set(group, key, value)
        api.load(score['deck'], str(source), play=False)
        wait_loaded(api, g, True)
        score['duration_seconds'] = api.get(g, 'duration')
        score['sample_rate'] = api.get(g, 'track_samplerate')
        # Never seek a fractional source position before its allowed first sample.
        number(score['sample_rate'], 'sample rate', 8000, 192000)
        score['cue_seconds'] = math.ceil(score['cue_seconds'] * score['sample_rate']) / score['sample_rate']
        compile_score(score)
        if digest(source) != before:
            raise ValueError('Source changed while loading')
        validate_region(score['cue_seconds'], score['source_end_seconds'], source_notes(source, index))
        # Reapply track-reset controls after load (Mixxx resets pitch on load).
        for group, key, value in settings(score['deck']):
            api.set(group, key, value)
        a = math.ceil(score['cue_seconds'] * score['sample_rate']) * 2
        b = math.floor(score['source_end_seconds'] * score['sample_rate']) * 2
        if b <= a:
            raise ValueError('Empty sample guard')
        for key, value in [('loop_enabled', 0), ('loop_start_position', a),
                           ('loop_end_position', b), ('loop_enabled', 1)]:
            api.set(g, key, value)
        print(f"Pitch play: deck {score['deck']}; original {source}; "
              f"cue {score['cue_seconds']:.6f}s, guard end {score['source_end_seconds']:.6f}s; "
              f"{len(score['notes'])} monophonic notes. Ctrl-C stops this experiment.", flush=True)
        runner(binary, port, score)
    finally:
        try:
            if owned:
                try:
                    cleanup(api, g, saved)
                except Exception:
                    # A dead request stream is not reusable: reconnect once and report
                    # failure if recovery cannot verify stopped/empty + restore.
                    api.close()
                    api = api_factory(port=port, timeout_s=1)
                    cleanup(api, g, saved)
        finally:
            api.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path, help='Exact indexed original file path')
    parser.add_argument('--cue-seconds', required=True, type=float)
    parser.add_argument('--source-end-seconds', required=True, type=float, help='Exclusive allowed cue-tail boundary')
    parser.add_argument('--deck', type=int, default=3)
    parser.add_argument('--bpm', type=float, default=90)
    parser.add_argument('--pitches', default='0,0,0,1,2,0', help='Absolute semitone offsets, within +/-3')
    parser.add_argument('--gate-beats', type=float, default=.5)
    parser.add_argument('--interval-beats', type=float, default=2)
    parser.add_argument('--prepare-seconds', type=float, default=.1)
    parser.add_argument('--max-late-seconds', type=float, default=.05)
    parser.add_argument('--port', type=int, default=9995)
    parser.add_argument('--binary', type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--live', action='store_true', help='Authorize this one original-source experiment')
    mode.add_argument('--dry-run', action='store_true', help='Default: print only; no Mixxx connection')
    args = parser.parse_args(argv)
    source = args.source.expanduser().resolve()
    duration, sr = probe_source(source)
    interval = number(args.interval_beats, 'interval', .01, 128)
    pitches = [float(p) for p in args.pitches.split(',')]
    score = dict(deck=args.deck, bpm=args.bpm, cue_seconds=args.cue_seconds,
        source_end_seconds=args.source_end_seconds, duration_seconds=duration, sample_rate=sr,
        prepare_seconds=args.prepare_seconds, max_late_seconds=args.max_late_seconds,
        notes=[dict(beat=i*interval, semitones=p, gate_beats=args.gate_beats) for i, p in enumerate(pitches)])
    perform(source, score, live=args.live, port=args.port, binary=args.binary)


if __name__ == '__main__':
    main()
