---
title: Render Note Events into Audio with FluidSynth
date: 2026-07-02
slug: fluidsynth-midi-python
description: Sample-position scheduling, separate instrument buses, and explicit SoundFont dependencies.
---

Somewhere between "here are the notes" and "here is a WAV file" sits an
instrument. It doesn't have to be a complicated one, and the performance you
hand it doesn't have to be a MIDI file. A list of tuples will do: a sample
position, an action, a channel, a pitch, a velocity. That same list can drive a
SoundFont synth or the studio's own [JSON-zone
sampler](/sample-instrument-python.html), which is the point of keeping it that
plain.

FluidSynth is one route, and it's optional. It wants three things that arrive
separately: the native FluidSynth library, the `pyfluidsynth` Python binding,
and a SoundFont whose terms actually permit what you intend to do with it.
Installing the binding gets you none of the other two — a fact I'd like you to
learn faster than I did. The [FluidSynth site](https://www.fluidsynth.org/) has
the platform-specific installation guidance.

None of this is required to use the studio. The portable examples need only
NumPy and SciPy, and The Quiet Hours plays prepared Salamander and VSCO
samples. Pick the renderer that matches the source you want to hear.

## Schedule in frames

At 44,100 Hz, half a second is frame 22,050. (A frame holds one sample for each
channel.) Every event in the studio uses the same five fields:

```python
(sample_position, 'on' or 'off', channel, midi_note, velocity)
```

Write your musical durations in seconds, convert both ends of each note to
integer frames, then work through the list: pull audio up to the next event,
apply the event, keep going. The event lands exactly on a frame boundary, and
nothing has to wait on a real-time audio device.

Here's a complete single note, assuming an installed FluidSynth runtime and a
SoundFont of your own:

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

The note ends at one second but the file runs to three, so the release has
somewhere to go. The binding hands back 16-bit values, which get converted to
float before writing. If you're building something more general than a
one-note demo, validate the rest of it too: sorted positions, channel and pitch
ranges in bounds, every note-on paired with a note-off, nothing scheduled past
the end of the render.

## One instrument bus at a time

Several MIDI channels inside one synth all come out of the same output. If you
want a separate bass fader and piano fader — and you will — render them to
separate buses, using separate synth instances or a renderer that hands you
separate outputs on purpose.

Overlapping notes at the same pitch are the classic trap. A MIDI note-off
carries no voice identifier, so something has to decide which of two sounding
middle Cs it ends. The zone sampler accepts explicit voice IDs for that; plain
five-field events fall back to its documented first-in, first-out pairing.
Don't assume another synth resolves the same ambiguity the same way.

One last thing worth writing down: the SoundFont's identity, the program you
selected, the sample rate and the runtime version, all recorded with the
result. A reproducible event list is only half a performance. The instrument
that received it is the other half. And save the dry float WAV, so that when
you change your mind about the mix next week you're reusing the actual
performance rather than re-deriving it from instructions.
