# Chapter 11 — The Shared Room

Play any single track from Chapter 10 alone and it sounds finished. Add
them together and something's missing that no volume adjustment fixes: the
players don't sound like they're *anywhere* — or worse, each rig's private
reverb puts each player somewhere *different*. Real records solve this
with the oldest wiring on a mixing console: every channel sends a little
of its signal to **one** shared reverb, and that reverb's output sits
quietly under the whole mix. This chapter builds it — about six lines of
code with the highest sound-per-line ratio in the book — and it's the
chapter where the band walks into a building.

## A room in a WAV file

The reverb we'll use isn't a simulation. It's a recording of an actual
room, applied by a technique called **convolution**.

Here's the idea. Record one sharp clap in a room, and the recording
captures everything the room does to sound: every wall reflection, the
flutter, the decay tail. That recording is called an **impulse response**
(IR) — and mathematics gives us an operation (convolution) that applies
"what the room did to the clap" to *any* sound, as if it had been played
there. It's not an effect *inspired by* the room. It's the room,
factored out into a file.

You don't implement convolution; pedalboard has it:

```python
from pedalboard import Convolution
room = Convolution("IRs/Nice Drum Room.wav", mix=1.0)
```

Free, professionally recorded IRs are easy to find — Voxengo's free pack
covers rooms, halls, and plates; this record uses its "Nice Drum Room" (a
tight, wooden, honest space). `mix=1.0` means the output is *only* the
room sound — we'll blend it with the dry band ourselves, next.

Why not use this for the rigs' private reverbs too? Chapter 10's
synthetic `Reverb` is smooth, adjustable, and idealized — right for an
amp's halo. But the *shared* space is the one the listener's ear
interrogates for realism, and there, a real room wins outright.

## The send architecture

```python
# The mix you already have (Chapter 10's processed buses, at their levels):
dry = bass + 0.95 * drums + 0.85 * gtr + 0.5 * pad

# Everyone plays into the same room — each at their own "send" level:
room_send = 0.7 * drums + 0.55 * gtr + 0.45 * pad + 0.25 * bass
room_wet = room(room_send.astype(np.float32), SR)

# Set the room's loudness RELATIVE to the band (explained below):
def rms(a):                              # "root mean square": a signal's
    return np.sqrt((a ** 2).mean())      #  RMS amplitude — a level measure; it
                                         #  feels, rather than its peak
room_wet *= 0.22 * rms(dry) / max(rms(room_wet), 1e-9)

master = dry + room_wet
```

This is a mixing console's "aux send" wiring in four statements. Every
coefficient is a decision:

**Send levels are not mix levels.** Look at the drums: 0.95 in the mix,
but 0.7 into the room — the *loudest send of any player* — because in a
real space, a drum kit excites the room like nothing else in a band. The
room you hear on a record is mostly drum reflections, and it's the first
thing your ear checks for realism. Now look at the bass: 0.25, almost
token. Low frequencies in a reverb turn instantly to mud, so engineers
have always starved the reverb of bass. The guitar and pad sit between:
enough to join the band, not enough to wash out.

**A starting level, not a perceptual constant.** The RMS ratio sets the room
return to 0.22 of the dry signal's RMS amplitude, about −13.2 dB. Its
mean-square energy ratio is about 4.8 percent. A dark long IR and a bright
short IR can feel very different at that same ratio. Rebalance by ear after
changing the room or arrangement; the number is a repeatable starting point.

**One space, singular.** The temptation arrives quickly: shouldn't the
pad get a *bigger* room than the drums? That instinct produces exactly
the disease this chapter cures — a band standing in several places at
once. Private space is the rig's business; the shared room is one room.
If the genre wants a huge pad wash, enlarge the *rig's* reverb and leave
the band's room alone.

## Hear it

This chapter has the most dramatic one-line experiment in the book:
render `master = dry` (no room), render with the room, and listen on
headphones. Without: six excellent recordings sitting side by side in a
void. With: depth appears — the drums step back a foot, the guitar's
echoes land on a wall, the band acquires a *location*. Nothing got louder
or brighter; the change is entirely in your ear's model of space, which
is why no amount of per-track polish could substitute.

Convolution with a fixed IR is linear: `convolve(a + b, ir)` equals
`convolve(a, ir) + convolve(b, ir)`, apart from numerical rounding, when
routing, state, gain and tail handling match. Separate copies of the same IR
do not inherently sound thinner. A shared send is economical and easy to
balance, but the routing alone does not create extra ensemble interaction.
Nonlinear or time-varying processing can break that equivalence.

## Choosing your room

Audition IRs like Chapter 6 auditions drum kits — a loop over the IR
folder, same eight bars — but go in with priors:

- **Small real rooms** (½-second decay): glue. The default for any music
  that could plausibly be played by people in a club.
- **Damped studios**: presence with almost invisible decay — right when
  the record's fiction is "tracked in a studio," like the synth album.
- **Halls and churches**: gorgeous, and instantly a *statement*. Better
  used as a featured effect than as glue. (The post-rock records send to
  a room *and* a church as two separate returns — a lead melody soaked in
  the church is an event, not glue.)
- **Plates and springs**: not rooms at all — vintage studio hardware
  that happens to ship as IRs. Rig-tier tools.

One production reality: the IR's recording quality is your ceiling —
a noisy IR adds its noise to every note you send it. The reputable free
packs (Voxengo, OpenAIR) are clean; audition anything else solo and loud
before it meets your mix.

## Practical notes

- **Convolution is heavy math, and it doesn't matter.** A three-second
  room applied to a six-minute song is billions of multiplications;
  modern FFT-based convolution does it in seconds, offline. DAW users
  ration convolution reverbs to spare their CPUs during playback; we
  send fourteen tracks to two rooms without thinking. No deadline, no
  tax.
- **The room's output is a track of its own.** When the next chapter
  exports the song's individual instrument files, `room_wet` gets
  written out as its own file — "Room Reverb Return" — exactly like a
  console's reverb channel. Whoever remixes the song later gets one
  fader that moves the whole band closer or further away.
- **A ghost trick for free.** We computed the send from the buses *after*
  their mix volumes (turn a player down, their room echo follows —
  usually what you want). Compute a player's send from the *pre-volume*
  bus instead and you get a player who is quiet in the band but huge in
  the room — a ghost at the back of the hall. Every console manual has a
  name for this switch; here it's just which variable you multiply.

The band is in the room. All that remains is to press *record* properly:
final levels, fades, and the export machinery that proves — with an
actual number — that the files you hand the world recombine into the
record you made. That number turns out to be −87.
