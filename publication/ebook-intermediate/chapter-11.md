# Chapter 11 — The Shared Room

A room return gives separate instruments a common surrounding space. Send
some of the piano and strings into one reverb, then keep its output as a
separate mix contribution. That creates a place to change the room's balance
without disturbing the performed sources.

The studio's self-contained path uses a synthesized impulse response and
convolution. An impulse response is a sequence that describes the response of
a linear system over time. It can come from a measured room or from a designed
signal; these are different sources for the same processing operation.

## Build a small synthetic response

The portable renderer starts with noise and a decaying envelope:

```python
import numpy as np
from scipy.signal import fftconvolve

rate = 44100
t = np.arange(round(1.8 * rate)) / rate
rng = np.random.default_rng(45)
ir = rng.normal(size=(2, len(t))) * np.exp(-t * 4)
ir /= np.sqrt(np.sum(ir * ir, axis=1, keepdims=True))
```

There are two independent channels. The exponential envelope makes the response
fade over time. Dividing by the square root of its summed squared values gives
each channel unit energy. It does not guarantee a particular output RMS for
every input: the result still depends on the input's frequency content and
its relationship to the response.

A fixed seed keeps this artificial room the same in repeated renders. The
response is not a measurement of a named physical space. It is a designed
ambience whose length and color can be adjusted to suit the arrangement.

## Convolve the send, not the whole mix by default

Given channels-by-frames piano and strings arrays of equal length:

```python
send = piano + strings
n = send.shape[1]
room = np.stack([
    fftconvolve(send[channel], ir[channel])[:n]
    for channel in range(2)
])
wet_gain = .07
mix = piano + strings + room * wet_gain
```

Convolution combines every input sample with a shifted copy of the response.
`fftconvolve` computes it efficiently using frequency-domain multiplication.
The full result has `input_length + response_length - 1` frames. This example
trims it to the bus length, so the bus must already include room for the tail.
A final fade then brings the delivery to its intended ending.

The wet gain is a send/return balance, not a calibrated percentage of perceived
reverb. Judge the result against the dry signal at listening level. In a sparse
piano arrangement, a small return can be clearly audible between notes.

## A measured room is an optional source

You can replace the synthetic response with a recorded IR you have permission
to use. Read its actual sample rate, convert it to the project rate, and inspect
its channel layout and length before convolution. A recording and processing
chain approximates aspects of a space; it does not capture every nonlinear or
position-dependent behavior of a real room.

A mono-to-stereo response and a full stereo-input response are also different
routing arrangements. Convolving left with left and right with right is not a
general model of cross-channel reflections. Use an appropriate convolution
processor when the source format requires a different topology.

The optional plugin path can host a convolution effect, but the portable
examples and album mix do not require that host for their room processing.

## Check the return as a stem

Save the scaled room return separately from the dry instruments. Its timing,
length and final fade must agree with the other stems if their sum is to
reconstruct the float mix. A dry-stem export plus instructions to add reverb
later is useful for a remixer, but it is not the same delivery contract.

Listen for the lead being pushed too far away, low notes filling the gaps,
and a tail that makes one section blur into the next. A room can connect the
instruments while still leaving their attacks and phrasing easy to follow.
