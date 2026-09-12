---
title: "Build a Sample Instrument You Can Share — Zones, Velocity Layers, and Python Playback"
date: 2026-07-02
slug: sample-instrument-python
description: "Create a small instrument from synthesized tones, describe it with a JSON zone map, and play it through a Python sampler without a factory library."
---

A sample instrument has two parts: recordings and a map that tells the player
which recording to use for each note. Build the recordings first, describe
the zones, then feed the sampler a performance with explicit note boundaries.

## Start with an instrument we generate ourselves

From the [repository](https://github.com/clintuitive/headless-studio):

```bash
python -m pip install -r requirements.txt
python scripts/generate_sampler_demo.py --output-dir Tracks/sampler-demo
```

The command creates six float WAV files, a JSON manifest, a provenance record,
and an eight-second `demo.wav`. It uses NumPy and SciPy; no plugin, sample
pack or external download is involved in generating the sounds.

There are three root notes: MIDI 48, 60 and 72. Each root gets a soft and a
bright recording. A fundamental sine wave establishes the pitch, a second
harmonic changes the tone, and an envelope supplies an attack and decay:

```python
frequency = 440 * 2 ** ((root - 69) / 12)
envelope = (1 - np.exp(-t / .008)) * np.exp(-t / .65)
signal = .5 * envelope * (
    np.sin(2 * np.pi * frequency * t)
    + overtone * np.sin(4 * np.pi * frequency * t)
)
```

The bright layer has more second harmonic. It is a different source waveform,
not merely a louder copy. These modest tones make the sampler's decisions easy
to hear; they are not intended to replace a recorded piano.

## Describe a zone

A zone is one recording plus the range of notes and velocities it answers:

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

`manifest.json` is a list of these objects. Notes outside one zone belong to a
neighboring zone; velocities 80–127 select the bright layer. Keep the source
files beside the manifest so the instrument can move as a folder.

The generator also writes `provenance.json`, recording how the sounds were
made and the SHA-256 of each WAV. A hash identifies a file; it does not prove
permission to use an unrelated sample library. For recordings obtained from
someone else, retain their actual license and source information too.

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

Run this with `PYTHONPATH=scripts`, or place it in a script under `scripts/`.
The output is a floating-point array in channel-by-frame order. Transpose it
before writing it with SciPy, which expects frame-by-channel audio.

The player selects a zone, converts its file's sample rate if needed, and
changes playback speed by `2 ** ((note - root) / 12)`. Faster playback raises
the pitch and shortens the recording. Note-offs and the release envelope end
the voice; overlaps are mixed instead of replacing an earlier note.

`ZoneSampler` is the descriptive name for the existing sampler implementation.
The player reads a JSON manifest and ordinary WAV files.

## Expand it with recordings you have permission to use

Replace the tones with your own recordings, or with sources whose terms
explicitly allow the intended sampling, rendering and distribution. Record
several root notes to limit extreme pitch shifting. Add velocity layers only
when you have recordings that justify the distinction. Listen to adjacent
zones so changes of source do not sound like accidental edits.

A free download or an installed application does not by itself grant these
permissions. Check the actual source license before using someone else's recordings.

The next step is [arranging multiple instruments](/band-in-a-python-script.html).
For the full manifest reference, see Appendix B of the [intermediate book](/book.html).
