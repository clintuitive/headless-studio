# Chapter 5 — Build a Sample Instrument from Your Own Sounds

A sampler plays recordings at different pitches. That's the whole trick, and it
has been the whole trick since the 1970s. The recording might be a piano note,
a struck wine glass, a drum hit, or a tone a program invented forty
milliseconds ago — the player doesn't care. Once the sound exists as a WAV
file, the player only needs a map: which file answers this note, how fast
should it play, and when should it stop?

Commercial sample libraries are enormous and genuinely clever, and they make
this look like deep magic. It isn't. It's a folder of WAVs and a lookup table,
and by the end of this chapter you'll have built one and the mystery will be
gone for good.

We'll use sounds we generate ourselves. No commercial library, no undocumented
file format, nothing to download and nothing to read a licence for first.

## Make a small instrument

From the repository root, install the core dependencies and run:

```bash
python -m pip install -r requirements.txt
python scripts/generate_sampler_demo.py --output-dir Tracks/sampler-demo
```

What lands is an instrument and a short performance of it:

```text
Tracks/sampler-demo/
  demo.wav
  instrument/
    manifest.json
    provenance.json
    tone-48-soft.wav
    tone-48-bright.wav
    tone-60-soft.wav
    tone-60-bright.wav
    tone-72-soft.wav
    tone-72-bright.wav
```

The script synthesizes all six recordings. Nothing is copied from a factory
library and no plugin is involved. The complete runnable implementation is
`scripts/generate_sampler_demo.py`; what follows explains the decisions inside
it rather than reprinting it line by line.

## A recording is an array

Chapter 2 established the shape of digital audio: a sample rate of 44,100 means
one second holds 44,100 amplitude values per channel. To lay out two seconds of
time coordinates:

```python
sample_rate = 44100
t = np.arange(sample_rate * 2, dtype=np.float64) / sample_rate
```

Every position in `t` is a moment, measured in seconds. A sine wave at some
frequency is then `np.sin(2 * np.pi * frequency * t)` — frequency being cycles
per second, so doubling it raises the pitch by exactly one octave. That
relationship is the reason the equal-tempered keyboard is built from twelfth
roots of two, and the reason this one line of arithmetic keeps reappearing:

```python
frequency = 440 * 2 ** ((root - 69) / 12)
```

MIDI note 69 is the A at 440 Hz. Twelve semitone steps double the frequency.
We generate roots at 48, 60 and 72 — an octave apart — so the player always
has a nearby recording to work from, rather than stretching one sound across
the entire keyboard and making everything above middle C sound like a chipmunk.

## Give the sound a beginning and an ending

A tone that jumps straight from silence to a nonzero value clicks. You've heard
it; it's the sound of a waveform being cut with scissors. The fix is an
**envelope**: an array of gains that shapes the amplitude over time. Ours uses
a fast attack and a longer exponential decay:

```python
envelope = (1 - np.exp(-t / .008)) * np.exp(-t / .65)
```

The first factor rises from zero — that's the attack, eight milliseconds of it.
The second falls toward zero, a decay with a time constant of 0.65 seconds.
Multiply them and you get something struck and fading, which is a surprisingly
large fraction of all the instruments there are. The full generator also fades
the last 441 frames (ten milliseconds) to zero, so the file itself ends
smoothly no matter where the decay got to.

Each pitch gets two timbres:

```python
signal = .5 * envelope * (
    np.sin(2 * np.pi * frequency * t)
    + overtone * np.sin(4 * np.pi * frequency * t)
)
```

That second sine is an octave above the fundamental. Set `overtone` to `.08`
for the soft layer and `.3` for the bright one. This is the point of a velocity
layer, and it's worth being precise about: a harder-played note doesn't just
get louder, it gets *brighter*, because hitting something harder excites more
high harmonics. A real multi-sampled instrument changes far more dramatically
between its soft and hard layers than our two sine waves do — but the principle
is identical, and now you can hear it working.

SciPy writes the source as floating-point WAV:

```python
wavfile.write(path, sample_rate, signal.astype(np.float32))
```

That preserves working precision. It is not the format our albums are delivered
in; conversion and mastering are their own stage, several chapters away.

## Map each recording to a zone

A **zone** says where a recording gets used. Its key range selects pitches; its
velocity range selects how hard the note was played. Both ranges are inclusive
in this sampler.

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

Put every zone in a list and save it as `manifest.json`. The bright version
takes the same key range with velocities 80–127. The lower root covers notes
0–53 and the upper covers 66–127 — deliberately broad outer ranges that keep
the demonstration simple, though stretching one recording two octaves or more
sounds about as natural as you'd expect.

`root` is the pitch actually recorded in the file. To play MIDI 64 from a
root-60 recording, we read through the file faster:

```python
ratio = 2 ** ((64 - 60) / 12)
```

About 1.26. The source position advances roughly 1.26 frames for every frame of
output, which means fractional positions, which means interpolation. It also
means the recording gets *shorter* as it gets higher: pitch and duration are
welded together in a simple sampler, exactly as they were on tape. This is not
a time-stretching instrument, and that limitation is why you record several
roots instead of one.

## Render a note

The shared engine exposes `ZoneSampler`, which reads the JSON manifest and
loads the WAVs it names. (You'll also meet `ExsSampler` in the album renderer —
it's the same class under a historical alias, kept so older scripts keep
working.)

```python
from music_engine import ZoneSampler

sampler = ZoneSampler(
    "Tracks/sampler-demo/instrument",
    deterministic=True,
    stereo_output=True,
)
events = [
    (0, "on", 0, 64, 70),
    (round(0.6 * 44100), "off", 0, 64, 0),
]
audio = sampler.render(events, total_seconds=2.0)
```

Put this in a file inside `scripts/`, or set `PYTHONPATH=scripts` before
running it from elsewhere. The tuple fields are the five from Chapter 2:
integer sample position, event kind, channel, MIDI note, velocity. The note
starts immediately and releases at 0.6 seconds. The result has two channels and
88,200 frames — two seconds, as requested.

The implementation converts a source file's sample rate before pitch shifting,
centers unsigned 8-bit PCM correctly, and can preserve stereo sources. Small
details, all three, and all three produce distinctive damage when got wrong: a
transposition error, a DC offset, a collapsed stereo image. Our generated
sources are mono, so stereo output simply duplicates them to both channels — it
does not invent width that was never recorded.

A note-off starts the release envelope. A voice can also end because its
recording ran out, which is what happens to short samples held for long notes.
If another note starts while the first is still sounding, the arrays are added
together rather than one stealing the other's voice. Overlapping notes at the
same pitch are paired first-in, first-out; an optional sixth tuple field
supplies an explicit voice ID when a score needs to be certain which note-off
belongs to which note.

## Check the instrument by listening to its boundaries

The demo alternates soft and bright notes across the three roots, which is a
start. But the interesting places are the seams. Play a slow phrase that
crosses MIDI 53 to 54, and 65 to 66 — those are where the selected source
changes. Then play the same note at velocity 79 and again at 80. You should
hear the layer change as a change of *character*, not as an accidental jump in
level. If it lurches, the instrument is miscalibrated, and no amount of mixing
downstream will hide it.

When you build something larger, record more root notes before relying on
extreme transposition. Match recording levels deliberately. Trim starts
carefully — a few milliseconds of silence before the attack becomes audible
sloppiness in a fast passage. Leave enough decay for the longest note you
intend to play. And several alternate recordings of the same note will stop
repeated hits from sounding mechanically identical. The engine picks randomly
among equally matching zones unless you pass `deterministic=True`; it is not a
strict round-robin player, so it won't guarantee each alternate gets its turn.

## Keep the source record with the instrument

The generator writes `provenance.json`: a description of how the sounds were
synthesized, and a SHA-256 hash for each WAV. Those hashes establish *which
files* were used. They do not establish that you were allowed to use them, and
nothing in a JSON file ever will.

For your own recordings, keep your recording notes. For a third-party library,
keep the actual licence and check that it permits your intended use —
including redistribution, if you plan to share the instrument itself.
Permission to use a sound in a finished composition is a different thing from
permission to publish its individual samples or extract them into another
player, and the second is much rarer than the first.

The project's MIT licence covers its code and documentation. It does not
relicense plugin libraries or anyone else's recordings, and it can't.

For this chapter you need none of that: the generator, the manifest and the
sampler are a complete instrument you can open, read and change. Appendix B
lists every manifest field.

---

*Next — Chapter 6: Drum Machines Are Sample Players.*
