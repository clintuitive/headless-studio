# Chapter 10 — Give Each Bus a Role in the Mix

The dry performance contains the notes and the instrument's sound. The mix
establishes a hierarchy: what the listener follows, what supports it, and what
can disappear without taking the song with it. A separate bus for each role
lets you make those choices without replaying the instruments.

The Quiet Hours has piano, strings and a room return. Sign-Off groups its
pitched sources into a treated music bus while the drums remain separate.
These are different routing choices for different records, not a rule that
every song needs the same number of faders.

## Begin with fixed gains

A gain is a multiplier. Multiply a float array by 0.5 and its amplitude halves,
which is approximately a 6 dB reduction. Applying the same gain to every sample
preserves the internal dynamics of the performance.

The piano mix uses fixed gains for its two dry instruments:

```python
piano = dry['piano'] * .353735
strings = dry['strings'] * .04244
```

These numbers belong to the prepared Salamander and VSCO sources in this
project. They are not suitable defaults for arbitrary libraries. The supporting
strings sit roughly 14 dB below the piano by whole-track RMS in Slow Rain.
Listen to the relationship in context before changing it.

Avoid normalizing each bus to the same peak. A brief piano attack and a sustained
string chord distribute their energy differently. Matching their highest
sample does not make them equally loud or establish a useful balance.

## Remove only what obscures the role

The renderer filters the piano between roughly 45 Hz and 11 kHz, and the
strings between roughly 180 Hz and 4 kHz. Those cutoffs reduce unnecessary
extremes and leave the piano forward. The effect depends on the source register,
filter slope and surrounding arrangement.

Here is a complete filter example for a channels-by-frames array:

```python
from scipy.signal import butter, sosfilt

rate = 44100
highpass = butter(2, 45, btype='highpass', fs=rate, output='sos')
lowpass = butter(2, 11000, btype='lowpass', fs=rate, output='sos')
filtered = sosfilt(lowpass, sosfilt(highpass, piano, axis=-1), axis=-1)
```

Second-order sections (`sos`) store the filter as a sequence of small filters.
`axis=-1` means time runs along the last dimension. Filtering the channel axis
instead would operate on two values rather than the waveform over time.

If the melody is masked, also inspect the score. Moving an accompaniment out
of its register can solve a conflict more directly than a stronger filter.

## Treat shared effects as shared effects

Sign-Off's pitched sources pass through a combined treatment with pitch motion,
filtering, saturation, dropouts and noise. The drums bypass the timing warp,
so their attacks remain a stable reference. Room and echo returns are separate
contributions to the mix.

Saturation is nonlinear. In general, processing the sum of two inputs is not
the same as processing them independently and adding the results:

```python
import numpy as np
shared = np.tanh(keys + bass)
independent = np.tanh(keys) + np.tanh(bass)
```

Keep `shared` as a group stem if it is the sound used in the mix. Keep the dry
keys and bass as well, because changing their relative levels requires another
pass through that shared effect. Do not promise that independently effected
stems reconstruct a nonlinear group bus.

## Compare one decision at a time

For a fader or filter comparison, reuse the same dry buses. Bring comparison
renders to similar listening levels and listen to the part of the song where
the decision matters. A darker soloed string may work better under piano;
a striking soloed effect may dominate the complete arrangement.

Save the chosen processed contributions as float stems. Apply any final fade
consistently to those stems and their sum. Chapter 11 adds a shared room, and
Chapter 12 checks that the saved contributions reconstruct the working mix
before delivery conversion.
