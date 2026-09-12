# Chapter 2 — A Synthesizer You Can Script

Our studio's first instrument needs to cover a lot of ground cheaply,
because everything else in the book builds on the patterns we establish
here. That instrument is [FluidSynth](https://www.fluidsynth.org/): a free,
open-source synthesizer that plays **SoundFont** files — portable sample
libraries containing entire banks of instruments — and renders audio much
faster than real time. By the end of this chapter you'll have the studio's
most important function: give it a list of notes, get back finished audio,
with a different instrument on every channel.

## Thirty seconds on how digital audio works

Since we'll be handling audio directly, let's define the material once.

Digital audio is just a very long list of numbers. Each number — a
**sample** — records where the speaker cone should be at one instant.
CD-quality audio uses 44,100 samples per second (the **sample rate**,
written as 44.1 kHz). Stereo audio is two such lists, left and right.

So three seconds of stereo music is 2 × 132,300 numbers. In Python we hold
those numbers in a **NumPy array** — think of it as a list that supports
math on every element at once. `audio * 0.5` halves the volume of a million
samples in one go, without writing a loop. That one idea — audio is an
array, and array math is audio processing — powers the entire book. The
convention we'll use everywhere: samples are decimal numbers between −1.0
and +1.0, and a stereo track is an array with 2 rows (left, right) and one
column per sample.

## What a SoundFont is

A SoundFont (a `.sf2` file) is a sampler instrument from the CD-ROM era:
recordings of real instruments plus the metadata that makes them playable —
which recording to use for which key, how notes fade out, and so on. One
SoundFont file typically contains all 128 instruments of the **General
MIDI** standard: piano is instrument 0, clean electric guitar is 27, picked
bass is 34, and so on, the same numbers in every SoundFont ever made.

General MIDI was much mocked in the 90s for the sound of cheap sound cards.
For us, that fixed numbering is a gift: it's a *stable API for
instruments*. Your code can say `CLEAN_GUITAR = 27` and mean it forever.

The SoundFont this book uses is
[GeneralUser GS](https://schristiancollins.com/generaluser.php) — free,
about 30 MB, and far better than anything you remember GM sounding like.
Download it once and keep it next to your scripts.

## Installing

FluidSynth is a C library; `pyfluidsynth` is the Python wrapper.

```bash
# macOS                          # Ubuntu/Debian
brew install fluid-synth         sudo apt-get install fluidsynth libfluidsynth-dev
pip install pyfluidsynth         pip install pyfluidsynth

# Windows (as administrator)
choco install fluidsynth
pip install pyfluidsynth
```

These are platform-specific setup paths; verify them on your machine. One trap is
worth knowing on macOS: the Python wrapper sometimes can't *find* the
library Homebrew installed, and fails with "Couldn't find the FluidSynth
library." The fix is to tell Python exactly where to look, *before* the
import:

```python
import ctypes.util, os

# Python finds C libraries via this function; teach it Homebrew's shelf.
_original = ctypes.util.find_library
def _patched(name):
    found = _original(name)
    if not found and name == "fluidsynth":
        path = "/opt/homebrew/lib/libfluidsynth.dylib"
        if os.path.exists(path):
            return path
    return found
ctypes.util.find_library = _patched

import fluidsynth   # now succeeds
```

(`ctypes` is Python's built-in bridge to C libraries; all we're doing is
wrapping its lookup function with a fallback path. On Windows, the
chocolatey install works out of the box.)

## Talking to the synthesizer

FluidSynth's API, reduced to what we need:

```python
fs = fluidsynth.Synth(samplerate=44100.0)
fs.setting("synth.gain", 0.6)              # overall volume; see notes below
sfid = fs.sfload("GeneralUser-GS.sf2")     # load the SoundFont

fs.program_select(0, sfid, 0, 27)   # channel 0 plays instrument 27 (clean guitar)
fs.program_select(1, sfid, 0, 34)   # channel 1 plays instrument 34 (picked bass)

fs.noteon(0, 60, 100)   # channel 0: start middle C at volume 100 (max 127)
fs.noteoff(0, 60)       # channel 0: release middle C
```

A synthesizer has 16 **channels** — think of each channel as one band
member, playing one instrument. Notes are numbered like piano keys (60 is
middle C; each step is one semitone), and the third argument to `noteon` is
**velocity** — how hard the key was struck, 1 to 127. In good SoundFonts,
velocity changes the *character* of the note, not just its loudness,
because the library contains different recordings for soft and hard
playing.

You can also position each player in the stereo field:

```python
fs.cc(0, 10, 44)    # "control change": controller 10 is pan.
fs.cc(1, 10, 84)    # 0 = hard left, 64 = center, 127 = hard right
```

## The key idea: pull audio between events

Here's the mechanism the whole studio is built on. FluidSynth has a method
`fs.get_samples(n)` that returns the next `n` samples of audio, *with
whatever notes are currently sounding rendered into them*. The synthesizer
only moves forward in time when you ask it for samples.

That suggests a simple and perfect scheduler. Say the song's first note
starts at sample 44,100 (one second in) and the second at sample 66,150:

1. Ask for 44,100 samples (silence so far). Then press the first key.
2. Ask for 22,050 more samples (the first note, sounding). Press the
   second key.
3. Continue to the end.

Every note lands on its *exact* sample, every time. No timers, no audio
driver, no drift. This is why rendering offline isn't a lesser version of
real-time audio — it's the same thing with the hard part (the deadline)
removed.

## The renderer

Here it is in full. Events are tuples — small fixed bundles of values —
of the form `(sample_position, "on" or "off", channel, note, velocity)`:

```python
import numpy as np

SR = 44100   # sample rate, used everywhere

def render_bus(events, total_secs, sf2_path, setup):
    """Render one instrument track ("bus"). Returns stereo audio as a
    NumPy array with shape (2, total_samples)."""
    n_samples = int(total_secs * SR)

    fs = fluidsynth.Synth(samplerate=float(SR))
    fs.setting("synth.gain", 0.6)
    sfid = fs.sfload(sf2_path)
    setup(fs, sfid)            # caller's function: assigns instruments/pans

    # FluidSynth hands back interleaved stereo: L,R,L,R,...  We collect it
    # into one flat array and split it at the end.
    audio = np.zeros(n_samples * 2, dtype=np.float32)
    pos = 0                    # our current position, in samples

    for ev in sorted(events, key=lambda e: e[0]):    # sort by time
        event_pos = min(ev[0], n_samples)
        if event_pos > pos:
            # Render everything between "now" and this event.
            raw = fs.get_samples(event_pos - pos)     # integers, -32768..32767
            end = min(pos * 2 + len(raw), len(audio))
            audio[pos * 2:end] += raw[:end - pos * 2].astype(np.float32) / 32768.0
            pos = event_pos
        if ev[1] == "on":
            fs.noteon(ev[2], ev[3], ev[4])
        else:
            fs.noteoff(ev[2], ev[3])

    if pos < n_samples:        # render the tail: notes fading out
        raw = fs.get_samples(n_samples - pos)
        end = min(pos * 2 + len(raw), len(audio))
        audio[pos * 2:end] += raw[:end - pos * 2].astype(np.float32) / 32768.0

    fs.delete()
    # De-interleave: every 2nd value starting at 0 is left, at 1 is right.
    return np.stack([audio[0::2], audio[1::2]])
```

A few lines deserve translation:

- `sorted(events, key=lambda e: e[0])` — sort the events by their first
  element (the time). A `lambda` is just a one-line unnamed function.
- `raw.astype(np.float32) / 32768.0` — FluidSynth returns whole numbers
  in the range ±32768 (the format called *16-bit*); dividing converts to
  our standard ±1.0 decimals.
- `audio[0::2]` — NumPy slicing: "every second element, starting at index
  0." That pulls the left channel out of the interleaved L,R,L,R stream.
- The block *after* the loop matters: notes released near the end still
  ring out (piano decay, reverb tails). Always budget a few extra seconds
  of `total_secs` for the tail.

Why events store *sample positions* rather than seconds: decimal seconds
accumulate tiny rounding differences; integer sample positions make every
render land identically — which Chapter 1's whole reproducibility argument
depends on. Convert seconds to samples once, when creating the event:

```python
def add_note(events, t, dur, ch, note, vel):
    events.append((int(t * SR), "on", ch, note, vel))
    events.append((int((t + dur) * SR), "off", ch, note, 0))
```

## One track per band member

You could render a whole band in one pass — sixteen channels is plenty.
Don't. Render one **bus** (one audio array) per band member:

```python
gtr  = render_bus(guitar_events, total_secs, SF2, setup_gtr)
bass = render_bus(bass_events,   total_secs, SF2, setup_bass)
pad  = render_bus(pad_events,    total_secs, SF2, setup_pad)
```

Three reasons, in rising importance. **Effects:** the next chapter puts a
guitar amp on the guitar and a compressor on the bass — only possible if
they're separate arrays. **Mixing:** combining buses at chosen volumes *is*
mixing, and you want those volumes adjustable per member. **Stems:** near
the end of the book we'll export each member as its own file so any DAW
can remix the song — impossible if they were merged early.

The cost is a few extra seconds of rendering. The songs in this book
render a full band in well under a minute.

## Practical notes

- **`synth.gain` 0.6**: FluidSynth's default overall volume is very
  conservative. 0.6 gives healthy levels with headroom. If a dense
  arrangement distorts, lower this — don't lower note velocities, which
  would change the *tone*.
- **Same input, same output**: render a bus twice and the arrays are
  equal. This is what makes listening tests trustworthy and lets us put
  renders under automated test.
- **The honest limitation**: a SoundFont guitar, played dry, will not fool
  a guitarist. What you get is correct notes with sterile air. The next
  chapter is about that air — we'll take these tracks and run them through
  the same amplifiers and effects real records use, and the sterility
  turns out to be exactly what a good amp wants to be fed.
