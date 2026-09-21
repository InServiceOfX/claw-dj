"""Optional local backbeat/pattern measurement; no preprocessing for playback.

Inputs and analysis windows are explicit. Fits are evidence for cue/rate choices,
not an automatic listening verdict. Original recordings are read only.
"""
from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path
import numpy as np
from scipy import ndimage, signal

SAMPLE_RATE=11025
HOP=55
FEATURE_RATE=SAMPLE_RATE/HOP


def envelopes(path):
    raw=subprocess.check_output(['ffmpeg','-v','error','-nostdin','-i',str(path),'-ac','1','-ar',str(SAMPLE_RATE),'-f','f32le','-'])
    audio=np.frombuffer(raw,dtype='<f4')
    if len(audio)<HOP:raise ValueError('Source too short for pattern analysis')
    result={}
    for name,band in [('bass',[35,180]),('backbeat',[1500,5000]),('mid',[250,1200])]:
        filtered=signal.sosfilt(signal.butter(4,band,btype='bandpass',fs=SAMPLE_RATE,output='sos'),audio)
        energy=np.sqrt(np.mean(filtered[:len(filtered)//HOP*HOP].reshape(-1,HOP)**2,axis=1))
        result[name]=energy
        result[name+'_onset']=np.maximum(0,energy-ndimage.uniform_filter1d(energy,9))
    return result


def features(data,start,end):
    if not 0<=start<end<=len(data['bass_onset'])/FEATURE_RATE:
        raise ValueError('Analysis window outside decoded source')
    lo,hi=int(start*FEATURE_RATE),int(end*FEATURE_RATE)
    channels=[]
    for key in ('bass_onset','backbeat_onset'):
        v=data[key][lo:hi:2].astype(float);v=np.minimum(v,np.percentile(v,97));v-=v.mean();v/=max(v.std(),1e-10);channels.append(v)
    return np.arange(lo,hi,2)/FEATURE_RATE,np.array(channels)


def fold(times,channels,bpm,zero=0.,*,beats=8,bins=512):
    indices=np.floor(((times-zero)*bpm/60%beats)/beats*bins).astype(int)%bins
    counts=np.bincount(indices,minlength=bins)
    return np.array([np.bincount(indices,weights=ch,minlength=bins)/np.maximum(counts,1) for ch in channels])


def template(times,channels,bpm,zero,*,beats=8,bins=512):
    result=ndimage.gaussian_filter1d(fold(times,channels,bpm,zero,beats=beats,bins=bins),1,axis=1,mode='wrap')
    result-=result.mean(axis=1,keepdims=True)
    return result/np.maximum(result.std(axis=1,keepdims=True),1e-10)


def match(times,channels,reference,bpm,*,span=.8,beats=8):
    if bpm<=span or span<=0:raise ValueError('Invalid tempo search range')
    bins=reference.shape[1]
    def score(tempo):
        folded=fold(times,channels,tempo,beats=beats,bins=bins)
        correlation=sum(np.fft.irfft(np.fft.rfft(a)*np.conj(np.fft.rfft(b)),n=bins) for a,b in zip(folded,reference))
        peak=int(np.argmax(correlation));return float(correlation[peak]),peak
    coarse=np.linspace(bpm-span,bpm+span,321);best=max(coarse,key=lambda b:score(b)[0])
    best=max(np.linspace(best-.01,best+.01,81),key=lambda b:score(b)[0]);_,peak=score(best)
    zero=peak/bins*beats*60/best
    x=(times-zero)*best/60%beats/beats*bins
    predicted=np.array([np.interp(x,np.arange(bins+1),np.r_[ch,ch[0]]) for ch in reference])
    correlations=[float(np.corrcoef(a,b)[0,1]) if a.std()>0 and b.std()>0 else 0. for a,b in zip(channels,predicted)]
    return {'bpm':float(best),'pattern_zero_seconds':float(zero),'pattern_beats':beats,'correlation_bass_backbeat':correlations}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',required=True);parser.add_argument('--reference-bpm',required=True,type=float);parser.add_argument('--reference-zero',required=True,type=float)
    parser.add_argument('--reference-window',required=True,nargs=2,type=float)
    parser.add_argument('--source',required=True);parser.add_argument('--source-bpm',required=True,type=float);parser.add_argument('--source-window',required=True,nargs=2,type=float)
    parser.add_argument('--span',type=float,default=.8);parser.add_argument('--pattern-beats',type=int,default=8);parser.add_argument('--out',required=True)
    args=parser.parse_args();out=Path(args.out).expanduser().resolve()
    if out.is_relative_to(Path(__file__).resolve().parents[1]):raise ValueError('Analysis artifacts belong outside the checkout')
    if out in {Path(args.reference).resolve(),Path(args.source).resolve()}:raise ValueError('Cannot overwrite an original source')
    reference=template(*features(envelopes(args.reference),*args.reference_window),args.reference_bpm,args.reference_zero,beats=args.pattern_beats)
    result=match(*features(envelopes(args.source),*args.source_window),reference,args.source_bpm,span=args.span,beats=args.pattern_beats)
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
