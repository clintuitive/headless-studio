---
title: Render Note Events into Audio with FluidSynth
date: 2026-07-02
slug: fluidsynth-midi-python
description: Sample-position scheduling, separate instrument buses, and explicit SoundFont dependencies.---

An instrument renderer turns a performance into audio. The performance can be
a list of tuples rather than a MIDI file: a sample position, an action, a
channel, a pitch and a velocity. The same list can drive a SoundFont synth or
the studio's [JSON-zone sampler](/sample-instrument-python.html).

FluidSynth is an optional route for SoundFont instruments. It requires both the
native FluidSynth library and the `pyfluidsynth` Python binding, plus a SoundFont
whose terms permit your use. Installing the binding alone does not supply the
native library or the instrument recordings. Follow the installation guidance
for your platform at [FluidSynth](https://www.fluidsynth.org/).

The core studio and its CI do not require this setup. The portable examples use
NumPy and SciPy; The Quiet Hours uses prepared Salamander and VSCO samples.
Choose the renderer that fits the source you intend to play.

## Schedule in frames

At 44,100 Hz, half a second is frame 22,050. A frame contains one sample for
each channel. The shared five-field event format is:

```python
(sample_position, 'on' or 'off', channel, midi_note, velocity)
```

Write a musical duration in seconds, then convert both boundaries to integer
frames. Pull audio up to each event, apply the event, and continue. This places
the event at a frame boundary without waiting for a real-time audio device.

Here is a complete single-note example for an installed FluidSynth runtime
and a SoundFont supplied by the reader:

```python
import numpy as np
import fluidsynth
from scipy.io import wavfile

rate = 44100
end = 3 * rate
synth = fluidsynth.Synth(samplerate=float(rate))
try:
    sfid = synth.sfload('/path/to/instrument.sf2')
    if sfid < 0:
        raise RuntimeError('SoundFont failed to load')
    synth.program_select(0, sfid, 0, 0)
    events = [(0, 'on', 0, 60, 72), (rate, 'off', 0, 60, 0)]
    chunks = []
    position = 0
    for frame, action, channel, note, velocity in events:
        if frame > position:
            chunks.append(synth.get_samples(frame - position))
        if action == 'on':
            synth.noteon(channel, note, velocity)
        else:
            synth.noteoff(channel, note)
        position = frame
    chunks.append(synth.get_samples(end - position))
    audio = np.concatenate(chunks).reshape(-1, 2).astype(np.float32) / 32768.0
    assert np.isfinite(audio).all() and np.max(np.abs(audio)) > 0
    wavfile.write('soundfont-note.wav', rate, audio)
finally:
    synth.delete()
```

The two seconds after note-off let the release sound. The binding's returned
16-bit sample values are converted to float before writing. For a general
renderer, also validate sorted positions, channel and pitch ranges, paired
note boundaries, and events beyond the requested duration.

## One instrument bus at a time

Several MIDI channels inside one synth share its output. If the mix needs a
separate bass and piano fader, render them to separate buses with separate synth
instances or a renderer that explicitly provides separate outputs.

Same-pitch overlaps need care. A MIDI note-off does not carry a unique voice
identifier. The custom zone sampler supports voice IDs for explicit pairing;
ordinary five-field events use its documented FIFO pairing. Do not assume that
a different synth interprets ambiguous overlapping notes the same way.

Record the SoundFont identity, program selection, sample rate and runtime
version with the result. A reproducible event list is only half the performance:
the instrument receiving it matters too. Save the dry float WAV so a later
mix change can reuse the actual performance, not merely its instructions.
