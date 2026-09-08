"""Offline backbeat timing report and optional transition audio. Never drives Mixxx."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path

from brain.preview_transitions import render_spec, transition_specs
from brain.rhythm import atomic_json, section_at


def onset_rows(metadata: dict) -> dict:
    preview = metadata.get("preview") or {}
    rows = {}
    for side in ("outgoing", "incoming"):
        rhythm = metadata.get(side)
        if not rhythm or not preview:
            continue
        start, rate = preview[f"{side}_seconds"], preview[f"{side}_rate"]
        section = section_at(rhythm, start)
        hits = []
        for hit in rhythm["onsets"]:
            time = (hit["seconds"]-start)/rate
            if not 0 <= time <= preview["overlap_seconds"]:
                continue
            phase = ((hit["seconds"]-rhythm["first_beat_seconds"])*rhythm["bpm"]/60-section["phase_beats"]) if section else 0
            cadence = section["cadence_beats"] if section else 2
            primary = section is not None and abs((phase+cadence/2) % cadence-cadence/2) <= 0.20
            hits.append({"wall_seconds":time,"source_seconds":hit["seconds"],"strength":hit["strength"],"candidate_backbeat":primary})
        rows[side] = {"section":section,"hits":hits}
    return rows


def timeline(rows: dict, duration: float) -> str:
    if not rows or duration <= 0: return ""
    parts = ['<svg viewBox="0 0 900 110" role="img" aria-label="Outgoing and incoming onset timing across the overlap">']
    for side, y in (("outgoing",30),("incoming",80)):
        parts.append(f'<text x="0" y="{y}" font-size="12">{side}</text><path d="M80 {y}H895" stroke="#aaa"/>')
        for hit in rows.get(side,{}).get("hits",[]):
            x=80+810*hit['wall_seconds']/duration
            color='#007f85' if hit['candidate_backbeat'] else '#aaa'
            height=min(24,5+hit['strength']*2)
            parts.append(f'<path d="M{x:.2f} {y}v-{height:.2f}" stroke="{color}"><title>{hit["wall_seconds"]:.3f}s; source {hit["source_seconds"]:.3f}s</title></path>')
    parts.append('</svg>')
    return ''.join(parts)


def audit(plan_path: Path, out_dir: Path, *, render_limit: int=0, telemetry: Path | None=None) -> dict:
    plan_bytes=plan_path.read_bytes()
    plan=json.loads(plan_bytes)
    transitions=[e for e in plan['events'] if e.get('op')=='transition']
    specs=transition_specs(plan['events'],{t['track_id']:t for t in plan['tracks']})
    out_dir.mkdir(parents=True,exist_ok=True)
    report={'plan':str(plan_path.resolve()),'plan_sha256':hashlib.sha256(plan_bytes).hexdigest(),
            'evidence_kind':'predicted_source_audio_not_live_or_ear_verified','summary':plan.get('backbeat'),
            'transitions':[]}
    cards=[]
    for index,event in enumerate(transitions,1):
        metadata=event.get('backbeat') or {'status':'legacy','reason':'rebuild to analyze'}
        row={k:v for k,v in metadata.items() if k not in {'outgoing','incoming'}}
        row.update(index=index,from_track=event.get('from_track'),to_track=event.get('to_track'),onsets=onset_rows(metadata))
        spec=specs[index-1] if index<=len(specs) else {'error':'missing preview'}
        if index<=render_limit and 'error' not in spec:
            try:
                render_spec(spec,out_dir/f'{index:02d}.mp3')
                row['audio']=f'{index:02d}.mp3'
            except (OSError, RuntimeError) as error:
                row['render_error']=str(error)
            except Exception as error:
                row['render_error']=f'{type(error).__name__}: {error}'
        report['transitions'].append(row)
        predicted=row.get('predicted') or {}
        metrics=' · '.join(f'{key}: {predicted[key]:.1f}' for key in ('median_error_ms','p90_error_ms') if predicted.get(key) is not None)
        title=html.escape(f"{index:02d}. {row['from_track']} → {row['to_track']}")
        detail=html.escape(f"{row['status']}: {row['reason']} · {metrics}")
        audio=f'<audio controls preload="none" src="{row["audio"]}"></audio>' if row.get('audio') else ''
        plot=timeline(row['onsets'],metadata.get('preview',{}).get('overlap_seconds',0))
        cards.append(f'<section><h2>{title}</h2><p>{detail}</p>{plot}{audio}</section>')
    if telemetry:
        records=[json.loads(line) for line in telemetry.read_text().splitlines() if line.strip()]
        errors=[abs(r['error_ms']) for r in records if r.get('event')=='position' and r.get('error_ms') is not None]
        report['live_position_evidence']={'path':str(telemetry),'observations':len(errors),'max_absolute_error_ms':max(errors,default=None),
                                          'fallbacks':[r for r in records if r.get('event')=='fallback'],'audio_verified':False}
    atomic_json(out_dir/'report.json',report)
    page='''<!doctype html><meta charset="utf-8"><title>Backbeat audit</title>
<style>body{font:16px system-ui;max-width:1000px;margin:2em auto;padding:0 1em}h2{font-size:18px}section{border-top:1px solid #ccc;padding:1em 0}svg,audio{width:100%}p{line-height:1.5}</style>
<h1>Backbeat audit — snare/clap alignment</h1>
<p>Predicted source-audio timing, not a live recording or an ear-verified result. Teal marks are candidate backbeats; gray marks are other transients. The solver selects one strongest hit per cycle. Audio previews approximate tempo and crossfade, without Mixxx EQ, effects or control latency. Load delays change live entrances, which are solved again from deck positions.</p>'''+''.join(cards)
    (out_dir/'index.html').write_text(page)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--out-dir',type=Path,required=True)
    parser.add_argument('--render-limit',type=int,default=0,help='Render the first N transitions; 0 writes timing report only')
    parser.add_argument('--telemetry',type=Path)
    args=parser.parse_args()
    report=audit(args.plan,args.out_dir,render_limit=args.render_limit,telemetry=args.telemetry)
    print(json.dumps(report['summary'],indent=2))
    print(f"Open {args.out_dir/'index.html'}")
    failures=[r for r in report['transitions'] if r.get('render_error')]
    if failures: raise SystemExit(f"{len(failures)} audio previews failed; see report.json")


if __name__=='__main__': main()
