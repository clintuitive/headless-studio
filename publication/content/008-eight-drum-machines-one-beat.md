---
title: One Groove, Several Drum Kits
date: 2026-07-06
slug: eight-drum-machines-one-beat
description: Compare sampled kits in the arrangement while preserving timing, source formats and listening level.---

A kick's tail matters differently under a bass line than it does in isolation.
When choosing a drum kit, render the same section through each candidate and
listen in the mix. Keep the groove, processing and comparison level fixed so
the kit is the decision you are actually hearing.

![Waveforms of eight drum machine kicks compared](/images/kick_comparison.png)

The waveform comparison shows how widely sampled kicks can differ in attack,
length and shape. It is a prompt for an audition, not a ranking. A short kick
may leave room for a sustained bass; a longer one may be the low end the
arrangement needs.

## Treat each sample as a source with a format

Use recordings you made or samples licensed for the intended use. Keep the
source and terms with the local kit. A download link alone is not a permission
record, and the public repository does not include the studio's drum samples.

A WAV is not necessarily 16-bit, mono or 44.1 kHz. The shared reader handles
integer and float PCM, centers unsigned 8-bit data, and resamples from the
file's actual rate:

```python
from music_engine.samplers import read_sample

rate = 44100
kick = read_sample('/path/to/your-kit/kick.wav', rate)
```

The returned array is frames by channels for stereo, or a one-dimensional
array for mono. Preserve that distinction until you intentionally choose how
the kit should sit in the stereo image. Casting every file to float and
dividing by 32768 only works for one source encoding.

## Fix the pattern before comparing kits

Write hit positions in beats, then convert to sample positions at the final
tempo. This minimal mono example places a kick four times:

```python
import numpy as np
from scipy.io import wavfile

bpm = 80
beat = 60 / bpm
mono = kick.mean(axis=1) if kick.ndim == 2 else kick
bus = np.zeros(round((4 * beat + 2) * rate), np.float32)
for beat_position, gain in [(0, .7), (1, .5), (2, .7), (3, .5)]:
    start = round(beat_position * beat * rate)
    count = min(len(mono), len(bus) - start)
    bus[start:start + count] += mono[:count] * gain
assert np.isfinite(bus).all()
wavfile.write('kit-pattern.wav', rate, bus)
```

For an audition harness, make the kit path the variable and reuse the same
pattern. Keep an unprocessed version for diagnosis and a version through the
actual drum bus for the musical decision. Compare at matched listening levels;
a peak-normalized sample can still have a very different perceived loudness.

## Keep a stable rhythmic reference

Sign-Off renders its LM-2 kick, snare and closed hat at final-tempo positions.
Pitched sources take the slowdown and warble path; drum attacks bypass that
timing warp. The kit can still be filtered and balanced without moving its
hits off the beat.

Contrast comes from the arrangement as well as the kit. Some tracks use a
heartbeat pattern, some a steady beat, and some no drums. A single strong kit
can cover that range when the pattern and surrounding texture have a purpose.

Check dense passages and transitions, not only the opening bar. Listen for
kick/bass masking, hats that become tiring, and tails cut short by the export.
Once a kit is selected, save the performed drum bus with the other dry sources
so [mix comparisons](/band-in-a-python-script.html) reuse exactly the same hits.
