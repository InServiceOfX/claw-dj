"""Enforce mandatory source ends before connecting to Mixxx.

Use a lossless, physically bounded copy: tempo changes, loops, delayed control
messages, and stale ride counts cannot expose a forbidden tail. Originals and
library identities remain untouched. Rendered masters require matching evidence.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import sqlite3
import subprocess
import tempfile
import wave
from pathlib import Path

from brain import library_index
from brain.build_mix_plan import track_directives
from brain.plan_notes import carry_library_skips


def library_notes(track_ids: set[str]) -> dict[str, str]:
    path = Path(library_index.current_index_path())
    if not track_ids or not path.exists():
        return {}
    # Never create a library merely by running a portable plan.
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        marks = ','.join('?' for _ in track_ids)
        return dict(db.execute(f'SELECT track_id,dj_notes FROM tracks WHERE track_id IN ({marks})', list(track_ids)))
    finally:
        db.close()


def _digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _bounded_audio(source: Path, end: float, cache: Path) -> Path:
    stat = source.stat()
    key = hashlib.sha256(f'{source.resolve()}:{stat.st_mtime_ns}:{stat.st_size}:{end}'.encode()).hexdigest()
    cache.mkdir(parents=True, exist_ok=True)
    dest = cache / f'{key}.wav'
    if dest.exists():
        with wave.open(str(dest)) as stream:
            if 0 < stream.getnframes() <= math.floor(end * stream.getframerate()):
                return dest
        raise ValueError(f'Invalid bounded audio cache: {dest}')
    fd, name = tempfile.mkstemp(suffix='.wav', dir=cache)
    os.close(fd)
    tmp = Path(name)
    try:
        # atrim runs BEFORE any rate conversion. Integer source sample count
        # ensures even fractional boundaries cannot round into excluded audio.
        probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0',
            '-show_entries', 'stream=sample_rate', '-of', 'json', str(source)],
            check=True, capture_output=True, text=True)
        sr = int(json.loads(probe.stdout)['streams'][0]['sample_rate'])
        frames = math.floor(end * sr)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(source), '-map', '0:a:0',
            '-af', f'atrim=end_sample={frames},asetpts=PTS-STARTPTS', '-c:a', 'pcm_s24le',
            str(tmp)], check=True, capture_output=True)
        with wave.open(str(tmp)) as stream:
            if not 0 < stream.getnframes() <= frames or stream.getframerate() != sr:
                raise ValueError('Encoded source exceeds mandatory boundary')
        tmp.replace(dest)
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, wave.Error) as error:
        raise ValueError(f'Cannot prepare bounded audio for {source}; refusing uncut playback') from error
    finally:
        tmp.unlink(missing_ok=True)
    return dest


def prepare_plan(plan: dict, *, cache_dir: Path | None = None, dry_run: bool = False) -> dict:
    tracks = {t['track_id']: t for t in plan.get('tracks', []) if t.get('track_id')}
    ids = set(tracks) | {e['track_id'] for e in plan.get('events', []) if e.get('track_id')}
    global_notes = library_notes(ids)
    ends = {}
    for tid in ids:
        note = carry_library_skips(global_notes.get(tid, ''), tracks.get(tid, {}).get('dj_notes', ''))
        end = track_directives({'dj_notes': note})['mandatory_end_seconds']
        if end is not None:
            if not math.isfinite(end) or end <= 0:
                raise ValueError(f'{tid}: invalid mandatory_end_seconds')
            ends[tid] = end
    if not ends:
        return plan
    if plan.get('execution_mode') == 'rendered_master_playback':
        recipe_path = Path(plan['render_recipe'])
        recipe = json.loads(recipe_path.read_text())
        for tid, end in ends.items():
            clips = [c for c in recipe['clips'] if c['track_id'] == tid]
            if not clips:
                raise ValueError(f'{tid}: no render evidence for mandatory_end_seconds={end}')
            for clip in clips:
                regions = clip.get('segments') or []
                if clip.get('loop_support'):
                    regions = [*regions, clip['loop_support']]
                if (not regions or float(clip['source_end']) > end or
                    any(not 0 <= float(s['source_start']) < float(s['source_end']) <= end for s in regions)):
                    raise ValueError(f'{tid}: rendered audio violates mandatory_end_seconds={end}; rerender required')
        if _digest(recipe_path) != plan.get('render_recipe_sha256'):
            raise ValueError('Rendered recipe hash is missing or changed; verify and repackage the render')
        loads = [e for e in plan['events'] if e.get('track_id')]
        if not loads or any(_digest(Path(e['track_id'])) != plan.get('master_sha256') for e in loads):
            raise ValueError('Rendered master hash does not match the reviewed artifact')
        return plan

    result = copy.deepcopy(plan)
    replacements = {}
    cache = Path(cache_dir) if cache_dir is not None else Path(tempfile.gettempdir()) / 'claw-dj' / 'bounded-audio'
    for event in result.get('events', []):
        tid = event.get('track_id')
        if tid not in ends:
            continue
        if float(event.get('cue_seconds') or 0) >= ends[tid]:
            raise ValueError(f'{tid}: cue reaches mandatory_end_seconds={ends[tid]}')
        if dry_run:
            event['mandatory_end_seconds'] = ends[tid]
            continue
        if tid not in replacements:
            replacements[tid] = str(_bounded_audio(Path(tid), ends[tid], cache))
        event['source_track_id'] = tid
        event['track_id'] = replacements[tid]
    for track in result.get('tracks', []):
        tid = track.get('track_id')
        if tid in replacements:
            track['source_track_id'] = tid
            track['track_id'] = replacements[tid]
    return result
