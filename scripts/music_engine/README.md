# music_engine

Shared studio infrastructure for the generators in this repository.

Song scripts remain responsible for musical decisions:

- tempo, meter, key and progressions;
- melodies, riffs and voicings;
- movements and arrangement;
- instrument and effects choices;
- final bus levels and creative automation.

The package owns reusable mechanics:

- `audio.py` — stereo panning, RMS/peak matching and fades;
- `events.py` — named event buses and controller envelopes;
- `humanize.py` — seeded timing and velocity drift;
- `samplers.py` — EXS instrument and velocity-layered drum playback;
- `plugins.py` — headless Neural Amp Modeler capture loading;
- `renderers.py` — subprocess bridges such as Intel-only Ample Bass.

All public functions accept explicit sample rates, paths and random-number
generators. This keeps the engine reusable while preserving deterministic
renders in the existing songs.

## Sampler behavior (Session 01 repairs)

`ExsSampler(..., stereo_output=True)` returns `(2, samples)` and preserves
source stereo; the default remains mono for legacy generators. Both samplers
convert source WAV sample rates to the requested rate and center unsigned
8-bit PCM correctly. Instruments interpolate only the region actually played.

Five-field events retain MIDI-style FIFO note-off matching for repeated
channel/pitch pairs. New callers may append a sixth field containing a stable
voice ID to both on/off events; use this for nested overlaps. Note-on velocity
zero is a note-off. Unterminated notes sustain to the render boundary.
Negative event positions are rejected. The sampler does not yet implement
sustain-pedal controllers or a high-quality pitch-shift engine.

The overlapping-note repair intentionally changes affected old renders.
Seeded rendering is repeatable with the same event order and asset set;
callers should create independent seeded samplers per track/part. NAM's host
loads only when requested, so sampler tests do not require Pedalboard.

## Audition session

From the project root:

```bash
.venv/bin/python Scripts/generate_studio_auditions.py
.venv/bin/python Scripts/generate_studio_auditions.py --remix
PYTHONPATH=Scripts .venv/bin/python -m unittest discover -s Scripts/tests -v
```

The second command reuses saved dry sources. It is an explicit cache reuse,
not automatic cache invalidation: rerun without `--remix` when composition,
sampler code, or source assets change. Source hashes, event data, seeds, and
working-code hashes are saved with the session. The original albums are not
output destinations. These auditions use NumPy, SciPy, and FFmpeg only.
