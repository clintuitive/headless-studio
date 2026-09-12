# Chapter 3 — Real Plugins, No DAW

Chapter 2 ended with a complaint: our instruments play correct notes into
sterile air. The audio industry solved sterile air decades ago, and the
solution is the **plugin** ecosystem — forty years of amplifier simulation,
reverbs, compressors, and synthesizers, shipped as small installable
programs (the formats are called VST3 and Audio Unit). Everyone assumes
plugins belong to DAWs. They don't. A plugin is a code library with a
standard interface; a DAW is one program that calls it, and your script can
be another. By the end of this chapter you'll run the same neural-network
amp simulation that professional guitarists record with — from Python, no
window, no clicking — and learn a trick for controlling even the settings
plugins don't officially expose.

## One import gets you a plugin host

Spotify maintains a Python library called
[pedalboard](https://github.com/spotify/pedalboard) that embeds a full
plugin host. Install it (`pip install pedalboard`), and loading a plugin is
one call:

```python
from pedalboard import load_plugin

amp = load_plugin("/path/to/NeuralAmpModeler.vst3")
```

Plugins install into standard folders, so you know where to point that
path:

| Platform | System-wide | Per-user |
|---|---|---|
| macOS | `/Library/Audio/Plug-Ins/VST3` | `~/Library/Audio/Plug-Ins/VST3` |
| Windows | `C:\Program Files\Common Files\VST3` | — |
| Linux | `/usr/lib/vst3` | `~/.vst3` |

Our running example is the free
[Neural Amp Modeler](https://www.neuralampmodeler.com/) (NAM). NAM plays
*capture files* — small neural networks trained to imitate a specific
physical amplifier, made by recording the real hardware. The community has
captured thousands of amps; the Vox AC15 and Fender Twin this book's
records use cost nothing. Let that sink in: a neural model of a vintage
tube amplifier, running in your script.

## Every knob is an attribute

A loaded plugin can tell you about itself:

```python
>>> amp.parameters.keys()
dict_keys(['input_db', 'bass', 'middle', 'treble', 'output_db', ...])
```

Each parameter — each knob you'd see in the plugin's window — becomes a
Python attribute you can read and set:

```python
amp.input_db = -3.0    # how hard the guitar drives the amp
```

Two habits will save you grief. First, check a parameter's allowed range
before setting it (printing `amp.parameters['input_db']` shows it) —
plugins measure knobs in decibels, percent, or arbitrary units as they
please. Second, read the value back after setting: some plugins snap your
value to the nearest allowed step, and the snapped value is what you'll
actually hear.

About that `-3.0`: it holds the AC15 *just below* the point where it
starts to distort, so that how hard each note is played decides, note by
note, whether it stays clean or barks. One number, and it's the difference
between polite and alive.

## Processing audio

A loaded plugin is *callable* — you use it like a function:

```python
amped = amp(guitar_audio, 44100)    # stereo array in, stereo array out
```

Chains of effects compose with a `Pedalboard`, which is a list of effects
that acts like a single one:

```python
from pedalboard import Pedalboard, Chorus, Delay, Reverb

rig = Pedalboard([
    Chorus(rate_hz=0.8, depth=0.2, mix=0.5),      # pedal in front of the amp
    amp,                                           # the real VST3
    Delay(delay_seconds=0.318, feedback=0.28, mix=0.16),
    Reverb(room_size=0.85, wet_level=0.24, dry_level=0.76),
])
produced = rig(guitar_audio, 44100)
```

(`Chorus`, `Delay`, and `Reverb` here are pedalboard's built-in effects —
no plugin files needed.) Order matters exactly like it does on a
guitarist's floor: chorus *before* the amp gives the amp a shimmering
signal to distort; chorus *after* the amp wobbles the already-distorted
sound — a different, swooshier effect. In a DAW, trying both means
re-cabling; here it's reordering a list.

Pedalboard also has routing primitives — `Mix` runs branches in parallel
and adds the results, `Chain` makes a serial branch. We'll use them in
Part II to build a classic studio bass sound (clean signal and distorted
signal side by side). For now just know the console-style wiring exists.

## Instruments too, not just effects

Some plugins *generate* sound from notes rather than processing audio.
Those take a list of timed MIDI messages (note-on and note-off events,
with times in seconds) plus how long to render:

```python
from mido import Message   # mido: a small library for MIDI messages

notes = [Message("note_on",  note=45, velocity=100, time=0.0),
         Message("note_off", note=45,               time=1.5)]
audio = synth_plugin(notes, duration=3.0, sample_rate=44100)
```

This is our second instrument loader (after Chapter 2's), and it will
matter in the next chapter when we rescue a beautiful bass instrument
that happens to be trapped in an outdated plugin.

## The setting that isn't a parameter

Here's where this chapter earns its keep. NAM's most important setting —
*which amp capture file to load* — does **not** appear in
`amp.parameters`. Neither does a sampler plugin's sample folder or a
reverb plugin's room file. File choices live in the plugin's saved
*state*, and state is normally set by clicking around the plugin's window.
We don't have a window. We have two workarounds, and together they handle
every plugin you'll meet.

### The easy way: save the state once, reuse it forever

Pedalboard exposes the plugin's entire saved state as a chunk of raw bytes
called `preset_data` — and it's writable. So: open the plugin's real
window *once* on your own machine, click what needs clicking, then keep
the bytes:

```python
plugin.show_editor()          # opens the actual plugin window; configure it
with open("ac15_setup.preset", "wb") as f:
    f.write(bytes(plugin.preset_data))

# From then on, in any script, no window:
amp = load_plugin(NAM_PATH)
amp.preset_data = open("ac15_setup.preset", "rb").read()
```

This works for any plugin, and if your rig never changes, it's all you
need.

### The powerful way: edit the bytes

The easy way freezes your choice. But Chapter 1 promised for-loops over
amps — *programmatically* swapping capture files. For that we have to open
the black box.

It's less scary than it sounds. The preset bytes have a documented outer
structure, and inside, NAM stores its settings in a simple pattern: a
marker string, then some length-prefixed text fields — including *the file
path of the amp capture*. "Length-prefixed" means each text field is
stored as a number (how many bytes of text) followed by the text itself.
So the surgery is: find the marker, skip one field, and replace the next
field with our own path — updating its length number to match.

Python's built-in `struct` module does the byte-level reading and writing.
Two calls cover everything: `struct.unpack("<i", data)` reads bytes as a
number, and `struct.pack("<i", n)` writes a number as bytes (the `"<i"`
describes the number format — a standard 4-byte integer).

```python
import os, struct
from pedalboard import load_plugin

def load_nam(vst3_path, model_path):
    """Load the NAM plugin with a chosen amp capture pre-selected."""
    p = load_plugin(vst3_path)
    data = bytes(p.preset_data)

    # The preset's table of contents lives at a fixed offset and tells us
    # where the plugin's own state ("component chunk") ends.
    comp_end = struct.unpack("<q", data[40:48])[0]
    comp, tail = data[48:comp_end], data[comp_end:]

    # Find the marker, skip the version field, land on the model path.
    marker = b"###NeuralAmpModeler###"
    i = comp.index(marker) + len(marker)
    version_len = struct.unpack("<i", comp[i:i + 4])[0]
    i += 4 + version_len
    old_len = struct.unpack("<i", comp[i:i + 4])[0]

    # Splice in our path, with its length in front.
    path = os.path.abspath(model_path).encode()
    comp = comp[:i] + struct.pack("<i", len(path)) + path \
                    + comp[i + 4 + old_len:]

    # Our splice changed the chunk's size, so the table of contents at the
    # end must be rebuilt to match — otherwise the plugin silently ignores
    # the whole preset. (Full walkthrough of this stanza in Appendix C.)
    n = struct.unpack("<i", tail[4:8])[0]
    entries = b""
    for k in range(n):
        e = tail[8 + k * 20:8 + (k + 1) * 20]
        chunk_id = e[:4]
        if chunk_id == b"Comp":
            off, size = 48, len(comp)
        else:
            off = 48 + len(comp)
            size = struct.unpack("<qq", e[4:20])[1]
        entries += chunk_id + struct.pack("<qq", off, size)

    p.preset_data = (data[:40] + struct.pack("<q", 48 + len(comp)) + comp
                     + b"List" + struct.pack("<i", n) + entries)
    return p

amp = load_nam(NAM_VST3, "captures/Vox_AC15_TopBoost.nam")
```

Every guitar and bass note on this book's records passes through that
function. And note the failure mode the table-of-contents rebuild
prevents: get it wrong and there's **no error** — the plugin just quietly
uses its default sound. When byte surgery misbehaves, suspect the
bookkeeping before the splice.

If you ever need this trick on a different plugin: save two presets that
differ only in the file path, and compare the bytes. The region that
differs *is* the path field, and the bytes around it reveal the pattern.

## Practical notes

- **A plugin instance is stateful.** Don't share one instance between two
  effect chains; load a fresh one per chain. Loading is cheap.
- **Some plugins report latency** (they delay the signal to look ahead);
  pedalboard compensates automatically when rendering.
- **Determinism holds.** Amp sims, EQs, and compressors give identical
  output for identical input — your renders stay reproducible.

Two loaders down. But this chapter quietly assumed the plugin *loads* on
your machine. The best bass instrument I know is built for a kind of
processor my Mac doesn't have — and the next chapter is about refusing to
take that for an answer.
