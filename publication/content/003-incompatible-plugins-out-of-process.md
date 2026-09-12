---
title: Run an Instrument in Its Own Process
date: 2026-07-02
slug: incompatible-plugins-out-of-process
description: Separate a plugin-specific runtime from the main studio with JSON events and a WAV result.---

A plugin can be useful without belonging inside the main Python process.
Its architecture, dependencies or host requirements may differ from the rest
of the studio. Put that instrument behind a small file-based interface:
write events to JSON, ask a helper to render them, then read its WAV.

The shared implementation is `scripts/music_engine/renderers.py`. It lets the
main arrangement use one interface while a helper owns the details of a
particular instrument and runtime.

## Keep the boundary small

The parent sends a duration and note records. The helper receives two paths:
one input JSON and one output WAV. It configures its own instrument, renders
the complete performance and exits. The parent does not need to know which
plugin parameter selects a preset or how the helper finds its native library.

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

The note fields in this example are a proposed helper contract. The bridge
passes records through; your helper must interpret the same field names and
units. It is not a universal instrument implementation.

The returned array uses channels by frames. The bridge reads the WAV at its
actual source sample rate, resamples when necessary, converts mono to stereo,
and pads or trims to the requested duration. Make that requested duration long
enough for note releases and effects tails before calling the helper.

## Match the runtime to the instrument

On a system that supports architecture translation, a helper may run under a
different architecture from its parent. That requires a compatible interpreter,
native dependencies and plugin. A process boundary alone does not translate
binaries or make a plugin portable to another operating system.

The bridge has an optional architecture argument for the macOS `arch` command.
Leave it unset for a normal subprocess. Confirm the helper works on its own
before adding it to a whole album render.

For a disk-streaming instrument, give its library time to initialize and
preserve its state across render blocks. Recreating the processor every block
can erase sustained notes or repeatedly trigger loading. Put these choices in
the helper where they can be tested independently.

## Failure is a result you must handle

The current bridge returns `None` for unavailable interpreters, empty note
lists and reported helper failures. A caller can stop the render or choose a
documented substitute. Quietly replacing an instrument during a delivery build
makes the result hard to trust, so treat the chosen source as part of the
manifest.

The bridge does not implement a timeout. For unattended work, add a bounded
supervisor around helpers that can hang, and keep their logs. Check the produced
WAV for its format, duration, finite samples and audible content. A zero exit
code can still accompany silence.

The portable sketches and both album render paths do not need this optional
plugin helper. The process boundary is there for a sound that warrants it,
while [saved dry buses](/band-in-a-python-script.html) keep that extra setup out
of routine mix comparisons.
