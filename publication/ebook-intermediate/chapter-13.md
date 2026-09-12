# Chapter 13 — Rebuilding Two Albums Without Repeating One Song

An album generator can produce twelve files without producing twelve distinct
pieces. That was the uncomfortable finding when revisiting *Sign-Off* and
*The Quiet Hours*. The code ran, but too much of the writing shared the same
shape, and the mixes did not support the intended character. Some motifs were
repeated exactly. Different titles and random seeds were not enough.

This revision began with listening feedback rather than more randomization.
Clint wanted Sign-Off to feel like vaporwave: an imperfect late-night
broadcast, with room for lush, dreamy pieces. For The Quiet Hours, Slow Rain
was the one composition he wanted to hear again. The other eleven could be
rewritten. Album titles, track titles and artwork stayed the same.

## Choose a direction with short comparisons

The first comparisons held a short musical passage constant while changing
the treatment. Sign-Off's preferred version was called Broadcast, with more
warble and defects. Its drums felt distracting, however. A second comparison
kept drum attacks on a steady clock and out of the warped music path. That
refinement became the reference.

The Quiet Hours comparison called Reperformed retained Slow Rain's writing
while changing performance and balance. It was selected because it still felt
like the same song. This is a useful boundary: preserving the notes does not
require preserving every sample choice, timing decision or fader level.

Do not treat an approved excerpt as approval of every future decision. It
establishes a direction. Full arrangements can reveal repetition, transitions
and fatigue that a minute-long comparison cannot show.

## Write an identity for each track

A shared palette makes an album coherent. A shared complete form makes it
predictable. Before rendering, specify how each track differs in several
musically meaningful ways: phrase length, harmonic movement, texture, density,
register, drum pattern, where the lead enters, and what the ending resolves.

The new Sign-Off score holds individual chord banks, motifs, answers and
section lists. Only Rabbit Ears and Vertical Hold use the heaviest warble
setting. Other tracks leave more space, use gentler movement, or omit drums.
The exact choices are in `scripts/album_v2/sign_off.py`; the point is not to
maximize a count of unique parameter values. Each difference must be audible
and serve the sequence.

The Quiet Hours gives eleven pieces new themes and forms. Slow Rain uses its
original event writing with the selected expressive performance. Strings are
selective support rather than an automatic layer under every piano. See
`scripts/album_v2/quiet_hours.py` and the performance functions in `render.py`.

A score table can expose accidental duplication before a costly render. Tests
check form variety and event validity, but they cannot judge whether two
melodies feel emotionally interchangeable. That remains an audition task.

## Separate score, performance, mix and delivery

The full renderer writes the decisions as well as the sound:

```text
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

Dry buses are the expensive performed sources. Processed stems are the mix
handoff described in Chapter 12. The manifest records the score specification,
code fingerprint, asset hashes, render time and delivered audio hash.

From the public repository, run one track before committing to a full album:

```bash
python scripts/album_v2/render.py --album sign-off --track 2 \
  --asset-root /path/to/studio-assets --output-dir Tracks/rebuilt
```

The asset root contains `Samples/`. Sign-Off needs the three LM-2 one-shots
listed in the renderer. The Quiet Hours needs extracted SteinwayPiano and
Mellotron manifests and their WAV files. These libraries are not redistributed
with the code. The portable examples work without them.

Use `--remix` only when the cached dry performance is still the performance
you want. It skips composition and instrument rendering. A melody, tempo,
source sound or performance change requires a source render, not a remix.
Use `--resume` to skip an unchanged, verified build; it checks the code/score
fingerprint, master hash and recorded asset hashes. Neither option is a
substitute for keeping the source assets and software environment.

## Reproducibility without identical performances everywhere

A single global random generator makes edits fragile: adding one note at the
start can change every later random choice. The rebuilt code derives a seed
from the track title and instrument part. That localizes many edits and makes
repeated renders comparable. Slow Rain retains the audition's specific seeds.

Timing variation is also structured. Map both ends of a note through the same
performance timeline. Keep retriggered notes paired by voice ID, or use the
sampler's documented FIFO pairing for older event tuples. Otherwise a new
note-off can accidentally cut off the wrong overlapping note.

## What was checked, and what remains a listening decision

The September rebuild produced twelve tracks per album: about 28:19 for
Sign-Off and 25:19 for The Quiet Hours. Delivery checks cover format, duration,
finite audio, measured loudness and true peak, processed-stem reconstruction,
and complete album previews. Slow Rain's preserved audition passage was also
compared at the dry-source level.

These checks establish that the pipeline delivered the intended files. They
do not establish that every track is finished artistically. Listen through
the entire sequence, including on a mono speaker, and record concrete notes:
which transition loses momentum, which phrase repeats once too often, which
piano register masks the melody. Then change the score or mix stage responsible
for that problem and render only what needs changing.
