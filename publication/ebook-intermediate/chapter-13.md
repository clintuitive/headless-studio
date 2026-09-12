# Chapter 13 — Two Albums, Distinct Musical Identities

An album renderer needs a shared engine and individual songs. Reusing sample
loading, event scheduling and export code makes work easier. Reusing a complete
form for every title can make a record feel like one long variation.

Sign-Off and The Quiet Hours demonstrate two palettes built on the same staged
workflow. Sign-Off is an imperfect late-night broadcast: steady drum attacks,
worn pitched sources and space for dreamy ambient pieces. The Quiet Hours puts
piano in front, with strings used selectively and timing shaped around phrases.

## Give each track a reason to exist

The Sign-Off specifications hold individual chord banks, motifs, answers,
section lists and production settings. Rabbit Ears and Vertical Hold use the
heaviest warble. Other tracks use gentler movement, thinner textures or fewer
drums. A strong identity does not require the same intensity everywhere.

The Quiet Hours varies meter, register, piano pattern, phrase length and string
entrances. Slow Rain uses its own event-writing path; the other tracks have
explicit specifications in `scripts/album_v2/quiet_hours.py`. Shared playback
does not require identical composition machinery.

Before rendering, describe the lead idea and the role of each section. A score
table can expose repeated forms, but different parameter values alone do not
prove musical contrast. Listen to the sequence and ask what each track adds.

## Prepare the instruments

The Quiet Hours uses Salamander Grand Piano and VSCO Community Edition strings.
Run the preparation script and preflight from the repository root:

```bash
python scripts/prepare_open_instruments.py --asset-root /path/to/studio-assets
python scripts/check_album_assets.py --album quiet-hours --asset-root /path/to/studio-assets
```

The preparer downloads pinned source revisions and retains their license
records. It selects the piano zones needed by the scores, applies onset offsets
and retuned root mappings, and converts them to stereo 44.1 kHz float WAVs.
For the strings it selects quiet sustain layers, normalizes them, and extends
sustains with crossfades. It does not implement the complete source SFZ player,
including its pedal, resonance and hammer-noise behavior.

The piano source is Salamander Grand Piano v3 by Alexander Holm, with mapping
by kinwie and retuning by Markus Fiedler, under
[CC BY 3.0](https://creativecommons.org/licenses/by/3.0/). Keep those credits,
the license link and a description of changes with shared performances.
VSCO Community Edition is by Sam Gossner/Versilian Studios and Simon Dalzell/Ivy
Audio, with sample cutting by Elan Hickler/Soundemote, under CC0. Full source
links and notices are in `THIRD_PARTY.md`.

Sign-Off needs three separately supplied LM-2 one-shots: `kick.wav`,
`snare-m.wav` and `hhclosed.wav` under `Samples/LM-2`. Its pitched sources are
synthesized. The public repository contains code, not the sample libraries.

## Render one track, then the record

```bash
python scripts/album_v2/render.py --album quiet-hours --track 2 --asset-root /path/to/studio-assets --output-dir Tracks/albums
```

Omit `--track 2` to render the album. The output separates decisions and sound:

```text
The Quiet Hours/
    Sessions/02 Slow Rain/
        score.json
        dry/piano.wav
        dry/strings.wav
        stems/piano.wav
        stems/strings.wav
        stems/room.wav
        mix-float.wav
        manifest.json
    Masters/02 Slow Rain.wav
    Listening/02 Slow Rain.mp3
```

Dry buses preserve the performed sources. Processed stems preserve their
contributions to the float mix. The manifest records the specification,
code/score fingerprint, asset hashes, render times and delivery measurements.

The piano and strings use fixed gains across the album, with the strings about
14 dB behind the piano in the Slow Rain reference. Final delivery gain then
brings each track toward its loudness target subject to the peak ceiling.
It does not individually normalize every quiet note or instrument.

## Reuse a stage deliberately

Use `--remix` after changing only mix decisions. It reads the existing dry
files, so it cannot apply changes to notes, timing or instrument sources.
Use `--resume` to skip tracks whose fingerprint, master hash and recorded asset
hashes still match. Keep a separate output folder for a comparison you want
to preserve.

The seed strategy localizes randomness by track and part. Explicit voice IDs
keep overlapping note boundaries paired. These mechanisms support repeatability;
recording source versions and retaining the dry files completes the comparison.

## Listen at album scale

Each record has twelve tracks: about 28:19 for Sign-Off and 25:19 for The Quiet
Hours. The website's custom album players let listeners choose a track or
continue through the sequence. Starting another album pauses the first.

Check transitions and endings as well as individual songs. A technically
valid export can still contain an overlong phrase or a tiring texture.
The delivery checks cover format, finite audio, loudness, true peak, tails
and float-stem reconstruction. The musical decision remains in the listening.
