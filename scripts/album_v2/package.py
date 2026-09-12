"""Verify completed master files and assemble album listening/delivery packages."""
import json, pathlib, subprocess, sys, zipfile
import numpy as np
from scipy.io import wavfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from album_v2.sign_off import TRACKS as SIGN
from album_v2.quiet_hours import TRACKS as QUIET
from generate_studio_auditions import digest
ROOT=pathlib.Path(__file__).resolve().parents[2];BASE=ROOT/'Releases/Rebuilt-2026'

def main():
    report=[]
    for album,specs in [('Sign-Off',SIGN),('The Quiet Hours',QUIET)]:
        folder=BASE/album;rows=[]
        for i,s in enumerate(specs,1):
            name=f'{i:02d} {s["title"]}'
            p=folder/'Masters'/f'{name}.wav'
            data=json.loads((folder/'Sessions'/name/'manifest.json').read_text())['result']
            assert digest(p)==data['master_sha256']
            info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=codec_name,sample_rate,channels,bits_per_raw_sample','-of','json',str(p)]))['streams'][0]
            assert info==dict(codec_name='pcm_s24le',sample_rate='44100',channels=2,bits_per_raw_sample='24'),info
            sr,x=wavfile.read(p);x=x.astype(np.float64)/2147483648
            assert len(x)>sr*60 and x.shape[1]==2
            assert np.isfinite(x).all() and np.max(abs(x))<1
            assert data['stem_residual']<2e-6
            # Final second must be below -55 dBFS after tail/fade; avoid chopped notes.
            tail=20*np.log10(max(np.sqrt(np.mean(x[-sr:]**2)),1e-12))
            assert tail < -55,(name,tail)
            corr=float(np.corrcoef(x.T)[0,1])
            mono_loss=10*np.log10(np.mean(x.mean(axis=1)**2)/np.mean(x**2))
            assert mono_loss > -6,(name,mono_loss)
            rows.append(dict(number=i,title=s['title'],seconds=len(x)/sr,lufs=float(data['master_metrics']['input_i']),true_peak=float(data['master_metrics']['input_tp']),tail_rms_dbfs=tail,stereo_correlation=corr,mono_fold_down_db=mono_loss,sha256=data['master_sha256']))
        assert len({r['sha256'] for r in rows})==12
        assert digest(folder/'cover_3000.png')==digest(ROOT/'Releases'/album/'cover_3000.png')
        metadata=dict(album=album,artist='Clintuitive',titles=[s['title'] for s in specs],instrumental=True,explicit=False,
            artwork='cover_3000.png',recording_version='New recordings / revised arrangements, not Audio Swap corrections',
            distribution_status='New release and original takedown authorized; submission pending',
            ai_disclosure='AI contributed compositions and arrangements; Python synthesis and sample playback, no generated vocals',tracks=rows)
        (folder/'release.json').write_text(json.dumps(metadata,indent=2))
        text=['# '+album,'','New recordings, same album and track titles. Original artwork retained.','',
              'Status: rendered and technically verified; not uploaded to DistroKid.','',
              '| # | Track | Duration | LUFS | True peak |','|---|---|---:|---:|---:|']
        for r in rows:
            secs=round(r['seconds']);text.append(f"| {r['number']} | {r['title']} | {secs//60}:{secs%60:02d} | {r['lufs']:.1f} | {r['true_peak']:.1f} dBTP |")
        text+=['','Masters are stereo 44.1 kHz, 24-bit WAV. Listening contains MP3s. Sessions contains dry sources, stems, score/event data and manifests.','',
               'Measurements do not replace a critical listening pass. The audition directions were approved; these full arrangements are ready for listening.']
        (folder/'README.md').write_text('\n'.join(text)+'\n')
        playlist='\n'.join(f'{i:02d} {s["title"]}.mp3' for i,s in enumerate(specs,1))+'\n'
        (folder/'Listening'/f'{album}.m3u8').write_text(playlist)
        concat=folder/'Listening'/'concat.txt'
        # All current titles contain no apostrophe. Fail closed if new titles do.
        assert all("'" not in s['title'] for s in specs)
        concat.write_text('\n'.join("file '../Masters/"+f'{i:02d} {s["title"]}.wav'+"'" for i,s in enumerate(specs,1))+'\n')
        preview=folder/f'{album} - Album Preview.mp3'
        subprocess.run(['ffmpeg','-v','error','-xerror','-y','-f','concat','-safe','0','-i',str(concat),'-af','asetpts=N/SR/TB','-c:a','libmp3lame','-b:a','192k',str(preview)],check=True,timeout=120)
        preview_seconds=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(preview)]))
        assert abs(preview_seconds-sum(r['seconds'] for r in rows)) < .2
        with zipfile.ZipFile(BASE/f'{album} - Delivery.zip','w',compression=zipfile.ZIP_STORED) as z:
            for p in sorted((folder/'Masters').glob('*.wav'))+[folder/'cover_3000.png',folder/'release.json',folder/'README.md']:
                z.write(p,p.relative_to(BASE))
        report.append(dict(album=album,tracks=12,seconds=sum(r['seconds'] for r in rows),checks='PCM format, duration, finite audio, peaks, stereo, tails, stem reconstruction, distinct masters, preserved artwork',distribution='not uploaded'))
    (BASE/'verification.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
