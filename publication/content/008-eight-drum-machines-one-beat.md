---
title: "Eight Drum Machines, One Beat: Auditioning Kits in Code"
date: 2026-07-06
slug: eight-drum-machines-one-beat
description: "A 60-line harness that renders the same groove through eight real drum machines — LinnDrum, Drumtraks, TR-808, and friends — with the actual track's processing, so kit choice becomes an A/B listen instead of a guess."
---

In [the band-pipeline post](/band-in-a-python-script.html) I made the case
that a drum machine is just a sample player, so your render script should be
one too: load real one-shots, place them on the grid, done. That opens a
question synthesis never had to answer: *which* machine? A LinnDrum kick and
an 808 kick occupy the same slot in the pattern and completely different
worlds in the mix.

Here's what eight real machines' kicks actually look like — same normalization,
same 150 ms window:

![Waveforms of eight drum machine kicks compared](/images/kick_comparison.png)

The TR-808 is nearly a pure sine that's still swinging at 150 ms; the
MFB-512 is done in 40; the SK-1 — an 8-bit toy sampler from 1985 — is mostly
beautiful garbage. Every one of them is "a kick drum." None of them are
interchangeable.

## Where the samples come from

The [smpldsnds/drum-machines](https://github.com/smpldsnds/drum-machines)
repository collects freely shared one-shots from dozens of hardware boxes —
LinnDrum LM-2, Sequential Drumtraks, Roland TR-808 and CR-8000, Casio RZ-1
and SK-1, Korg MR10, MFB-512, and more. Each machine is a folder of WAVs (or
m4a — on macOS, `afconvert -f WAVE -d LEI16@44100 in.m4a out.wav` batch-converts;
elsewhere `ffmpeg` does). One folder per machine, four filenames per kit, and
your pipeline can treat "which drum machine" as a config key.

## The wrong way and the right way to audition

The wrong way is to listen to the one-shots in a file browser. A kick soloed
in Finder tells you almost nothing about a kick under a bass line, through
your compressor, in your room reverb. Drum sounds are defined by context —
the 808's sub-tail is either the glue of the track or mud smeared over your
bass, and you can't hear which from the sample alone.

The right way costs 60 lines: render *the actual groove from your actual
track*, once per kit, **through the track's actual drum-bus processing**. The
audition then differs from the real thing in one variable only — the kit.

```python
KITS = {
    "LM-2":      ("kick.wav", "snare-m.wav", "hhclosed.wav", "hhopen.wav"),
    "Drumtraks": ("DT_Kick.wav", "DT_Snare.wav", "DT_Closedhat.wav", "DT_Openhat.wav"),
    "TR-808":    ("kick.wav", "snare.wav", "hhc.wav", "hho.wav"),
    "CR-8000":   ("kick.wav", "snare.wav", "hhc.wav", "hho.wav"),
    "RZ-1":      ("kick.wav", "snare.wav", "hhc.wav", "hho.wav"),
    "MFB-512":   ("kick.wav", "snare.wav", "hhc.wav", "hho.wav"),
    "MR10":      ("kick.wav", "snare.wav", "hhc.wav", "hho.wav"),
    "SK-1":      ("kick.wav", "snare.wav", "hhc.wav", "hho.wav"),
}
GAINS = {"kick": 0.95, "snare": 0.8, "hhc": 0.4, "hho": 0.45}

def load_hit(kit, fname, gain):
    _, data = wavfile.read(os.path.join(SAMPLES_DIR, kit, fname))
    data = data.astype(np.float32) / 32768.0
    if data.ndim == 2:
        data = data.mean(axis=1)
    return data / max(np.abs(data).max(), 1e-9) * gain
```

Peak-normalizing every hit before applying the kit gain is the detail that
makes the comparison fair — raw one-shot levels vary wildly between source
machines, and without normalization you're A/B-ing loudness, not character.

Then the loop: the same beat my darkwave track uses (kick on 1 and 3, snare
on 2 and 4, straight eighth hats, open hat on the last offbeat, dead
quantized at 118 BPM), rendered once per machine, through the same glue
compressor and the same convolution room send as the real track:

```python
fx = Pedalboard([Compressor(threshold_db=-15, ratio=3, attack_ms=2, release_ms=60)])
room = Convolution(ROOM_IR, mix=1.0)

for kit, files in KITS.items():
    hits = {name: load_hit(kit, f, GAINS[name])
            for name, f in zip(("kick", "snare", "hhc", "hho"), files)}
    bus = np.zeros((2, n_samples), dtype=np.float32)
    for bar in range(N_BARS):
        bar_t = bar * BAR
        events = ([(bar_t + b * BEAT, "kick") for b in (0, 2)]
                  + [(bar_t + b * BEAT, "snare") for b in (1, 3)]
                  + [(bar_t + k * BEAT / 2, "hho" if k == 7 else "hhc")
                     for k in range(8)])
        for t, name in events:
            s = hits[name]
            start = int(t * SR)
            end = min(start + len(s), n_samples)
            bus[:, start:end] += s[:end - start]

    dry = fx(bus, SR)
    wet = room((dry * 0.7).astype(np.float32), SR)
    rms = lambda a: np.sqrt((a ** 2).mean())
    out = dry + wet * (0.22 * rms(dry) / max(rms(wet), 1e-9))
    wavfile.write(f"auditions/{kit}.wav", SR,
                  (out / np.abs(out).max() * 0.9 * 32767).T.astype(np.int16))
```

Eight WAVs, a few seconds of render time, and kit selection becomes what it
should have been all along: a blind listening test. Open the folder, play
them back to back, pick the one that serves the song.

## What the audition actually taught me

For the darkwave track this harness was built for, I expected to pick the
LinnDrum — it's *the* sound of the genre's source material. I shipped the
MFB-512. Under the driving eighth-note bass, the Linn's roomy kick fought
the low end, while the German box's 40 ms thump sat in the pocket and let
the bass own the fundamental. In the file browser I'd never have heard it;
in context it wasn't close.

Which is the general point, and it's bigger than drums: **any decision your
pipeline encodes as data — a kit folder, an amp capture, an IR file — is a
decision you can audition exhaustively for the cost of a for-loop.** DAWs
make you audition by hand, one swap at a time, and so you try three options
and settle. A render script tries all eight while you make coffee, and the
one variable that changed is the one you're choosing. That's not a
convenience feature. On the margin, it's a better record.
