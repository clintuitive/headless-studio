---
title: "A Complete Band in a Python Script"
date: 2026-07-02
slug: band-in-a-python-script
description: "The full architecture: MIDI events per band member, real amp captures per bus, sampled drum machines on the grid, seeded humanization, and one shared convolution room that glues it into a record. python3 generate.py -> finished track."
---

**September 2026 update:** The original synthesis examples below are retained for context. The rebuilt Sign-Off uses individual forms, source resampling, and drums that bypass timing warp. Naive sawtooth oscillators can alias; filtering after generation cannot remove aliases already folded into the passband. See the [rebuild notes](/rebuilding-the-albums.html).


The previous four posts built the pieces: [VST3 hosting](/headless-vst3-python.html),
[FluidSynth instruments](/fluidsynth-midi-python.html),
[out-of-process plugins](/incompatible-plugins-out-of-process.html), and
[extracted sampler libraries](/garageband-exs-extraction.html). This post is
the payoff — the architecture that assembles them into a band. One command:

```bash
python3 generate_track.py
# Rendering 96 bars (195.3s) in 3 bus passes + drum samples ...
# Applying effects ...
# Wrote Tracks/modern_darkwave_band.wav: 201.3s, 96 bars at 118 BPM
```

Out comes a finished, mixed, mastered song. Here are eight of the fourteen
stems (exported per-instrument audio tracks) of one such track — every waveform below was placed, played, amped, and
mixed by code:

![Stem waveforms of a finished track, one row per band member](/images/stems_stack.png)

The pipeline is five stages, and every stage is a plain function over NumPy
arrays:

```text
arrangement -> per-bus MIDI events -> per-bus audio -> per-bus FX -> mix + shared room -> master
```

## 1. Arrangement as data

A song is a list of sections; a section says which band members play and
which patterns they use. This is the entire top-level structure of a track:

```python
movements = [
    dict(n_bars=4,  bass="hook"),                                  # bass opens alone
    dict(n_bars=4,  bass="drive", drums=True),                     # machine locks in
    dict(n_bars=16, bass="drive", drums=True, arp="muted"),        # verse: palm-muted
    dict(n_bars=16, bass="hook",  drums=True, arp="open",
         pad=True, lead=True),                                     # chorus
    dict(n_bars=8,  arp="open", pad=True),                         # breakdown
    dict(n_bars=16, bass="hook",  drums=True, arp="open",
         pad=True, lead=True),                                     # final chorus
    dict(n_bars=8,  bass="drive", drums=True),                     # outro
]
```

A `render_bar` function walks this, appending note events to per-member
buses: `EVENTS = {"gtr": [], "bass": [], "drums": [], "pad": []}`. Reading an
arrangement as data means rearranging a song is editing a list — double the
breakdown, drop the second verse — and re-rendering.

## 2. Humanization: the hands drift, the machine doesn't

The single highest-leverage realism trick costs six lines. Every *human*
note — bass, both guitars — gets seeded timing and velocity jitter; the drum
machine and pad stay bit-exact on the grid:

```python
rng = np.random.default_rng(SEED)          # seeded: every render is identical

def human(t, vel, t_sd=0.005, v_sd=6):
    """Jitter start time and velocity, clamped so an outlier never
    lands a note audibly early."""
    t = max(t + float(np.clip(rng.normal(0, t_sd), -2.5 * t_sd, 2.5 * t_sd)), 0.0)
    vel = int(np.clip(vel + rng.normal(0, v_sd), 1, 127))
    return t, vel
```

The *contrast* is what sells it. If everything drifts it sounds sloppy; if
nothing drifts it sounds like a MIDI file. A drum machine plodding along
unmoved while the bassist pushes a few milliseconds ahead — that's a genre
(and a band) in two lines of standard deviations. Note durations get the same
treatment (`* rng.uniform(0.92, 1.08)`), and a fret-noise squeak fires with
`rng.random() < 0.28` when the guitarist's hand shifts. Because everything
draws from one seeded generator, the performance is *reproducible* — take 47
is bit-identical to take 1.

## 3. Drums: don't synthesize, place

Real drum machines are sample players, so be one. Load each one-shot once,
peak-normalize, scale by a kit gain, and add it onto the grid:

```python
def render_drum_bus(events, total_secs, kit_dir, kit):
    n = int(total_secs * SR)
    bus = np.zeros((2, n), dtype=np.float32)
    hits = {}
    for name, (fname, gain) in kit.items():
        _, d = wavfile.read(os.path.join(kit_dir, fname))
        d = d.astype(np.float32) / 32768.0
        if d.ndim == 2:
            d = d.mean(axis=1)
        hits[name] = d / max(np.abs(d).max(), 1e-9) * gain
    for t, name in events:                    # [(seconds, "kick"), ...]
        s, start = hits[name], int(t * SR)
        end = min(start + len(s), n)
        bus[:, start:end] += s[:end - start]
    return bus
```

Every kick is the *identical waveform* — which is exactly what an LM-2 or a
TR-808 does, and why this sounds more like a drum machine than any synthesis
would. The one-shots come from hardware sample packs
([smpldsnds' drum-machines](https://github.com/smpldsnds/drum-machines) has
LinnDrum, Drumtraks, 808s and more, free).

## 4. Per-bus effects: every member gets their rig

This is where the [NAM amp captures](/headless-vst3-python.html) earn their
keep. Each bus gets its own chain; the guitar gets the signature rig in pedal
order, and the bass gets a **parallel split** — clean fundamental plus an
amped grit path tucked underneath, the oldest trick in the bass-recording
book:

```python
gtr_fx = Pedalboard([
    Chorus(rate_hz=0.8, depth=0.2, centre_delay_ms=12.0, mix=0.5),
    load_nam(AMP_AC15),                       # chorus INTO the amp
    Delay(delay_seconds=BEAT * 0.75, feedback=0.28, mix=0.16),   # dotted 8th
    Reverb(room_size=0.85, wet_level=0.24, dry_level=0.76),
])

bass_fx = Pedalboard([
    HighpassFilter(cutoff_frequency_hz=35),
    Mix([
        Chain([Gain(gain_db=0.0)]),                    # dry path
        Chain([load_nam(AMP_DUG), Gain(gain_db=-8.0)]),  # grit, tucked under
    ]),
    Compressor(threshold_db=-18, ratio=4, attack_ms=4, release_ms=90),
])
```

## 5. The glue: one shared room

Per-bus reverbs make four musicians in four different rooms. The band-in-a-
room illusion needs everyone in *the same* space: a single convolution reverb
loaded with a real measured impulse response (a recording of an actual room's
echo, applied mathematically), fed by every bus at its own send level — drums loudest (a kit fills a room), bass barely (low end stays
tight):

```python
from pedalboard import Convolution

dry = bass + drums + 0.85 * gtr + 0.5 * pad

room_send = (0.7 * drums + 0.55 * gtr + 0.45 * pad + 0.25 * bass)
room = Convolution("Nice Drum Room.wav", mix=1.0)(room_send, SR)   # free Voxengo IR

rms = lambda a: np.sqrt((a ** 2).mean())   # RMS: average energy, i.e. felt loudness
room *= 0.22 * rms(dry) / max(rms(room), 1e-9)   # room sits 13 dB under the dry mix

master = dry + room
```

This is a real mixing console's reverb-send architecture, expressed as four
lines of array math. It is also the single biggest before/after in the whole
pipeline: mute the room return and the band collapses back into separate
tracks.

Mastering, minimally: a fade envelope and peak normalization to −1 dB.

```python
master = master / max(np.abs(master).max(), 1e-9) * 0.9
wavfile.write("track.wav", SR, (master.T * 32767).astype(np.int16))
```

(Export each processed bus with the same fades *before* summing and you have
stems that sum exactly to the mix — drag them into any DAW for a human
mixing pass.)

## Why build a studio you can't touch?

Determinism, mostly. Every creative decision in this pipeline is a line of
code under version control. "Take 47 but with the AC15 swapped for the Twin"
is a one-line diff and a re-render. A/B-ing two room IRs is a for-loop. The
performance never has a bad night, and when something finally sounds right,
you know *exactly* why, forever.

Everything in this series — plus the parts that didn't fit: the album-scale
composition engine, tape-wow simulation for period-correct synths, velocity-
layered sampler playback from extracted EXS zones, and the full mixing
notebook — is being expanded into a book, **The Headless Studio**. Subscribe
below and you'll hear when it lands.
