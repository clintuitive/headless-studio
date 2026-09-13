# Chapter 10 — Give Each Bus a Role in the Mix

The dry performance has the notes and the instrument's sound in it. What it
doesn't have is a hierarchy — and a mix is mostly hierarchy. What does the
listener follow? What supports that? What could vanish entirely without taking
the song with it? Every one of those is a decision about *role*, and roles are
easiest to change when each one lives on its own bus.

Which is the practical payoff of everything the last few chapters insisted on.
Because the instruments were rendered to separate arrays and saved, you can
spend an afternoon rearranging the hierarchy without a single note being played
again.

The Quiet Hours has piano, strings and a room return. Sign-Off groups its
pitched sources into one treated music bus and keeps the drums separate. Those
are different answers for different records, not a rule about how many faders a
song is supposed to have.

## Begin with fixed gains

A gain is a multiplier. Multiply a float array by 0.5 and the amplitude halves,
which is about a 6 dB reduction. Apply the same number to every sample and the
performance keeps all its internal dynamics — the loud notes stay loud relative
to the quiet ones. That's the whole operation. It is the fader, and it is
addition's quieter cousin, and almost everything in a mix is one of those two.

The piano mix uses fixed gains for its two dry instruments:

```python
piano = dry['piano'] * .353735
strings = dry['strings'] * .04244
```

Those numbers look absurdly precise and they are: they're the output of
listening, not of a formula, and they belong to the prepared Salamander and
VSCO sources in this project specifically. Do not copy them into a project with
different sources and expect anything sensible. What's transferable is the
*relationship* — the supporting strings sit roughly 14 dB below the piano by
whole-track RMS in Slow Rain. Listen to that relationship in context before you
decide it's wrong.

One temptation to resist: normalizing every bus to the same peak level. A brief
piano attack and a sustained string chord distribute their energy in completely
different ways over time. Matching their highest single sample tells you
nothing about how loud they *sound*, and gives you a balance that's arbitrary
rather than chosen.

## Remove only what obscures the role

The renderer filters the piano between roughly 45 Hz and 11 kHz, and the
strings between roughly 180 Hz and 4 kHz. The strings are the ones being asked
to step back: taking their low end out stops them from crowding the piano's
left hand, and taking their top off keeps them behind it. Whether those exact
cutoffs suit your material depends on register, filter slope and what else is
playing.

Here's a complete filter for a channels-by-frames array:

```python
from scipy.signal import butter, sosfilt

rate = 44100
highpass = butter(2, 45, btype='highpass', fs=rate, output='sos')
lowpass = butter(2, 11000, btype='lowpass', fs=rate, output='sos')
filtered = sosfilt(lowpass, sosfilt(highpass, piano, axis=-1), axis=-1)
```

A highpass lets high frequencies through and removes what's below its cutoff; a
lowpass does the reverse. Second-order sections (`sos`) store the filter as a
chain of small stable filters rather than one big fragile one, which matters
more than it sounds like at low cutoff frequencies.

The `axis=-1` is not decoration. It tells SciPy that time runs along the last
dimension. Filter the channel axis by mistake and you'll be running a filter
across two values — left, right — which is meaningless, produces no error, and
returns audio that sounds subtly wrong in a way you'll chase for an hour.

And before you reach for a sharper filter: if the melody is masked, look at the
score. Moving an accompaniment out of the lead's register solves the conflict
at its source. EQ is for the residue after the arrangement has done its job,
not a substitute for the arrangement.

## Treat shared effects as shared effects

Sign-Off's pitched sources pass through a combined treatment — pitch motion,
filtering, saturation, dropouts, noise — while the drums bypass the timing warp
and hold the beat steady. Room and echo returns are separate contributions to
the mix.

There's a mathematical fact hiding in that routing, and it will matter
enormously in two chapters' time. Saturation is nonlinear, which means
processing a sum is not the same as processing the parts and adding:

```python
import numpy as np
shared = np.tanh(keys + bass)
independent = np.tanh(keys) + np.tanh(bass)
```

Those two lines produce different audio. Not subtly different — audibly
different, because the whole character of saturation comes from how signals
interact inside it. (Linear operations like gain and filtering don't have this
problem: you can filter first and sum, or sum and filter, and get the same
answer.)

So if `shared` is the sound you're using, `shared` is what you keep as a group
stem. Keep the dry keys and bass too, because changing their relative levels
means running that shared effect again — there's no shortcut. And never promise
anyone that independently effected stems will reconstruct a nonlinear group
bus. They won't, and they'll find out at the worst possible moment.

## Compare one decision at a time

For a fader or filter comparison, reuse the same dry buses. Bring the
comparison renders to similar listening levels. And listen to the part of the
song where the decision actually matters, not the intro.

Solo is a liar, incidentally. A string part that sounds dull on its own may be
exactly right underneath the piano; an effect that sounds spectacular soloed
frequently turns out to be eating the entire arrangement. Judge in context and
solo only to diagnose.

Save the chosen processed contributions as float stems, and apply any final
fade consistently across those stems and their sum — Chapter 12 checks that
they still add up, and an inconsistent fade is the most common reason they
don't. Chapter 11 adds the shared room first.

---

*Next — Chapter 11: The Shared Room.*
