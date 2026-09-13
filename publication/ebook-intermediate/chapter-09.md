# Chapter 9 — Performance Timing and a Stable Beat

Timing has a shape. A pianist leans into a phrase, lingers at its end, rolls a
chord across the keyboard because the hand arrives in an order. None of that is
random, and this is the chapter where I talk you out of the first thing
everyone tries.

The first thing everyone tries is adding a small random offset to every note.
It's one line, it's satisfying to write, and it doesn't work. What it produces
isn't a human player; it's a machine with a tremor. Real timing deviations are
*correlated* — the notes of a chord move together, a phrase drifts as a unit,
the player is late because the last bar was busy. Independent jitter throws all
that structure away and keeps only the noise.

So the studio treats performance as a genuine stage between the score and the
instrument. The score says what happens in musical time. The performance places
related note boundaries on a shared timeline, and decides articulation and
velocity. What the instrument actually receives is the result.

## Move both ends of a note

The Quiet Hours uses a smooth mapping from score time to performed time, with
`t` in seconds:

```python
import numpy as np

def warp(t):
    return t + .20 * np.sin(2 * np.pi * t / 16) + .055 * np.sin(2 * np.pi * t / 4)
```

Two cycles: a sixteen-second one that creates phrase-level movement, and a
four-second one adding a smaller variation on top. Because every note consults
the same function, notes that are close together in the score stay close
together in the performance — which is exactly the correlation that random
jitter destroys.

Two things worth noting. These particular numbers are choices for this record,
not universal constants for a convincing performance; treat them as a starting
point to argue with. And at these settings the mapping stays increasing, so a
note later in the score is still later in the performance. Push the
coefficients far enough and it would stop being monotonic, at which point your
music would begin playing backwards in places, which is a fun way to spend an
evening but not what anyone ordered.

Now the important part. Apply the map to the start *and* the end:

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

Move only the start and you've changed the note's *duration* as a side effect —
a note that was meant to last a beat now lasts a beat plus however much the
warp happened to shift it. Nobody decided that. Move both ends and the note
keeps its intended length while sitting where the performance put it. The
`max(start + .03, ...)` floor just guarantees the note never collapses to
nothing.

The first field is an integer frame position, as always. The sixth field is new:
a voice ID. Repeated notes at the same pitch can now overlap without a later
note-off accidentally ending the wrong one — which is a real hazard the moment
a performance starts moving note boundaries around. The zone sampler still
accepts plain five-field events and pairs them first-in, first-out; explicit
IDs simply remove the ambiguity when you're building something complicated.

## Velocity and articulation have different jobs

Write the strong and weak notes into the phrase *before* you add any variation.
A phrase that has no shape at velocity 64 will not acquire one from randomness.

Remember too that velocity can select a different recording in a layered
instrument — Chapter 5's soft and bright layers, or a real piano library's
dozen. So a small velocity change can alter attack character as well as
loudness, and it can do so suddenly, at a layer boundary. Listen across those
boundaries rather than assuming the response is smooth.

Articulation is a separate control: how long the note is held. In the piano
renderer, supporting parts release earlier than the melodic line, which keeps
the texture from turning into mud while the melody still sings. Apply that
shortening *after* the shared time map, so it stays a deliberate relationship
between voices rather than an accident of two maps disagreeing.

And chord rolls belong in the score or in an explicit performance rule. A
consistent upward roll is a gesture — a hand moving in a direction.
Independent random offsets on every chord tone are something else entirely, and
the difference is instantly audible. Choose the one the passage wants.

## Keep randomness local and repeatable

Where the renderer does use random choices, it derives the seed from the track
and the part:

```python
import hashlib

def part_rng(title, part):
    key = (title + ':' + part).encode()
    seed = int.from_bytes(hashlib.sha256(key).digest()[:8], 'little')
    return np.random.default_rng(seed)
```

Without this, every part draws from one shared generator, and adding a note to
the bass silently re-rolls the guitar. You change one thing, and something
unrelated changes too — the exact failure that Chapter 1's determinism argument
exists to prevent.

Be clear about what it doesn't fix, though. Randomness is now local to each
part, but it isn't local *within* a part: insert an extra draw near the start
and every later draw from that generator shifts. When you need an exact
comparison, save the performed events and the dry audio. Those are the only
real guarantee.

Worth saying plainly: The Quiet Hours' main timing map is fully deterministic.
It doesn't need per-note random jitter to create movement, and it doesn't
sound stiff without it. Seeded variation is one tool among several, not a
required ingredient.

## Let the rhythm provide a reference

Sign-Off puts its drum attacks on the final tempo grid and sends its pitched
material through slowdown and warble afterwards. That's an audio transformation
applied to rendered sound — a different operation entirely from mapping note
boundaries before playback, even though both make timing move. One edits the
schedule; the other edits the waveform.

The musical principle underneath is the same in both records: a stable beat
makes pitch drift feel intentional. Take the beat away and drift just sounds
broken. Conversely, an unaccompanied piano phrase carries its own time and
needs no drum clock at all. Decide which part is the reference before you start
applying timing effects across a mix.

When you listen back, listen to one thing at a time: accents, then chord
attacks, then note releases, then transitions. And keep the performance fixed
while you compare mixes. Regenerate it only when timing or articulation is the
thing you actually meant to change.

---

*Next — Chapter 10: Give Each Bus a Role in the Mix.*
