# Appendix B — The Sample Instrument Manifest

Chapter 5's instrument uses a JSON list and WAV files. This is the input to
`music_engine.ZoneSampler`, also available under the historical name
`ExsSampler`. Neither name grants rights to a sample library. The public
teaching workflow generates its own recordings.

## Folder layout

```text
instrument/
  manifest.json
  provenance.json
  tone-48-soft.wav
  tone-48-bright.wav
  tone-60-soft.wav
  tone-60-bright.wav
  tone-72-soft.wav
  tone-72-bright.wav
```

Run `python scripts/generate_sampler_demo.py` to create this example under
`Tracks/sampler-demo/`. All six sounds are synthesized locally.

## Zone fields

`manifest.json` contains a list of objects:

```json
[
  {
    "name": "Tone 60 soft",
    "root": 60,
    "keylo": 54,
    "keyhi": 65,
    "vello": 1,
    "velhi": 79,
    "group": "Synth tones",
    "file": "tone-60-soft.wav"
  }
]
```

The complete demonstration has six objects. This abbreviated example contains
only one, so it does not show the full keyboard and velocity coverage.

| Field | Meaning |
|---|---|
| `name` | Descriptive zone label |
| `root` | MIDI pitch recorded in the WAV |
| `keylo`, `keyhi` | Inclusive MIDI note range selecting this zone |
| `vello`, `velhi` | Inclusive velocity range selecting this zone |
| `group` | Optional articulation label, usable for group filtering |
| `file` | WAV filename relative to the instrument directory |

Use MIDI notes 0–127 and positive note-on velocities 1–127. A velocity-zero
note-on is treated as note-off. Prefer complete coverage of the notes and
velocities used by your score. The player has nearest-root and velocity
fallbacks, but those are not substitutes for a deliberately mapped instrument.

If several zones match, deterministic mode selects the first. Otherwise the
engine selects among them using its random generator. Supply a seeded generator
for repeatable performances. Group filters match substrings in group labels,
so choose labels that do not accidentally overlap.

## Audio and event conventions

WAV input may be integer PCM or floating point. Source sample rates are
converted to the requested rendering rate. Stereo preservation is optional;
`stereo_output=True` returns two channels in channel-by-frame order. SciPy
expects frame-by-channel data when writing a stereo WAV, so transpose the
rendered array.

Events have the form `(sample_position, kind, channel, note, value)`, where `kind` is
`on` or `off`. An optional sixth value identifies a voice. Without explicit
voice IDs, overlapping notes of the same channel and pitch use first-in,
first-out note-off matching. Negative event times are rejected.

The current player reads each zone's WAV as its source; it does not use old
container `start` or `end` offsets. Prepare each source recording as a separate
WAV. Sustain-loop metadata is not implemented in this player.

## Provenance

`provenance.json` is a companion record, not a required sampler input. The
example records its synthesis method, sample rate and WAV hashes. For external
recordings, also retain source and permission records. A permissive code license
does not replace the terms governing the recordings themselves.
