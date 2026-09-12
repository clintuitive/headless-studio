"""Session 01: original vaporwave source/treatments and Slow Rain comparisons.

python Scripts/generate_studio_auditions.py          # sources + mixes
python Scripts/generate_studio_auditions.py --remix  # cached dry stems only

All outputs go to Auditions/Session-01. Release files are read-only inputs.
Uses NumPy/SciPy and ffmpeg; no plugins or generative-audio service.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import subprocess
import time
from collections import defaultdict, deque
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, fftconvolve, resample_poly
from music_engine.samplers import ExsSampler, read_sample
from music_engine.audio import stereo, apply_fades
from generate_album_quiet_hours import TrackWriter, TRACKS

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT/'Auditions/Session-01'
SR = 44100
SECONDS = 68
N = SR*SECONDS
ASSETS = {}

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def save(path, x):
    path.parent.mkdir(parents=True,exist_ok=True)
    if not np.isfinite(x).all(): raise ValueError(f'Nonfinite audio: {path}')
    wavfile.write(path,SR,np.asarray(x.T,dtype=np.float32))

def load(path):
    ASSETS[str(path.relative_to(ROOT))]=digest(path)
    return read_sample(str(path),SR).T

def fit(x,n=N):
    return np.pad(x,((0,0),(0,max(0,n-x.shape[-1]))))[:,:n]

def filt(x,hz,kind='lowpass'):
    return sosfilt(butter(2,hz,fs=SR,btype=kind,output='sos'),x,axis=-1).astype(np.float32)

def put(bus,t,x,g=1,pan=0):
    x=stereo(x,pan) if x.ndim==1 else x
    start=round(t*SR); end=min(bus.shape[-1],start+x.shape[-1])
    if end>start: bus[:,start:end]+=x[:,:end-start]*g

def tone(midi,dur,voice):
    t=np.arange(round(dur*SR))/SR; f=440*2**((midi-69)/12)
    if voice=='keys':
        env=(1-np.exp(-t/0.006))*np.exp(-t/1.8)
        x=np.sin(2*np.pi*f*t+1.1*np.exp(-t/0.2)*np.sin(2*np.pi*f*2*t))*.7
        x+=.16*np.sin(2*np.pi*f*2*t)*np.exp(-t/.8)
    elif voice=='bass':
        env=(1-np.exp(-t/.008))*np.exp(-t/1.1)
        x=np.sin(2*np.pi*f*t)+.25*np.sin(2*np.pi*f*2*t)
    elif voice=='bell':
        env=(1-np.exp(-t/.003))*np.exp(-t/.7)
        x=np.sin(2*np.pi*f*t)+.22*np.sin(2*np.pi*f*3*t)*np.exp(-t/.2)
    else:
        env=np.sin(np.pi*np.clip(t/dur,0,1))**.7
        x=sum(np.sin(2*np.pi*f*k*t+0.002*k*np.sin(t))*1/k**2 for k in range(1,7))
    return apply_fades((x*env).astype(np.float32),SR,fade_out=min(.12,dur/3))

def source_recording():
    """A 96 BPM, 24-bar original lounge fragment in D major/B minor."""
    beat=.625; bar=beat*4; length=64*SR
    buses={k:np.zeros((2,length),np.float32) for k in ['keys','bass','melody','pad','drums']}
    # Bm9, E13, Amaj9, F#7sus: close upper voices over moving bass.
    chords=[[57,61,62,66],[56,61,62,66],[56,59,61,64],[54,59,61,64],
            [54,57,61,64],[55,59,62,66],[54,57,61,64],[53,57,59,62]]
    basses=[35,40,33,30,38,43,35,30]
    melody=[(0,.5,73,1),(0,2,69,.75),(1,1.5,66,.5),(1,3,68,.6),
            (2,.5,71,1.5),(3,1,69,1),(3,3,66,.6),
            (4,0,66,.8),(4,1.5,69,.6),(5,1,71,1.5),
            (6,.5,73,.9),(6,2.5,71,.7),(7,1,69,1.5)]
    rng=np.random.default_rng(91031)
    kit={k:load(ROOT/'Samples/LM-2'/fn) for k,fn in [('kick','kick.wav'),('snare','snare-m.wav'),('hat','hhclosed.wav')]}
    for k,v in kit.items():
        if v.ndim==2:v=v.mean(axis=0)
        kit[k]=v/max(float(abs(v).max()),1e-6)
    for b in range(24):
        chord=chords[b%8]; t=b*bar
        for pulse,gain in [(0,.12),(1.75,.075),(3,.055)]:
            for j,note in enumerate(chord):
                put(buses['keys'],t+pulse*beat+j*.014,tone(note,2,'keys'),gain, -.15+j*.1)
        for offset,note,gain in [(0,basses[b%8],.27),(1.5,basses[b%8]+12,.13),(2.75,basses[b%8]+7,.16)]:
            put(buses['bass'],t+offset*beat,tone(note,1.05,'bass'),gain)
        for j,note in enumerate(chord[1:]):put(buses['pad'],t,tone(note,bar*1.15,'pad'),.024,(-.5,.1,.5)[j])
        for offset,piece,g in [(0,'kick',.18),(2.5,'kick',.12),(1,'snare',.115),(3,'snare',.13)]:
            put(buses['drums'],t+offset*beat,kit[piece],g)
        for k in range(8):put(buses['drums'],t+(k*.5+(0.08 if k%2 else 0))*beat,kit['hat'],.023 if k%2 else .037,.16)
        for mb,off,note,dur in melody:
            if mb==b%8:
                put(buses['melody'],t+off*beat+float(rng.uniform(-.008,.008)),tone(note,dur+1,'bell'),.12,-.12)
    for name,x in buses.items():save(OUT/'sources/sign-off'/f'{name}.wav',x)
    save(OUT/'sources/sign-off/source-mix.wav',sum(buses.values()))
    (OUT/'sources/sign-off/score.json').write_text(json.dumps(dict(bpm=96,bars=24,chords=chords,bass=basses,melody=melody,seed=91031),indent=2))

def piano_sources():
    spec=next(s for s in TRACKS if s['title']=='Slow Rain')
    writer=TrackWriter(spec); writer.build()
    for version in ['repaired','reperformed']:
        all_events={}
        for part,events in [('piano',writer.piano),('cello',writer.mello)]:
            # Tag legacy FIFO pairs before timing edits, retaining voice identity.
            active=defaultdict(deque); out=[]; uid=0
            for e in sorted(events,key=lambda e:(e[0],e[1]!='off')):
                pos,kind,ch,pitch,vel=e; key=(ch,pitch)
                if kind=='on':
                    active[key].append((uid,e)); uid+=1
                elif active[key]:
                    voice,on=active[key].popleft(); start=on[0]/SR; end=pos/SR
                    velocity=on[4]
                    if version=='reperformed':
                        warp=lambda t:t+.20*np.sin(2*np.pi*t/16)+.055*np.sin(2*np.pi*t/4)
                        start=max(0,warp(start)); end=max(start+.03,warp(end))
                        velocity=int(np.clip(velocity+(5 if ch==0 and part=='piano' else -7)+3*np.sin(2*np.pi*start/16),1,127))
                        if part=='piano' and ch!=0:end=start+(end-start)*.87
                    out.extend([(round(start*SR),'on',ch,pitch,velocity,voice),(round(end*SR),'off',ch,pitch,0,voice)])
            all_events[part]=out
            sampler=ExsSampler(str(ROOT/'Samples'/('SteinwayPiano' if part=='piano' else 'Mellotron')),
                rng=np.random.default_rng(731 if part=='piano' else 732),stereo_output=True,
                release=.22 if version=='reperformed' and part=='piano' else .09,
                groups=['Cello'] if part=='cello' else None)
            x=sampler.render(out,86,attack=.25 if part=='cello' else 0)
            # Same opening A/A2/breath/B neighborhood as the released excerpt.
            x=x[:,16*SR:84*SR]
            save(OUT/f'sources/slow-rain-{version}'/f'{part}.wav',x)
            for filename in sampler._cache:
                path=pathlib.Path(sampler.directory)/filename
                ASSETS[str(path.relative_to(ROOT))]=digest(path)
            path=pathlib.Path(sampler.directory)/'manifest.json'
            ASSETS[str(path.relative_to(ROOT))]=digest(path)
        (OUT/f'sources/slow-rain-{version}'/'events.json').write_text(json.dumps(all_events))

# A deterministic stereo ambience with decaying, decorrelated reflections.
# Exposed as a separate return, not folded irreversibly into instruments.
def room(x,decay=1.8):
    rng=np.random.default_rng(300)
    n=int(decay*SR); t=np.arange(n)/SR
    ir=rng.normal(0,1,(2,n)).astype(np.float32)*np.exp(-7*t/decay)
    ir[:,:int(.025*SR)]=0
    for c in range(2):
        ir[c]=filt(ir[c],4800)
        ir[c]/=max(np.sqrt(np.sum(ir[c]**2)),1e-8)
    wet=np.stack([fftconvolve(x[c],ir[c])[:x.shape[-1]] for c in range(2)])
    return wet.astype(np.float32)

def delay(x,seconds,feedback=.32):
    out=np.zeros_like(x)
    for i in range(1,5):
        offset=round(seconds*i*SR)
        if offset<x.shape[-1]:out[:,offset:]+=x[::-1 if i%2 else 1,:-offset]*feedback**i
    return out

def tape(x,rate,depth):
    # Resampling lowers pitch and tempo together; common drift moves all voices.
    slow=resample_poly(x,100,round(rate*100),axis=-1).astype(np.float32)
    n=min(slow.shape[-1],N);t=np.arange(n)/SR
    positions=np.arange(n)+SR*depth*(np.sin(2*np.pi*.29*t)+.25*np.sin(2*np.pi*3.1*t))
    return fit(np.stack([np.interp(positions,np.arange(slow.shape[-1]),ch) for ch in slow]).astype(np.float32))

def meter(path):
    p=subprocess.run(['ffmpeg','-hide_banner','-nostats','-i',str(path),'-af','loudnorm=I=-22:TP=-1:LRA=11:print_format=json','-f','null','-'],capture_output=True,text=True,timeout=90,check=True)
    return json.loads(p.stderr[p.stderr.rfind('{'):p.stderr.rfind('}')+1])

def deliver(name,stems,target=-22):
    folder=OUT/'stems'/name
    stems={k:apply_fades(fit(v),SR,fade_in=.08,fade_out=3) for k,v in stems.items()}
    mix=sum(stems.values());path=OUT/f'{name}.wav';save(path,mix)
    m=meter(path);gain_db=min(target-float(m['input_i']),-1.2-float(m['input_tp']))
    gain=10**(gain_db/20)
    for k,v in stems.items():save(folder/f'{k}.wav',v*gain)
    save(path,mix*gain)
    # Reload the actual files for a float-stem reconstruction check.
    summed=sum(read_sample(str(p),SR).T for p in sorted(folder.glob('*.wav')))
    rendered=read_sample(str(path),SR).T
    residual=float(np.max(abs(summed-rendered)))
    if residual>2e-6:raise AssertionError((name,residual))
    final=meter(path)
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(path),'-af','aresample=osf=s32:output_sample_bits=24:dither_method=triangular','-c:a','pcm_s24le',str(OUT/f'{name}-24bit.wav')],check=True,timeout=90)
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(path),'-c:a','libmp3lame','-b:a','192k',str(OUT/f'{name}.mp3')],check=True,timeout=90)
    preview=meter(OUT/f'{name}.mp3')
    print(name,final['input_i'],'LUFS',final['input_tp'],'dBTP',flush=True)
    return dict(name=name,seconds=SECONDS,gain_db=gain_db,wav=final,mp3=preview,stem_peak_residual=residual,sha256=digest(path))

def mixes():
    reports=[]
    src={k:load(OUT/'sources/sign-off'/f'{k}.wav') for k in ['keys','bass','melody','pad','drums']}
    for name,rate,depth in [('01 Sign-Off - Lush',.72,.0014),('02 Sign-Off - Broadcast',.66,.0035),('03 Sign-Off - Groove',.84,.0007)]:
        b={k:tape(v,rate,depth) for k,v in src.items()}
        if 'Broadcast' in name:
            # Reorder two-bar fragments of the same source into a channel collage.
            chunk=round(5/rate*SR);order=[0,1,0,3,2,4,1,5,3]
            for k in b:
                parts=[apply_fades(b[k][:,i*chunk:(i+1)*chunk],SR,fade_in=.025,fade_out=.09) for i in order]
                b[k]=fit(np.concatenate(parts,axis=-1))
            dry=sum(v*(.6 if k=='drums' else 1) for k,v in b.items())
            dry=filt(filt(dry,3700),130,'highpass')
            t=np.arange(N)/SR
            drop=np.ones(N)
            for center in [15.4,31.6,48.1]:drop*=1-.7*np.exp(-((t-center)/.12)**2)
            dry*=drop
            hiss=filt(np.random.default_rng(51).normal(0,.0015,(2,N)).astype(np.float32),5000)
            stems=dict(source= dry,space=room(dry,3.0)*.11,echo=delay(dry,.48)*.35,hiss=hiss)
        elif 'Lush' in name:
            dry=sum(v*(.68 if k=='drums' else .85 if k=='melody' else 1) for k,v in b.items())
            dry=filt(np.tanh(dry*1.5)/1.5,6500)
            stems=dict(source=dry,space=room(dry,2.4)*.10,echo=delay(b['keys']+b['melody'],.65)*.48)
        else:
            dry=sum(v*(1.3 if k=='drums' else .55 if k=='pad' else 1) for k,v in b.items())
            dry=filt(np.tanh(dry*1.3)/1.3,8500)
            stems=dict(source=dry,space=room(dry,1.1)*.055,echo=delay(b['melody'],.36)*.3)
        reports.append(deliver(name,stems))
    original=load(ROOT/'Releases/The Quiet Hours/02 Slow Rain.wav')[:,16*SR:84*SR]
    reports.append(deliver('04 Slow Rain - Released',dict(released_excerpt=original)))
    for version,name in [('repaired','05 Slow Rain - Restrained Remix'),('reperformed','06 Slow Rain - Reperformed')]:
        p=load(OUT/f'sources/slow-rain-{version}/piano.wav')
        c=load(OUT/f'sources/slow-rain-{version}/cello.wav')
        # Fixed calibration from the same repaired source for both versions:
        # retain the new performance's own dynamics instead of renormalizing parts.
        cal=read_sample(str(OUT/'sources/slow-rain-repaired/piano.wav'),SR)
        p*=.42/max(abs(cal).max(),1e-6)
        cal=read_sample(str(OUT/'sources/slow-rain-repaired/cello.wav'),SR)
        c*=.065/max(abs(cal).max(),1e-6)
        p=filt(filt(p,11000),45,'highpass');c=filt(filt(c,4000),180,'highpass')
        dry=p+c
        reports.append(deliver(name,dict(piano=p,cello=c,room=room(dry,1.5)*.07)))
    return reports

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--remix',action='store_true');args=parser.parse_args()
    start=time.perf_counter();OUT.mkdir(parents=True,exist_ok=True)
    if not args.remix:
        print('Rendering original Sign-Off source',flush=True);source_recording()
        print('Rendering Slow Rain sources',flush=True);piano_sources()
        (OUT/'source-manifest.json').write_text(json.dumps(dict(assets=ASSETS,seed_policy='Independent fixed seeds per source and part'),indent=2))
    source_time=time.perf_counter()-start
    print('Mixing and metering six auditions',flush=True);reports=mixes()
    manifest=dict(sample_rate=SR,format='float32 working WAV; 24-bit listening WAV; 192k MP3',target_lufs=-22,
        source_seconds=source_time,total_seconds=time.perf_counter()-start,remix_only=args.remix,
        code={str(p.relative_to(ROOT)):digest(p) for p in [pathlib.Path(__file__),ROOT/'Scripts/music_engine/samplers.py',ROOT/'Scripts/generate_album_quiet_hours.py']},
        outputs=reports)
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print('Complete:',OUT,flush=True)
if __name__=='__main__':main()
