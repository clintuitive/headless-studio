# Chapter 7 — Synthesis from a Few Sine Waves

A synthesized source starts with numbers rather than a recorded instrument.
That makes it a useful first render: there is no plugin to install and no sample
library to locate. The portable sketches use a few sine waves, envelopes and
noise to build complete arrangements.

Run one from the repository root:

```bash
python scripts/generate_portable_samples.py --piece open-window --output-dir Tracks/demo
```

Open Window is the sparse, beatless example. Afterimage and Night Transit add
percussion and use different tempos, melodies and amounts of pitch movement.
All three expose composition and mix settings in one file.

## Frequency, phase and time

A MIDI note number identifies a pitch. Note 69 is A at 440 Hz, and twelve
semitones double the frequency:

```python
import numpy as np
rate = 44100
note = 69
seconds = 2.0
frequency = 440 * 2 ** ((note - 69) / 12)
t = np.arange(round(seconds * rate)) / rate
signal = np.sin(2 * np.pi * frequency * t)
```

`t` is an array of times, one per frame. Multiplying time by frequency counts
cycles; multiplying by `2 * pi` converts cycles to radians, the input expected
by `np.sin`. NumPy evaluates the expression for the entire array.

A sine wave has one frequency. Add another at twice the frequency and the
sound becomes brighter without changing its fundamental pitch:

```python
signal += 0.28 * np.sin(2 * np.pi * 2 * frequency * t) * np.exp(-t * 3)
```

The second harmonic decays faster than the fundamental. That gives the attack
a brighter character than the tail, which is more useful for a struck sound
than a static blend of oscillators.

## An envelope makes a note

An oscillator does not know when a note should start or stop. An envelope is
an array of gains that gives the sound a shape:

```python
attack = 1 - np.exp(-t / 0.008)
decay = np.exp(-t / 0.6)
release = np.clip((seconds - t) / 0.05, 0, 1)
signal *= attack * decay * release
```

The attack rises quickly, the decay falls gradually, and the release brings
the final samples toward zero. Abruptly cutting a waveform away from zero can
create a click. For a pad, use a slower attack and release; the portable
renderer uses a different envelope for its sustained harmony voice.

These time constants are artistic parameters. Compare them over an actual
phrase, because a pleasant isolated note can obscure the next one when its
tail is too long.

## Place the sound on a bus

The studio's working buses use channels by frames. A stereo bus has shape
`(2, frame_count)`. Place a mono note at its start frame and distribute it
between left and right channels. The portable renderer uses equal-power pan:

```python
pan = -0.2                         # -1 left, 0 center, +1 right
angle = (pan + 1) * np.pi / 4
stereo_note = signal[None, :] * np.array([[np.cos(angle)], [np.sin(angle)]])
```

`signal[None, :]` adds a one-row dimension. Multiplying by the two gains makes
two channels. Reserve space in the song bus for the note's release before
adding it at its scheduled position.

## Pitch movement belongs to a routing decision

The portable sketches move the read position of the harmony and melody buses
with a slow sinusoid. Interpolating between sample positions creates a small
continuous change in pitch. The drums bypass that movement.

Sign-Off extends this idea with source resampling, tape motion, dropouts,
filtering and noise. It assigns a different treatment to each track. Keep a
steady drum clock when the contrast between stable rhythm and unstable pitched
material is part of the sound.

The Quiet Hours uses performance timing instead: note boundaries follow a
phrase-level timeline before the piano and strings render. Chapter 9 explains
why these are different operations even though both can make rigid material
feel less static.

## Respect the available frequency range

Digital audio represents frequencies below half its sample rate, called the
Nyquist frequency. A harmonic above that boundary can fold into the audible
range as aliasing. Filtering the resulting signal cannot selectively remove
an alias that already overlaps the musical frequencies.

The portable oscillator uses a small number of sine partials within a bounded
note range. If you extend its pitch range or add harmonics, omit partials that
would reach Nyquist. A naive sawtooth or square wave has infinitely many
harmonics; use a suitable band-limited oscillator or a carefully filtered
oversampling design for those sources.

Save the synthesized dry buses before adding the room or master gain. A
synthesis change needs a source render. A room-balance change can reuse those
buses. The same separation works whether a note came from an equation, a
SoundFont, a zone map or a plugin.
