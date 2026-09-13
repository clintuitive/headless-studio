---
title: Run an Instrument in Its Own Process
date: 2026-07-02
slug: incompatible-plugins-out-of-process
description: Separate a plugin-specific runtime from the main studio with JSON events and a WAV result.
---

Sooner or later you meet a plugin that is wonderful and impossible. It wants a
different processor architecture, or a Python it can't share with yours, or
native libraries that fight everything else you've installed. The temptation is
to bend the whole studio around it. Don't. Put it in its own process and talk
to it through files: write the events to JSON, ask a helper to render them,
read back the WAV.

The shared implementation is `scripts/music_engine/renderers.py`. The
arrangement code keeps calling one interface; the helper quietly owns all the
awkwardness of one particular instrument.

## Keep the boundary small

The parent sends a duration and a list of note records. The helper gets two
paths — one JSON in, one WAV out. It sets up its own instrument, renders the
whole performance and exits. The parent never learns which plugin parameter
selects a preset, or where the helper found its native library, and that
ignorance is the feature.

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

Those note fields are a contract you're proposing, not one the bridge enforces.
It passes the records through; your helper has to agree about the field names
and their units. There's no universal instrument hiding in here.

What comes back is channels by frames. The bridge reads the helper's WAV at
whatever rate it was actually written, resamples if it has to, promotes mono to
stereo, and pads or trims to the duration you asked for. Which means you should
ask for a duration generous enough to hold the note releases and any effect
tails, because trimming happens afterwards and doesn't care about your reverb.

## Match the runtime to the instrument

On a system with architecture translation, the helper can run under a different
architecture from its parent — provided you have a compatible interpreter,
compatible native dependencies and a compatible plugin. A process boundary is
not a binary translator, and it certainly won't carry a Windows-only plugin
onto a Mac. It just stops two incompatible things from having to share an
address space.

The bridge takes an optional architecture argument for the macOS `arch`
command. Leave it unset for an ordinary subprocess. And get the helper working
on its own before you wire it into a twelve-track album render, unless you
enjoy debugging by album.

For an instrument that streams from disk, give its library time to initialize
and keep its state alive across render blocks. Tearing the processor down every
block can cut sustained notes off or send it back to loading samples over and
over. Decisions like that belong inside the helper, where you can test them
without running everything else.

## Failure is a result you must handle

The bridge returns `None` when the interpreter isn't available, when the note
list is empty, and when the helper reports failure. That's a real outcome, and
the caller has to do something about it: stop the render, or fall back to a
substitute you've documented. What you must not do is quietly swap in a
different instrument during a delivery build. Three months later nobody can
tell you what's actually on the record. The chosen source belongs in the
manifest.

There's no timeout in the bridge. If you're running unattended, wrap helpers
that can hang in something with a bound on it and keep their logs. Then check
the WAV it produced — format, duration, finite samples, audible content. A zero
exit code and thirty seconds of silence go together more often than you'd like.

None of this is needed for the portable sketches or either album render path.
The process boundary exists for a sound that's worth the trouble, and [saved
dry buses](/band-in-a-python-script.html) keep that setup well away from your
routine mix comparisons.
