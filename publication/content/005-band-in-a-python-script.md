---
title: A Complete Studio in a Python Script
date: 2026-07-02
slug: band-in-a-python-script
description: Separate the score, performed sources, processed stems and delivery files so each change has a clear place.---

A code-driven studio becomes useful when it lets you change one decision
without repeating every other decision. Moving a melody requires a performance
render. Turning down its room return should only require a mix.

The repository makes that distinction visible in its output folders. A score
records the notes, dry buses hold the performed sound, processed stems hold the
mix contributions, and delivery exports hold the files people hear.

## Begin with a complete small piece

From the [repository](https://github.com/clintuitive/headless-studio):

```bash
python -m pip install -r requirements.txt
python scripts/generate_portable_samples.py --piece afterimage --output-dir Tracks/demo
```

Afterimage uses synthesized tones and noise, so no plugin or sample download
is required. Open Window and Night Transit provide different arrangements using
the same small renderer. FFmpeg adds the optional delivery WAV and MP3 exports.

The output under `Tracks/demo/afterimage` includes `score.json`, a `dry/`
directory, a `stems/` directory, `mix-float.wav` and a manifest. Open the script
beside those files: each directory corresponds to a stage you can inspect.

## Write the form before the sound

A track specification holds tempo, harmony, motifs and section choices. A
composition function walks that specification and places notes on instrument
buses. The portable example keeps this deliberately small; the album modules
hold individual forms and per-track production settings.

A different random seed is not a different composition. Give each track a
reason to exist: a shorter phrase, a different register, a delayed lead entrance,
a contrasting middle, or an ending that resolves the sequence.

The performance stage decides note timing, articulation and velocity. Keep
related notes related. A chord can roll in one direction; a phrase can lean
into its ending. Independent jitter on every boundary often sounds less
intentional than the grid it replaces.

## Keep the drums outside the pitch warp

Sign-Off's pitched material passes through slowdown and tape movement. Drum
attacks stay on the final tempo grid. That routing lets the music drift without
making the beat difficult to follow. The amount of damage belongs to the track:
some pieces need an unstable broadcast, others a gentler ambient texture.

The Quiet Hours uses a different palette: Salamander Grand Piano with VSCO
Community Edition strings. Its source preparation script retains license
records and pinned source revisions. Those samples are obtained separately;
they are not copied into the public code repository.

## Reuse the correct stage

After a source render, edit the portable sketch's mix settings and run:

```bash
python scripts/generate_portable_samples.py --piece afterimage --output-dir Tracks/demo --remix
```

This reuses dry WAVs. It does not apply changes to notes, tempo, source timbre
or performance rules. Regenerate sources for those changes.

The album renderer also has `--resume`, which compares its code/score
fingerprint, master hash and recorded asset hashes before skipping a track.
This is track-level caching, not a general dependency graph. Keep the source
assets and render environment alongside the project.

## Export what the mix actually contains

A shared room return is its own stem. A nonlinear group effect produces a group
stem. Sum the processed float stems and compare that sum with the float mix
before final dither or MP3 encoding. Then measure the delivery files themselves.
The [stem article](/stems-null-test.html) covers the checks in detail.

The [album players](/music.html) present the result as a sequence rather than a
folder of files. Listen through the transitions. The saved stages make a change
cheap enough to try; they do not decide whether it improves the record.
