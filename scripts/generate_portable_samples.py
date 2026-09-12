"""Three self-contained composition examples: NumPy/SciPy + optional FFmpeg.

python scripts/generate_portable_samples.py --piece afterimage --output-dir Tracks/demo
Use --remix after editing mix gains; cached dry buses retain the performance.
These are new teaching sketches, not the album masters. No sampled assets.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt, fftconvolve

SR = 44100
PIECES = {
    'afterimage': dict(bpm=78, bars=16, roots=[45,41,48,43], melody=[76,72,71,67,69,72,74,71], beat=True, wet=.16, drift=.002),
    'open-window': dict(bpm=60, bars=12, roots=[48,45,53,50], melody=[72,79,76,74,81,79], beat=False, wet=.26, drift=.0002),
    'night-transit': dict(bpm=96, bars=20, roots=[50,46,53,48], melody=[74,77,81,79,72,74,69,72], beat=True, wet=.10, drift=.0007),
}

def tone(note, seconds, voice):
    t=np.arange(round(seconds*SR))/SR
    f=440*2**((note-69)/12)
    if voice=='pad':
        x=np.sin(2*np.pi*f*t)+.2*np.sin(2*np.pi*2*f*t)
        env=(1-np.exp(-t/.45))*np.minimum(1,(seconds-t)/.8)
    else:
        x=np.sin(2*np.pi*f*t)+.28*np.sin(2*np.pi*2*f*t)*np.exp(-t*3)
        env=(1-np.exp(-t/.008))*np.exp(-t/(.6 if voice=='bell' else 1.5))*np.minimum(1,(seconds-t)/.05)
    return (x*env).astype(np.float32)

def put(bus, seconds, x, gain, pan=0):
    start=round(seconds*SR); count=min(len(x),bus.shape[1]-start)
    if count<=0:return
    theta=(pan+1)*np.pi/4
    bus[:,start:start+count]+=x[:count]*np.array([[np.cos(theta)],[np.sin(theta)]])*gain

def compose(name):
    spec=PIECES[name]; beat=60/spec['bpm']; n=round((spec['bars']*4*beat+5)*SR)
    buses={k:np.zeros((2,n),np.float32) for k in ['harmony','melody','drums']}
    rng=np.random.default_rng(90210)
    score=[]
    for bar in range(spec['bars']):
        root=spec['roots'][(bar//2)%4]; at=bar*4*beat
        # A thinner middle section and a final answer create a small, explicit form.
        middle=spec['bars']//2<=bar<spec['bars']//2+2
        for j,offset in enumerate([0,7,10,14]):
            put(buses['harmony'],at,tone(root+12+offset,beat*4.6,'pad'),.045,[-.65,-.2,.2,.65][j])
        if not middle and bar>0:
            for step in range(2 if name=='open-window' else 4):
                note=spec['melody'][(bar*3+step)%len(spec['melody'])]
                when=at+(step*(2 if name=='open-window' else 1)+.1)*beat
                velocity=.11 if step==0 else .075
                put(buses['melody'],when,tone(note,beat*2.5,'bell'),velocity,-.15 if step%2 else .15)
                score.append([round(when,6),note,velocity])
        if spec['beat'] and bar>=2 and not middle:
            for step in range(4):
                t=np.arange(round(.23*SR))/SR
                if step%2==0:
                    phase=2*np.pi*(48*t+42*.025*(1-np.exp(-t/.025)))
                    hit=np.sin(phase)*np.exp(-t*20)
                else:
                    hit=sosfilt(butter(2,1400,fs=SR,btype='highpass',output='sos'),rng.normal(size=len(t)))*np.exp(-t*35)*.32
                put(buses['drums'],at+step*beat,hit.astype(np.float32),.13)
    # Apply slow pitch movement to tonal buses only. Percussion retains its grid.
    t=np.arange(n)/SR; positions=np.arange(n)+SR*spec['drift']*np.sin(2*np.pi*.31*t)
    for key in ['harmony','melody']:
        buses[key]=np.stack([np.interp(positions,np.arange(n),ch,left=0,right=0) for ch in buses[key]]).astype(np.float32)
    return buses,score

def mix(buses,name):
    stems={key:val.copy() for key,val in buses.items()}
    signal=stems['harmony']+stems['melody']; n=signal.shape[1]
    t=np.arange(round(1.8*SR))/SR; rng=np.random.default_rng(45)
    ir=rng.normal(size=(2,len(t)))*np.exp(-t*4)
    ir/=np.sqrt(np.sum(ir*ir,axis=1,keepdims=True))
    stems['room']=np.stack([fftconvolve(signal[c],ir[c])[:n] for c in range(2)]).astype(np.float32)*PIECES[name]['wet']
    fade=np.ones(n,np.float32);fade[:441]=np.linspace(0,1,441);fade[-SR*4:]=np.linspace(1,0,SR*4)
    for key in stems:stems[key]*=fade
    total=sum(stems.values()); gain=min(1,.7/max(float(abs(total).max()),1e-9))
    return {k:v*gain for k,v in stems.items()}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--piece',choices=PIECES,default='afterimage')
    p.add_argument('--output-dir',type=Path,default=Path('Tracks/portable'));p.add_argument('--remix',action='store_true')
    args=p.parse_args();out=args.output_dir/args.piece;out.mkdir(parents=True,exist_ok=True)
    if args.remix:
        buses={}
        for key in ['harmony','melody','drums']:
            rate,data=wavfile.read(out/'dry'/f'{key}.wav')
            if rate!=SR:raise ValueError('Cached source rate changed; regenerate sources')
            buses[key]=data.T
    else:
        buses,score=compose(args.piece);(out/'dry').mkdir(exist_ok=True)
        for k,v in buses.items():wavfile.write(out/'dry'/f'{k}.wav',SR,v.T)
        (out/'score.json').write_text(json.dumps(score,indent=2))
    stems=mix(buses,args.piece);total=sum(stems.values());(out/'stems').mkdir(exist_ok=True)
    for k,v in stems.items():wavfile.write(out/'stems'/f'{k}.wav',SR,v.T)
    wavfile.write(out/'mix-float.wav',SR,total.T)
    error=float(abs(sum(wavfile.read(out/'stems'/f'{k}.wav')[1].T for k in stems)-total).max())
    assert np.isfinite(total).all() and error<2e-6 and abs(total).max()<1
    if shutil.which('ffmpeg'):
        subprocess.run(['ffmpeg','-v','error','-y','-i',str(out/'mix-float.wav'),'-af','aresample=osf=s32:output_sample_bits=24:dither_method=triangular','-c:a','pcm_s24le',str(out/'master.wav')],check=True)
        subprocess.run(['ffmpeg','-v','error','-y','-i',str(out/'mix-float.wav'),'-b:a','192k',str(out/'preview.mp3')],check=True)
    (out/'manifest.json').write_text(json.dumps(dict(piece=args.piece,sample_rate=SR,seconds=total.shape[1]/SR,stem_residual=error,mix_sha256=hashlib.sha256(total.tobytes()).hexdigest(),note='Peak-controlled teaching sketch; not a loudness-mastered album track.'),indent=2))
    print(out)
if __name__=='__main__':main()
