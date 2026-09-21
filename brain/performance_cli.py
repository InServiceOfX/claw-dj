"""Compile shared musical decisions into live events without rendering audio."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from shared.performance import LIVE_MODE, compile_events, duration, fingerprint, validate
from brain.plan_revision import file_rev, write_checked


def compile_plan(plan: dict) -> dict:
    import copy
    from hands.performance_validation import current_limits
    result=copy.deepcopy(plan);p=result['performance']
    validate(p,current_limits(result))
    result['events']=compile_events(p)
    result['performance_sha256']=fingerprint(p)
    result['execution_mode']=LIVE_MODE
    result['execution_note']='Original source songs; Mixxx performs cues, rate correction, loops, source skips, EQ and volume envelopes live. Offline rendering is optional and never required for playback.'
    result['duration_seconds']=duration(p)
    # Display/transition summaries are derived too, never a second arrangement.
    prior={t['track_id']:t for t in result.get('tracks',[]) if isinstance(t,dict)}
    rows=[];seen=set()
    for c in p['clips']:
        if c['track_id'] in seen:continue
        seen.add(c['track_id'])
        row=prior.get(c['track_id'],{'track_id':c['track_id']}).copy()
        for key in ('artist','title'):
            if key in c:row[key]=c[key]
        row.update(cue_seconds=c['segments'][0]['source_start'],performance_start_seconds=c['start'])
        if 'source_bpm' in c:row['measured_source_bpm']=c['source_bpm']
        for key in list(row):
            if key.startswith('rendered_'):row.pop(key)
        rows.append(row)
    result['tracks']=rows;result['track_count']=len(rows)
    result['segments']=[{'from_track_id':a['track_id'],'to_track_id':b['track_id'],
        'start_seconds':b['start'],'transition_seconds':b['fade_in'],
        'transition_beats':b['fade_in']*p['tempo_bpm']/60,'technique':'live_source_blend',
        'note':'Concurrent support and all source jumps are defined by performance clips.'}
        for a,b in zip(p['clips'],p['clips'][1:])]
    # Obsolete master/recipe hashes must not masquerade as the execution source.
    for key in ('master_sha256','render_recipe_sha256','render_recipe','render_layers','comparison_entry','render_root','dj_notes_compliance','source_constraints'):
        result.pop(key,None)
    return result


def publish(path: Path, plan: dict, expected_rev: str):
    from brain import plan_paths,plan_journal
    from brain.plan_mix_envelope import decorate
    result=compile_plan(plan)
    slug=result.get('plan_slug')
    if slug:
        paths=plan_paths.resolve(slug)
        if paths.mix_plan.resolve()!=path.resolve():raise ValueError('Named plan path mismatch')
        result=decorate(result,slug,paths)
    after=write_checked(path,result,expected_rev)
    if slug:plan_journal.append(slug,'agent','compile_live_performance',{'performance_sha256':result['performance_sha256']},expected_rev,after)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',required=True)
    args=parser.parse_args()
    from hands.run_mix_plan import resolve_plan_argument
    path=resolve_plan_argument(args.plan);before=file_rev(path)
    result=publish(path,json.loads(path.read_text()),before)
    print(f"Compiled {len(result['events'])} live events from the shared performance; {result['duration_seconds']:.3f}s")

if __name__=='__main__':main()
