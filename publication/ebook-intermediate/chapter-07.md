# Chapter 7 — Synthesis from a Few Sine Waves

Every instrument so far has needed something from outside: a SoundFont, a
plugin, a folder of recordings. This chapter needs nothing. A synthesized
source starts from numbers, which means it starts from an equation you can read
— and it means the first sound you make in this studio can be made on a
laptop on a train with no internet.

The portable sketches are built this way. A few sine waves, some envelopes, a
little noise, and out comes a complete arrangement:

```bash
python scripts/generate_portable_samples.py --piece open-window --output-dir Tracks/demo
```

Open Window is the sparse, beatless one. Afterimage and Night Transit add
percussion and use different tempos, melodies and amounts of pitch movement.
All three keep their composition and mix settings in a single file, so you can
change something and hear the result before you've finished wondering about it.

## Frequency, phase and time

We've met the arithmetic twice now, so here it is doing actual work:

```python
import numpy as np
rate = 44100
note = 69
seconds = 2.0
frequency = 440 * 2 ** ((note - 69) / 12)
t = np.arange(round(seconds * rate)) / rate
signal = np.sin(2 * np.pi * frequency * t)
```

`t` is an array of times, one entry per frame. Multiplying time by frequency
counts cycles; multiplying by `2 * pi` converts cycles into radians, which is
what `np.sin` expects. NumPy then evaluates the whole expression across the
entire array at once — no loop, no per-sample Python, which is the only reason
any of this runs fast enough to be enjoyable.

A single sine wave is one frequency and nothing else, which is why it sounds
like a hearing test. Add another at twice the frequency and the sound gets
brighter without its pitch changing:

```python
signal += 0.28 * np.sin(2 * np.pi * 2 * frequency * t) * np.exp(-t * 3)
```

Note that the second harmonic decays *faster* than the fundamental. That's the
detail that makes it sound struck rather than synthetic: real instruments are
brightest at the attack and mellow as they ring. A static blend of oscillators
never does that, and the ear notices immediately even if it can't say why.

## An envelope makes a note

An oscillator has no idea when a note begins or ends; left alone it drones
forever. An envelope is an array of gains that gives the sound a shape:

```python
attack = 1 - np.exp(-t / 0.008)
decay = np.exp(-t / 0.6)
release = np.clip((seconds - t) / 0.05, 0, 1)
signal *= attack * decay * release
```

The attack rises quickly, the decay falls gradually, and the release pulls the
final samples to zero — because cutting a waveform off partway through a cycle
produces a click, and the click is louder than you expect. For a pad, slow the
attack and the release down; the portable renderer keeps a different envelope
for its sustained harmony voice.

These time constants are artistic parameters, not settings with correct values.
Judge them over a real phrase rather than a single note, because a tone that
sounds lovely on its own can have a tail that smears the note after it.

## Place the sound on a bus

The studio's working buses are channels by frames, so a stereo bus has shape
`(2, frame_count)`. To place a mono note, we distribute it between left and
right. The portable renderer uses an equal-power pan:

```python
pan = -0.2                         # -1 left, 0 center, +1 right
angle = (pan + 1) * np.pi / 4
stereo_note = signal[None, :] * np.array([[np.cos(angle)], [np.sin(angle)]])
```

`signal[None, :]` adds a one-row dimension, turning a flat array into a single
row; multiplying by the two gains produces two channels. The reason for the
cosine and sine, rather than simply splitting the level in two, is that they
keep the *power* constant as the sound moves across the stereo field — a
straight-line pan sounds like it dips in the middle.

Reserve space in the song bus for the note's release before adding it at its
scheduled position. This is the same lesson as Chapter 2's three-second file,
and it will be the same lesson again in Chapter 12. Audio needs room after the
last event.

## Pitch movement belongs to a routing decision

The portable sketches move the read position of the harmony and melody buses
with a slow sinusoid, interpolating between sample positions to produce a
small, continuous pitch change — the sound of tape that isn't quite well. The
drums bypass it entirely, exactly as Chapter 6 described.

Sign-Off takes this much further: source resampling, tape motion, dropouts,
filtering and noise, with a different treatment assigned to each track. Keep a
steady drum clock whenever the contrast between stable rhythm and unstable
pitched material is part of the sound, which for that record it very much is.

The Quiet Hours does something different that's easy to confuse with this. It
shapes *performance timing* — where note boundaries fall — before the piano and
strings render a single sample. Chapter 9 explains why these are genuinely
different operations, even though both can stop rigid material feeling
mechanical.

## Respect the available frequency range

Digital audio can only represent frequencies below half its sample rate, a
limit called the Nyquist frequency — 22,050 Hz at our rate. Generate a harmonic
above that and it doesn't disappear; it folds back down into the audible range
as an **alias**, a phantom tone at a frequency nobody asked for. And once it's
there, it's there. Filtering afterwards cannot selectively remove an alias
that's landed on top of your music, because at that point it *is* your music,
numerically speaking.

The portable oscillator uses a small number of sine partials across a bounded
note range, which keeps it safe. If you extend the pitch range or add
harmonics, leave out the partials that would cross Nyquist. And be careful with
the textbook waveforms: a naive sawtooth or square wave has infinitely many
harmonics and aliases enthusiastically at high pitches. Use a proper
band-limited oscillator, or a carefully filtered oversampling design, when you
want those sounds.

Save the synthesized dry buses before adding the room or the master gain. A
synthesis change needs a fresh source render; a room-balance change can reuse
what's already there. That separation works identically whether the note came
from an equation, a SoundFont, a zone map or a plugin — which is the point of
the whole arrangement, and the subject of the next three chapters.

---

*Next — Chapter 8: The Song Is a Data Structure.*
