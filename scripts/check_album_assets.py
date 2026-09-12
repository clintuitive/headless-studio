"""Report missing album assets before spending time rendering."""
import argparse
import json
from pathlib import Path
import shutil

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--asset-root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--album',choices=['all','sign-off','quiet-hours'],default='all');args=p.parse_args()
    missing=[]
    for tool in ['ffmpeg','ffprobe']:
        if not shutil.which(tool):missing.append('Executable: '+tool)
    if args.album in ['all','sign-off']:
        for name in ['kick.wav','snare-m.wav','hhclosed.wav']:
            file=args.asset_root/'Samples/LM-2'/name
            if not file.is_file():missing.append(str(file))
    if args.album in ['all','quiet-hours']:
        for name in ['OpenPiano','OpenStrings']:
            folder=args.asset_root/'Samples'/name;manifest=folder/'manifest.json'
            if not manifest.is_file():missing.append(str(manifest));continue
            zones=json.loads(manifest.read_text())
            if not zones:missing.append('Empty manifest: '+str(manifest))
            for file in sorted({z['file'] for z in zones}):
                if not (folder/file).is_file():missing.append(str(folder/file))
    if missing:
        print('Missing requirements:\n'+'\n'.join(missing));raise SystemExit(1)
    print('Required paths and tools found. This checks availability, not sample licensing or musical quality.')
if __name__=='__main__':main()
