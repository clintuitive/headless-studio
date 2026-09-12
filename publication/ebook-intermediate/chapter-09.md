# Chapter 9 — Performance Timing and a Stable Beat

Timing has a musical shape. A pianist can lean into a phrase, linger at its
end, or roll a chord across the keyboard. Adding unrelated random offsets to
every note is a poor substitute for those decisions.

The studio treats performance as a step between the score and the instrument.
The score says what happens in musical time; the performance places related
note boundaries on a shared timeline and assigns articulation and velocity.
The saved events are what the instrument actually receives.

## Move both ends of a note

The Quiet Hours renderer uses this smooth mapping, with `t` measured in seconds:

```python
import numpy as np

def warp(t):
    return t + .20 * np.sin(2 * np.pi * t / 16) + .055 * np.sin(2 * np.pi * t / 4)
```

The long cycle creates phrase-level movement; the shorter cycle adds a smaller
variation. These settings are choices for this record, not universal values
for a convincing performance. The mapping remains increasing at these settings,
so later score positions remain later in the performance.

Apply the same map to the start and end. Moving only the start changes the
note's duration for an unrelated reason:

```python
rate = 44100
start_seconds = 2.0
end_seconds = 3.5
start = max(0, warp(start_seconds))
end = max(start + .03, warp(end_seconds))
voice_id = 17
performed = [
    (round(start * rate), 'on', 0, 60, 64, voice_id),
    (round(end * rate), 'off', 0, 60, 0, voice_id),
]
```

The first field is now an integer frame position. The final field identifies
this particular voice. Repeated notes at the same pitch can overlap without
a later note-off accidentally ending the wrong voice. The zone sampler also
accepts five-field events and pairs them FIFO; explicit IDs remove ambiguity
when constructing complex performances.

## Velocity and articulation have different jobs

Write strong and weak notes into the phrase before adding variation. Velocity
can select a different recording in a layered instrument, so a small change
can affect attack character as well as loudness. Listen across layer boundaries
instead of assuming the response is smooth.

Articulation controls how long a note is held. In the piano renderer, supporting
parts can release earlier than the melodic line. Apply that shortening after
the shared time map so it remains a deliberate relationship between voices.

Chord rolls belong in the score or performance rule. A consistent upward roll
is a gesture; independent random offsets on every chord tone are a different
sound. Choose the one the passage calls for.

## Keep randomness local and repeatable

Where the renderer uses random choices, derive a seed from the track and part:

```python
import hashlib

def part_rng(title, part):
    key = (title + ':' + part).encode()
    seed = int.from_bytes(hashlib.sha256(key).digest()[:8], 'little')
    return np.random.default_rng(seed)
```

This prevents a change in one instrument from consuming another instrument's
random sequence. It does not make every edit local within a part: inserting
an extra draw can still change later draws from that generator. Save the
performed events and dry audio when you need an exact comparison.

The Quiet Hours' main timing map is deterministic. It does not need per-note
random jitter to create movement. Seeded variation is one tool, not a required
ingredient in every performance.

## Let the rhythm provide a reference

Sign-Off places its drum attacks on the final tempo grid. Its pitched material
passes through slowdown and warble afterward. That is an audio transformation,
not the same operation as mapping piano note boundaries before playback.

A stable beat can make pitch drift feel intentional. Conversely, an unaccompanied
piano phrase can carry its own timing without a drum clock. Decide which part
provides the reference before applying timing effects across a mix.

Listen to accents, chord attacks, note releases and transitions separately.
Keep the performance fixed while comparing mixes, then regenerate it only when
the timing or articulation is the thing you intend to change.
