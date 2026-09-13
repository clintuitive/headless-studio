# Chapter 12 — Mixing, Mastering, and What a Null Test Proves

A rendered performance is still only a performance. The mix is where you decide
what the listener follows, how close it feels, and what needs to get out of the
way. In a Python studio those decisions arrive as gains, filters, envelopes and
effects — but the job hasn't changed at all from moving faders with your hands.
Listen. Change one relationship. Compare.

The albums keep four stages apart: score, dry performance, mix, delivery.
Saving the boundary between them is what makes revision fast. Changing the
piano's balance should never require playing every sampled note again, and in
this studio it doesn't.

## Balance is a relationship

Start with whatever carries the song. Bring the supporting parts up until they
have a purpose, and stop there — not at some level a meter suggested, at the
point where the part is doing its job.

If a part only works when it's loud enough to hide the lead, that isn't a level
problem. Change its register, its notes or its rhythm before you reach for an
EQ, because you're fixing an arrangement mistake in the wrong stage. Two
instruments in the same register are in each other's way long before either of
them clips.

```python
stems = {
    "piano": piano * piano_gain,
    "strings": strings * strings_gain,
    "room": room_return * room_gain,
}
mix = sum(stems.values())
```

That really is the mix: a dictionary of scaled arrays and one `sum`. Keeping
the stems in a dictionary rather than adding as you go is what makes the rest
of this chapter possible — you can write each one to disk and later check that
they still add up to what you exported.

These gains are the last balance stage, not the whole mix. Sample choice,
velocity, note length, filtering and room send have already done most of the
shaping by the time you get here. For *The Quiet Hours*, fixed gains keep the
strings behind the piano across the entire record — in the Slow Rain reference
they sit about 14 dB below it by whole-track RMS. The gains are explicit
constants in the renderer, and the final delivery gain scales the combined mix
rather than normalizing each gesture into the same shape.

*Sign-Off* needs a different routing decision. Its pitched instruments go
through the damaged broadcast treatment together, while the drums bypass the
timing warp and the echo. That leaves every kick and snare attack as a fixed
reference point while the music behind it wanders, which is the whole trick of
the record. How much damage a given track takes belongs to its score: some want
an unstable signal, others want a spacious, gentle bed.

## RMS, LUFS, sample peak and true peak

Four measurements, four different questions, routinely confused — including by
software that ought to know better.

**RMS** is the square root of the mean squared sample value. It describes
signal magnitude honestly and says nothing about frequency weighting or how an
arrangement lands on human ears. One piece of arithmetic worth internalizing:
an RMS ratio of 0.22 is an *amplitude* ratio. The mean-square energy ratio is
0.22², about 0.048. It is not 22 percent of the energy, however much it looks
like it should be.

**LUFS** is a loudness measurement with frequency weighting and gating — it
approximates perceived loudness rather than raw magnitude, and integrated LUFS
describes a whole program rather than a moment.

**Sample peak** is simply the largest stored sample. **True peak** estimates
the waveform *between* samples, once it's been reconstructed by a converter.
Those between-sample excursions are real, which is why a file with perfectly
respectable sample peaks can overshoot after conversion and distort on
somebody's playback chain.

These records target −22 LUFS, with selected interludes and closers at −23, and
a −1.2 dBTP ceiling. Those are artistic choices for these recordings, not
requirements handed down by a streaming service. The exporter measures the
float mix with FFmpeg and then picks one single linear gain:

```python
gain_db = min(target_lufs - measured_lufs,
              ceiling_dbtp - measured_true_peak)
gain = 10 ** (gain_db / 20)
```

Read the `min` carefully, because it encodes a policy: the peak ceiling wins.
If reaching the loudness target would break the ceiling, the track simply stays
quieter than the target. And that's the end of it — no limiter appears to
rescue the number, because a limiter inserted to make a test pass is a change
to the record made by a script instead of a person. Decide whether the
arrangement genuinely has too much peak energy, or whether quieter is the right
answer for this album.

Then measure again after export. The release verification covers both the WAV
and the MP3 preview, because lossy encoding moves peaks around. And remember
what none of these numbers can tell you: whether the bass is balanced, whether
the reverb suits the song, whether the composition is interesting. That's still
listening, at matched levels.

## Fades and tails

Leave render time for releases and reverb before the final fade goes on. A
note-off is not the end of the sound — Chapter 2's spare seconds, Chapter 7's
reserved release and Chapter 11's convolution tail have all been making this
point, and here's where forgetting it costs you a master. Trim the array at the
last event and you'll cut the piano decay off mid-breath, or lose the room
return entirely.

Use one final envelope for the mix and every exported stem. If they get their
own fades their edges stop agreeing, and the null test below starts failing for
reasons that have nothing to do with your mix.

Listen to beginnings and endings on their own, too. A numerical check for low
ending RMS will happily confirm that the file fades out, while the fade starts
three seconds too early and swallows the phrase that was meant to close the
song.

## The exact stem contract

Each session holds three useful layers:

- **Dry buses** preserve the rendered performance, before any mix effects.
- **Processed float stems** reconstruct the saved float mix.
- **The distribution WAV** is a 24-bit PCM conversion of that float mix.

A **null test** checks the middle claim by adding the stems back together and
looking at what's left over. It compares that sum against the float mix, before
PCM quantization and lossy encoding. It does **not** promise that independently
dithered integer stems sum bit-for-bit to a separately dithered master — those
are different files with different rounding, and anyone who tells you otherwise
is selling something.

```python
summed = np.zeros_like(mix)
for stem in processed_stems:
    summed += stem
residual = np.max(np.abs(summed - mix))
assert residual < 2e-6
```

The tolerance accommodates float32 rounding in these files; it isn't zero
because floating-point addition isn't associative, and the mix and the sum
didn't add things in the same order.

Two disciplines make this test worth running. Test the files read back from
disk, not arrays that have never left memory — the export is the thing you're
actually verifying. And test that the mix is finite and non-silent while you're
in there, because a folder of zero arrays nulls absolutely perfectly and
contains no music whatsoever.

Nonlinear routing is where this gets subtle, and Chapter 10 set up the reason:
saturation applied to a sum is not the sum of separately saturated parts. So
Sign-Off exports its processed music bus as a group stem alongside the
separately routed parts, and keeps the dry instrument buses available for a
real rebalance — which reruns the music bus treatment, because there's no
shortcut. Calling those dry buses finished independent stems would hide a
limitation the session genuinely has.

## Deliver once, retain the working files

Keep the working mix and stems as float WAV. Convert the final mix once to
24-bit PCM with triangular dither — dither being a tiny amount of deliberately
added noise that stops quantization from producing correlated distortion in
quiet passages. Once. Make listening MP3s from the float mix rather than
transcoding the distribution master again and again, since every lossy
generation throws away a little more.

Record sample rate, duration, measurements and hashes in a manifest, so that in
a year you can still say exactly which file went out.

For a DAW handoff, import all the processed stems at the same timeline start
with unity gain and no master processing, then verify the reconstruction there
rather than assuming it survived the trip. A folder of WAVs is a portable
handoff, not a project file that configures itself in every DAW. If the point
is to change the routing, import the dry buses instead and expect to rebuild
the mix effects by hand.

What all this buys you is a mix you can come back to. A failed null check points
at an export or routing problem, and points at it precisely. A boring chorus
points back at the song, where it always did.

---

*Next — Chapter 13: Two Albums, Distinct Musical Identities.*
