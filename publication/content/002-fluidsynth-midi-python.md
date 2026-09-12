---
title: "Rendering MIDI Through Real Instruments in Python — No DAW, Sample-Accurate"
date: 2026-07-02
slug: fluidsynth-midi-python
description: Use FluidSynth and a free soundfont to turn note events into audio from a Python script, with a sample-accurate event loop and one bus per instrument — the foundation of a code-only studio. macOS, Windows, Linux.
---

The [previous post](/headless-vst3-python.html) covered hosting VST3 effects
from Python. This one covers the other half of a studio: **instruments**. By
the end you'll have a render function that takes a list of note events and
returns a stereo NumPy array, sample-accurate, with a different General MIDI
instrument on every channel — guitars, bass, pads, anything.

The engine is [FluidSynth](https://www.fluidsynth.org/), the open-source
synthesizer that plays SoundFont (`.sf2`) sample libraries. It's fast enough
to render minutes of multitrack audio in seconds, and it runs everywhere.

## Install

**macOS**

```bash
brew install fluid-synth
pip install pyfluidsynth numpy scipy
```

**Linux (Debian/Ubuntu)**

```bash
sudo apt install fluidsynth libfluidsynth-dev
pip install pyfluidsynth numpy scipy
```

**Windows**

```powershell
choco install fluidsynth        # or grab a release zip and add it to PATH
pip install pyfluidsynth numpy scipy
```

(Verified on a clean Windows machine: the chocolatey install works
out of the box — pyfluidsynth special-cases choco's `C:\tools\fluidsynth\bin`
in its own loader. If you installed FluidSynth anywhere *else*, register that
directory **both** ways before importing, because `ctypes.util.find_library`
only searches `PATH`, while the DLL's own dependencies resolve via
`add_dll_directory`:

```python
import os
os.add_dll_directory(r"C:\path\to\fluidsynth\bin")
os.environ["PATH"] = r"C:\path\to\fluidsynth\bin;" + os.environ["PATH"]
```
)

You also need a soundfont.
[GeneralUser GS](https://schristiancollins.com/generaluser.php) is free,
excellent, and covers all 128 General MIDI instruments in ~30 MB. Download it
once and keep it next to your scripts.

### The macOS gotcha that costs everyone an hour

`pyfluidsynth` locates the C library with `ctypes.util.find_library`, which on
older Pythons doesn't search Homebrew's `/opt/homebrew/lib`. If
`import fluidsynth` dies with "couldn't find the FluidSynth library", shim the
lookup **before** the import:

```python
import ctypes.util, os

_orig = ctypes.util.find_library
def _find_library(name):
    found = _orig(name)
    if not found and name == "fluidsynth":
        path = "/opt/homebrew/lib/libfluidsynth.dylib"
        if os.path.exists(path):
            return path
    return found
ctypes.util.find_library = _find_library

import fluidsynth   # now succeeds
```

(Recent pyfluidsynth versions also fall back to `$HOMEBREW_PREFIX/lib` — but
only when that environment variable is set, which it isn't for scripts run
outside a brew-configured shell, cron jobs, or IDEs. The shim covers every
case. On Linux the same trick applies with `libfluidsynth.so` if you've built
from source into a nonstandard prefix.)

## The core idea: an event loop that pulls samples

FluidSynth's Python binding gives you two primitives that matter:
`fs.noteon(channel, note, velocity)` / `fs.noteoff(channel, note)`, and
`fs.get_samples(n)`, which returns the next `n` frames of interleaved stereo
audio — samples alternating left, right, left, right — *with all
currently-sounding notes rendered into it*.

That suggests a dead-simple, perfectly sample-accurate renderer: sort your
events by time, and alternate between "pull samples up to the next event" and
"fire the event."

```python
import numpy as np
import fluidsynth

SR = 44100

def render_bus(events, total_secs, sf2_path, setup):
    """Render one bus. `events` is a list of
    (sample_pos, 'on'|'off', channel, note, velocity) tuples.
    `setup(fs, sfid)` configures programs and CCs on a fresh synth."""
    n_samples = int(total_secs * SR)
    fs = fluidsynth.Synth(samplerate=float(SR))
    fs.setting("synth.gain", 0.6)
    sfid = fs.sfload(sf2_path)
    setup(fs, sfid)

    audio = np.zeros(n_samples * 2, dtype=np.float32)   # interleaved stereo
    pos = 0
    for ev in sorted(events, key=lambda e: e[0]):
        sp = min(ev[0], n_samples)
        if sp > pos:                                     # render up to this event
            raw = fs.get_samples(sp - pos)
            end = min(pos * 2 + len(raw), len(audio))
            audio[pos * 2:end] += raw[:end - pos * 2].astype(np.float32) / 32768.0
            pos = sp
        if ev[1] == "on":
            fs.noteon(ev[2], ev[3], ev[4])
        else:
            fs.noteoff(ev[2], ev[3])
    if pos < n_samples:                                  # tail: reverbs, releases
        raw = fs.get_samples(n_samples - pos)
        end = min(pos * 2 + len(raw), len(audio))
        audio[pos * 2:end] += raw[:end - pos * 2].astype(np.float32) / 32768.0
    fs.delete()
    return np.stack([audio[0::2], audio[1::2]])          # (2, n) stereo
```

No timers, no real-time audio driver, no jitter. An event at sample 173,492
fires at *exactly* sample 173,492, every render, forever. This determinism is
the superpower of offline rendering — the same script produces the same
waveform bit-for-bit.

## Setting up the band

The `setup` callback assigns General MIDI programs to channels and sets pan
positions with CC 10 (MIDI "control change" messages; controller 10 is
stereo pan, 0 = left, 64 = center, 127 = right). Each MIDI channel becomes a
band member:

```python
CLEAN_GUITAR = 27   # GM program numbers
MUTED_GUITAR = 28
BASS_PICK    = 34
WARM_PAD     = 89

def setup_gtr(fs, sfid):
    fs.program_select(0, sfid, 0, CLEAN_GUITAR)   # arpeggio guitar on ch 0
    fs.program_select(1, sfid, 0, CLEAN_GUITAR)   # lead on ch 1
    fs.program_select(2, sfid, 0, MUTED_GUITAR)   # palm-muted verses on ch 2
    fs.cc(0, 10, 44)    # pan the arp a little left
    fs.cc(1, 10, 84)    # lead a little right
```

Writing note events is just appending tuples. A helper keeps it readable:

```python
EVENTS = {"gtr": [], "bass": [], "pad": []}

def add_note(bus, t, dur, ch, note, vel):
    EVENTS[bus].append((int(t * SR), "on", ch, note, vel))
    EVENTS[bus].append((int((t + dur) * SR), "off", ch, note, 0))

# Two bars of driving eighth-note bass at 118 BPM:
BEAT = 60.0 / 118
for i in range(16):
    add_note("bass", i * BEAT / 2, BEAT * 0.41, 0, 45, 105 if i % 4 == 0 else 96)
```

## Why one bus per instrument

You could render everything in one FluidSynth pass — but then the mix is
baked. Render **one bus per band member** instead:

```python
gtr  = render_bus(EVENTS["gtr"],  total_secs, SF2, setup_gtr)
bass = render_bus(EVENTS["bass"], total_secs, SF2, setup_bass)
pad  = render_bus(EVENTS["pad"],  total_secs, SF2, setup_pad)
```

Each comes back as its own `(2, n)` array — a stem. Now the
[previous post](/headless-vst3-python.html) pays off: run the guitar bus
through a chorus pedal and a real amp capture, the pad through a slow wash,
compress the bass, and sum them at whatever gains you like:

```python
mix = 1.0 * bass_fx(bass, SR) + 0.85 * gtr_fx(gtr, SR) + 0.5 * pad_fx(pad, SR)
```

A GM soundfont guitar sounds like a GM soundfont guitar — until it goes
through a chorus pedal and a neural capture of a Vox AC15, at which point it
sounds like a guitarist with a very consistent right hand. The soundfont
provides the *notes*; the effects chain provides the *record*.

## Where this leads

MIDI events in, mixed multitrack audio out, deterministic, no DAW process
anywhere in sight. Two pieces are still missing for a full band: plugins that
*won't load* in your process (next post — including the Rosetta trick for
running 2016 Intel-only plugins on Apple Silicon), and drums, which we'll do
with real drum machine one-shots rather than synthesis. Then we put the whole
band together.
