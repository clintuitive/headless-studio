# The Headless Studio

**Make finished records with Python. No DAW.**

This is a complete music-production pipeline that lives entirely in code.
It generates a band's performance as note events, renders each instrument
through real VST3/AU plugins, samplers, and synthesis — no GUI, no DAW open
— and mixes down to a finished, mastered track from one `python` command.

It's the real thing I use to make albums, released free and open for anyone
who wants to build the same. In it for the love of the game.

📖 **The book** (free, every chapter): https://clintjohnson.cloud/headless-studio
📝 **The articles**: https://clintjohnson.cloud/headless-studio
🎵 Two albums were made with this pipeline. So can yours.

[![License: MIT](https://img.shields.io/badge/License-MIT-8b8bf5.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)
![No DAW required](https://img.shields.io/badge/DAW-not%20required-e94f37.svg)

---

## What it does

```
the song, as data     →   sections, chords, patterns (plain Python lists)
per-instrument events  →   one note list per band member, humanized
instruments            →   FluidSynth · real VST3/AU plugins · samplers · synthesis
effects                →   each member's amp/pedal chain (real plugins, headless)
the mix                →   gains + one shared convolution "room"
the record             →   mastered WAV + per-instrument stems that null
```

Every arrow is a plain function over NumPy arrays. The whole book explains
each stage; this repo is the working code behind it.

## Quickstart

```bash
git clone https://github.com/clintuitive/headless-studio
cd headless-studio
pip install -r requirements.txt

# grab a free General MIDI soundfont (see "Assets" below), then:
python scripts/generate_modern_darkwave_band.py
# → writes a finished track to Tracks/
```

That script is the reference implementation — a full band (bass, two
guitars through a real amp-sim, drum-machine samples, pad) rendered and
mixed from scratch. Read it top to bottom; it's commented as a tutorial.

## What's inside

| Script | What it demonstrates |
|---|---|
| `generate_modern_darkwave_band.py` | **Start here.** The full band pipeline: MIDI events → FluidSynth buses → real amp-sim plugins → shared room → mix |
| `generate_album_sign_off.py` | Album engine + from-scratch synthesis (oscillators, FM, tape-wow) |
| `generate_album_quiet_hours.py` | Album engine driving an extracted sampler (Steinway, Mellotron) |
| `exs_extract.py` | Parser for Apple's undocumented EXS sampler format |
| `render_ample_bass.py` | Hosting an Intel-only plugin via a Rosetta subprocess |
| `audition_drum_kits.py` | Render one groove through eight real drum machines to A/B them |
| `generate_postrock_epic.py` · `_hammock.py` · `_ambient.py` | Long-form post-rock arrangements |
| `generate_*` (others) | The rest of the studio — darkwave, synthwave, coldwave, ambient, sequences |

## Assets (not included — here's where to get them free)

The code is MIT-licensed and free. The *sounds* aren't mine to
redistribute, so grab these once and point the scripts at them:

- **GeneralUser GS** soundfont (free) — https://schristiancollins.com/generaluser.php
  Put it in `Soundfonts/`. (Some scripts use FluidR3 GM, shipped by
  `apt install fluid-soundfont-gm` or many free mirrors.)
- **Neural Amp Modeler** VST3 (free) — https://www.neuralampmodeler.com/
  and free amp captures from https://tonehunt.org
- **Drum-machine one-shots** (free) — https://github.com/smpldsnds/drum-machines
  → `Samples/<machine>/`
- **Impulse responses** for the room reverb (free) — Voxengo's IR pack.
- **GarageBand factory library** — already on your Mac; `exs_extract.py`
  pulls it into your own sampler (for your own use; don't redistribute the
  samples).

Full setup, per-OS, is in the book's Appendix A.

## Requirements

Python 3.9+, and:

```
pedalboard   # Spotify's headless plugin host
pyfluidsynth # the FluidSynth binding
numpy scipy  # audio is NumPy arrays
mido         # MIDI messages for instrument plugins
```

Works on macOS, Windows, and Linux — every install path is tested in CI on
clean runners for all three (see the companion
[headless-studio-tests](https://github.com/clintuitive/headless-studio-tests)
repo).

## The book

This repo is the code; the [book](https://clintjohnson.cloud/headless-studio)
is the *why* — 15 chapters and 5 appendices, free in full, written for an
intermediate programmer with no audio background. It walks the whole system:
hosting plugins headlessly, rescuing incompatible plugins, reverse-
engineering the EXS format, building a sampler, synthesis from oscillators,
arranging as data, humanization, mixing, and stems that provably sum to the
master. Start with
[chapter 1](https://clintjohnson.cloud/headless-studio/the-case-for-a-headless-studio.html).

## License

[MIT](LICENSE) — do whatever you like with the code. Attribution is
appreciated but not required.

## Support

This is free and always will be. If it saved you an afternoon and you feel
like it, you can [buy me a coffee](https://buymeacoffee.com/clintjohnson) —
entirely optional, never a wall. Enjoy, and go make something.

— Clint Johnson
