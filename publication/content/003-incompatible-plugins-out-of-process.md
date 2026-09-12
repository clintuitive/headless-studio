---
title: "The Plugin Won't Load? Run It in Another Process"
date: 2026-07-02
slug: incompatible-plugins-out-of-process
description: "Host Intel-only plugins on Apple Silicon via a Rosetta subprocess, Windows VSTs on Linux via yabridge, and 32-bit relics anywhere — the process boundary is a compatibility boundary. Plus two hard-won fixes for disk-streaming sample plugins."
---

Some of the best instrument plugins are old. My favorite free bass — Ample
Bass P Lite II, a beautifully sampled P-bass — is a 2016 **Intel-only** build.
On an Apple Silicon Mac, an arm64 Python process flatly cannot load it: you
can't mix architectures inside one process.

The fix is to stop trying. **A process boundary is a compatibility boundary.**
Run the plugin in a small helper process of whatever architecture (or OS
translation layer) it needs, and talk to it with files: JSON note events in,
WAV stem out. This post builds that helper for the macOS/Rosetta case, then
maps the same pattern onto Linux and Windows.

## macOS: the Rosetta subprocess

Rosetta 2 will happily run an entire x86_64 Python interpreter, which will
happily load an Intel-only Audio Unit (Apple's plugin format) or VST3. Setup, once:

```bash
# Install an Intel-arch Python venv alongside your arm64 one.
arch -x86_64 /usr/bin/python3 -m venv ~/.venvs/x86-audio
arch -x86_64 ~/.venvs/x86-audio/bin/pip install pedalboard mido numpy scipy
```

The helper script does one job — read a JSON note list, play it through the
plugin, write a WAV:

```python
"""render_helper.py — runs under the x86_64 Python via `arch -x86_64`.
Usage: python render_helper.py <events.json> <out.wav>
JSON: {"duration": secs, "notes": [{"t": s, "dur": s, "note": midi, "vel": 1-127}]}
"""
import json, os, sys
import numpy as np
from mido import Message
from pedalboard import load_plugin
from scipy.io import wavfile

SR = 44100
PLUGIN = os.path.expanduser("~/Library/Audio/Plug-Ins/Components/ABPL2.component")

def main():
    events_path, out_path = sys.argv[1], sys.argv[2]
    with open(events_path) as f:
        spec = json.load(f)

    plugin = load_plugin(PLUGIN)

    # Warm-up: see "the two quirks" below.
    warmup = [Message("note_on", note=45, velocity=100, time=0.1),
              Message("note_off", note=45, time=0.6)]
    for attempt in range(8):
        test = plugin(warmup, duration=1.0, sample_rate=SR,
                      buffer_size=8192, reset=False)
        if float(np.abs(test).max()) > 0.001:
            break
    else:
        sys.exit("plugin produced no audio after warm-up attempts")

    msgs = []
    for n in spec["notes"]:
        msgs.append(Message("note_on", note=n["note"], velocity=n["vel"], time=n["t"]))
        msgs.append(Message("note_off", note=n["note"], time=n["t"] + n["dur"]))
    msgs.sort(key=lambda m: m.time)

    audio = plugin(msgs, duration=spec["duration"], sample_rate=SR,
                   buffer_size=8192, reset=False)
    if float(np.abs(audio).max()) < 0.001:
        sys.exit("plugin rendered silence")
    wavfile.write(out_path, SR, (np.clip(audio.T, -1, 1) * 32767).astype(np.int16))

if __name__ == "__main__":
    main()
```

And the caller, in your normal arm64 render script:

```python
import json, os, subprocess, tempfile
from scipy.io import wavfile

X86_PYTHON = os.path.expanduser("~/.venvs/x86-audio/bin/python")

def render_out_of_process(notes, total_secs):
    """Returns a (2, n) float array, or None so the caller can fall back."""
    with tempfile.TemporaryDirectory() as td:
        events, stem = os.path.join(td, "in.json"), os.path.join(td, "out.wav")
        with open(events, "w") as f:
            json.dump({"duration": total_secs, "notes": notes}, f)
        result = subprocess.run(
            ["arch", "-x86_64", X86_PYTHON, "render_helper.py", events, stem],
            capture_output=True, text=True)
        if result.returncode != 0:
            print(f"helper failed, falling back:\n{result.stderr.strip()}")
            return None
        _, data = wavfile.read(stem)
    return (data.astype("float32") / 32768.0).T
```

Note the shape of the failure path: the caller **falls back** (in my pipeline,
to a FluidSynth rendering of the same notes) rather than dying. Your render
always completes; the bass just sounds slightly less expensive on a bad day.

## The two quirks that will eat your afternoon

These apply to *any* sampler plugin that streams its samples from disk
(Kontakt-style instruments, most sampled basses and pianos), on every
platform:

**1. Disk streamers render silence until they've spun up.** The plugin loads
instantly, reports ready, and produces zeros — its background streaming thread
hasn't filled its buffers yet. Offline rendering doesn't wait for wall-clock
time, so you must: render a short throwaway phrase in a loop until audio
actually comes out (the warm-up block above).

**2. `reset=False` on every call.** Pedalboard's default `reset=True` tears
down and rebuilds the plugin processor on each call — which discards the
streamer you just warmed up, forever. Passing `reset=False` keeps the same
live instance across the warm-up calls *and* the real render. This one flag
is the difference between "works perfectly" and "renders silence with no
error message."

## Linux: Windows plugins via yabridge

Same pattern, different bridge. [yabridge](https://github.com/robbert-vdh/yabridge)
runs Windows VST3/VST2 plugins on Linux through Wine, exposing them as native
Linux `.so` plugins:

```bash
yay -S yabridge yabridgectl wine-staging     # Arch; see the repo for apt/dnf
yabridgectl add "$HOME/.wine/drive_c/Program Files/Common Files/VST3"
yabridgectl sync
```

After `sync`, the bridged plugins appear in `~/.vst3` and `load_plugin` treats
them like any native plugin — yabridge already runs the Windows code
out-of-process for you. For flakier plugins, the JSON-in/WAV-out helper
pattern above adds crash isolation on top.

## Windows: the 32-bit relics

Windows Python is 64-bit; that beloved 2009-era 32-bit VST2 can't load into
it. Identical solution: install a 32-bit Python, put the helper script behind
it, and call it with `subprocess.run([r"C:\Python39-32\python.exe", ...])`.
No `arch` prefix needed — the interpreter's own architecture does the work.

## The bonus you get for free: crash isolation

Old plugins crash. When a plugin lives in your render process, it takes your
whole pipeline down with a segfault you can't catch. When it lives in a
subprocess, a crash is just a nonzero return code — you log it, fall back,
and the render finishes. I now run *every* third-party instrument
out-of-process on principle; DAWs like Bitwig and Reaper arrived at the same
architecture for the same reason.

Next in the series: the drum machine that never needed a plugin at all, and
[the 6.7 GB of sampled instruments hiding inside GarageBand](/garageband-exs-extraction.html).
