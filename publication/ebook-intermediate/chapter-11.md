# Chapter 11 — The Shared Room

Instruments rendered separately don't share anything. Each one arrives dry,
recorded in no particular place, sitting in its own vacuum. Put three of them
in a mix and they sound like three files playing at once, because that's
exactly what they are.

A shared room fixes this, and it fixes it for a reason worth understanding:
when two sounds produce the same reflections, the ear concludes they're in the
same space. So we send some of the piano and some of the strings into one
reverb and keep its output as a separate contribution to the mix. Separate,
because then the room's balance becomes something you can change later without
touching the performances.

The studio's self-contained path builds that room out of noise and convolution
— no plugin required. An **impulse response** is simply a recording of how a
space answers a single sharp click: the click goes in, the reflections and
decay come out, and that answer turns out to characterize the whole space.
Convolving a signal with it makes the signal sound as though it happened there.
The response can come from a measured room or from a designed signal. Same
processing operation either way; different provenance.

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

Random noise, faded out over 1.8 seconds. That's a reverb. It works because a
dense room's late reflections really are, statistically, a decaying wash of
uncorrelated arrivals — the noise isn't a cheap substitute for reflections so
much as a reasonable model of thousands of them.

The two channels are generated independently, which gives the room stereo width
without any extra machinery. The last line divides each channel by the square
root of its summed squared values, normalizing it to unit energy so that
changing the decay time doesn't also change the volume. It does *not* guarantee
any particular output level: that still depends on the input's frequency
content and how it interacts with the response.

The fixed seed keeps this artificial room identical across renders — Chapter
1's determinism, applied to a space. It is not a measurement of anywhere real.
It's a designed ambience whose length and colour you adjust until the
arrangement sounds right.

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

Note the structure: the dry instruments go into the mix at full strength, and
the room is *added* alongside them rather than replacing them. That's a
send/return arrangement, and it's what keeps the room adjustable. Change
`wet_gain` and nothing else needs to move.

Convolution combines every input sample with a shifted copy of the response,
which as written would be astronomically slow. `fftconvolve` does it in the
frequency domain instead, where convolution becomes multiplication — one of
those transformations that feels like cheating and is simply mathematics.

The full result is `input_length + response_length - 1` frames long, since the
tail has to go somewhere. Here it's trimmed to the bus length, which means the
bus must already be long enough to contain the tail. (This is the same rule as
Chapter 2's three spare seconds and Chapter 7's reserved release. It will come
up again.) A final fade then brings the delivery to its intended ending.

That `wet_gain` of 0.07 is a send/return balance, not a percentage of perceived
reverb — judge it against the dry signal at listening level and nowhere else.
In a sparse piano arrangement a very small return is clearly audible, because
there's nothing to hide it. The gaps between notes are where reverb lives.

## A measured room is an optional source

You can swap in a recorded impulse response you have permission to use. Read
its actual sample rate, convert it to the project rate, and look at its channel
layout and length before you convolve anything — an IR at the wrong sample rate
produces a room of the wrong size, which is at least an interesting mistake.

Be realistic about what a convolution reverb is. It applies one fixed linear
response, so it captures a great deal about a space and nothing about its
nonlinear or position-dependent behaviour. Real rooms change as sources and
listeners move; this one doesn't.

Channel topology matters too. A mono-to-stereo response and a true stereo
response are different arrangements, and convolving left with left and right
with right — as our example does — is a simplification, not a general model of
cross-channel reflections. When the source format calls for something more
elaborate, use a convolution processor built for it.

The optional plugin path from Chapter 3 can host a convolution effect, but
neither the portable examples nor the album mix needs one for their rooms.

## Check the return as a stem

Save the scaled room return separately from the dry instruments, and make sure
its timing, length and final fade agree with everything else — if the sum is
supposed to reconstruct the float mix, and in Chapter 12 it is, then a room
stem that ends two seconds early will be the reason it doesn't.

Exporting dry stems plus a note saying "add reverb to taste" is a perfectly
useful thing to hand a remixer. It's just a different contract, and worth
labelling as one.

Then listen for the three ways a room goes wrong: the lead pushed too far back,
low notes filling in every gap until the texture turns to soup, and a tail so
long that one section blurs into the next. A good room connects the instruments
while leaving their attacks and phrasing completely legible.

---

*Next — Chapter 12: Mixing, Mastering, and What a Null Test Proves.*
