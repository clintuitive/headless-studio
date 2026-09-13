# Chapter 13 — Two Albums, Distinct Musical Identities

An album renderer needs two things that pull against each other: a shared
engine, and songs that don't sound like each other. Reusing the sample loading,
event scheduling and export code is obviously good — that's an afternoon saved
per track. Reusing the *form* is the trap, and it's a comfortable one, because
the twelfth track renders without complaint and the record quietly becomes one
long variation on the first idea you had.

Sign-Off and The Quiet Hours come out of the same staged workflow and sound
nothing alike, which is the point of putting them side by side here. Sign-Off
is an imperfect late-night broadcast: steady drum attacks, worn pitched
sources, room for pieces that drift. The Quiet Hours puts piano in front, uses
strings selectively, and shapes its timing around phrases rather than a grid.

## Give each track a reason to exist

The Sign-Off specifications carry individual chord banks, motifs, answering
phrases, section lists and production settings. Rabbit Ears and Vertical Hold
take the heaviest warble; elsewhere the damage backs off in favour of thinner
textures, gentler movement, or no drums at all. A strong identity doesn't
require the same intensity everywhere — it requires the intensity to mean
something when it arrives.

The Quiet Hours varies meter, register, piano pattern, phrase length and where
the strings come in. Slow Rain writes its events through its own path; the
other tracks have explicit specifications in
`scripts/album_v2/quiet_hours.py`. Shared playback machinery does not oblige
you to share composition machinery.

Before rendering anything, describe the lead idea and say what each section is
for. A score table will happily show you twelve different parameter sets, and
different parameters are not the same thing as musical contrast — the numbers
can vary while the record stays static. Listen to the sequence and ask what
each track adds that the one before it didn't.

## Prepare the instruments

The Quiet Hours uses Salamander Grand Piano and VSCO Community Edition strings.
Run the preparation script and the preflight from the repository root:

```bash
python scripts/prepare_open_instruments.py --asset-root /path/to/studio-assets
python scripts/check_album_assets.py --album quiet-hours --asset-root /path/to/studio-assets
```

The preparer downloads pinned source revisions and keeps their licence records.
It selects the piano zones the scores actually need, applies onset offsets and
retuned root mappings, and converts everything to stereo 44.1 kHz float WAVs.
For the strings it selects quiet sustain layers, normalizes them, and extends
the sustains with crossfades so a long note holds without wobbling.

What it does not do is implement the complete source SFZ player — the pedal
behaviour, sympathetic resonance and hammer noise all stay behind. This is a
prepared instrument built from those recordings, not an emulation of the
original library, and that distinction belongs in your credits as much as in
your head.

Speaking of which. The piano source is Salamander Grand Piano v3 by Alexander
Holm, with mapping by kinwie and retuning by Markus Fiedler, under
[CC BY 3.0](https://creativecommons.org/licenses/by/3.0/). Keep those credits,
the licence link and a description of your changes with any shared performance.
VSCO Community Edition is by Sam Gossner/Versilian Studios and Simon
Dalzell/Ivy Audio, with sample cutting by Elan Hickler/Soundemote, under CC0.
Full source links and notices live in `THIRD_PARTY.md`.

Sign-Off needs three separately supplied LM-2 one-shots — `kick.wav`,
`snare-m.wav` and `hhclosed.wav` under `Samples/LM-2`. Its pitched sources are
synthesized, so that's the entire external dependency. The public repository
contains code, not sample libraries.

## Render one track, then the record

```bash
python scripts/album_v2/render.py --album quiet-hours --track 2 --asset-root /path/to/studio-assets --output-dir Tracks/albums
```

Drop `--track 2` to render the whole album. What lands on disk separates
decisions from sound, exactly as the last eleven chapters have been arguing:

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
contributions to the float mix. The manifest records the specification, the
code and score fingerprint, asset hashes, render times and delivery
measurements — everything you'd need to answer "what is this file, exactly?"
long after you've forgotten.

The piano and strings use fixed gains across the album, with the strings about
14 dB behind the piano in the Slow Rain reference. Final delivery gain then
brings each track toward its loudness target, subject to the peak ceiling from
Chapter 12. It does not individually normalize every quiet note or instrument,
which is how a record keeps its dynamics between tracks as well as within them.

## Reuse a stage deliberately

Use `--remix` when you've changed only mix decisions. It reads the existing dry
files, so it *cannot* apply a change to notes, timing or instrument sources —
and it won't warn you that you've edited a melody it isn't going to render.
Know which stage your change lives in before you pick the flag.

Use `--resume` to skip tracks whose fingerprint, master hash and recorded asset
hashes all still match. And keep a separate output folder for any comparison
you want to preserve, because the renderer's job is to produce the current
version, not to protect the previous one from you.

The seed strategy from Chapter 9 localizes randomness by track and part, and
explicit voice IDs keep overlapping note boundaries paired. Those mechanisms
support repeatability. Recording your source versions and keeping the dry files
is what completes it.

## Listen at album scale

Each record runs twelve tracks: about 28:19 for Sign-Off, 25:19 for The Quiet
Hours. The website's custom album players let a listener pick a track or ride
the whole sequence, and starting one album pauses the other.

Check the transitions and the endings, not only the songs. A technically
flawless export can still contain a phrase that repeats twice too often, a
texture that turns tiring at minute three, or two tracks in a row that open the
same way. The delivery checks cover format, finite audio, loudness, true peak,
tails and float-stem reconstruction. Every musical decision on the record is
still yours, made with headphones on, in order, at the same volume.

---

*Next — Chapter 14: AI Collaboration and a Clear Production Record.*
