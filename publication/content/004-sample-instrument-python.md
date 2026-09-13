---
title: "Build a Sample Instrument You Can Share — Zones, Velocity Layers, and Python Playback"
date: 2026-07-02
slug: sample-instrument-python
description: "Create a small instrument from synthesized tones, describe it with a JSON zone map, and play it through a Python sampler without a factory library."
---

A sample instrument is two things: some recordings, and a map telling the
player which recording answers which note. That's genuinely all it is. The
commercial libraries are enormous and clever, but the shape underneath is a
folder of WAVs and a lookup table, and once you've built one yourself the
mystery goes away for good.

So: make the recordings, describe the zones, hand the sampler a performance
with explicit note boundaries.

## Start with an instrument we generate ourselves

From the [repository](https://github.com/clintuitive/headless-studio):

```bash
python -m pip install -r requirements.txt
python scripts/generate_sampler_demo.py --output-dir Tracks/sampler-demo
```

You get six float WAV files, a JSON manifest, a provenance record and an
eight-second `demo.wav`. NumPy and SciPy do all of it — no plugin, no sample
pack, nothing downloaded.

Three root notes: MIDI 48, 60 and 72. Each one gets a soft recording and a
bright one. A fundamental sine establishes the pitch, a second harmonic changes
the colour, and an envelope gives it an attack and a decay:

```python
frequency = 440 * 2 ** ((root - 69) / 12)
envelope = (1 - np.exp(-t / .008)) * np.exp(-t / .65)
signal = .5 * envelope * (
    np.sin(2 * np.pi * frequency * t)
    + overtone * np.sin(4 * np.pi * frequency * t)
)
```

The bright layer carries more of that second harmonic. It's a genuinely
different waveform, not the soft one turned up — which matters, because the
whole point of a velocity layer is that playing harder changes the tone and not
just the volume. These are modest little tones. They exist so you can hear the
sampler making decisions, not to stand in for a recorded piano.

## Describe a zone

A zone is one recording plus the range of notes and velocities it answers to:

```json
{
  "name": "Tone 60 soft",
  "root": 60,
  "keylo": 54,
  "keyhi": 65,
  "vello": 1,
  "velhi": 79,
  "group": "Synth tones",
  "file": "tone-60-soft.wav"
}
```

`manifest.json` is a list of those. Notes past the edge of one zone belong to
its neighbour; velocities 80–127 pick the bright layer. Keep the WAVs beside
the manifest and the whole instrument travels as a folder.

The generator also writes `provenance.json`: how the sounds were made, and a
SHA-256 for every WAV. A hash tells you which file you have. It does not tell
you that you're allowed to use it — for anything you didn't record yourself,
keep the actual license and source information alongside.

## Play the map

```python
from music_engine import ZoneSampler

sampler = ZoneSampler(
    "Tracks/sampler-demo/instrument",
    deterministic=True,
    stereo_output=True,
)
events = [(0, "on", 0, 64, 70), (round(0.6 * 44100), "off", 0, 64, 0)]
audio = sampler.render(events, total_seconds=2.0)
```

Run it with `PYTHONPATH=scripts`, or drop the file into `scripts/`. What comes
back is a float array in channel-by-frame order, so transpose before handing it
to SciPy, which wants frames by channels.

Inside, the player picks a zone, converts the file's sample rate if it needs
to, and changes playback speed by `2 ** ((note - root) / 12)`. Playing faster
raises the pitch and shortens the recording — pitch and duration are welded
together here, which is why you record several roots instead of stretching one
sample across the keyboard. Note-offs start the release envelope, and
overlapping notes are added together rather than stealing each other's voices.

(`ZoneSampler` is the current name for the sampler. You'll also see
`ExsSampler` in older code; it's the same class under a historical alias.)

## Expand it with recordings you have permission to use

Swap the tones for your own recordings, or for sources whose terms plainly
allow the sampling, rendering and distribution you have in mind. Record several
root notes so you're never pitch-shifting something halfway across the
keyboard. Add velocity layers when you have recordings that earn the
distinction, not because the format has a slot for them. And listen across
adjacent zones — a change of source should sound like the instrument, not like
an editing mistake.

Worth saying plainly: a free download, or a library that came with an
application you paid for, does not by itself grant these permissions. Read the
actual license before you build someone else's recordings into something you
plan to share.

Next up is [arranging several instruments together](/band-in-a-python-script.html).
The complete manifest reference lives in Appendix B of the [book](/book.html).
