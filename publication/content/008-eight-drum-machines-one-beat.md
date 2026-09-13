---
title: One Groove, Several Drum Kits
date: 2026-07-06
slug: eight-drum-machines-one-beat
description: Compare sampled kits in the arrangement while preserving timing, source formats and listening level.
---

A kick drum auditioned on its own tells you almost nothing. What matters is
what its tail does underneath a bass line, and you can't hear that until the
bass is playing. So when you're choosing a kit, render the same section through
every candidate and listen to it in the mix — same groove, same processing,
same comparison level, so that the kit is genuinely the only thing changing.

![Waveforms of eight drum machine kicks compared](/images/kick_comparison.png)

Look how different sampled kicks can be in attack, length and shape. That
picture isn't a ranking; it's an argument for auditioning. A short kick may
leave exactly the room a sustained bass needs. A longer one may *be* the low
end the arrangement was missing. The waveform can't tell you which, and neither
can I.

## Treat each sample as a source with a format

Use recordings you made, or samples licensed for what you actually intend to
do. Keep the source and its terms with the local kit, because a download link
is not a permission record and you will not remember in a year. (The public
repository doesn't include the studio's drum samples for exactly this reason.)

A WAV is not necessarily 16-bit, mono or 44.1 kHz, whatever the last ten files
you opened happened to be. The shared reader handles integer and float PCM,
centers unsigned 8-bit data, and resamples from whatever rate the file actually
claims:

```python
from music_engine.samplers import read_sample

rate = 44100
kick = read_sample('/path/to/your-kit/kick.wav', rate)
```

You get frames by channels for a stereo file, or a one-dimensional array for
mono. Hold on to that distinction until you've decided deliberately how the kit
should sit in the stereo image. Casting everything to float and dividing by
32768 works beautifully for one encoding and silently mangles the rest.

## Fix the pattern before comparing kits

Write the hit positions in beats, then convert to sample positions at the final
tempo. Here's a minimal mono example putting a kick down four times:

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

For a real audition harness, make the kit path the variable and reuse the same
pattern for all of them. Keep an unprocessed version for diagnosis and a
version through the actual drum bus for the musical decision — they answer
different questions. Compare at matched listening levels, too: peak-normalizing
two samples can still leave one of them obviously louder, and louder wins
auditions it hasn't earned.

## Keep a stable rhythmic reference

Sign-Off renders its LM-2 kick, snare and closed hat at final-tempo positions.
The pitched sources go off through the slowdown and warble path; the drum
attacks skip that timing warp entirely. The kit can still be filtered and
balanced however the track needs — it just never leaves the beat.

Contrast comes from the arrangement as much as the kit. Some tracks run on a
slow heartbeat pattern, some on a steady beat, some on nothing at all. One
strong kit covers that whole range as long as the pattern and the texture
around it have a reason for being there.

Check the dense passages and the transitions, not just the opening bar, which
always sounds fine. Listen for kick and bass masking each other, for hats that
turn tiring by the third minute, for tails clipped short by the export. Then,
once you've chosen, save the performed drum bus with the other dry sources so
your [mix comparisons](/band-in-a-python-script.html) reuse exactly the same
hits.
