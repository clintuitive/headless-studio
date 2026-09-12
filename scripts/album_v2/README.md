# Full album rebuilds

The score modules contain individual writing and forms. The renderer uses
NumPy/SciPy synthesis and a stereo zone sampler, with FFmpeg export.
AI assisted the composition, arrangement and code; no generative-audio service
or generated vocals were used for these recordings.

From the public repository root:

```bash
python scripts/album_v2/render.py --album sign-off --track 2 \
  --asset-root /path/to/studio-assets --output-dir Tracks/rebuilt
python scripts/album_v2/render.py --album quiet-hours \
  --asset-root /path/to/studio-assets --output-dir Tracks/rebuilt
```

The asset root must contain:

- Sign-Off: `Samples/LM-2/kick.wav`, `snare-m.wav`, `hhclosed.wav`.
- The Quiet Hours: `Samples/OpenPiano/manifest.json` and prepared Salamander WAVs;
  `Samples/OpenStrings/manifest.json` and prepared VSCO WAVs.
  See `THIRD_PARTY.md` for credits and source licenses.

Prepare the exact piano and string subset from pinned, licensed source revisions:

```bash
python scripts/prepare_open_instruments.py --asset-root /path/to/studio-assets
```

This downloads source samples and license records outside the repository and
uses FFmpeg to prepare stereo WAVs. It implements the selected notes and
velocity layers, not the source SFZ's pedal/noise/resonance features.
The source licenses and attribution requirements still apply.
Run `python scripts/check_album_assets.py --asset-root /path/to/studio-assets`
for a preflight. For a no-asset first render, use `generate_portable_samples.py`.

Choose a new output directory. The default is `Releases/Rebuilt-2026` under the
repository; legacy releases are inputs only when packaging preserved artwork.
Each track includes dry float sources, processed float stems, float mix,
24-bit PCM master, 192k MP3 and a manifest. The exact source used for the
September 2026 masters is archived with the local delivery package; subsequent
portability changes are tracked in Git.

`--resume` checks code/score fingerprint, master hash and recorded asset hashes.
`--remix` deliberately reuses saved dry sources: do not use it after changing
notes, tempo, performance rules, source assets or sampler behavior. Stored
asset paths describe the local rendering machine; moving a session can require
a full render. This is track-level caching, not a general dependency graph.

Sign-Off slows and warps pitched material while drum attacks stay at final
tempo. Rabbit Ears and Vertical Hold carry the heaviest damage. Other tracks
provide softer and ambient contrast. Quiet Hours has eleven new scores and
the preserved Slow Rain composition with the selected performance treatment.
Fixed piano/string calibration keeps the bowed strings about 14 dB behind
the piano in the Slow Rain reference; the same gains apply across the record.

Mastering uses gain only: −22 LUFS for core tracks, −23 for selected quieter
pieces, with a −1.2 dBTP ceiling taking priority. WAV and MP3 are measured after
export. Processed float stems reconstruct the float mix before final dither.
A nonlinear music bus is a group stem; use dry sources to rebalance its inputs.

`package.py` is the studio's album-specific delivery verifier. It requires the
completed session tree and the original artwork under `Releases/<album>/`.
It is not necessary for the portable demos or an individual track render.
Technical checks do not replace a full critical listening pass.

The website revision uses these open sample sources.
