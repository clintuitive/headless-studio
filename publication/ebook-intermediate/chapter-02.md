# Chapter 2 — Rendering Note Events with FluidSynth

Somewhere between "here are the notes" and "here is an audio file" there has to
be an instrument. This chapter builds the smallest useful one, and along the way
finally explains the `44100` I waved at in Chapter 1.

The performance we hand the instrument doesn't need to be a MIDI file. A list
of tuples will do — a sample position, an action, a channel, a pitch, a
velocity. Keeping it that plain is deliberate: the same list can drive a
SoundFont synth or the studio's own [JSON-zone
sampler](https://clintjohnson.cloud/headless-studio/sample-instrument-python.html),
and later on it can drive both at once.

FluidSynth is one route to sound, and it's optional. It wants three things,
which arrive from three different places: the native FluidSynth library, the
`pyfluidsynth` Python binding, and a SoundFont — a file full of recorded
instruments — whose terms permit what you intend to do with it. Installing the
binding gets you none of the other two, a fact I would like you to learn faster
than I did. The [FluidSynth site](https://www.fluidsynth.org/) has the
platform-specific installation guidance.

None of this is required to use the studio. The portable examples need only
NumPy and SciPy, and The Quiet Hours plays prepared Salamander and VSCO
samples. Pick the renderer that suits the source you want to hear; skipping
this chapter's setup costs you nothing later.

## Audio is a list of numbers, very fast

Here is the whole of digital audio. A microphone's diaphragm moves; we measure
its position 44,100 times a second; we write those measurements down. Play them
back at the same rate and the speaker traces the same movement. That's it.

The 44,100 is the **sample rate**, in hertz — measurements per second — and
44.1 kHz is the CD standard, which is why it's everywhere. Each measurement is
a **sample**. A **frame** holds one sample for each channel, so a stereo frame
is two numbers. Count in frames and the arithmetic stays honest: at 44,100 Hz,
half a second is frame 22,050, no matter how many channels you have.

Everything in this book is an array of floating-point numbers with that shape.
Effects are functions over those arrays. Mixing is addition. Once you've
internalized that, most of the mystique drains out of audio software, which is
either liberating or disappointing depending on your temperament.

## Schedule in frames

Every event in the studio uses the same five fields:

```python
(sample_position, 'on' or 'off', channel, midi_note, velocity)
```

The `midi_note` is a pitch number — 60 is middle C, and each step of 1 is one
semitone up or down the keyboard. `velocity` is how hard the note was struck,
from 1 to 127, a range MIDI inherited in 1983 and has never escaped.

Write your musical durations in seconds, convert both ends of each note to
integer frames, then walk the list: pull audio up to the next event, apply the
event, keep going. The event lands exactly on a frame boundary, and nothing has
to wait around for a real-time audio device to catch up. This is the one genuine
advantage of rendering offline — the clock is yours.

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

Read the loop and you'll see the pattern that runs through the whole studio:
*advance to the event, apply the event, repeat.* The `try`/`finally` makes sure
the synth is released even if the SoundFont turns out to be missing, which it
will be at least once.

The note ends at one second but the file runs to three. Those two spare seconds
are where the release lives — the sound a piano makes after you let go of the
key. Cut the array at the note-off and you don't get a clean ending, you get a
click and a piano that's been switched off at the wall.

The binding hands back 16-bit whole numbers, which is why we divide by 32768 to
land in the −1.0 to 1.0 float range the rest of the studio uses. And if you go
on to build something more general than a one-note demo, validate the rest of
it: positions in sorted order, channel and pitch ranges in bounds, every
note-on paired with a note-off, nothing scheduled past the end of the render.
Every one of those has cost me an afternoon.

## One instrument bus at a time

Several MIDI channels inside a single synth all emerge from the same output. If
you want a separate bass fader and piano fader — and by Chapter 10 you will
badly want them — render them to separate **buses**: separate arrays, from
separate synth instances or from a renderer that hands you separate outputs on
purpose. Mixing things together is easy and permanent. Keeping them apart costs
almost nothing and buys you every later decision.

Overlapping notes at the same pitch are the classic trap. A MIDI note-off
carries no voice identifier, so if two middle Cs are sounding, something has to
decide which one it ends. The zone sampler accepts explicit voice IDs for
exactly this; plain five-field events fall back on its documented first-in,
first-out pairing. Don't assume another synth resolves the ambiguity the same
way, because the standard doesn't make it.

Last, write things down. The SoundFont's identity, the program you selected,
the sample rate, the runtime version — recorded with the result. A reproducible
event list is only half a performance; the instrument that received it is the
other half, and it is the half that quietly changes when you upgrade something.
And save the dry float WAV, so that when you change your mind about the mix
next week, you're reusing the actual performance instead of re-deriving it from
instructions and hoping.

---

*Next — Chapter 3: Processing Saved Audio with VST3 Effects.*
