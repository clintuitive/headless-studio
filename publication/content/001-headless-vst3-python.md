---
title: Driving VST3 Plugins Headlessly from Python
date: 2026-07-02
slug: headless-vst3-python
description: Load real VST3 plugins — amp sims, synths, effects — in a Python script with no DAW and no GUI, on macOS, Windows, and Linux. Including how to set plugin state that isn't exposed as a parameter.
---

Every DAW is, at its core, a program that feeds audio buffers through plugins
and writes the result to disk. There is no law that says that program needs a
timeline, a mixer view, or a window at all. This post shows how to host real
VST3 plugins — the same Neural Amp Modeler, synths, and effects you'd use in
Logic or Reaper — directly from a Python script, and render audio through them
with one function call.

Everything here works on **macOS, Windows, and Linux**. The only dependency is
Spotify's [pedalboard](https://github.com/spotify/pedalboard) library, which
embeds the JUCE plugin host behind a NumPy-friendly API:

```bash
pip install pedalboard numpy
```

## Loading a plugin

VST3 plugins install to a standard location per platform:

| Platform | System-wide | Per-user |
|---|---|---|
| macOS | `/Library/Audio/Plug-Ins/VST3` | `~/Library/Audio/Plug-Ins/VST3` |
| Windows | `C:\Program Files\Common Files\VST3` | — |
| Linux | `/usr/lib/vst3` | `~/.vst3` |

Loading one is a single call. I'll use the free
[Neural Amp Modeler](https://www.neuralampmodeler.com/) (NAM) plugin as the
running example, because a neural network trained on a real tube amp is the
most dramatic possible demo of "professional tool, no GUI":

```python
import platform, os
from pedalboard import load_plugin

VST3 = {
    "Darwin":  os.path.expanduser("~/Library/Audio/Plug-Ins/VST3/NeuralAmpModeler.vst3"),
    "Windows": r"C:\Program Files\Common Files\VST3\NeuralAmpModeler.vst3",
    "Linux":   os.path.expanduser("~/.vst3/NeuralAmpModeler.vst3"),
}[platform.system()]

amp = load_plugin(VST3)
print(amp.parameters.keys())
```

That last line prints every automatable parameter the plugin exposes —
`input_db`, `bass`, `middle`, `treble`, `output_db` and friends — and each one
is now a plain Python attribute:

```python
amp.input_db = -3.0   # keep a Vox AC15 just below break-up
```

## Processing audio

A plugin instance is callable. Give it a `(channels, samples)` NumPy array and
a sample rate, get the processed audio back:

```python
import numpy as np
from scipy.io import wavfile

sr, di = wavfile.read("guitar_di.wav")   # DI = "direct input": guitar recorded straight in, no amp
di = di.astype(np.float32) / 32768.0            # int16 -> float32
if di.ndim == 1:
    di = np.stack([di, di])                     # mono -> stereo
else:
    di = di.T                                   # (n, 2) -> (2, n)

amped = amp(di, sr)                             # <- the entire amp rig

wavfile.write("guitar_amped.wav", sr, (amped.T * 32767).astype(np.int16))
```

That's it. Here is a dry plucked chord and the same audio after `amp(di, sr)`
through an AC15 Top Boost capture — note the sustain and compression in the
waveform, and the harmonic saturation reshaping the spectrum:

![Dry DI versus the same audio through a NAM amp capture](/images/nam_before_after.png)

Chain plugins — including pedalboard's own built-in effects — in a
`Pedalboard`, which is itself callable and behaves like one big plugin:

```python
from pedalboard import Pedalboard, Chorus, Delay, Reverb

rig = Pedalboard([
    Chorus(rate_hz=0.8, depth=0.2, mix=0.5),   # pedal in front of the amp
    amp,                                        # the real VST3
    Delay(delay_seconds=0.318, feedback=0.28, mix=0.16),
    Reverb(room_size=0.85, wet_level=0.24, dry_level=0.76),
])
produced = rig(di, sr)
```

Pedal order matters exactly like it does on a real pedalboard: chorus in front
of the amp is a different sound than chorus in the loop.

## Instruments: MIDI in, audio out

Instrument plugins take a list of MIDI messages instead of audio. Note times
are in seconds:

```python
from mido import Message

synth = load_plugin("path/to/Vital.vst3")   # any VST3 instrument
notes = [
    Message("note_on",  note=45, velocity=100, time=0.0),
    Message("note_off", note=45,               time=1.5),
]
audio = synth(notes, duration=3.0, sample_rate=44100)
```

## When the setting you need isn't a parameter

Here's where headless hosting gets interesting. NAM's most important setting —
*which amp capture file to load* — is **not** an automatable parameter. It
lives in the plugin's saved state, normally set by clicking a file picker in
the GUI. No GUI, no file picker.

The escape hatch: pedalboard exposes the plugin's entire serialized state as
`plugin.preset_data` (raw VST3 preset bytes), and you can write it as well as
read it. NAM is built on the iPlug2 framework, whose state chunk is
documented-by-source: a `###NeuralAmpModeler###` marker, a version string,
then two length-prefixed strings — the model path and the IR path, each
stored as a byte count followed by the text — then the parameter values. So we load the plugin, splice our model path into a
fresh copy of its own preset, and hand it back:

```python
import struct

def load_nam(vst3_path, model_path):
    """Load the NAM VST3 with an amp capture pre-selected."""
    p = load_plugin(vst3_path)
    pd = bytes(p.preset_data)
    # VST3 preset container: header, component chunk, then a 'List' index.
    list_off = struct.unpack("<q", pd[40:48])[0]
    comp, tail = pd[48:list_off], pd[list_off:]
    # iPlug2 state: marker, version string, then the model path string.
    i = comp.index(b"###NeuralAmpModeler###") + len(b"###NeuralAmpModeler###")
    vlen = struct.unpack("<i", comp[i:i + 4])[0]
    i += 4 + vlen
    mlen = struct.unpack("<i", comp[i:i + 4])[0]
    path = os.path.abspath(model_path).encode()
    comp = comp[:i] + struct.pack("<i", len(path)) + path + comp[i + 4 + mlen:]
    # Rebuild the 'List' index so chunk offsets/sizes stay consistent.
    n = struct.unpack("<i", tail[4:8])[0]
    entries = b""
    for k in range(n):
        e = tail[8 + k * 20:8 + (k + 1) * 20]
        eid = e[:4]
        off, size = (48, len(comp)) if eid == b"Comp" else (
            48 + len(comp), struct.unpack("<qq", e[4:20])[1])
        entries += eid + struct.pack("<qq", off, size)
    p.preset_data = (pd[:40] + struct.pack("<q", 48 + len(comp)) + comp
                     + b"List" + struct.pack("<i", n) + entries)
    return p

amp = load_nam(VST3, "captures/Vox_AC15_TopBoost.nam")
```

This exact function renders every guitar and bass track on my generated
albums. Two takeaways generalize beyond NAM:

1. **`preset_data` is the universal backdoor.** Any state a plugin saves —
   sample paths, wavetables, IR files — travels through it.
2. **You don't always need to reverse-engineer.** The lazy version: open the
   plugin GUI *once* (locally, `plugin.show_editor()` pops the real editor),
   configure it, save `bytes(plugin.preset_data)` to a file, and reload those
   bytes in your headless script forever after. The byte-splicing above is
   only necessary when you want to swap files programmatically — say, one
   script rendering through six different amps.

## Why bother?

Because once a plugin is a Python object, everything composes. Render the same
DI through ten amp captures in a loop and A/B them. Grid-search a compressor's
attack against your mix bus. Batch-process 400 podcast episodes. Or — where
this series is headed — generate an entire band's performance as MIDI events
and render it through real amps into a finished, mixed record, from one
script, with no DAW open.

Next up: [the instrument side — rendering MIDI through FluidSynth, sample-accurately, one bus per band member](/fluidsynth-midi-python.html).
