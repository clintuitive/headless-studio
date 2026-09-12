---
title: Two Albums from One Python Studio
date: 2026-09-12
slug: rebuilding-the-albums
description: Distinct writing, source preparation, performed buses, and two albums with different musical identities.
---

Sign-Off and The Quiet Hours share a renderer architecture, but their musical
roles are different. Sign-Off is a worn late-night broadcast. The Quiet Hours
is piano-led night music with selective string support. The studio preserves
those decisions as scores, performed audio, mix stems and delivery records.

## Write the identity into the score

Sign-Off varies its chord banks, motifs, section lengths and production settings.
Rabbit Ears and Vertical Hold carry the strongest warble; other tracks leave
room for softer, more ambient textures. Its drums stay on a steady final-tempo
grid while pitched material passes through slowdown and tape movement.

The Quiet Hours varies piano patterns, register, meter and phrase length.
A smooth performance timeline maps both ends of a note, and voice IDs keep
same-pitch overlaps paired. The piano stays in front of the strings rather
than competing with an equally loud accompaniment in every passage.

## Prepare sources with records attached

The piano is Salamander Grand Piano and the strings are VSCO Community Edition.
The preparation script downloads pinned sources, retains licenses, and builds
the zone maps used by the renderer. It adjusts piano onsets and root tuning,
and extends selected string sustains with crossfades. Source and attribution
details appear on the [listening page](/music.html).

Sign-Off uses synthesized pitched sources and three separately supplied LM-2
drum samples. The public repository includes the code and source requirements,
not copies of the studio's installed plugins or sample libraries.

## Save a boundary before each expensive change

Each session contains score data, dry performed buses, processed stems, a float
mix and a manifest. A room-balance change can reuse dry audio. A note, tempo or
instrument change needs another source render. Code and asset hashes help
identify which existing track renders still match their inputs.

Processed float stems reconstruct the float mix. A nonlinear shared music bus
remains a group stem; independently processing each input is a different mix.
Final delivery applies the selected gain and exports PCM WAV and MP3, which
are measured after encoding.

## Listen as a record

The [album players](/music.html) show the artwork and complete track lists.
Choose a song or play through the sequence. Each player advances to the next
track and stops at the end; starting other audio pauses the current player.

Technical checks establish that the expected files were produced. Listen to
transitions, density, phrase repetition and endings to decide whether the
sequence works. The [album chapter](/book/chapter-13.html) explains the choices
in more detail, and the [repository](https://github.com/clintuitive/headless-studio)
contains the runnable scores and renderer.

To explore the system without external assets, start with Afterimage, Open
Window or Night Transit. These compact sketches demonstrate the same stages
using synthesized tones and noise.
