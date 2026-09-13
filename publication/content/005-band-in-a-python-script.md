---
title: A Complete Studio in a Python Script
date: 2026-07-02
slug: band-in-a-python-script
description: Separate the score, performed sources, processed stems and delivery files so each change has a clear place.
---

A code studio earns its keep the moment you can change one decision without
paying for all the others. Move a melody and yes, something has to play it
again. Turn down the room return and nothing should have to play anything —
that's a mix, and a mix ought to cost seconds.

The repository makes that split visible in its output folders. A score holds
the notes. Dry buses hold the performance. Processed stems hold what each part
actually contributes to the mix. Delivery exports hold the files people listen
to. Every change belongs to exactly one of those stages, and knowing which one
is most of the skill.

## Begin with a complete small piece

From the [repository](https://github.com/clintuitive/headless-studio):

```bash
python -m pip install -r requirements.txt
python scripts/generate_portable_samples.py --piece afterimage --output-dir Tracks/demo
```

Afterimage is built from synthesized tones and noise, so there's nothing to
download and no plugin to configure. Open Window and Night Transit are
different arrangements through the same small renderer. FFmpeg, if you have it,
adds the WAV and MP3 delivery exports.

Look under `Tracks/demo/afterimage` and you'll find `score.json`, a `dry/`
directory, a `stems/` directory, `mix-float.wav` and a manifest. Open the
script next to those folders. Each directory is a stage you can open up and
inspect, which is a thing a DAW project file will never let you do.

## Write the form before the sound

A track specification holds tempo, harmony, motifs and section choices. A
composition function walks that specification and puts notes on instrument
buses. The portable example keeps this deliberately tiny; the album modules
carry each track's own form and production settings.

A word of warning, learned the hard way: a different random seed is not a
different composition. It's the same song wearing a slightly different hat.
Give each track an actual reason to exist — a shorter phrase, a different
register, a lead that holds back for eight bars, a middle section that
contradicts the rest, an ending that finally resolves what the sequence has
been circling.

Then the performance stage decides timing, articulation and velocity. Keep
related notes related. A chord can roll in one direction; a phrase can lean
into its ending. Independent jitter sprinkled on every note boundary usually
sounds *less* intentional than the rigid grid it replaced.

## Keep the drums outside the pitch warp

In Sign-Off the pitched material goes through slowdown and tape movement while
the drum attacks stay on the final tempo grid. That one routing decision lets
the music drift and sag without making the beat hard to follow. How much damage
a track takes is the track's own business — some want an unstable broadcast,
others want something gentler to lie underneath.

The Quiet Hours works from a different palette entirely: Salamander Grand Piano
with VSCO Community Edition strings. Its source preparation script keeps the
license records and pins the source revisions it downloaded. Those samples are
obtained separately; they aren't copied into the public repository.

## Reuse the correct stage

Once the sources are rendered, edit the portable sketch's mix settings and run:

```bash
python scripts/generate_portable_samples.py --piece afterimage --output-dir Tracks/demo --remix
```

That reuses the dry WAVs. It will not apply changes to notes, tempo, timbre or
performance rules — those need a fresh source render, and quietly pretending
otherwise is how you end up shipping last week's melody.

The album renderer has `--resume` as well, which compares its code and score
fingerprint, the master hash and the recorded asset hashes before it skips a
track. That's track-level caching, not a general dependency graph; it can only
notice what it was told to fingerprint. Keep the source assets and the render
environment with the project.

## Export what the mix actually contains

A shared room return is its own stem. A nonlinear group effect produces a group
stem. Sum the processed float stems, compare that sum against the float mix
before any dither or MP3 encoding, and then measure the delivery files
themselves rather than assuming they inherited the mix's good behaviour. The
[stem article](/stems-null-test.html) goes through the checks properly.

And then listen. The [album players](/music.html) present the result as a
sequence rather than a folder of files, which is the only way to hear whether
the transitions work. Saved stages make it cheap to try a change. They have no
opinion whatsoever about whether it was an improvement.
