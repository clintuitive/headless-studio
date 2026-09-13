# Appendix A — Setup and Dependency Boundaries

The studio is deliberately layered: a core that installs in one command, and
optional pieces you only set up when you want what they do. This appendix
draws those lines clearly, so that when something fails you know which layer
you're in.

Run every command from the public repository root unless a section says
otherwise. The core CI matrix covers Python 3.11 and 3.12 on Linux, macOS and
Windows. Use a virtual environment — it keeps this project's packages from
colliding with the rest of your machine, and audio libraries are unusually good
at colliding.

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

The core requirements are NumPy and SciPy. That's it. The portable sketches
synthesize their own sources; the sampler demo generates six WAV zones and a
manifest. Neither needs an installed plugin or a downloaded sample library, and
neither asks you to read a licence first. FFmpeg, if you have it, enables the
portable script's extra delivery exports.

If those three commands work, you can run the load-bearing parts of this book:
the sampler, synthesis from scratch, arrangement as data, performance timing,
the mix and the null test. The rest of this appendix is optional.

## Album assets and export tools

Install FFmpeg and confirm both `ffmpeg` and `ffprobe` are on your path — the
delivery stage uses both, and a missing `ffprobe` produces a confusing failure
much later than you'd like. Use whatever installation method suits your
operating system.

Then prepare the licensed piano and strings:

```bash
python scripts/prepare_open_instruments.py --asset-root /path/to/studio-assets
python scripts/check_album_assets.py --album quiet-hours --asset-root /path/to/studio-assets
```

Sign-Off additionally needs its three documented LM-2 one-shots. Obtain any
external asset under terms that permit what you intend to do, and keep those
records with the files. None of it is included in the repository, which is
deliberate rather than an oversight.

## Optional instrument and effect runtimes

`requirements-plugins.txt` lists the optional Python dependencies. Native
FluidSynth, SoundFonts, VST3 plugins, amp models and plugin-specific libraries
are all separate installations, and each has its own view about which operating
system and processor architecture it will tolerate. The core CI does not
validate any of them, so a green build tells you nothing about whether your
plugin loads.

For FluidSynth, install the native library as well as the Python binding —
these are two different things and the error message will not tell you which is
missing. For a VST3 effect, install the effect and point the host at its actual
path. For an instrument helper, get it running standalone before integrating it
through `render_external_instrument`, as Chapter 4 recommends at some length.

When a loader fails, diagnose the specific cause before changing anything:
missing Python package, missing native library, incompatible architecture, or
missing instrument content. Those four failures produce similar-looking errors
and have entirely different fixes. Adding unrelated library paths in the hope
that one sticks is how an afternoon disappears.

## Publication

```bash
python -m pip install -r publication/requirements.txt
python publication/build_epub.py
python publication/build.py
```

Both builders write local files and neither deploys anything. Add the media to
the downloads directory when you're assembling a complete website bundle — and
don't replace a live music site with a build that has no recordings in it.
