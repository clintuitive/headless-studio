---
title: "Stems That Sum to the Mix — and What the Null Test Proves"
date: 2026-07-07
slug: stems-null-test
description: Float-stem reconstruction, nonlinear buses, delivery dither, and the limits of a null test.
---

A rendered performance is still only a performance. The mix is where you decide
what the listener follows, how close it feels, and what needs to get out of the
way. In a Python studio those decisions arrive as gains, filters, envelopes and
effects — but the job hasn't changed at all from moving faders with your hands.
Listen. Change one relationship. Compare.

The albums keep four stages apart: score, dry performance, mix, delivery.
Saving the boundary between them is what makes revision fast. Changing the
piano's balance should never require playing every sampled note again.

## Balance is a relationship

Start with whatever carries the song. Bring the supporting parts up until they
have a purpose, and stop there. If a part only works when it's loud enough to
hide the lead, that's not a level problem — change its register, its notes or
its rhythm before you reach for an EQ. A low piano chord and a bass line can be
in each other's way long before either of them clips.

```python
stems = {
    "piano": piano * piano_gain,
    "strings": strings * strings_gain,
    "room": room_return * room_gain,
}
mix = sum(stems.values())
```

Those gains are the last balance stage, not the whole mix. Sample choice,
velocity, note length, filtering and room send have already done most of the
shaping by the time you get here. For *The Quiet Hours*, fixed gains keep the
strings behind the piano across the whole record — in the Slow Rain reference
they sit about 14 dB below it by whole-track RMS. The gains are explicit
constants in the renderer, and the final delivery gain scales the combined mix
rather than normalizing each gesture into the same shape.

*Sign-Off* needs a different routing decision. Its pitched instruments go
through the damaged broadcast treatment together, while the drums bypass the
timing warp and the echo. That leaves every kick and snare attack as a fixed
reference point while the music behind it wanders, which is the whole trick of
the record. How much damage a track takes belongs to its score: some want an
unstable signal, others want a spacious, gentle bed.

## RMS, LUFS, sample peak and true peak

Four measurements, four different questions, routinely confused.

RMS is the square root of the mean squared sample value. It describes signal
magnitude honestly and tells you nothing about frequency weighting or how a
particular arrangement lands on human ears. Worth remembering: an RMS ratio of
0.22 is an *amplitude* ratio. The mean-square energy ratio is 0.22², about
0.048. It is not 22 percent of the energy, however much it looks like it.

LUFS is a loudness measurement with frequency weighting and gating; integrated
LUFS describes a whole program. Sample peak is simply the largest stored
sample. True peak estimates the reconstructed waveform *between* samples, which
is why a file with perfectly respectable sample peaks can overshoot after
conversion.

These records target −22 LUFS, with selected interludes and closers at −23, and
a −1.2 dBTP ceiling. Those are artistic choices for these recordings, not
requirements handed down by a streaming service. The exporter measures the
float mix with FFmpeg and picks one linear gain:

```python
gain_db = min(target_lufs - measured_lufs,
              ceiling_dbtp - measured_true_peak)
gain = 10 ** (gain_db / 20)
```

The peak ceiling wins. If reaching the loudness target would break it, the
track simply stays quieter. What you must not do is slip a limiter in to make
the number go green — decide whether the arrangement genuinely has too much
peak energy, or whether quieter is the right answer for this album.

Then measure again after export. The release verification covers the WAV and
the MP3 preview, because lossy encoding moves peaks around. None of these
numbers will tell you the bass is balanced, the reverb suits the song, or the
composition is interesting. That's still listening, at matched levels.

## Fades and tails

Leave render time for releases and reverb before the final fade goes on. A
note-off is not the end of the sound. Trim the array at the last event and
you'll cut the piano decay off mid-breath, or lose the room return entirely.

Use one final envelope for the mix and every exported stem, or their edges stop
agreeing and the null test starts failing for reasons that have nothing to do
with the mix. Listen to beginnings and endings on their own, too — a numerical
check for low ending RMS cannot tell you the fade starts three seconds too
early in the phrase.

## The exact stem contract

Each session holds three useful layers:

- Dry buses preserve the rendered performance, before mix effects.
- Processed float stems reconstruct the saved float mix.
- The distribution WAV is a 24-bit PCM conversion of that float mix.

The null test compares the second layer against the float mix, before PCM
quantization and lossy encoding. It does **not** promise that independently
dithered integer stems sum bit-for-bit to a separately dithered master, and
anyone who tells you otherwise is selling something.

```python
summed = np.zeros_like(mix)
for stem in processed_stems:
    summed += stem
residual = np.max(np.abs(summed - mix))
assert residual < 2e-6
```

The tolerance accommodates float32 rounding in these files. Test the files read
back from disk, not arrays that have never left memory — the export is exactly
what you're trying to verify. And test that the mix is finite and non-silent
while you're there, because a folder of zero arrays nulls perfectly and
contains no music.

Nonlinear routing is where this gets subtle. Saturation applied to a sum is not
the sum of separately saturated parts, in general. So Sign-Off exports its
processed music bus as a group stem alongside the separately routed parts, and
keeps the dry instrument buses available for a real rebalance, which reruns the
music bus treatment. Calling those dry buses finished independent stems would
hide a limitation the session genuinely has.

## Deliver once, retain the working files

Keep the working mix and stems as float WAV. Convert the final mix once to
24-bit PCM with triangular dither. Make listening MP3s from the float mix
rather than transcoding the distribution master again and again. Record sample
rate, duration, measurements and hashes in a manifest, so that in a year you
can still say exactly which file went out.

For a DAW handoff, import all the processed stems at the same timeline start
with unity gain and no master processing, then verify the reconstruction there.
A folder of WAVs is a portable handoff, not a project file that configures
itself in every DAW. If the point is to change the routing, import the dry
buses instead and expect to rebuild the mix effects by hand.

What all this buys you is a mix you can come back to. A failed null check
points at an export or routing problem. A boring chorus points back at the
song, where it always did.

Read the [mixing chapter](/book/chapter-12.html) alongside the runnable renderer.
