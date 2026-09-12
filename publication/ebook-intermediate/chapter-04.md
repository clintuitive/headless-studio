# Chapter 4 — Rescuing Plugins That Won't Load

Every plugin ecosystem accumulates orphans: plugins that are excellent,
often free, irreplaceable in character — and built for a kind of computer
your Python can't pretend to be. On newer Macs it's plugins compiled for
Intel processors; on Windows it's the beloved 32-bit plugins of the 2000s
that a modern 64-bit Python can't touch; on Linux it's most commercial
plugins, which never shipped for Linux at all.

The fix rests on one idea worth framing: **a process boundary is a
compatibility boundary.** Your script can't *load* an incompatible plugin,
but it can *launch a second program* that can — a small helper process of
whatever type the plugin needs — and trade files with it. This chapter
builds that helper for the hardest everyday case, then shows the same
pattern on the other platforms, and along the way covers two sampler-plugin
gotchas that apply everywhere and cost me an afternoon each.

## The case study

Ample Bass P Lite II: a gorgeous, deeply-sampled Fender bass, free — and,
permanently, a 2016 Intel-only build. A modern Mac runs an "Apple Silicon"
(ARM) processor; a program built for Intel processors simply cannot be
loaded *into* an ARM program. No setting fixes this; it's like trying to
play a Blu-ray in a cassette deck.

But macOS ships a translator called Rosetta 2 that runs *entire Intel
programs* on ARM Macs, seamlessly. It can't translate a plugin inside your
ARM Python — it works on whole processes. So run a whole Intel Python:

```bash
# One-time setup: create an Intel-flavored Python environment.
arch -x86_64 /usr/bin/python3 -m venv ~/.venvs/x86-audio
arch -x86_64 ~/.venvs/x86-audio/bin/pip install pedalboard mido numpy scipy
```

(`arch -x86_64` means "run this as an Intel program"; the system Python
contains both flavors. A *venv* is Python's standard isolated
environment — this one, created by the Intel Python, stays Intel,
including every package installed into it.) You now have two Pythons: your
normal one, and an Intel one for plugin archaeology.

## Keep the interface primitive: files in, files out

The helper program does one job: read a list of notes from a JSON file,
play them through the plugin, write a WAV file. Deliberately no sockets,
no clever inter-process anything — files. Files can be inspected when
something goes wrong (`cat` the JSON; *listen* to the WAV), the helper can
be tested by hand from a terminal, and the overhead — a few milliseconds —
is nothing against renders measured in seconds.

The note format:

```json
{"duration": 201.3,
 "notes": [{"t": 0.0, "dur": 0.42, "note": 45, "vel": 105}, ...]}
```

The helper, complete:

```python
"""render_helper.py — runs under the Intel Python.
Usage: python render_helper.py notes.json out.wav"""
import json, os, sys
import numpy as np
from mido import Message
from pedalboard import load_plugin
from scipy.io import wavfile

SR = 44100
PLUGIN = os.path.expanduser(
    "~/Library/Audio/Plug-Ins/Components/ABPL2.component")

def main():
    events_path, out_path = sys.argv[1], sys.argv[2]
    with open(events_path) as f:
        spec = json.load(f)

    plugin = load_plugin(PLUGIN)

    # Warm-up: see "the two gotchas" below.
    warmup = [Message("note_on", note=45, velocity=100, time=0.1),
              Message("note_off", note=45, time=0.6)]
    for attempt in range(8):
        test = plugin(warmup, duration=1.0, sample_rate=SR,
                      buffer_size=8192, reset=False)
        if float(np.abs(test).max()) > 0.001:   # did any sound come out?
            break
    else:
        sys.exit("plugin produced no audio after warm-up attempts")

    # Convert the JSON notes into MIDI messages.
    msgs = []
    for n in spec["notes"]:
        msgs.append(Message("note_on", note=n["note"],
                            velocity=n["vel"], time=n["t"]))
        msgs.append(Message("note_off", note=n["note"],
                            time=n["t"] + n["dur"]))
    msgs.sort(key=lambda m: m.time)

    audio = plugin(msgs, duration=spec["duration"], sample_rate=SR,
                   buffer_size=8192, reset=False)
    if float(np.abs(audio).max()) < 0.001:
        sys.exit("plugin rendered silence")
    wavfile.write(out_path, SR,
                  (np.clip(audio.T, -1, 1) * 32767).astype(np.int16))

if __name__ == "__main__":
    main()
```

One design point to steal: both failure checks measure **audio, not
success codes**. `np.abs(test).max()` asks "what was the loudest sample?" —
because a sampler's signature failure is to load happily, report success,
and produce silence. Only listening (numerically) catches it.

## The caller, and the dignity of a fallback

Back in your normal script, running the helper is Python's standard
`subprocess` module — launch a program, wait, check the result:

```python
import json, os, subprocess, tempfile
from scipy.io import wavfile

X86_PYTHON = os.path.expanduser("~/.venvs/x86-audio/bin/python")

def render_ample_bass(notes, total_secs):
    """Returns stereo audio, or None if the helper fails."""
    with tempfile.TemporaryDirectory() as td:      # auto-cleaned temp folder
        ev = os.path.join(td, "in.json")
        stem = os.path.join(td, "out.wav")
        with open(ev, "w") as f:
            json.dump({"duration": total_secs, "notes": notes}, f)
        result = subprocess.run(
            ["arch", "-x86_64", X86_PYTHON, "render_helper.py", ev, stem],
            capture_output=True, text=True)
        if result.returncode != 0:
            print("helper failed, falling back:", result.stderr.strip())
            return None
        _, data = wavfile.read(stem)
    return (data.astype("float32") / 32768.0).T
```

And at the call site:

```python
bass = render_ample_bass(bass_notes, total_secs)
if bass is None:
    bass = render_bus(bass_events, total_secs, SF2, setup_bass)  # Chapter 2
```

That `if` is a production philosophy. The deep-sampled bass is *better*;
the Chapter 2 SoundFont bass is *always available*. The song always
renders — on a bad day the bass just sounds slightly less expensive, and
the console says why. When your pipeline runs unattended, every luxury
needs a boring understudy.

## The two gotchas that cost an afternoon each

Both apply to any sampler that streams its sound files from disk (most
sampled pianos, basses, and orchestral instruments), no matter how you
host it.

**Gotcha 1: disk streamers start silent.** These plugins load instantly
but keep their samples on disk, read by a background thread. In a DAW,
that thread has warmed up long before a human presses play. A script
renders *immediately* — and captures silence. Hence the warm-up loop:
render a short throwaway phrase repeatedly until sound actually comes out.
In my logs it's never needed more than two attempts; the loop shape means
a genuinely broken install fails with a clear message instead of a silent
bass track.

**Gotcha 2: pass `reset=False`, always, for these plugins.** By default,
pedalboard *resets* a plugin to factory-fresh state on every call — a
sensible default for effects. For a disk streamer it means the warm-up you
just did is thrown away before the real render. The symptom is maddening:
warm-up works, real render is silent, no error anywhere. `reset=False`
keeps the same living plugin across all the calls. This one keyword
argument is the most expensive thing this book knows, per character.

## The same trick elsewhere

**Linux:** the tool [yabridge](https://github.com/robbert-vdh/yabridge)
runs *Windows* plugins on Linux (via the Wine compatibility layer) and
presents them as normal Linux plugins — the incompatible code is already
isolated in its own process. After `yabridgectl sync`, `load_plugin`
just sees them.

**Windows:** for a 32-bit plugin, install a 32-bit Python alongside your
64-bit one and run the *identical* helper script under it:

```python
subprocess.run([r"C:\Python311-32\python.exe", "render_helper.py", ev, stem])
```

Notice what changed across all three platforms: nothing in the helper.
Only *which interpreter runs it*. Compatibility is a property of the
process, so pick the right process per plugin.

## The bonus that becomes the reason

Old plugins crash. When a plugin lives inside your script's process, its
crash *is your crash* — the whole pipeline dies mid-album, uncatchably.
When it lives in a helper process, the same crash is just a non-zero
return code: log it, fall back, finish the record. Professional DAWs
(Bitwig, Reaper) evolved this exact per-plugin sandboxing after decades of
crashes; we get it free because we started at the boundary.

Two loaders in two chapters, plus a rescue procedure for the ones that
resist. Next: several gigabytes of professionally recorded instruments
that are probably already on your Mac — locked in a file format nobody
documented. We're going to document it.
