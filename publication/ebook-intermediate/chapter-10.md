# Chapter 10 — Every Band Member Gets a Rig

The plugin rigs below are optional, platform-dependent examples. The
rebuilt albums use NumPy/SciPy effects and FFmpeg delivery without requiring
Pedalboard. Sign-Off combines pitched instruments before nonlinear treatment;
dry buses are cached so a rebalance can rerun that shared processing. See
Chapter 12 for the resulting stem contract.

A band isn't six instruments; it's six *rigs*. The guitarist owns a chorus
pedal, an amp with the volume parked exactly where pick attack decides
between clean and dirty, and a delay pedal set to the song's tempo. The
bassist's sound is a recording-studio trick older than most studios. This
chapter builds each member's signal chain out of Chapter 3's plugin
hosting, and its organizing idea is that **a rig is knowledge written as a
chain** — the order of effects, how hard each stage drives the next, and
the occasional parallel split are where genre actually lives. We'll build
the three rigs that carry the darkwave record, each number explained.

First, one unit of measure, since this chapter speaks it constantly:
audio levels are measured in **decibels (dB)** — a relative scale where
+6 dB is roughly "twice as loud a signal," −6 dB half, and 0 dB "no
change." Effect parameters like `gain_db=-8` mean "turn this down to
about 40% of its level."

## The guitar rig: chorus into the amp, delay after

```python
amp = load_nam(NAM_VST3, "Amps/Vox_AC15_TopBoost.nam")
amp.input_db = -3.0    # hold the amp just below break-up

dotted_8th = BEAT * 0.75          # a delay time locked to the tempo
gtr_fx = Pedalboard([
    Chorus(rate_hz=0.8, depth=0.2, centre_delay_ms=12.0, mix=0.5),
    amp,
    Delay(delay_seconds=dotted_8th, feedback=0.28, mix=0.16),
    Reverb(room_size=0.85, damping=0.45, wet_level=0.24, dry_level=0.76),
])
```

Four devices, four decisions:

**Chorus placement.** A chorus makes one signal sound like several
slightly-detuned copies. Placed *before* the amp — on the floor, where
this genre's players put it — the amp distorts the shimmering signal, and
the amp's natural compression glues the wobble into the sound. Placed
after the amp, it wobbles the finished distortion instead: wider,
swooshier, more of an 80s-studio-rack move. Both are legitimate; only one
is *this* record; the difference is the order of a Python list.

**The amp's one critical knob.** `input_db = -3.0` sets how hard the
guitar signal hits the amp — parked just under the point where the AC15
starts to growl. Result: each note's *velocity* decides, note by note,
whether it stays clean or barks. Feel the system click together: Chapter
9's velocity jitter only becomes *audible* because the amp sits at this
sensitive spot. Humanization and amp settings are one mechanism wearing
two chapters.

**The tempo-locked delay.** A delay repeats the signal like an echo.
`BEAT * 0.75` — a "dotted eighth note" — is the post-punk echo: repeats
that land *between* the notes being played, weaving a single picked line
into perpetual motion. `feedback=0.28` gives about two audible repeats;
`mix=0.16` keeps them felt more than heard. The delay sits *after* the
amp because echoes of a distorted note stay distinct, while distorting an
echoing signal turns to mush.

**A private reverb, small.** This is the amp's own halo, not the band's
shared room (that's next chapter — the two coexist deliberately).

One trap for anyone using amp captures: some `.nam` files capture a *full
rig* — amplifier plus speaker cabinet plus microphone — and some capture
the *amplifier head only*. A guitar speaker cabinet acts as a brutal
treble filter; play a head-only capture without one and you get a fizzy
mess that sounds broken. Head-only captures need a cabinet simulation
after them (one `Convolution` effect loaded with a speaker recording —
next chapter explains the technique). Half the "this amp capture is bad"
complaints online are a missing cabinet.

## The bass rig: the parallel split

The oldest trick in bass recording, as code:

```python
from pedalboard import Mix, Chain, Gain, HighpassFilter, Compressor

dug = load_nam(NAM_VST3, "Amps/Tech21_dUg_BassPreamp.nam")
dug.input_db = -6.0

bass_fx = Pedalboard([
    HighpassFilter(cutoff_frequency_hz=35),      # remove sub-rumble
    Mix([                                        # run BOTH in parallel:
        Chain([Gain(gain_db=0.0)]),              #   path 1: untouched
        Chain([dug, Gain(gain_db=-8.0)]),        #   path 2: distorted, quiet
    ]),
    Compressor(threshold_db=-18, ratio=4, attack_ms=4, release_ms=90),
])
```

`Mix` splits the signal into branches, runs each `Chain`, and adds the
results — a parallel wiring, like a console's routing.

Why split at all? Distortion is how a bass gets *heard* on small speakers
— but distorting the bass directly makes it thinner, because distortion
squashes the deep fundamental tone while adding buzz. So the studio trick:
keep the clean low end untouched in one path, add a distorted copy
*underneath* it — 8 dB down, reinforcement rather than replacement. On
good speakers you mostly hear the clean path; on a phone speaker, the
gritty path *is* the bass. That's not compromise; that's engineering for
how people actually hear records.

Placement details that matter: the rumble filter comes *before* the split
so both paths agree about the low end; the compressor comes *after* the
split so it squeezes both paths together and they move as one instrument
(its release time, 90 ms, is chosen to recover between eighth-notes at
this tempo, so it breathes *with* the bassline). Compress before the split
and the two paths' dynamics drift apart on accented notes.

## The others, briefly

**Pad:** slow chorus into a big reverb, nothing else — texture wants width
and depth. On the synth album this is the *entire* pad sound; the script's
comment is six words of synth history: *the Juno move: chorus makes the
pad*. **Drums:** the Chapter 6 compressor, and *no reverb at all* — their
space comes exclusively from the shared room, because nothing exposes fake
space like a drum kit in two rooms at once. **The synth lead:** the same
dotted-eighth delay as the guitar — that delay is the genre's signature,
portable across instruments.

Across all of them, one pattern: **two to four devices, each with a
reason.** A rig is not a place to accumulate insurance effects. When a
four-device chain sounds wrong, commenting out devices one render at a
time finds the culprit in minutes. A twelve-device chain, never.

## Rigs are for sweeping

Because a rig is a data-shaped object, every knob is one for-loop away
from being a controlled experiment — Chapter 1's leverage argument,
landing where it pays most:

```python
# Which amp? (this is how the AC15 beat the Twin for this record)
for capture in glob.glob("Amps/*.nam"):       # glob: list files by pattern
    render_song_with(load_nam(NAM_VST3, capture))

# How hard into the amp?
for drive in (-9, -6, -3, 0, 3):
    amp.input_db = drive
    render_song_with(amp)

# Chorus in front of the amp, or behind?
for chain in ([chorus, amp, delay], [amp, chorus, delay]):
    render_song_with(Pedalboard(chain + [reverb]))
```

Each render costs about a minute; each settles a question that studio
folklore usually settles by argument.

## Practical notes

- **One plugin instance per chain.** Plugins keep internal state; sharing
  one instance between two chains eventually misbehaves. Loading is
  cheap — load per rig.
- **Fix "too hot" at the amp's input, not in the mix.** If a bus is
  overdriving its amp, add a `Gain` *before* the amp (that's a volume
  pedal). Turning the bus down *after* the amp changes loudness but keeps
  the wrong tone — the classic mixup when there are no meters to look at.
- **Process the whole bus once, at the end.** Render the complete
  performance dry, then run it through the rig in one call. Processing
  note-by-note would restart every delay and reverb per note — echoes
  that never repeat, reverbs that never bloom. The rig hears the
  *performance*, the way an amp does.

Six players, six rigs — still six separate rooms. The next chapter builds
the one thing they'll share, and it's where the band finally sounds like
it's standing somewhere.
