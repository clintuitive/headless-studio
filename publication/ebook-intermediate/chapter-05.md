# Chapter 5 — The Treasure in GarageBand: Reading an Undocumented Format

Implementation update: use `music_engine.samplers.ExsSampler` for the
maintained sampler. It converts source sample rates, centers unsigned 8-bit
PCM, and can preserve stereo with `stereo_output=True`. Legacy five-field
events pair overlapping note-offs FIFO; an optional sixth voice ID supports
explicit overlapping voices. Velocity-zero note-ons act as note-offs.
The simplified reader below explains the format, not every production guard.

If you have a Mac with GarageBand's sound library installed, you're
sitting on several gigabytes of professionally recorded instruments: a
Steinway grand piano, drum kits recorded in real rooms, a Mellotron (the
tape-based keyboard from every Beatles record you're thinking of),
electric and acoustic guitars sampled fret by fret. All of it is locked in
Apple's **EXS format** — no export button, no documentation, no API.

This chapter picks the lock. We'll reverse-engineer the format, extract
the instruments, and then build the piece no one else writes about: a
working *sampler* — the program that turns a folder of extracted
recordings back into a playable instrument — in about ninety lines. Two of
this book's albums run on it.

Apple's current [GarageBand license, sections 2G and 2I](https://www.apple.com/legal/sla/docs/GarageBand.pdf)
permits certain original soundtrack uses, but also restricts standalone
extraction, use outside the software's intended context, redistribution and
reverse engineering, subject to the exceptions in those terms and applicable
law. Permission to distribute a finished composition is not blanket permission
to extract factory samples for another renderer. This format walkthrough does
not establish that permission. Use the parser with files you created or have
explicit permission to parse and extract; no Apple software or sample content
is included in this repository.

## What's actually on disk

```text
/Library/Application Support/GarageBand/Instrument Library/Sampler/
├── Sampler Instruments/     the .exs files — small "map" files
└── Sampler Files/           the audio — often many hits packed into
                             one big container file
```

The audio files are often *consolidated*: dozens of individual recordings
packed end-to-end into one container. That's why you can't just browse the
folders and grab WAVs — without the map, you don't know where one piano
note ends and the next begins. The `.exs` map file knows. So the map is
what we parse.

## How you read a format nobody documented

A `.exs` file is **binary** — raw bytes, not text. Binary formats sound
intimidating, but most are just C structures written straight to disk:
fixed-size records whose fields live at known offsets. The whole game is
learning the offsets. (How does anyone learn them without documentation?
Patient hex-dumping: change one thing in the app, save, and see which
bytes changed. What follows is the result of that process so you don't
have to repeat it.)

An EXS file is a sequence of *chunks*. Every chunk starts with the same
84-byte header:

| bytes | meaning |
|---|---|
| 0–3 | flags — the chunk's *kind* hides in byte 3 |
| 4–7 | size of the data that follows (a 4-byte integer) |
| 8–15 | id + padding |
| 16–19 | the magic marker `TBOS` — how we know we're aligned |
| 20–83 | the chunk's name, as text padded with zeros |

Three kinds of chunk matter:

- **Zones** (kind 1) — one playable region each: *which key range*, *which
  velocity range* (how hard the key is hit), and — crucially — *the exact
  start and end position, in samples, inside which audio file*.
- **Groups** (kind 2) — named categories of zones ("hits", "palm-mute",
  or a Mellotron tape bank name).
- **Samples** (kind 3) — the audio files being referenced, by name.

Python reads binary with the built-in `struct` module — you met it in
Chapter 3. `struct.unpack_from("<I", data, offset)` means "read a 4-byte
unsigned integer at this offset." Single bytes can be read by plain
indexing: `data[pos + 3]` is a number 0–255.

```python
import struct

def parse_exs(path):
    data = open(path, "rb").read()          # "rb": read as raw bytes
    zones, samples, groups = [], [], []
    pos = 0
    while pos + 84 <= len(data):
        if data[pos + 16:pos + 20] != b"TBOS":
            pos += 1        # not aligned on a chunk — slide forward and resync
            continue
        kind = data[pos + 3] & 0x0F         # keep only the low bits of byte 3
        size = struct.unpack_from("<I", data, pos + 4)[0]
        name = data[pos + 20:pos + 84].split(b"\x00")[0].decode("ascii", "replace")
        body = data[pos + 84:pos + 84 + size]

        if kind == 1 and size >= 96:        # a zone
            zones.append({
                "name": name,
                "root":  body[1],           # the key the sample was recorded at
                "keylo": body[6],  "keyhi": body[7],
                "vello": body[9],  "velhi": body[10],
                "start": struct.unpack_from("<I", body, 12)[0],
                "end":   struct.unpack_from("<I", body, 16)[0],
                "group_idx":  struct.unpack_from("<I", body, 88)[0],
                "sample_idx": struct.unpack_from("<I", body, 92)[0],
            })
        elif kind == 2:                     # a group name
            groups.append(name)
        elif kind == 3:                     # an audio file reference
            samples.append(name)
        pos += 84 + size

    for z in zones:                         # attach group names to zones
        z["group"] = groups[z["group_idx"]] if z["group_idx"] < len(groups) else ""
    return zones, samples
```

That byte-by-byte "resync" when the magic marker isn't where we expect is
inelegant and necessary — some files carry padding between chunks, and a
parser that trusts arithmetic alone walks off a cliff mid-file.

Run this on a factory drum kit and you get something wonderful: a complete
map. "MIDI key 38, velocities 80–112, samples 1,204,551 through 1,310,006
of audio file 0." No guesswork; the format *tells* you where every hit
lives, down to the sample.

## Extraction

The container files are Apple's `.caf` format; macOS's built-in
`afconvert` tool converts them to WAV (on other platforms, `ffmpeg` does):

```python
import subprocess, json
from scipy.io import wavfile

subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@44100",
                "Kit_consolidated.caf", "kit.wav"], check=True)
sr, x = wavfile.read("kit.wav")

manifest = []
for i, z in enumerate(zones):
    hit = x[z["start"]:z["end"]]            # slice out one recording, exactly
    fname = f"note{z['keylo']:03d}_vel{z['vello']:03d}-{z['velhi']:03d}_{i:03d}.wav"
    wavfile.write(f"out/{fname}", sr, hit)
    manifest.append({**z, "file": fname})   # the zone info, plus its filename

with open("out/manifest.json", "w") as f:
    json.dump(manifest, f, indent=1)
```

The real deliverable is that `manifest.json` — the zone map, preserved as
readable JSON next to the extracted WAVs. The folder becomes a
self-describing instrument: audio plus map. Everything downstream reads
the manifest, never the filenames.

## Building the sampler

Extracting samples is where most write-ups stop. But a folder of WAVs
isn't an instrument until something can *play* it. Here's what a sampler
actually has to do — and it's less magic than the products suggest:

1. Given a note and how hard it's played, **choose the right recording**.
2. **Re-pitch it** if the exact note wasn't sampled.
3. **End it gracefully** when the note is released.

Choosing the recording is a filter over the manifest:

```python
class ExsSampler:
    def __init__(self, sample_dir, groups=None):
        with open(os.path.join(sample_dir, "manifest.json")) as f:
            self.zones = json.load(f)
        if groups:   # keep only zones whose group name matches
            self.zones = [z for z in self.zones
                          if any(g in z["group"] for g in groups)]
        self.dir = sample_dir
        self.cache = {}

    def _pick_zone(self, note, vel):
        candidates = [z for z in self.zones
                      if z["keylo"] <= note <= z["keyhi"]]
        by_vel = [z for z in candidates
                  if z["vello"] <= vel <= z["velhi"]] or candidates
        return by_vel[int(rng.integers(len(by_vel)))]
```

Read `_pick_zone` slowly — it's the entire intelligence of every sampler
you've ever bought, in a few lines. Filter by key range. Filter by
velocity, which selects among the *soft, medium, and hard recordings* the
library actually contains — this is why sampled instruments respond to
touch. And when several recordings survive both filters, they're alternate
takes of the same note, and picking one at random is the industry's
**round-robin** trick: it prevents rapid repeated notes from sounding like
a stuck record (the dreaded "machine-gun effect").

Re-pitching is one formula. Playing a recording faster raises its pitch:
to shift by `k` semitones, read it `2^(k/12)` times faster. The code reads
the recording at fractional positions, interpolating between neighboring
samples:

```python
    def _play(self, zone, note):
        data = self._load(zone["file"])
        ratio = 2.0 ** ((note - zone["root"]) / 12.0)   # speed factor
        idx = np.arange(int(len(data) / ratio)) * ratio  # fractional positions
        i0 = np.floor(idx).astype(int)                   # sample before
        i1 = np.minimum(i0 + 1, len(data) - 1)           # sample after
        frac = (idx - i0).astype(np.float32)
        return data[i0] * (1 - frac) + data[i1] * frac   # blend between them
```

(This is why real libraries sample every two or three keys — so no
recording ever gets stretched far enough to sound like a chipmunk.)

Ending gracefully: keep the recording's own natural decay — that decay
*is* the instrument — and only if the note is released early, fade the
last 90 milliseconds to zero. A synthetic volume envelope pasted over a
sampled piano is precisely how cheap keyboards sound cheap.

## One extraction, many instruments

That `groups` argument in the constructor multiplies your instruments for
free. The Mellotron extraction's groups are its tape banks — so
`ExsSampler(mello_dir, groups=["Strings"])` and `groups=["Choir"]` are
*different band members* from one folder, exactly how the original
hardware's swappable tape frames worked. The acoustic guitar uses it in
reverse: excluding the "palm-mute" group keeps the muted articulations
from randomly round-robining into open strums.

And a bonus trick from the codebase: a three-line filter that makes a
guitar sample sound like it's being heard through a different *pickup
position* — physics says a pickup subtracts a delayed copy of the string's
vibration from itself, and code can do exactly that subtraction. One
extracted Stratocaster became two usable guitar characters. (The full
version is in the companion code.)

## What this buys

On this book's albums: the Steinway carries an entire piano record; the
Mellotron banks pad half the synth record; the extracted Strat answers
lead lines. After extraction there is *no plugin in the signal path* —
just JSON and array math — which means Chapter 4's compatibility worries
simply don't exist for these instruments, on any platform, forever.

Next up: the one band member that was never anything *but* a sample
player — and why that's a feature to lean into rather than an economy to
apologize for.
