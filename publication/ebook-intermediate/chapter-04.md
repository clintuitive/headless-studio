# Chapter 4 — An Instrument Across a Process Boundary

Sooner or later you meet a plugin that is wonderful and impossible. It wants a
different processor architecture, or a Python it refuses to share with yours,
or native libraries that quietly break three other things you'd installed. The
temptation is to bend the whole studio around it, and the studio will let you,
right up until the day it doesn't.

Don't. Put the awkward instrument in its own process and talk to it through
files. Write the events to JSON, ask a helper program to render them, read back
the WAV it produces. Two processes that agree on a file format don't have to
agree on anything else — not their dependencies, not their Python version, not
even their instruction set.

The shared implementation is `scripts/music_engine/renderers.py`. Your
arrangement code keeps calling one interface, while the helper quietly owns all
the awkwardness of one particular instrument.

## Keep the boundary small

The parent sends a duration and a list of note records. The helper gets two
paths: one JSON in, one WAV out. It sets up its own instrument, renders the
whole performance and exits. The parent never learns which plugin parameter
selects a preset, or where the helper found its native library, and that
ignorance is the entire point — it's what keeps the mess from spreading.

```python
from music_engine import render_external_instrument

notes = [{'time': 0.0, 'duration': 0.8, 'pitch': 48, 'velocity': 72}]
audio = render_external_instrument(
    notes,
    total_seconds=3.0,
    python_path='/path/to/instrument-python',
    helper_path='/path/to/your-render-helper.py',
    sample_rate=44100,
)
if audio is None:
    raise RuntimeError('The selected instrument did not render')
```

Notice that these notes carry `time` and `duration` in seconds, not the
frame-position on/off pairs of Chapter 2. That's deliberate: the bridge hands
whole notes across, and the helper decides how to schedule them. It suits a
process boundary better — fewer, larger messages, each one self-contained.

Those field names are a contract you're proposing, not one the bridge enforces.
It passes the records through as JSON; your helper has to agree about the names
and their units. There is no universal instrument hiding in here, and if you
invent a `pan` field the bridge will carry it faithfully without ever knowing
what it means.

What comes back is channels by frames, the studio's working layout. The bridge
reads the helper's WAV at whatever rate it was actually written, resamples if
it must, promotes mono to stereo, and pads or trims to the duration you asked
for. Which means: ask for a duration generous enough to hold your note releases
and effect tails. Trimming happens at the end and has no sympathy for your
reverb.

## Match the runtime to the instrument

On a system with architecture translation — an Apple Silicon Mac running Intel
binaries, say — the helper can run under a different architecture from its
parent, provided you have a compatible interpreter, compatible native
dependencies and a compatible plugin, all three. A process boundary is not a
binary translator, and it certainly won't carry a Windows-only plugin onto a
Mac. All it does is stop two incompatible things from having to share one
address space, which is quite enough.

The bridge takes an optional architecture argument for the macOS `arch`
command. Leave it unset for an ordinary subprocess. And get the helper working
on its own, from a terminal, before you wire it into a twelve-track album
render — unless you enjoy debugging by album, which takes about forty minutes
per attempt and teaches you very little.

For an instrument that streams from disk, give its library time to initialize
and keep its state alive across render blocks. Tearing the processor down every
block can cut sustained notes short, or send it back to reloading samples over
and over while your render crawls. Those decisions belong inside the helper,
where you can test them without running everything else.

## Failure is a result you must handle

The bridge returns `None` when the interpreter isn't available, when the note
list is empty, and when the helper reports failure. That's a real outcome and
the caller has to do something about it: stop the render, or fall back to a
substitute you have written down somewhere.

What you must not do is quietly swap in a different instrument during a
delivery build. It's the most tempting line of code in this chapter and the
worst — three months later, nobody can tell you what's actually on the record.
The chosen source belongs in the manifest, named, every time.

There is no timeout in the bridge. If you're rendering unattended, wrap helpers
that can hang in something with a bound on it, and keep their logs. Then check
the WAV that came back: format, duration, finite samples, audible content. A
zero exit code and thirty seconds of silence go together far more often than
you would like.

None of this is needed for the portable sketches or either album render path.
The process boundary exists for a sound that's worth the trouble, and saved dry
buses keep that setup well away from your routine mix comparisons.

---

*Next — Chapter 5: Build a Sample Instrument from Your Own Sounds.*
