# Appendix B — The Sample Instrument Manifest

This is the reference for the instrument format Chapter 5 builds: a JSON list
and a folder of WAV files. It's the input to `music_engine.ZoneSampler`, which
is also available under the historical name `ExsSampler` so older scripts keep
working. Neither name grants rights to anybody's sample library — the teaching
workflow generates its own recordings for exactly that reason.

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

Run `python scripts/generate_sampler_demo.py` to create this under
`Tracks/sampler-demo/`. All six sounds are synthesized locally.

## Zone fields

`manifest.json` is a list of objects:

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

The real demonstration has six of these; the one above is abbreviated, so it
doesn't show full keyboard and velocity coverage.

| Field | Meaning |
|---|---|
| `name` | Descriptive zone label |
| `root` | MIDI pitch recorded in the WAV |
| `keylo`, `keyhi` | Inclusive MIDI note range selecting this zone |
| `vello`, `velhi` | Inclusive velocity range selecting this zone |
| `group` | Optional articulation label, usable for group filtering |
| `file` | WAV filename relative to the instrument directory |

Use MIDI notes 0–127 and note-on velocities from 1 to 127. A note-on with
velocity zero is treated as a note-off, a MIDI convention that predates most of
us and isn't going anywhere.

Aim for complete coverage of the notes and velocities your score actually uses.
The player does have nearest-root and velocity fallbacks, and they will keep
you from silence — but a fallback is a rescue, not a mapping decision, and it
tends to sound like one.

If several zones match a note, deterministic mode selects the first; otherwise
the engine picks among them with its random generator, so supply a seeded
generator when you want repeatable performances. Group filters match substrings
in group labels, which means labels that accidentally contain one another will
accidentally match. Name them apart.

## Audio and event conventions

WAV input may be integer PCM or floating point, and source sample rates are
converted to the rendering rate. Stereo preservation is optional:
`stereo_output=True` returns two channels in channel-by-frame order. SciPy
wants frame-by-channel data when writing a stereo WAV, so transpose the
rendered array before you write it — this is the same trap as Chapter 3's, from
the other direction.

Events take the form `(sample_position, kind, channel, note, value)`, where
`kind` is `on` or `off`. An optional sixth value identifies a voice. Without
explicit voice IDs, overlapping notes on the same channel and pitch are matched
first-in, first-out. Negative event times are rejected outright.

Two things this player does not do. It reads each zone's WAV as the whole
source, ignoring the `start` and `end` offsets that older container formats
used — so prepare each recording as its own trimmed WAV file. And it implements
no sustain-loop metadata, which means a note can't be held longer than its
recording.

## Provenance

`provenance.json` is a companion record, not something the sampler reads. The
example stores its synthesis method, sample rate and WAV hashes. For external
recordings, keep the source and permission records alongside as well — a
permissive code licence has nothing to say about the terms governing somebody
else's recordings, however tidy it would be if it did.
