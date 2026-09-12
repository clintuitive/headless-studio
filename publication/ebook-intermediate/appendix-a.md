# Appendix A — Setup and Dependency Boundaries

Run commands from the public repository root unless a section says otherwise.
The core CI matrix uses Python 3.11 and 3.12 on Linux, macOS and Windows. A
virtual environment keeps this project's Python packages separate from other
work on the machine.

## Core studio

```bash
python -m venv .venv
```

Activate it with `source .venv/bin/activate` on a POSIX shell, or
`.venv\Scripts\Activate.ps1` in PowerShell. Then:

```bash
python -m pip install -r requirements.txt
python scripts/generate_portable_samples.py --piece afterimage --output-dir Tracks/demo
python scripts/generate_sampler_demo.py --output-dir Tracks/sampler-demo
```

The core requirements provide NumPy and SciPy. The portable sketches synthesize
their sources; the sampler demo generates six WAV zones and a manifest. Neither
command needs an installed plugin or downloaded sample library. FFmpeg enables
the portable script's additional delivery exports.

## Album assets and export tools

Install FFmpeg and confirm both `ffmpeg` and `ffprobe` are on the command path.
Use the installation method appropriate to your operating system. Then prepare
the licensed piano and strings:

```bash
python scripts/prepare_open_instruments.py --asset-root /path/to/studio-assets
python scripts/check_album_assets.py --album quiet-hours --asset-root /path/to/studio-assets
```

Sign-Off additionally requires its three documented LM-2 one-shots. Obtain
external assets under terms that permit your intended use. Keep their records
with the files; they are not included in the repository.

## Optional instrument and effect runtimes

`requirements-plugins.txt` lists optional Python dependencies. Native FluidSynth,
SoundFonts, VST3 plugins, amp models and plugin-specific libraries are separate
installations. Check the operating system and processor architecture supported
by each one. The core CI does not validate these external installations.

For FluidSynth, install its native library as well as the Python binding.
For a VST3 effect, install the effect and point the host at its actual path.
For an instrument helper, verify the helper independently before integrating
it through `render_external_instrument`.

A loader error needs a specific diagnosis: missing package, missing native
library, incompatible architecture or missing instrument content. Avoid adding
unrelated library paths until the actual failing dependency is known.

## Publication

```bash
python -m pip install -r publication/requirements.txt
python publication/build_epub.py
python publication/build.py
```

The builders write local files. They do not deploy the site. Add the media to
the downloads directory when preparing a complete website bundle; do not
replace a live music site with a build that lacks its recordings.
