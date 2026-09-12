# Chapter 9 — Humanization: The Hands Drift, the Machine Doesn't

Rebuild note: the new piano performance uses phrase-level timing and
paired note boundaries. Both ends of a note follow the same timeline, with
voice IDs retained through overlap. Sign-Off's drums deliberately keep a
steady grid; random jitter is not automatically more musical. Keep a fixed
seed for A/B comparisons, then decide by listening.

Render Chapter 8's arrangement exactly as written and you'll get something
technically perfect and emotionally dead: every note precisely on the
grid, every volume exactly as specified, every bar a clone of the last.
Real performances live in the flaws — the few milliseconds a bassist leans
ahead of the beat, the extra weight of a fingertip on an accented note.
This chapter adds those flaws with a random number generator. Its thesis:
the craft is all in restraint. The randomness must be **small**,
**clipped**, **repeatable** — and above all **unevenly applied**, because
the *contrast* between what drifts and what doesn't is where the life
actually comes from.

## The whole engine

```python
rng = np.random.default_rng(SEED)     # one seeded generator for the song

def human(t, vel, t_sd=0.005, v_sd=6):
    """Nudge a note's start time and velocity by a small random amount."""
    nudge = rng.normal(0, t_sd)                       # bell-curve random
    nudge = np.clip(nudge, -2.5 * t_sd, 2.5 * t_sd)   # cut off the extremes
    t = max(t + float(nudge), 0.0)
    vel = int(np.clip(vel + rng.normal(0, v_sd), 1, 127))
    return t, vel
```

Eight lines. Everything else in the chapter is about how to use them.

**The sizes.** `rng.normal(0, t_sd)` draws from a bell curve centered on
zero — most nudges tiny, a few larger — with a spread (`t_sd`) of 5
milliseconds. Is that a lot? At this song's tempo an eighth note lasts 254
ms, so we're moving notes by about two percent of their slot: *felt*, not
heard as sloppiness. Measured against real players, ±5 ms is a tight
bassist on a good night — we're not simulating error, we're simulating a
professional. Push past ±15 ms and the illusion flips: instead of a player
breathing, you hear a machine glitching.

**The clip.** Bell curves have tails — rare, large draws. One note in a
thousand would land 20+ ms early, and a single such note reads as a
mistake. `np.clip(x, lo, hi)` (clamp a value into a range) amputates the
tails while keeping the natural bell shape. The extra `max(..., 0.0)`
guards one absurd edge case: the very first note of the song drawing a
negative start time. Across an album, every possible random draw *will*
eventually be drawn; cheap paranoia is mandatory.

**The seed.** All randomness flows from one generator started with a fixed
`SEED`. So the "random" performance is *a take* in the fullest sense —
render 47 is note-for-note identical to render 1, and every listening
comparison in this book compares mixes, never accidentally-different
performances. The seed even becomes a musical control: if this
performance's particular constellation of nudges bothers you in the second
chorus, `SEED = 8` is a *different take* of the same song. I've re-rolled
a performance exactly twice across an album; both times the new take fixed
the bar in question, and it lives in version control now, where takes live.

## The contrast principle

Here's what separates this chapter from the "humanize" checkbox in a DAW.
In the darkwave band, the jitter applies to the bass and the guitars —
**and not to the drum machine, and not to the synth pad.** The script's
comment states the rule:

```python
# Humanization: the hands drift, the machine doesn't.
```

Think about why. If *everything* drifts, the listener has no reference
grid to feel the drift against — the whole song is just slightly loose.
If *nothing* drifts, there's no life. But a drum machine ticking
immovably while a bassist pushes eighth-notes a few milliseconds hot
against it? That tension is a *sound* — arguably the defining sound of
every band that ever played alongside a drum machine, which is this
genre's entire family tree. The pad stays on the grid for a different
reason: it's texture, not performance. Nobody "plays" a pad.

So the rule generalizes: **for each band member, decide — hands or
machine — and commit.** It's a musical decision, and it changes per
record: the synth album humanizes nearly everything (that album's fiction
is "played live onto tape"), the darkwave record humanizes exactly three
players.

## Three more dimensions

**Velocity is tone, not just volume.** Remember from Chapters 2 and 5
that good sample libraries switch *recordings* based on how hard a note
is played. So ±6 of velocity jitter doesn't make notes slightly
louder/quieter — it varies the *attack character* hit by hit, which is
most of what "a hand" sounds like. One discipline: write the *accents*
into the base velocities first (downbeats 105, offbeats 96), then let
noise perturb around them. Accents are composition; jitter is
performance; don't let the second wash out the first.

**Duration.** Real note lengths vary even more than start times — fingers
release early, linger late:

```python
dur = dur_beats * BEAT * 0.82 * rng.uniform(0.92, 1.08)
```

The `0.82` is *articulation* — this bassline is short-and-punchy by
intent. The ±8% (`rng.uniform` — evenly spread randomness, no bell curve
needed here) is the hand.

**The byproducts — the best trick in the chapter.** The most persuasive
humanization isn't jitter at all; it's the sounds a performance makes
*besides the notes*:

```python
# Occasionally, a fret squeak as the hand shifts position between bars.
if rng.random() < 0.28:                    # 28% of bars
    t, vel = human(bar_t + 3.45 * BEAT, 46, t_sd=0.03)
    add_note("gtr", t, 0.3, FRET_NOISE_CHANNEL, 60, vel)
```

General MIDI instrument #120 — "Guitar Fret Noise," the joke instrument of
every 90s sound card — earns its existence here: a quiet squeak near the
end of about a quarter of the guitar bars, placed where a real left hand
shifts, with extra timing looseness because squeaks aren't *played*, they
happen. Listeners never consciously notice it. But mute that channel
after a day of living with it, and the guitarist evaporates — what's left
is unmistakably a sequencer. The principle travels: **model the
byproducts, not just the product.** Breath before a sung phrase, the
scrape of a pick on a heavy downstroke, a piano's pedal thump — every
instrument has them, and each costs a conditional and a quiet note.

(Chapter 7's lead voice was doing humanization too, by the way — the
pitch slide between notes and the vibrato that fades in late are
*continuous* human behaviors, where this chapter's jitter is per-note.
Melodic instruments carry their humanity between the notes.)

## What NOT to humanize

A checklist, each entry paid for with a mistake:

- **The drum machine** — covered above. Note that even its *volumes* stay
  fixed: the real hardware had accent buttons, not touch sensitivity. A
  velocity-humanized LinnDrum is a category error.
- **Notes of one chord, independently.** A pad chord is one gesture; give
  its notes independent ±5 ms nudges and you get a sloppy flam, not
  warmth. If you want a strum, model a *strum* — a deliberate roll in one
  direction — not noise.
- **Structure.** Don't randomize *what* gets played per render… which the
  fret squeak, at 28% per bar, seems to violate. The resolution: it's
  drawn from the *seeded* generator, so the take includes its accidents,
  reproducibly. Randomness in content is fine when it's committed to the
  take; what's forbidden is randomness that escapes the seed and changes
  between renders.

## One architectural note

`human()` runs when the events are *written* (Chapter 8's walker), not
when audio renders. The event lists that reach the instruments are the
finished performance, fully decided. Consequence: stems, re-renders
through different amps, and every downstream experiment all share the
identical performance by construction. Humanization is the last thing
that happens to the *score*; nothing that happens to the *sound* ever
touches timing again.

The band now plays like a band. But it still sounds like six signals in
a void — every player recorded direct into nothing. The next two chapters
build what you can't see in the arrangement: each member's rig, and then
the room they're all standing in.
