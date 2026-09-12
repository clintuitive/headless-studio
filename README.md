# The Headless Studio

Make music with Python: explicit scores, reusable performances, inspectable
mixes and verified delivery files. The September 2026 rebuild adds new versions
of **Sign-Off** and **The Quiet Hours**, a repaired sampler, and three examples
that work without external samples or plugins.

[Listen](https://clintjohnson.cloud/headless-studio/music.html) ·
[Read the intermediate book](https://clintjohnson.cloud/headless-studio/book.html) ·
[What changed](https://clintjohnson.cloud/headless-studio/rebuilding-the-albums.html)

## Start here — no sample library required

Python 3.9 or newer:

```bash
git clone https://github.com/clintuitive/headless-studio
cd headless-studio
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/generate_portable_samples.py --piece afterimage
```

This writes a float WAV mix, dry buses, processed stems, score and manifest
under `Tracks/portable/afterimage/`. Install FFmpeg on your system PATH to also
produce a 24-bit WAV and 192k MP3. Try `--piece open-window` for an ambient
sketch or `--piece night-transit` for a more rhythmic one. These sketches are
teaching examples, not the album masters; their peak-controlled exports do
not claim a particular integrated loudness.

Use `--remix` to reuse a sketch's saved dry performance after changing the mix.
Regenerate sources after composition or synthesis changes.

## The rebuilt albums

See [album setup and rendering](scripts/album_v2/README.md).
`sign_off.py` and `quiet_hours.py` hold individual motifs, harmonies and forms.
Sign-Off combines broadcast damage with gentler ambient pieces; its drums
bypass the timing warp. The Quiet Hours retains Slow Rain's composition and
selected new performance; the other eleven pieces have new writing.

```bash
python scripts/check_album_assets.py --asset-root /path/to/assets
python scripts/album_v2/render.py --album sign-off --track 2 \
  --asset-root /path/to/assets --output-dir Tracks/rebuilt
```

The sampled albums require independently obtained assets: LM-2 drum hits,
extracted SteinwayPiano and Mellotron libraries. They are **not included**.
Do not redistribute factory samples or infer asset rights from this code's
license. The portable examples need none of those assets.

The album renderer saves score → dry performance → processed float stems →
float mix → delivery WAV/MP3. `--remix` reuses dry sources; `--resume` verifies
code/score, master and recorded asset hashes before skipping a track. A
nonlinear shared music bus remains a group stem; its dry instrument inputs
are available for rebalancing. Processed float stems reconstruct the float
mix within numerical tolerance, before final PCM dither.

September masters have passed technical delivery checks. Both replacement
albums were **submitted to DistroKid on September 12, 2026**. Store publication
is pending, and takedowns of both originals have been requested. The website's
rebuilt players contain the new audio.
AI contributed writing, arrangement and code; the audio was rendered with
Python synthesis/sample playback, without generated vocals or a generative
audio service. Technical verification does not replace critical listening.

## Code map

| Path | Purpose |
|---|---|
| `scripts/generate_portable_samples.py` | Three self-contained teaching sketches |
| `scripts/music_engine/` | Events, sampler, audio helpers and optional plugin bridges |
| `scripts/album_v2/` | New album scores, renderer and studio delivery packaging |
| `scripts/tests/` | Sampler regressions, event and score checks |
| `scripts/generate_studio_auditions.py` | Audition source and DSP used by the rebuild |
| `scripts/generate_album_*.py` | Original album engines; retained for comparison and Slow Rain's writing |
| Other `scripts/generate_*.py` | Legacy studio experiments with extra assets/plugin setup |
| `publication/` | Maintained site and intermediate manuscript sources |

The original plugin examples remain useful, but many contain local asset or
plugin paths. They are not the minimal quickstart. Install
`requirements-plugins.txt` and the documented native libraries/plugins for
those rigs. Audio assets, native plugins and GUI compatibility differ by OS.
No claim is made that every legacy rig has been validated on every platform.

## Verification

```bash
PYTHONPATH=scripts python -m unittest discover -s scripts/tests -v
# PowerShell: $env:PYTHONPATH="scripts"; python -m unittest discover -s scripts/tests -v
```

The current core tests and portable render/remix checks were run on macOS
with Python 3.9, NumPy 2.0.2, SciPy 1.13.1 and FFmpeg 8.1.2. CI runs core
tests and a portable smoke render; it does not validate proprietary plugins,
private album libraries or musical quality.

## Publish the book and site locally

```bash
python -m pip install -r publication/requirements.txt
python publication/build_epub.py
python publication/build.py
```

The site is written to `publication/site/`; building never deploys it.
Album previews are hosted on the website and excluded from Git. The old
technical manuscript is archival; the intermediate edition is maintained.

## License

[MIT](LICENSE) applies to the code and accompanying documentation. Third-party
assets retain their own terms; the license does not grant rights in samples
or recordings that are not included in the repository.
