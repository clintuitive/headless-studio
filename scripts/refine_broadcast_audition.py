"""Refine approved Broadcast palette; preserve Session 01 for comparison."""
import json
import time
import pathlib
import numpy as np
from scipy.signal import resample_poly
import generate_studio_auditions as studio

ROOT=studio.ROOT
PREVIOUS=ROOT/'Auditions/Session-01'
OUT=ROOT/'Auditions/Session-02'
SR=studio.SR
RATE=.66
BEAT=.625/RATE
N=studio.N

def main():
    started=time.perf_counter()
    src={k:studio.load(PREVIOUS/'sources/sign-off'/f'{k}.wav') for k in ['keys','bass','melody','pad']}
    chunk=round(8*BEAT*SR)
    order=[0,1,0,3,2,4,1,5,3]
    music={}
    for name,x in src.items():
        # Bass stays relatively stable; keys/pad/melody carry the stronger damage.
        x=studio.tape(x,RATE,.0008 if name=='bass' else .0075)
        parts=[studio.apply_fades(x[:,i*chunk:(i+1)*chunk],SR,fade_in=.025,fade_out=.09) for i in order]
        music[name]=studio.fit(np.concatenate(parts,axis=-1))
    musical=sum(music.values())
    musical=studio.filt(studio.filt(musical,3700),130,'highpass')
    t=np.arange(N)/SR
    drop=np.ones(N)
    for center,width,depth in [(9.6,.07,.55),(15.4,.12,.8),(23.9,.035,.65),(31.6,.16,.85),(40.2,.08,.65),(48.1,.1,.85),(57.3,.15,.6)]:
        drop*=1-depth*np.exp(-((t-center)/width)**2)
    # Intermittent treble loss, separate from level dropout.
    dull=studio.filt(musical,1500)
    loss=.6*np.exp(-((t-26)/1.6)**2)+.7*np.exp(-((t-52)/1.2)**2)
    musical=(musical*(1-loss)+dull*loss)*drop
    musical=(np.tanh(musical*1.7)/1.7).astype(np.float32)
    drums=np.zeros((2,N),np.float32)
    kit={}
    for name,filename in [('kick','kick.wav'),('snare','snare-m.wav'),('hat','hhclosed.wav')]:
        x=studio.load(ROOT/'Samples/LM-2'/filename)
        if x.ndim==2:x=x.mean(axis=0)
        x=x/max(float(abs(x).max()),1e-6)
        # Keep the slowed timbre while scheduling every attack on the output grid.
        kit[name]=resample_poly(x,100,66).astype(np.float32)
    hits=[]
    for bar in range(int(studio.SECONDS/(4*BEAT))+1):
        for beat,name,gain in [(0,'kick',.108),(2,'kick',.083),(1,'snare',.069),(3,'snare',.078)]:
            onset=(bar*4+beat)*BEAT
            if onset<studio.SECONDS:
                studio.put(drums,onset,kit[name],gain);hits.append(dict(piece=name,sample=round(onset*SR),beat=bar*4+beat))
        for k in range(8):
            onset=(bar*4+k*.5)*BEAT
            if onset<studio.SECONDS:
                studio.put(drums,onset,kit['hat'],.012 if k%2 else .019,pan=.16)
                hits.append(dict(piece='hat',sample=round(onset*SR),beat=bar*4+k*.5))
    drums=studio.filt(studio.filt(drums,5000),45,'highpass')
    rng=np.random.default_rng(5102)
    noise=studio.filt(rng.normal(0,.0015,(2,N)).astype(np.float32),5000)
    # Tiny tape ticks, not large digital full-scale clicks.
    for onset in [5.3,12.7,20.4,29.1,38.6,46.8,55.2,62.1]:
        tick=rng.normal(0,1,round(.014*SR)).astype(np.float32)*np.exp(-np.arange(round(.014*SR))/(.0018*SR))
        studio.put(noise,onset,tick,.008,pan=float(rng.uniform(-.5,.5)))
    stems=dict(music=musical,drums=drums,music_room=studio.room(musical,3)*.11,
        drum_room=studio.room(drums,.6)*.022,music_echo=studio.delay(musical,BEAT/2)*.35,noise=noise)
    OUT.mkdir(parents=True,exist_ok=True)
    studio.OUT=OUT
    result=studio.deliver('07 Sign-Off - Broadcast Refined',stems)
    assert abs(float(result['wav']['input_i'])+22)<.1
    assert float(result['mp3']['input_tp'])<-1
    assert all(abs(h['sample']-h['beat']*BEAT*SR)<=.5 for h in hits)
    manifest=dict(bpm=96*RATE,warble_depth=.0075,original_warble_depth=.0035,
        musical_edit_order=order,drum_swing=0,drum_echo=False,drum_hits=hits,
        elapsed_seconds=time.perf_counter()-started,assets=studio.ASSETS,
        code={str(p.relative_to(ROOT)):studio.digest(p) for p in [pathlib.Path(__file__),ROOT/'Scripts/generate_studio_auditions.py']},output=result)
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print('Verified drum grid, loudness, true peak, and stem reconstruction.',flush=True)

if __name__=='__main__':main()
