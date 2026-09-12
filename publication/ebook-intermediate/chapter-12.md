# Chapter 12 — Mixing, Mastering, and What a Null Test Proves

A rendered performance is still only a performance. A mix decides what the
listener follows, how close it feels, and what gets out of the way. In a Python
studio those decisions appear as gains, filters, envelopes and effects, but
the job is the same as moving faders: listen, change one relationship, compare.

The albums use separate stages: score, dry performance, mix, and
delivery. Saving the boundary between stages makes revision much faster. A
piano balance change should not require playing every sampled note again.

## Balance is a relationship

Start with the instrument that carries the song. Bring supporting parts up
until they have a purpose. If a part only works when it is loud enough to
hide the lead, change its register, notes or rhythm before reaching for an EQ.
A low piano chord and a bass line can compete even when neither clips.

```python
stems = {
    "piano": piano * piano_gain,
    "strings": strings * strings_gain,
    "room": room_return * room_gain,
}
mix = sum(stems.values())
```

These gains describe the last balance stage, not the whole mix. The choice of
sample, velocity, note length, filter and room send already shaped the sound.
For *The Quiet Hours*, fixed gains keep the strings behind the piano across
the record. In the Slow Rain reference the strings sit about 14 dB below the
piano by whole-track RMS. The gains are explicit constants in the renderer;
final delivery gain scales the combined mix without normalizing each gesture.

*Sign-Off* needs a different routing decision. Its pitched instruments pass
through the damaged broadcast treatment together. The drums bypass the timing
warp and echo. That makes the attack of each kick and snare a stable reference
while the music behind it moves. The amount of damage belongs to each track's
score: some tracks need an unstable signal; others need a spacious, gentle bed.

## RMS, LUFS, sample peak and true peak

These measurements answer different questions. RMS is the square root of the
mean squared sample value. It describes signal magnitude, but does not account
for frequency weighting or the way we hear different arrangements. An RMS
ratio of 0.22 is an amplitude ratio; its mean-square energy ratio is 0.22²,
about 0.048. It is not 22 percent of the energy.

LUFS is a loudness measurement with frequency weighting and gating. Integrated
LUFS describes a whole program. Sample peak is the largest stored sample;
true peak estimates the reconstructed waveform between samples. A file can
have acceptable sample peaks and still produce higher peaks after conversion.

The records use project targets of −22 LUFS, with selected interludes
and closers at −23 LUFS, and a −1.2 dBTP ceiling. These are artistic choices
for these recordings, not universal streaming requirements. The exporter
measures the float mix with FFmpeg, then chooses one linear gain:

```python
gain_db = min(target_lufs - measured_lufs,
              ceiling_dbtp - measured_true_peak)
gain = 10 ** (gain_db / 20)
```

The peak ceiling takes priority. If hitting a loudness target would exceed it,
the gain calculation leaves the track quieter. Do not silently introduce a
limiter to make a test pass. Decide whether the arrangement needs less peak
energy or whether that quieter result is right for the album.

Measure again after export. The release verification includes the WAV and MP3
preview, because lossy encoding can change peaks. Loudness measurements do not
prove that the bass is balanced, the reverb is appropriate, or the composition
is interesting. Those decisions still require listening at matched levels.

## Fades and tails

Leave render time for releases and reverb before applying the final fade.
A note-off is not necessarily the end of the sound. Abruptly trimming the
array at the last event can remove the piano decay or cut a room return.

Use one final envelope for the mix and all exported stems. Otherwise their
edges will no longer agree. Listen to beginnings and endings separately;
a numerical test for low ending RMS cannot tell you whether the fade starts
too early in the musical phrase.

## The exact stem contract

The sessions contain three useful layers:

- Dry buses preserve the rendered performance before the mix effects.
- Processed float stems reconstruct the saved float mix.
- The distribution WAV is a 24-bit PCM conversion of that float mix.

The null test compares the second layer with the float mix, before final PCM
quantization and lossy encoding. It does **not** promise that independently
dithered integer stems sum bit-for-bit to a separately dithered master.

```python
summed = np.zeros_like(mix)
for stem in processed_stems:
    summed += stem
residual = np.max(np.abs(summed - mix))
assert residual < 2e-6
```

The tolerance accommodates float32 rounding in these files. Test the files
read back from disk, not just arrays that have never been exported. Also test
that the mix is finite and non-silent: a folder of zero arrays nulls perfectly
and contains no music.

Nonlinear routing matters. In general, saturation applied to a sum is not the
sum of separately saturated parts. Sign-Off therefore exports its processed
music bus as a group stem alongside the separately routed parts. The dry
instrument buses remain available for a real rebalance, which reruns the music
bus treatment. Calling those dry buses independent finished stems would hide
an important limitation of the session.

## Deliver once, retain the working files

Keep the working mix and stems as float WAV. Convert the final mix once to
24-bit PCM with triangular dither. Create listening MP3s from the float mix;
do not repeatedly transcode the distribution master. Record sample rate,
duration, measurements and hashes in a manifest so you can identify exactly
which file was delivered.

For a DAW handoff, import all processed stems at the same timeline start with
unity gain and no extra master processing. Verify their reconstruction there.
A folder of WAV files is a portable handoff, not an automatically configured
project for every DAW. Import the dry buses instead when you intend to change
the routing, and expect to recreate the mix effects.

The practical result is a mix you can revisit. A failed null check points to
an export or routing problem. A boring chorus points back to the song.
