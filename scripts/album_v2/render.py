"""Render full albums, with independent score, performance, stems and delivery.

.venv/bin/python Scripts/album_v2/render.py --album sign-off
.venv/bin/python Scripts/album_v2/render.py --album quiet-hours
Use --track 2 for one song, --resume to skip verified builds, --remix for dry cache.
"""
from __future__ import annotations
import argparse, gc, hashlib, json, math, pathlib, subprocess, sys, time
from collections import defaultdict, deque
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly
import generate_studio_auditions as dsp
from music_engine import ExsSampler
from music_engine.samplers import read_sample
from generate_album_quiet_hours import TrackWriter, TRACKS as OLD, MODES
from album_v2.sign_off import TRACKS as SIGN
from album_v2.quiet_hours import TRACKS as QUIET
ROOT=dsp.ROOT; SR=dsp.SR
BUILD=ROOT/'Releases/Rebuilt-2026'
ASSETS={}

def read(path):
    path=pathlib.Path(path)
    ASSETS[str(path.resolve())]=dsp.digest(path)
    return read_sample(str(path),SR).T

def write(path,x):dsp.save(path,x)
def pad(x,n):return np.pad(x,((0,0),(0,max(0,n-x.shape[-1]))))[:,:n]
def zeros(n):return np.zeros((2,n),np.float32)
def seeded(title,part):return np.random.default_rng(int.from_bytes(hashlib.sha256((title+':'+part).encode()).digest()[:8],'little'))
def add(bus,t,sig,g=1,pan=0):dsp.put(bus,max(0,t),sig,g,pan)

def tape(x,rate,depth,n):
    slow=resample_poly(x,100,round(rate*100),axis=-1).astype(np.float32)
    t=np.arange(n)/SR; positions=np.arange(n)+SR*depth*(np.sin(2*np.pi*.29*t)+.25*np.sin(2*np.pi*3.1*t))
    idx=np.arange(slow.shape[-1])
    return np.stack([np.interp(positions,idx,ch,left=0,right=0) for ch in slow]).astype(np.float32)

def drums_for(spec,n,sections):
    bus=zeros(n); hits=[]; beat=60/spec['bpm']; rate=spec['rate']
    kit={}
    for name,fn in [('kick','kick.wav'),('snare','snare-m.wav'),('hat','hhclosed.wav')]:
        x=read(ROOT/'Samples/LM-2'/fn)
        if x.ndim==2:x=x.mean(axis=0)
        kit[name]=resample_poly(x/max(float(abs(x).max()),1e-9),100,round(rate*100)).astype(np.float32)
    for start,bars,_,level,pattern,_ in sections:
        for bar in range(bars):
            b=start+bar
            if pattern=='none':continue
            if pattern=='heartbeat': seq=[(0,'kick',.07),(2,'kick',.045)]
            elif pattern=='half':seq=[(0,'kick',.105),(2,'snare',.07)]
            else:seq=[(0,'kick',.11),(2,'kick',.085),(1,'snare',.07),(3,'snare',.078)]
            if pattern=='drive':seq+=[(3.5,'kick',.04)]
            if pattern not in ['heartbeat']:
                steps=8 if pattern in ['steady','drive'] else 4
                seq += [(i*4/steps,'hat',.016 if i%2 else .021) for i in range(steps)]
            for offset,piece,gain in seq:
                at=(b*4+offset)*beat
                add(bus,at,kit[piece],gain*level*(.75 if pattern=='soft' else 1),.16 if piece=='hat' else 0)
                hits.append([piece,round(at*SR),b*4+offset])
    assert all(abs(p-b*beat*SR)<=.500001 for _,p,b in hits)
    return dsp.filt(dsp.filt(bus,5000),45,'highpass'),hits

def sign_source(spec):
    beat=60/spec['bpm']; rate=spec['rate']; source_beat=beat*rate
    bars=sum(x[1] for x in spec['form']); seconds=bars*4*beat+9;n=math.ceil(seconds*SR)
    sn=math.ceil((bars*4*source_beat+9*rate)*SR)
    buses={k:zeros(sn) for k in ['keys','bass','melody','pad']}
    sections=[];cursor=0;notes=[]
    for sec,count,bank,level,pattern,variation in spec['form']:
        sections.append((cursor,count,bank,level,pattern,variation))
        chords=spec[bank];bass=spec['bass_b' if bank=='b' else 'bass']
        phrase=spec['answer'] if variation=='answer' else spec['motif']
        phrase_bars=max(x[0] for x in phrase)+1
        for local in range(count):
            b=cursor+local;t=b*4*source_beat;chord=chords[local%len(chords)];root=bass[local%len(bass)]
            if level==0:continue
            style=spec['keys']
            pulses={'syncopated':[(0,.12),(1.75,.075),(3,.055)],'sustain':[(0,.11)],'sparse':[(0,.075)] if local%2==0 else [],'bossa':[(0,.105),(1.5,.065),(3,.08)],'stabs':[(0,.09),(1.5,.08),(2.5,.055)]}[style]
            for offset,gain in pulses:
                for j,note in enumerate(chord):
                    dur=4*source_beat if style=='sustain' else 2 if style!='stabs' else .55
                    add(buses['keys'],t+offset*source_beat+j*.014,dsp.tone(note,dur,'keys'),gain*level,-.15+j*.1)
                    notes.append(['keys',b*4+offset,note,dur,gain*level])
            bass_pattern=[(0,root,.23)] if pattern in ['none','heartbeat'] else [(0,root,.27),(1.5,root+12,.13),(2.75,root+7,.16)]
            for offset,note,gain in bass_pattern:
                dur=source_beat*3.6 if pattern in ['none','heartbeat'] else 1.05
                add(buses['bass'],t+offset*source_beat,dsp.tone(note,dur,'bass'),gain*level)
            for j,note in enumerate(chord[1:]):
                add(buses['pad'],t,dsp.tone(note,source_beat*4.8,'pad'),(.04 if pattern=='none' else .024)*level,[-.5,.1,.5][j])
            if variation!='rest':
                for mb,offset,note,dur in phrase:
                    if mb==local%phrase_bars and (variation!='fragment' or mb==0):
                        add(buses['melody'],t+offset*source_beat,dsp.tone(note,dur*source_beat+1,'bell'),.12*level,-.12)
                        notes.append(['melody',b*4+offset,note,dur,level])
        cursor+=count
    out={k:tape(x,rate,.0008 if k=='bass' else spec['warble'],n) for k,x in buses.items()}
    drum,hits=drums_for(spec,n,sections);out['drums']=drum
    return out,dict(seconds=seconds,sections=sections,source_notes=notes,drum_hits=hits)

def sign_mix(spec,dry):
    n=dry['keys'].shape[-1];t=np.arange(n)/SR;damage=spec['damage'];rng=seeded(spec['title'],'defects')
    music=dsp.filt(dsp.filt(sum(dry[k] for k in ['keys','bass','melody','pad']),spec['cutoff']),100 if spec['keys']=='sparse' else 70,'highpass')
    drop=np.ones(n,np.float32)
    centers=np.arange(11,max(12,n/SR-10),16 if damage>.5 else 33)+rng.uniform(-2,2,len(np.arange(11,max(12,n/SR-10),16 if damage>.5 else 33)))
    for at in centers:
        drop*=1-(.5+.3*rng.random())*damage*np.exp(-((t-at)/(.06+.1*rng.random()))**2)
    loss=np.clip(.6*damage*(.5+.5*np.sin(2*np.pi*t/43))**10,0,.8)
    music=(music*(1-loss)+dsp.filt(music,1500)*loss)*drop
    music=(np.tanh(music*1.7)/1.7).astype(np.float32)
    noise=dsp.filt(rng.normal(0,.0004+.001*damage,(2,n)).astype(np.float32),5000)
    for at in centers[::2]:
        tick=rng.normal(0,1,round(.014*SR)).astype(np.float32)*np.exp(-np.arange(round(.014*SR))/(.0018*SR))
        add(noise,at+.6,tick,.008*damage,float(rng.uniform(-.5,.5)))
    # Noise belongs to the recording and disappears before the natural tail.
    noise=dsp.apply_fades(noise,SR,fade_in=1,fade_out=9)
    return dict(music=music,drums=dry['drums'],room=dsp.room(music,spec['room'])*(.11 if damage>.5 else .09),
        drum_room=dsp.room(dry['drums'],.6)*.022,echo=dsp.delay(music,30/spec['bpm'])*(.35 if damage>.5 else .2),noise=noise)

def pitch(spec,degree,octave=5):return 12*(octave+degree//7)+spec['root']+MODES[spec['mode']][degree%7]
def warp(t):return t+.20*np.sin(2*np.pi*t/16)+.055*np.sin(2*np.pi*t/4)

def quiet_events(spec):
    beat=60/spec['bpm'];meter=spec['meter']; events={'piano':[],'strings':[]};uid=0
    def note(part,b,dur,p,vel,ch=0):
        nonlocal uid
        start=max(0,warp(b*beat));end=max(start+.03,warp((b+dur)*beat))
        v=int(np.clip(vel+(5 if ch==0 and part=='piano' else -7)+3*np.sin(2*np.pi*start/16),1,127))
        if part=='piano' and ch!=0:end=start+(end-start)*.87
        events[part].extend([(round(start*SR),'on',ch,p,v,uid),(round(end*SR),'off',ch,p,0,uid)]);uid+=1
    cursor=0
    for sec,bars,bank,level,variation in spec['form']:
        progression=spec[bank]
        for local in range(bars):
            b=(cursor+local)*meter;degree=progression[local%len(progression)]
            root=pitch(spec,degree,3);fifth=pitch(spec,degree+4,3);third=pitch(spec,degree+2,4);ninth=pitch(spec,degree+8,4)
            style=spec['style'];v=40+16*level
            if style in ['sparse','sustain']:
                if local%2==0:
                    note('piano',b,meter*1.7,root,v,1);note('piano',b+.08,meter*1.6,fifth,v-8,2)
                    if style=='sustain':note('piano',b+.14,meter*1.65,ninth,v-12,3)
            elif style=='open':
                note('piano',b,meter*.9,root,v,1)
                if local%2:note('piano',b+meter/2,meter*.45,third,v-10,2)
            elif style=='counterline':
                for off,p in [(0,root),(1.5,fifth),(3,third)]:note('piano',b+off,1.1,p,v-6,1)
            elif style=='ostinato':
                for off,p in [(0,root),(1,fifth),(2,root+12),(3,fifth)]:note('piano',b+off,.85,p,v-8+(3 if off==0 else 0),1)
            elif style in ['waltz','broken']:
                note('piano',b,2.5,root,v,1)
                note('piano',b+1,1.6,third,v-10,2);note('piano',b+2,.9,fifth+12,v-12,3)
            elif style=='flow':
                for k,p in enumerate([root,fifth,third,fifth,root+12,fifth,third,fifth]):note('piano',b+k*.5,.78,p,v-11,1)
            elif style=='dialogue':
                note('piano',b,1.6,root,v,1)
                if local%2:note('piano',b+2,1.7,third,v-4,2)
            elif style=='glass':
                note('piano',b,2.7,root+12,v-8,1)
                if local%2==0:note('piano',b+1.6,1.2,third+12,v-14,2)
            if spec['strings'] and level>=.75 and local%2==0:
                for d in [degree,degree+2]:
                    p=pitch(spec,d,4)
                    while p<55:p+=12
                    while p>89:p-=12
                    note('strings',b+.05,min(meter*1.8,6/beat),p,35,0)
        phrase=spec['answer'] if variation=='answer' else spec['motif']
        if variation!='rest':
            position=0; index=0;limit=bars*meter
            while position<limit:
                d,dur=phrase[index%len(phrase)];dur=min(dur,limit-position)
                if d is not None and (variation!='fragment' or index<len(phrase)//2):
                    note('piano',cursor*meter+position,dur*1.02,pitch(spec,d),53+10*level)
                position+=dur;index+=1
        cursor+=bars
    # A composed rolled tonic with sufficient tail; no universal octave climax.
    for i,d in enumerate([0,2,4]):note('piano',cursor*meter+i*.10,3.5,pitch(spec,d,4),39-i*2,2)
    return events,cursor*meter*beat+8

def legacy_rain():
    w=TrackWriter(next(x for x in OLD if x['title']=='Slow Rain'));seconds=w.build()+2
    events={}
    for part,raw in [('piano',w.piano),('strings',w.mello)]:
        active=defaultdict(deque);out=[];uid=0
        for e in sorted(raw,key=lambda e:(e[0],e[1]!='off')):
            pos,kind,ch,p,v=e;key=ch,p
            if kind=='on':active[key].append((uid,e));uid+=1
            elif active[key]:
                voice,on=active[key].popleft();start=max(0,warp(on[0]/SR));end=max(start+.03,warp(pos/SR))
                vel=int(np.clip(on[4]+(5 if ch==0 and part=='piano' else -7)+3*np.sin(2*np.pi*start/16),1,127))
                if part=='piano' and ch!=0:end=start+(end-start)*.87
                out.extend([(round(start*SR),'on',ch,p,vel,voice),(round(end*SR),'off',ch,p,0,voice)])
        events[part]=out
    return events,seconds

def quiet_source(spec):
    legacy=spec.get('legacy',False)
    events,seconds=legacy_rain() if legacy else quiet_events(spec)
    dry={};bank='Cello' if legacy else spec['strings']
    for part in ['piano','strings']:
        if part=='strings' and not bank:dry[part]=zeros(int(seconds*SR));continue
        sampler=ExsSampler(str(ROOT/'Samples'/('SteinwayPiano' if part=='piano' else 'Mellotron')),
            rng=np.random.default_rng(731 if part=='piano' else 732) if legacy else seeded(spec['title'],part),
            stereo_output=True,release=.22 if part=='piano' else .09,groups=[bank] if part=='strings' else None)
        dry[part]=sampler.render(events[part],seconds,attack=.25 if part=='strings' else 0)
        for file in list(sampler._cache)+['manifest.json']:
            path=pathlib.Path(sampler.directory)/file;ASSETS[str(path.resolve())]=dsp.digest(path)
    return dry,dict(seconds=seconds,events=events)

def quiet_mix(spec,dry):
    # Preserve the selected audition's fixed calibration across the full record.
    # Measured peaks of the approved audition's dry piano and cello.
    # Constants keep identical calibration without requiring private audition WAVs.
    p=dry['piano']*(.42/np.float32(1.1873321533203125))
    s=dry['strings']*(.065/np.float32(0.9425227642059326))
    p=dsp.filt(dsp.filt(p,11000),45,'highpass');s=dsp.filt(dsp.filt(s,4000),180,'highpass')
    return dict(piano=p,strings=s,room=dsp.room(p+s,1.5)*.07)

def deliver(album,num,spec,stems,folder):
    name=f'{num:02d} {spec["title"]}';n=max(x.shape[-1] for x in stems.values());seconds=n/SR
    stems={k:dsp.apply_fades(pad(v,n),SR,fade_in=.08,fade_out=3) for k,v in stems.items()}
    mix=sum(stems.values());work=folder/'mix-float.wav';write(work,mix)
    m=dsp.meter(work)
    target=-23 if spec['title'] in ['Test Pattern','Rabbit Ears','Static Bloom','School Night','Sign-Off','The Small Hours','Last Page'] else -22
    db=min(target-float(m['input_i']),-1.2-float(m['input_tp']));gain=10**(db/20)
    write(work,mix*gain)
    for k,v in stems.items():write(folder/'stems'/f'{k}.wav',v*gain)
    # Sequential summation avoids another simultaneous allocation per stem.
    summed=zeros(n)
    for k in stems:summed+=read_sample(str(folder/'stems'/f'{k}.wav'),SR).T
    residual=float(np.max(abs(summed-read_sample(str(work),SR).T)))
    assert residual<2e-6,(name,residual)
    master=BUILD/album/'Masters'/f'{name}.wav';master.parent.mkdir(parents=True,exist_ok=True)
    preview=BUILD/album/'Listening'/f'{name}.mp3';preview.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(work),'-af','aresample=osf=s32:output_sample_bits=24:dither_method=triangular','-c:a','pcm_s24le',str(master)],check=True,timeout=120)
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(work),'-c:a','libmp3lame','-b:a','192k',str(preview)],check=True,timeout=120)
    final=dsp.meter(master);mp3=dsp.meter(preview)
    expected_lufs=float(m['input_i'])+db
    assert abs(float(final['input_i'])-expected_lufs)<.3,(name,final)
    assert float(final['input_tp'])<=-1.1,(name,final)
    assert float(mp3['input_tp'])<-1,(name,mp3)
    assert np.isfinite(mix).all()
    ending=float(np.sqrt(np.mean((mix[:,-SR:]*gain)**2)))
    beginning=float(np.sqrt(np.mean((mix[:,:SR]*gain)**2)))
    return dict(title=spec['title'],number=num,seconds=seconds,target_lufs=target,gain_db=db,master_metrics=final,
        mp3_metrics=mp3,stem_residual=residual,ending_rms=ending,opening_rms=beginning,
        master_sha256=dsp.digest(master),working_sha256=dsp.digest(work))

def fingerprint(spec):
    script_dir=pathlib.Path(__file__).resolve().parents[1]
    paths=[pathlib.Path(__file__)]+[script_dir/p for p in ['album_v2/sign_off.py','album_v2/quiet_hours.py','music_engine/samplers.py','generate_studio_auditions.py','generate_album_quiet_hours.py']]
    return hashlib.sha256((json.dumps(spec,sort_keys=True)+''.join(dsp.digest(p) for p in paths)).encode()).hexdigest()

def main():
    global ROOT, BUILD
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--album',choices=['sign-off','quiet-hours'],required=True)
    parser.add_argument('--track',type=int,choices=range(1,13))
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--remix',action='store_true')
    parser.add_argument('--asset-root',type=pathlib.Path,default=ROOT,help='Directory containing Samples/')
    parser.add_argument('--output-dir',type=pathlib.Path,default=BUILD)
    args=parser.parse_args()
    ROOT=args.asset_root.resolve(); BUILD=args.output_dir.resolve()
    album='Sign-Off' if args.album=='sign-off' else 'The Quiet Hours';specs=SIGN if args.album=='sign-off' else QUIET
    for num,spec in enumerate(specs,1):
        if args.track and args.track!=num:continue
        stamp=fingerprint(spec);folder=BUILD/album/'Sessions'/f'{num:02d} {spec["title"]}';manifest=folder/'manifest.json'
        if args.resume and manifest.exists():
            old=json.loads(manifest.read_text()); master=BUILD/album/'Masters'/f'{num:02d} {spec["title"]}.wav'
            if (old['fingerprint']==stamp and master.exists()
                and old['result']['master_sha256']==dsp.digest(master)
                and all((ROOT/pathlib.Path(p)).is_file() and dsp.digest(ROOT/pathlib.Path(p))==h for p,h in old.get('assets',{}).items())):
                print('Verified existing',album,spec['title'],flush=True);continue
        print('Rendering',album,num,spec['title'],flush=True);start=time.perf_counter();ASSETS.clear()
        if args.remix:
            dry={p.stem:read(p) for p in (folder/'dry').glob('*.wav')}
            if not dry:raise FileNotFoundError('Render sources before --remix')
            score=json.loads((folder/'score.json').read_text())
        else:
            dry,score=sign_source(spec) if args.album=='sign-off' else quiet_source(spec)
            for k,v in dry.items():write(folder/'dry'/f'{k}.wav',v)
            (folder/'score.json').write_text(json.dumps(score,indent=2))
        render_secs=time.perf_counter()-start
        stems=sign_mix(spec,dry) if args.album=='sign-off' else quiet_mix(spec,dry)
        del dry;gc.collect()
        result=deliver(album,num,spec,stems,folder)
        manifest.write_text(json.dumps(dict(fingerprint=stamp,spec=spec,assets=dict(ASSETS),source_seconds=render_secs,total_seconds=time.perf_counter()-start,result=result),indent=2))
        print('Finished',spec['title'],f'{result["seconds"]:.1f}s',result['master_metrics']['input_i'],'LUFS',flush=True)
        del stems;gc.collect()
    print('Album render complete:',album,flush=True)
if __name__=='__main__':main()
