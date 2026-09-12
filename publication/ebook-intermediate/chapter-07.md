# Chapter 7 — Building Sound From Scratch (and Making It Wobble)

Part I ends with the instrument that ships with nothing: sounds built
directly from math. Why bother, when the last five chapters handed you a
studio's worth of instruments? Two honest reasons. **Control** — a
synthesized voice exposes everything (pitch, brightness, envelope, drift)
as a parameter your code can play with. And **period truth** — one of this
book's albums is a nostalgic 1983 synth record, and in 1983 the sounds
*were* raw sawtooth waves, brand-new digital bells, and square-wave
arpeggios, all warped by the tape they were recorded to. This chapter
builds that album's entire instrument rack — five voices, a tape-wobble
engine, and a hiss bed — in about a hundred lines, and closes with an
honest note about the corner we're cutting.

## Oscillators: sound is a repeating shape

Pull up a tone generator and you're hearing an **oscillator**: a wave
shape repeating fast enough to be a pitch (440 repetitions per second is
the A above middle C). The shape determines the character:

- **Sine** (`np.sin`) — pure, round, no edge. Sub-bass and soft flutes.
- **Sawtooth** (`scipy.signal.sawtooth`) — a ramp; bright and buzzy. The
  classic analog synth string/brass sound.
- **Square** (`np.sign(np.sin(...))`) — hollow, woody, video-game-y.

Generating one *at a fixed pitch* is a one-liner. But every interesting
voice in this chapter bends its pitch over time — slides, vibrato, tape
drift — and there's a trap waiting there. You might write:

```python
sig = np.sin(2 * np.pi * freq_array * t)     # WRONG for changing pitch
```

That formula assumes the frequency was `freq_array[i]` *for all time up to
sample i* — so when the frequency moves, the pitch lurches absurdly. The
fix is one idea from calculus put into one line of NumPy: **a wave's
phase — how far along its cycle it is — is the running total of its
frequency.** Running total = `np.cumsum` (cumulative sum):

```python
phase = 2 * np.pi * np.cumsum(freq_array) / SR   # accumulate the frequency
sig = np.sin(phase)                              # then shape it
```

Internalize this pattern — *build the per-sample frequency array, cumsum
it, apply the wave shape* — and every analog trick below becomes easy.
It's this chapter's version of Chapter 2's render loop.

## The tape-wow engine

What makes cheap oscillators feel alive is *instability*, and the most
flattering instability is the kind an old tape machine adds: slow,
compound pitch drift, called **wow**. Every voice in this rack draws its
frequency through this little engine:

```python
class Synth:
    """Every note's pitch drifts on two slow sine waves ("LFOs" — low-
    frequency oscillators). `wobble` scales the depth per song."""

    def __init__(self, rng, wobble=1.0):
        self.rng = rng            # the song's seeded random generator
        self.wob = wobble

    def _freq(self, f0, n):
        t = np.arange(n) / SR
        p1, p2 = self.rng.uniform(0, 2 * np.pi, 2)    # random start phases
        drift = (0.0012 * np.sin(2 * np.pi * 0.31  * t + p1)
               + 0.0007 * np.sin(2 * np.pi * 0.077 * t + p2)) * self.wob
        return f0 * (1.0 + drift)     # base pitch, bent by ±0.1-ish percent
```

Read the numbers like a spec sheet. Two drift waves: one wobbling 0.31
times per second at ±0.12% depth (a slightly worn tape-drive motor), one
at 0.077 Hz and ±0.07% (the slower breathing of tape tension). Both are
far below the speed of vibrato, which is why the ear reads them as
*atmosphere*, not effect.

Random starting phases per note make oscillators drift independently. This
can create a useful chorus-like shimmer, but it is not a model of one shared
tape transport: that transport changes playback time for the recorded mix
together. The rebuilt Sign-Off uses resampling of pitched source buses for
its broadcast movement and leaves drum timing on a separate clock. The
seeded generator makes the chosen performance repeatable.

`wobble` is set per song. The confident opener runs 1.0. A queasy
interlude titled "Vertical Hold" runs 2.2 — and the mood shift from that
one number is remarkable.

## The voice rack

Five voices cover the whole record. Each is a dozen lines; each encodes a
piece of synth history. Two shown in full, three sketched:

**The pad** — the lush sustained chord bed:

```python
    def pad(self, midi, dur):
        n = int(dur * SR)
        f = self._freq(440 * 2 ** ((midi - 69) / 12), n)   # note -> Hz
        ph = 2 * np.pi * np.cumsum(f) / SR
        sig = (sawtooth(ph * 1.0035)      # two saws, detuned a third of
             + sawtooth(ph * 0.9965)      #   a percent apart: instant width
             + 0.5 * np.sin(ph * 0.5))    # quiet sine an octave below: floor
        env = adsr(n, dur * 0.3, 0.2, 0.85, dur * 0.35)    # slow swell
        return lowpass(sig * env, 1300) / 2.5              # darken, level
```

Two slightly-detuned sawtooths is *the* analog pad recipe — their slow
beating against each other is the lushness. The envelope's attack scales
with the note's duration (`dur * 0.3`), so long pad notes bloom slowly and
short ones still speak. Downstream this bus gets a chorus effect, and the
album script's comment says why in six words: *"the Juno move: chorus
makes the pad"* — how a famously modest 1982 synthesizer made its one
oscillator sound huge.

(The helpers: `adsr` builds the classic attack/decay/sustain/release
volume envelope by gluing straight-line ramps together; `lowpass` wraps
SciPy's filter functions — "remove frequencies above this cutoff." Both
are ten lines, in the companion code.)

**The bell** — 1983's brand-new sound, FM synthesis:

```python
    def bell(self, midi, dur):
        n = int(dur * SR)
        t = np.arange(n) / SR
        f = self._freq(440 * 2 ** ((midi - 69) / 12), n)
        ph = 2 * np.pi * np.cumsum(f) / SR
        index = 2.2 * np.exp(-t / (dur * 0.35))       # how hard to modulate,
        sig = np.sin(ph + index * np.sin(3.53 * ph))  #   fading over time
        return sig * np.exp(-t / (dur * 0.5)) * adsr(n, 0.005, 0.1, 0.8, 0.2) / 1.4
```

One sine wave bending the phase of another — that's **FM synthesis**, the
technology of the Yamaha DX7 that had just hit the shops in our album's
year. The modulation amount (`index`) decays over the note, which is what
makes it a *bell*: bright metallic attack mellowing into a pure tone. And
the magic constant 3.53 — the ratio between the two sines — is chosen to
be *not* a whole number: that's what makes the overtones clang like metal
instead of humming like an organ. (The DX7 had six sines to our two; now
you know what the other four were for.)

**The lead** melody voice adds two *performance* behaviors: an 80 ms
pitch slide from the previous note (the way a mono synth glides when you
play legato) and vibrato that only fades in a third of a second into each
note — because that's what a player's wrist does. That late-vibrato ramp
does more for "a human is playing this" than any tone shaping. **The
arp** is a square wave with a sharp exponential fade, plucky and
video-game-adjacent. **The bass** is nearly a pure sine with a whisper of
overtone — the polite foundation a nostalgic record wants.

And under every track, a **tape hiss bed**: filtered noise at whisper
level, its volume breathing on a 20-second cycle. It reads as "machine in
the room" long before it reads as "noise," and its absence is
conspicuously *digital*.

## Where these plug in

A voice returns a mono array; placing it on a bus is the same "add it at
sample position t" arithmetic as placing a drum hit; the buses flow into
the same effects and mix stages as every other chapter's instruments.
That's the note to end Part I on: synthesis isn't a separate studio.
It's the sixth loader plugged into the same four sockets — events, buses,
effects, mix — that the other five use.

## The honest footnote: aliasing

The perfect sawtooth has infinitely many overtones; digital audio can only
represent frequencies up to half the sample rate. Generate a naive
sawtooth and the overtones past that limit don't vanish — they *fold back*
down into the audible range as inharmonic garbage, called **aliasing**.
Textbook synthesis uses cleverer oscillators that avoid it.

These older sawtooth examples are deliberately simple and can alias. A
low-pass filter after generation cannot remove aliases that have already
folded into the audible passband. A dark sound is not proof of a clean source.

For a small teaching oscillator, sum only harmonics below Nyquist. For more
complex waveforms, use an appropriate band-limited oscillator or oversample
with proper anti-alias filtering before downsampling. Oversampling reduces
the problem; it does not make an infinite-harmonic waveform automatically
alias-free. Listen across the full register you intend to use.

The new portable examples use a small number of sine partials in a bounded
note range. They are a simpler starting point than copying the old sawtooth
rack and assuming its sound is correct for every pitch.

---

Part I is complete: a synthesizer you can script, real plugins, rescued
plugins, an unlocked sample library with its own sampler, eight drum
machines, and now raw synthesis — six instrument loaders, one event
format, one bus convention. Part II puts players behind the instruments:
the arrangement that tells everyone what to play, the imperfections that
make hands sound like hands, each member's rig, and the shared room that
turns six audio files into a band.
