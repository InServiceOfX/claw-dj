"""Validate/setup a live source performance; Rust schedules Mixxx's native DSP."""
from __future__ import annotations
import json
import subprocess
from shared.performance import compile_events, duration, live_clips
from hands.mixxx_control import MixxxControl


def native_payload(p, paths):
    events=compile_events(p)
    placements={e['clip_id']:e for e in events if e['op']=='load_clip'}
    clips=live_clips(p)
    for c in clips:
        c.update(path=str(paths[c['track_id']]),deck=placements[c['id']]['deck'],load_at=placements[c['id']]['at'])
        c.setdefault('live_eq',[1-c.get('low_subtract',0),1,1])
    return {**p,'clips':clips}


def execute_rust(binary, port, payload):
    # The child is owned by this call. Always terminate/join before mixer cleanup,
    # so no detached scheduler can restart a deck after Ctrl-C.
    child=subprocess.Popen([str(binary),'perform','--port',str(port)],stdin=subprocess.PIPE,text=True)
    try:
        child.communicate(json.dumps(payload,allow_nan=False))
        if child.returncode:
            raise RuntimeError(f'Native performance stopped with status {child.returncode}')
    finally:
        if child.poll() is None:
            child.terminate()
            try:child.wait(timeout=3)
            except subprocess.TimeoutExpired:child.kill();child.wait()


def run_performance(plan,*,port,dry_run=False,max_events=None,record=False,source_map=None,muted=False):
    from hands.performance_validation import validate_current,check_sources
    validate_current(plan)
    if max_events is not None:raise ValueError('--max-events is unsupported for simultaneous timelines; use a short test plan')
    p=plan['performance'];events=compile_events(p)
    if dry_run:
        print('LIVE SOURCE TRACKS: Mixxx loads original songs and performs transport, loops, EQ and fades. No render required.')
        for i,e in enumerate(events,1):print(f"{i:03} {e['at']:9.3f}s deck {e['deck']} {e['op']:14} {e['clip_id']}")
        print(f"dry-run: {len(events)} events; {duration(p):.3f}s; no Mixxx connection")
        return
    paths=check_sources(p,source_map)
    from hands.run_mix_plan import clawdj_binary
    binary=clawdj_binary()
    if binary is None:
        raise ValueError('Build the live executor first: cd core-rust && cargo build --release -p clawdj-cli')
    probe=subprocess.run([str(binary),'perform','--help'],capture_output=True,text=True)
    if probe.returncode:
        raise ValueError('Rebuild the Rust executor: cd core-rust && cargo build --release -p clawdj-cli')
    payload=native_payload(p,paths)
    used=sorted({e['deck'] for e in events});saved=[]
    def save_set(m,g,k,v,optional=False):
        try:old=m.get(g,k)
        except Exception:
            if optional:return
            raise
        saved.append((g,k,old));m.set(g,k,v)
    with MixxxControl(port=port,timeout_s=3) as m:
        for d in range(1,5):
            try:playing=m.get(f'[Channel{d}]','play')
            except Exception:
                if d in used:raise
                continue
            if playing>.5:raise ValueError(f'Deck {d} is playing; stop it before starting this plan')
        started_recording=False
        try:
            # Disable automatic gain corrections during this explicit gain recipe, then restore.
            save_set(m,'[ReplayGain]','ReplayGainEnabled',0)
            save_set(m,'[Master]','gain',.5);save_set(m,'[Master]','volume',0 if muted else 1)
            for d in used:
                g=f'[Channel{d}]'
                for k,v in {'orientation':1,'volume':0,'pregain':1,'mute':0,'pfl':0,'sync_enabled':0,'rate_ratio':1,'pitch_adjust':0,'keylock':0,'quantize':0,'loop_enabled':0}.items():save_set(m,g,k,v)
                save_set(m,f'[EqualizerRack1_{g}]','enabled',1)
                save_set(m,f'[QuickEffectRack1_{g}]','enabled',0,optional=True)
                for i in range(1,4):
                    save_set(m,f'[EqualizerRack1_{g}_Effect1]',f'parameter{i}',1)
                    save_set(m,f'[EqualizerRack1_{g}_Effect1]',f'button_parameter{i}',0,optional=True)
                for unit in range(1,5):save_set(m,f'[EffectRack1_EffectUnit{unit}]',f'group_{g}_enable',0,optional=True)
            if record:
                from hands.run_mix_plan import start_recording
                started_recording=start_recording(m)
            execute_rust(binary,port,payload)
            return {'mode':'live_source_tracks','executor':'rust','duration_seconds':duration(p)}
        except KeyboardInterrupt:
            print('\nstopped by user — stopping every performance deck')
        finally:
            for d in used:
                for k,v in (('volume',0),('play',0),('loop_enabled',0)):
                    try:m.set(f'[Channel{d}]',k,v)
                    except Exception:pass
            if started_recording:
                from hands.run_mix_plan import stop_recording
                stop_recording(m)
            for g,k,v in reversed(saved):
                try:m.set(g,k,v)
                except Exception:pass
