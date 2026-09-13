---
title: Two Albums from One Python Studio
date: 2026-09-12
slug: rebuilding-the-albums
description: Distinct writing, source preparation, performed buses, and two albums with different musical identities.
---

Sign-Off and The Quiet Hours came out of the same renderer and sound nothing
alike, which was the whole idea. Sign-Off is a worn late-night broadcast — the
last hour before the transmitter gives up. The Quiet Hours is piano-led night
music with strings that only turn up when they're needed. Shared engine,
separate records.

What the studio keeps of each one is the reasoning: scores, performed audio,
mix stems and delivery records, saved at every stage so any decision can be
found again and argued with.

## Write the identity into the score

Sign-Off varies its chord banks, motifs, section lengths and production
settings from track to track. Rabbit Ears and Vertical Hold carry the heaviest
warble; elsewhere the damage backs off and leaves room for something softer.
Its drums stay on a steady final-tempo grid while the pitched material goes
through slowdown and tape movement, so the beat holds its shape while
everything around it sags.

The Quiet Hours varies piano patterns, register, meter and phrase length
instead. A smooth performance timeline moves both ends of every note, and voice
IDs keep same-pitch overlaps correctly paired. The piano stays in front
throughout — no equally loud accompaniment elbowing it out of the way in every
passage.

## Prepare sources with records attached

The piano is Salamander Grand Piano; the strings are VSCO Community Edition.
The preparation script downloads pinned source revisions, keeps their licenses,
and builds the zone maps the renderer plays. It adjusts piano onsets and root
tuning, and extends selected string sustains with crossfades so they can hold a
long note without drifting. Source and attribution details are on the
[listening page](/music.html).

Sign-Off uses synthesized pitched sources and three separately supplied LM-2
drum samples. The public repository holds the code and the list of what's
required — not copies of the studio's installed plugins or sample libraries.

## Save a boundary before each expensive change

Every session contains score data, dry performed buses, processed stems, a
float mix and a manifest. A room-balance change reuses the dry audio and takes
seconds. A note, tempo or instrument change needs another source render and
takes as long as it takes. Code and asset hashes make it possible to ask which
existing renders still match their inputs, which matters more than it sounds
like when you come back to a record after a month away.

Processed float stems reconstruct the float mix. The nonlinear shared music bus
stays a group stem, because processing each input separately is simply a
different mix and pretending otherwise would be a lie told in WAV format. Final
delivery applies the chosen gain and exports PCM WAV and MP3, both measured
after encoding rather than before.

## Listen as a record

The [album players](/music.html) show the artwork and the complete track lists.
Pick a song, or let the sequence run. Each player moves to the next track on
its own and stops at the end, and starting one pauses the other.

The technical checks confirm that the expected files were produced — nothing
more than that. Whether the sequence works is a question about transitions,
density, how often a phrase repeats before it wears out, and whether the last
track earns the ending. That part only answers to listening. The [album
chapter](/book/chapter-13.html) goes into the choices in detail, and the
[repository](https://github.com/clintuitive/headless-studio) has the runnable
scores and renderer if you'd rather read the source.

To explore the system without tracking down external assets, start with
Afterimage, Open Window or Night Transit. They're compact sketches built from
synthesized tones and noise, and they go through exactly the same stages.
