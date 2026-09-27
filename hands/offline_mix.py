"""Optional offline export of the same musical timeline used for live performance.

Generated files belong outside the checkout. All scratch audio has a scoped
TemporaryDirectory owner. No source files or executable plans are overwritten.
"""
from __future__ import annotations
import argparse
import html
import json
import math
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal
from shared.performance import clip_eq, duration, fingerprint, validate
from hands.performance_validation import sha, check_sources, validate_current


def _smooth(x):
    x=np.clip(x,0,1)
    return x*x*(3-2*x)


def clip_envelope(c, sample_rate):
    t=np.arange(round(c['length']*sample_rate))/sample_rate
    env=np.ones(len(t),dtype='float32')
    if c['fade_in']: env*=_smooth(t/c['fade_in']).astype('float32')
    if c['fade_out']: env*=_smooth((c['length']-t)/c['fade_out']).astype('float32')
    return env


# Mixxx's default 3-band equalizer crossovers (Preferences > Equalizers).
EQ_LOW_HZ,EQ_HIGH_HZ=246.0,2484.0


def apply_live_eq(x, gains, sample_rate):
    """Approximate the live low/mid/high EQ: zero-phase 3-band split that sums
    back to the input exactly, each band scaled by its time-varying gain.
    ``gains`` is (3, n) from ``shared.performance.clip_eq``."""
    gains=np.asarray(gains,dtype='float32')
    if np.allclose(gains,1,atol=1e-4):return x
    lo=signal.sosfiltfilt(signal.butter(2,EQ_LOW_HZ,btype='lowpass',fs=sample_rate,output='sos'),x,axis=0)
    hi=signal.sosfiltfilt(signal.butter(2,EQ_HIGH_HZ,btype='highpass',fs=sample_rate,output='sos'),x,axis=0)
    mid=x-lo-hi
    return (lo*gains[0][:,None]+mid*gains[1][:,None]+hi*gains[2][:,None]).astype('float32')


def prepare_clips(p, work: Path, source_map=None):
    """Return temporary processed clips for offline export only."""
    validate(p)
    paths=check_sources(p,source_map);sr=p['sample_rate'];beat=60/p['tempo_bpm']
    work=Path(work);work.mkdir(parents=True,exist_ok=True)
    sample_rates={}
    cache={}
    def region(tid,a,b,rate,gain):
        key=(tid,a,b,rate,gain)
        if key in cache:return cache[key]
        if tid not in sample_rates:
            probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','a:0',
                '-show_entries','stream=sample_rate','-of','json',str(paths[tid])]))
            sample_rates[tid]=int(probe['streams'][0]['sample_rate'])
        native=sample_rates[tid]
        # Trim BEFORE resampling: excluded source frames never enter a prepared clip.
        first=math.ceil(a*native-1e-7);last=math.floor(b*native+1e-7)
        target=work/f'region-{len(cache)}.wav'
        filters=f'atrim=start_sample={first}:end_sample={last},asetpts=PTS-STARTPTS,aresample={sr}:resampler=soxr:precision=28,asetrate={sr*rate:.9f},aresample={sr}:resampler=soxr:precision=28'
        subprocess.run(['ffmpeg','-v','error','-nostdin','-y','-i',str(paths[tid]),'-af',filters,
                        '-ar',str(sr),'-ac','2','-c:a','pcm_f32le',str(target)],check=True)
        x,actual_sr=sf.read(target,dtype='float32',always_2d=True)
        if actual_sr!=sr or abs(len(x)/sr-(b-a)/rate)>.06:
            raise ValueError(f'Source span outside decoded recording: {tid} {a}–{b}')
        x*=10**(gain/20)
        if not np.isfinite(x).all():raise ValueError('Nonfinite source samples')
        cache[key]=x;target.unlink()
        return x
    loop=None
    if p.get('loop'):
        l=p['loop'];x=region(l['track_id'],l['source_start'],l['source_end'],l['rate'],l['gain_db'])
        n=round(l['beats']*beat*sr)
        loop=np.zeros((n,2),dtype='float32');loop[:min(n,len(x))]=x[:n]
        # Short periodic crossfade using the loop's own tail; never reads past its approved span.
        edge=min(round(.003*sr),n//4)
        ramp=_smooth(np.arange(edge)/max(1,edge))
        loop[:edge]=loop[-edge:]*(1-ramp[:,None])+loop[:edge]*ramp[:,None]
    def bed(start,n):
        if loop is None:raise ValueError('No instrumental loop')
        return loop[(np.arange(n)+round((start-p['global_pattern_zero_seconds'])*sr))%len(loop)]
    result={}
    for c in p['clips']:
        n=round(c['length']*sr);part=np.zeros((n,2),dtype='float32')
        for s in c['segments']:
            x=region(c['track_id'],s['source_start'],s['source_end'],c['rate'],c['gain_db'])
            at=round(s['local_start']*sr);size=min(len(x),n-at)
            part[at:at+size]+=x[:size]
        t=np.arange(n)/sr
        if c.get('support'):
            # Same source rule as the live executor: the loop replaces the
            # straight segment at takeover; the EQ curve does the easing.
            take=min(n,max(0,round(c['support']['takeover_seconds']*sr)))
            part[take:]=bed(c['start'],n)[take:]
        part=apply_live_eq(part,clip_eq(c,t),sr)
        for gap in c.get('skip_fills',[]):
            edge=2*beat
            cover=(_smooth((t-(gap['start']-edge))/edge)*_smooth(((gap['end']+edge)-t)/edge)).astype('float32')
            part*=1-cover[:,None];part+=bed(c['start'],n)*cover[:,None]
        if c.get('edge_fade_seconds'):
            edge=min(n,round(c['edge_fade_seconds']*sr))
            part[:edge]*=np.linspace(0,1,edge,dtype='float32')[:,None]
        dest=work/f"clip-{len(result):03}.wav"
        sf.write(dest,part,sr,subtype='FLOAT')
        result[c['id']]={'path':str(dest),'duration':n/sr,'peak':float(np.max(np.abs(part)))}
        print(f"prepared {c['id']}: {c.get('artist','')} — {c.get('title','')}",flush=True)
    return result


def render(plan, output_dir, *, stem='mix', source_map=None):
    validate_current(plan)
    root=Path(output_dir).expanduser().resolve()
    checkout=Path(__file__).resolve().parents[1]
    if root.is_relative_to(checkout):raise ValueError('Generated audio must be outside the checkout')
    if not stem or Path(stem).name!=stem or stem in ('.','..'):
        raise ValueError('Output stem must be a filename')
    paths=check_sources(plan['performance'],source_map)
    originals={Path(path).resolve() for path in paths.values()}
    if any((root/f'{stem}{suffix}').resolve() in originals for suffix in ('.wav','.mp3')):
        raise ValueError('Export must never overwrite an original source')
    root.mkdir(parents=True,exist_ok=True)
    p=plan['performance'];sr=p['sample_rate'];seconds=duration(p)
    with tempfile.TemporaryDirectory(prefix='.render-',dir=root) as name:
        work=Path(name);prepared=prepare_clips(p,work,source_map)
        mix=np.memmap(work/'sum.raw',mode='w+',dtype='float32',shape=(math.ceil(seconds*sr)+1,2));mix[:]=0
        for c in p['clips']:
            x,_=sf.read(prepared[c['id']]['path'],dtype='float32',always_2d=True)
            x*=clip_envelope(c,sr)[:,None]
            at=round(c['start']*sr);mix[at:at+len(x)]+=x
        if not np.isfinite(mix).all():raise ValueError('Nonfinite rendered samples')
        peak=float(np.max(np.abs(mix)))
        if peak<=0:raise ValueError('Empty rendered audio')
        premaster=work/'premaster.wav';sf.write(premaster,mix,sr,subtype='FLOAT');del mix
        wav=work/f'{stem}.wav';mp3=work/f'{stem}.mp3'
        subprocess.run(['ffmpeg','-v','error','-nostdin','-y','-i',str(premaster),
            '-filter_complex',f'[0:a]loudnorm=I=-16:TP=-2:LRA=11,aresample={sr},asplit=2[w][m]',
            '-map','[w]','-c:a','pcm_s24le',str(wav),'-map','[m]','-c:a','libmp3lame','-b:a','320k',
            '-metadata',f'title={plan.get("title",stem)}',str(mp3)],check=True)
        outputs=[]
        for path in (wav,mp3):
            r=subprocess.run(['ffmpeg','-hide_banner','-nostdin','-nostats','-i',str(path),
                '-af','loudnorm=I=-16:TP=-2:LRA=11:print_format=json','-f','null','-'],capture_output=True,text=True,check=True)
            measures=json.JSONDecoder().raw_decode(r.stderr[r.stderr.rfind('{'):])[0]
            info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(path)]))
            if abs(float(info['format']['duration'])-seconds)>.15 or float(measures['input_tp'])>-.5:
                raise ValueError('Rendered duration/peak verification failed')
            outputs.append({'file':path.name,'sha256':sha(path),'fully_decoded':True,
                'integrated_lufs':float(measures['input_i']),'true_peak_dbtp':float(measures['input_tp'])})
        # A render never replaces the executable plan with a master-playback wrapper.
        validate_current(plan)
        report={'performance_sha256':fingerprint(p),'duration_seconds':seconds,'outputs':outputs,
            'source_sha256':{tid:sha(path) for tid,path in check_sources(p,source_map).items()},
            'human_listening_acceptance':'pending','live_equivalence':'Same musical timeline, source boundaries and fades. Native Mixxx EQ/loops and live timing differ from offline filtering/mastering.'}
        (work/'render-report.json').write_text(json.dumps(report,indent=2)+'\n')
        (work/'render-plan.json').write_text(json.dumps(p,indent=2)+'\n')
        def stamp(s):return f'{int(s)//60}:{int(s)%60:02}'
        rows=''.join(f'<li><button data-time="{max(0,c["start"]-8):.3f}">{stamp(c["start"])} · {html.escape(c.get("artist", ""))} — {html.escape(c.get("title",c["id"]))}</button></li>' for c in p['clips'])
        (work/'index.html').write_text(f'''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Current mix</title><style>body{{font:18px/1.6 system-ui;max-width:850px;margin:50px auto;padding:0 24px;background:#faf8f3}}audio{{width:100%}}button{{font:inherit;cursor:pointer}}</style><h1>{html.escape(plan.get('title','Current mix'))}</h1><p>Current mix · {stamp(seconds)} · {p['tempo_bpm']} BPM</p><audio id="player" controls src="{html.escape(stem)}.mp3"></audio><p><a href="{html.escape(stem)}.mp3">MP3</a> · <a href="{html.escape(stem)}.wav">WAV</a> — the same mix.</p><p>Click a transition to listen from eight seconds before it.</p><ol>{rows}</ol><script>const p=document.getElementById('player');document.querySelectorAll('[data-time]').forEach(b=>b.onclick=()=>{{p.currentTime=+b.dataset.time;p.play()}})</script>''')
        for file in (wav,mp3,work/'render-report.json',work/'render-plan.json',work/'index.html'):file.replace(root/file.name)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',required=True);parser.add_argument('--out',required=True)
    parser.add_argument('--stem',default='mix');parser.add_argument('--source-map')
    args=parser.parse_args()
    from hands.run_mix_plan import resolve_plan_argument
    plan=json.loads(resolve_plan_argument(args.plan).read_text())
    source_map=json.loads(Path(args.source_map).read_text()) if args.source_map else None
    print(json.dumps(render(plan,args.out,stem=args.stem,source_map=source_map),indent=2))

if __name__=='__main__':main()
