"""Download pinned open sample sources and prepare the album's required zones.

Sources and credits: see THIRD_PARTY.md. Piano CC BY 3.0; strings CC0.
This deliberately implements a selected zone map, not the complete source SFZ
player: pedal, resonance and hammer-noise opcodes are not implemented.
"""
from pathlib import Path
import json,re,urllib.request,urllib.parse,hashlib,concurrent.futures,subprocess
import numpy as np
from scipy.io import wavfile
import argparse
from album_v2.render import quiet_events, legacy_rain, QUIET
parser=argparse.ArgumentParser(description="Prepare licensed piano and strings for The Quiet Hours (FFmpeg required).")
parser.add_argument('--asset-root',type=Path,required=True)
args=parser.parse_args()
ROOT=args.asset_root.resolve()
P_REV='3382bf9496bba2486f5ab0de55a264d1dfc38404'
S_REV='440300901dfe9275fd84e0b7763af1f8443ae62e'
SFZ_REV='6dd651d55dde97fd4028699be9d4481f26917891'
def source_file(folder,repo,revision,name):
 target=folder/name
 if not target.exists():
  target.parent.mkdir(parents=True,exist_ok=True)
  url='https://raw.githubusercontent.com/'+repo+'/'+revision+'/'+urllib.parse.quote(name)
  target.write_bytes(urllib.request.urlopen(url,timeout=90).read())
 return target
for foldername,repo,revision in [('SalamanderSource','sfzinstruments/SalamanderGrandPiano',P_REV),('VSCO2Source','sgossner/VSCO-2-CE',S_REV)]:
 folder=ROOT/'Samples'/foldername;folder.mkdir(parents=True,exist_ok=True)
 (folder/'commit.txt').write_text(revision+'\n')
 treefile=folder/'source-tree.json'
 if not treefile.exists():
  request=urllib.request.Request('https://api.github.com/repos/'+repo+'/git/trees/'+revision+'?recursive=1',headers={'User-Agent':'headless-studio'})
  treefile.write_bytes(urllib.request.urlopen(request,timeout=90).read())
 tree=json.loads(treefile.read_text());assert not tree.get('truncated'), 'Incomplete source tree'
 for item in tree['tree']:
  name=item['path']
  if item['type']=='blob' and (name in ('LICENSE','README.md','Readme.txt') or (foldername=='SalamanderSource' and name.startswith('Data/') and name.endswith('.txt'))):
   f=source_file(folder,repo,revision,name);b=f.read_bytes()
   assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==item['sha'],name
piano=ROOT/'Samples/SalamanderSource';strings=ROOT/'Samples/VSCO2Source'
scores=[legacy_rain()[0] if spec.get('legacy') else quiet_events(spec)[0] for spec in QUIET]
pairs={(e[3],e[4]) for events in scores for e in events['piano'] if e[1]=='on'}
regions=[]
for line in (piano/'Data/region.txt').read_text().splitlines():
 if '<region>' not in line:continue
 d=dict(re.findall(r'(region_label|lokey|hikey|pitch_keycenter|sample)=([^\s]+)',line));regions.append(d)
vels=[(int(a),int(b),int(c)) for a,b,c in re.findall(r'vel_(\d+)\.txt" lovel=(\d+) hivel=(\d+)',(piano/'Data/notes.txt').read_text())]
tunes=dict((int(a),float(b)) for a,b in re.findall(r'\$TUNE(\d+) ([-\d]+)',(piano/'Data/tune_ret.txt').read_text()))
zones=[];downloads=[]
ptree={x['path']:x for x in json.loads((piano/'source-tree.json').read_text())['tree']};psha=(piano/'commit.txt').read_text().strip()
for region in regions:
 for layer,vlo,vhi in vels:
  lo=int(region['lokey']);hi=int(region['hikey'])
  if not any(lo<=n<=hi and vlo<=v<=vhi for n,v in pairs):continue
  name=region['sample'].replace('$VEL','v'+str(layer)).replace('$EXT','flac');raw='Samples/'+name
  off=dict((int(a),int(b)) for a,b in re.findall(r'\$OFF(\d+) (\d+)',(piano/f'Data/vel_{layer:02d}.txt').read_text()))[int(region['region_label'])]
  zones.append(dict(name=name,root=int(region['pitch_keycenter'])-tunes[int(region['region_label'])]/100,keylo=lo,keyhi=hi,vello=vlo,velhi=vhi,group='Salamander',file=name.replace('.flac','.wav'),source=raw,offset=off))
  downloads.append((piano,raw,'sfzinstruments/SalamanderGrandPiano',psha,ptree[raw]['sha']))
ssha=(strings/'commit.txt').read_text().strip();stree={x['path']:x for x in json.loads((strings/'source-tree.json').read_text())['tree']}
szones=[]
for bank,filename,folder in [('Cello','CelloEnsSusVib-Quiet.sfz','Strings/Cello Section/susvib/'),('3 Violins','ViolinEnsSusVib-Quiet.sfz','Strings/Violin Section/susVib/')]:
 sfz=strings/filename
 source_file(strings,'sgossner/VSCO-2-CE',SFZ_REV,filename)
 for chunk in sfz.read_text().split('<region>')[1:]:
  d=dict(re.findall(r'(sample|lokey|hikey|pitch_keycenter|lovel|hivel)=([^\s]+)',chunk))
  lo=int(d['lokey']);hi=int(d['hikey'])
  if hi<55 or lo>69:continue
  raw=folder+d['sample'];dest=('cello-' if bank=='Cello' else 'violin-')+d['sample']
  szones.append(dict(name=dest,root=int(d['pitch_keycenter']),keylo=lo,keyhi=hi,vello=1,velhi=127,group=bank,file=dest,source=raw))
  downloads.append((strings,raw,'sgossner/VSCO-2-CE',ssha,stree[raw]['sha']))
def fetch(task):
 folder,name,repo,sha,blobsha=task;target=folder/name;target.parent.mkdir(parents=True,exist_ok=True)
 if target.exists():b=target.read_bytes()
 else:
  u='https://raw.githubusercontent.com/'+repo+'/'+sha+'/'+urllib.parse.quote(name)
  with urllib.request.urlopen(u,timeout=90) as r:b=r.read()
 assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==blobsha,name
 target.write_bytes(b)
 return name
print('Fetching',len(downloads),'verified source samples;',len(zones),'piano zones',flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
 for i,name in enumerate(ex.map(fetch,downloads),1):
  if i%10==0 or i==len(downloads):print('Downloaded',i,'/',len(downloads),flush=True)
for family,source,data in [('OpenPiano',piano,zones),('OpenStrings',strings,szones)]:
 out=ROOT/'Samples'/family;out.mkdir(exist_ok=True)
 for z in data:
  tmp=out/('.convert-'+z['file'])
  cmd=['ffmpeg','-v','error','-y','-i',str(source/z['source'])]
  if family=='OpenPiano':cmd+=['-af',f'atrim=start_sample={z["offset"]},asetpts=PTS-STARTPTS']
  cmd+=['-ar','44100','-ac','2','-c:a','pcm_f32le',str(tmp)]
  subprocess.run(cmd,check=True)
  rate,a=wavfile.read(tmp);tmp.unlink()
  if family=='OpenStrings':
   # Keep the original bow attack and crossfade a steady middle section for long chords.
   body=a[int(rate*1.2):int(rate*3.2)].copy();fade=int(rate*.3)
   assert len(body)>fade*2,z['file']
   result=a[:int(rate*3.2)].copy()
   while len(result)<rate*30:
    w=np.linspace(0,1,fade,dtype=np.float32)[:,None]
    result[-fade:]=result[-fade:]*(1-w)+body[:fade]*w
    result=np.concatenate([result,body[fade:]])
   a=result[:rate*30]
   level=np.sqrt(np.mean(a[rate:rate*3]**2));a*=.10/max(float(level),1e-8)
   a[-rate:]*=np.linspace(1,0,rate,dtype=np.float32)[:,None]
  wavfile.write(out/z['file'],rate,a.astype(np.float32))
  z['sha256']=hashlib.sha256((out/z['file']).read_bytes()).hexdigest()
 # The String Section score uses the same violin ensemble in its existing register.
 if family=='OpenStrings':data += [{**z,'group':'String Section'} for z in list(data) if z['group']=='3 Violins']
 (out/'manifest.json').write_text(json.dumps(data,indent=2)+'\n')
 (out/'LICENSE.txt').write_bytes((source/'LICENSE').read_bytes())
 (out/'provenance.json').write_text(json.dumps({'project':'Salamander Grand Piano v3' if family=='OpenPiano' else 'VSCO 2 Community Edition','revision':psha if family=='OpenPiano' else ssha,'license':'CC BY 3.0' if family=='OpenPiano' else 'CC0 1.0','changes':'Decoded to stereo float WAV at 44.1kHz; onset offsets and retuned root mapping' if family=='OpenPiano' else 'Selected quiet sustain layers; normalized and crossfade-extended bow sustains','zones':data},indent=2)+'\n')
 print('Prepared',family,len(data),'zones',flush=True)
