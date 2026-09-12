"""Rooms After Rain — slow, moody post-punk instrumental.

Same local band as Ashen Windows: GarageBand Picked Rock Bass and Vintage
Strat, MFB-512 drums, a Twin capture, chorus, and an always-present analog pad.
"""

import os

import numpy as np
from pedalboard import (
    Chorus, Compressor, Delay, Gain, HighpassFilter, LowpassFilter,
    Pedalboard, Reverb,
)
from scipy.io import wavfile
from scipy.signal import sawtooth

from music_engine import (
    EventTimeline, ExsSampler, Humanizer, apply_fades, load_nam,
    normalize_peak, stereo,
)

SR = 44_100
BPM = 78
BEAT = 60 / BPM
BAR = BEAT * 4
SEED = 119

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SAMPLES = os.path.join(ROOT, "Samples")
AMPS = os.path.join(ROOT, "Amps")
OUT = os.path.join(ROOT, "Tracks", "rooms_after_rain.wav")
TWIN = os.path.join(AMPS, "Fender_TwinVerb_Clean.nam")
KIT_DIR = os.path.join(SAMPLES, "MFB-512")

# An eight-bar descent that withholds the dominant resolution until the end.
CHORDS = [
    {"name": "Dm(add9)", "bass": 38, "gtr": [50, 57, 62, 64], "pad": [50, 57, 64]},
    {"name": "Bbmaj7",   "bass": 34, "gtr": [50, 53, 57, 62], "pad": [46, 53, 57]},
    {"name": "F/A",      "bass": 33, "gtr": [48, 53, 57, 60], "pad": [45, 53, 60]},
    {"name": "C",        "bass": 36, "gtr": [48, 55, 60, 64], "pad": [48, 55, 60]},
    {"name": "Gm",       "bass": 31, "gtr": [50, 55, 58, 62], "pad": [43, 50, 58]},
    {"name": "Bb",       "bass": 34, "gtr": [50, 53, 58, 62], "pad": [46, 53, 58]},
    {"name": "A7sus",    "bass": 33, "gtr": [52, 55, 57, 62], "pad": [45, 52, 62]},
    {"name": "A7",       "bass": 33, "gtr": [49, 52, 57, 61], "pad": [45, 52, 61]},
]

# Sparse foundation: long roots, one fifth, and an occasional octave pickup.
# The restraint leaves the guitar wash and half-time drums more room.
BASS_A = [
    (0, 1.45, 0), (2, .78, 7), (3.25, .58, 0),
]
BASS_B = [
    (0, 1.45, 0), (2, .78, 7), (3.25, .58, 12),
]

HOOKS = {
    "Dm(add9)": [(0, 1.3, 69), (2, .85, 72), (3.25, .6, 74)],
    "Bbmaj7":   [(0, 1.3, 69), (2, .85, 65), (3.25, .6, 62)],
    "F/A":      [(0, 1.3, 69), (2, .85, 72), (3.25, .6, 77)],
    "C":        [(0, 1.3, 67), (2, .85, 64), (3.25, .6, 60)],
    "Gm":       [(0, 1.3, 70), (2, .85, 69), (3.25, .6, 67)],
    "Bb":       [(0, 1.3, 65), (2, .85, 69), (3.25, .6, 70)],
    "A7sus":    [(0, 1.3, 67), (2, .85, 69), (3.25, .6, 74)],
    "A7":       [(0, 1.3, 73), (2, .85, 69), (3.25, .6, 64)],
}

SYNTH_LEADS = {
    "Dm(add9)": [(0, 1.55, 74), (2, 1.35, 69)],
    "Bbmaj7":   [(0, 1.55, 70), (2, 1.35, 69)],
    "F/A":      [(0, 1.55, 72), (2, 1.35, 69)],
    "C":        [(0, 1.55, 67), (2, 1.35, 64)],
    "Gm":       [(0, 1.55, 70), (2, 1.35, 74)],
    "Bb":       [(0, 1.55, 70), (2, 1.35, 65)],
    "A7sus":    [(0, 1.55, 74), (2, 1.35, 69)],
    "A7":       [(0, 1.55, 73), (2, 1.35, 69)],
}

timeline = EventTimeline(SR, ("bass", "guitar", "hook", "synthlead", "pad", "drums"))
human = Humanizer.seeded(SEED, timing_sd=.004, velocity_sd=4)
rng = np.random.default_rng(SEED)


def add_note(bus, time, duration, pitch, velocity, loose=False):
    if loose:
        time, velocity = human(time, velocity)
        duration *= float(rng.uniform(.96, 1.04))
    timeline.note(bus, time, duration, pitch, velocity)


def bass_bar(bar, chord, variation=False):
    pattern = BASS_B if variation else BASS_A
    for beat, duration, interval in pattern:
        add_note("bass", bar * BAR + beat * BEAT, duration * BEAT,
                 chord["bass"] + interval, 99 if beat == 0 else 88, True)


def guitar_bar(bar, chord, sparse=False):
    # The structural attacks now lock to the bass instead of implying a
    # separate dotted rhythm.
    order = [0, 2, 1, 3]
    beats = [0, 1, 2, 3.25]
    if sparse:
        order, beats = [0, 1, 3], [0, 2, 3.25]
    for index, beat in zip(order, beats):
        add_note("guitar", bar * BAR + beat * BEAT, BEAT * (1.15 if sparse else .72),
                 chord["gtr"][index], 68 if sparse else 73, True)


def hook_bar(bar, chord):
    for beat, duration, pitch in HOOKS[chord["name"]]:
        add_note("hook", bar * BAR + beat * BEAT, duration * BEAT,
                 pitch, 77, True)


def synthlead_bar(bar, chord):
    for beat, duration, pitch in SYNTH_LEADS[chord["name"]]:
        add_note("synthlead", bar * BAR + beat * BEAT, duration * BEAT,
                 pitch, 67)


def pad_bar(bar, chord):
    for index, pitch in enumerate(chord["pad"]):
        add_note("pad", bar * BAR, BAR * 1.12, pitch, 48 - index * 3)


def drum_hit(time, pitch, velocity):
    timeline.note("drums", time, .04, pitch, velocity)


def drums_bar(bar, restrained=False, fill=False):
    t = bar * BAR
    # Half-time: the single backbeat on three makes the whole band trudge.
    drum_hit(t, 36, 115)
    drum_hit(t + 1.5 * BEAT, 36, 88)
    drum_hit(t + 2 * BEAT, 38, 112)
    drum_hit(t + 3.25 * BEAT, 36, 98)
    step_range = range(0, 8, 2) if restrained else range(8)
    for step in step_range:
        drum_hit(t + step * BEAT / 2, 46 if step == 7 else 42,
                 61 if step % 2 == 0 else 47)
    if fill:
        for step, velocity in zip((12, 13, 14, 15), (70, 79, 91, 108)):
            drum_hit(t + step * BEAT / 4, 38, velocity)


def render_drums(total_seconds):
    files = {
        36: ("kick.wav", .92), 38: ("snare.wav", .74),
        42: ("hhc.wav", .25), 46: ("hho.wav", .28),
    }
    n = int(total_seconds * SR)
    output = np.zeros((2, n), dtype=np.float32)
    cache = {}
    for pitch, (filename, gain) in files.items():
        _, audio = wavfile.read(os.path.join(KIT_DIR, filename))
        audio = audio.astype(np.float32) / 32768
        if audio.ndim == 2:
            audio = audio.mean(axis=1)
        cache[pitch] = audio / max(np.abs(audio).max(), 1e-9) * gain
    for position, kind, _, pitch, velocity in timeline["drums"]:
        if kind != "on":
            continue
        sample = cache[pitch] * (.55 + .45 * velocity / 127)
        end = min(position + len(sample), n)
        output[:, position:end] += sample[:end - position]
    return output


def render_pad(total_seconds):
    n = int(total_seconds * SR)
    output = np.zeros((2, n), dtype=np.float32)
    active, notes = {}, []
    for event in sorted(timeline["pad"], key=lambda item: item[0]):
        position, kind, channel, pitch, velocity = event
        key = (channel, pitch)
        if kind == "on":
            active[key] = (position, velocity)
        elif kind == "off" and key in active:
            start, note_velocity = active.pop(key)
            notes.append((start, position - start, pitch, note_velocity))
    for index, (start, duration, pitch, velocity) in enumerate(notes):
        length = min(duration + int(1.4 * SR), n - start)
        time = np.arange(length, dtype=np.float32) / SR
        frequency = 440 * 2 ** ((pitch - 69) / 12)
        phase = rng.uniform(0, 2 * np.pi)
        drift_l = 1 + .0015 * np.sin(2 * np.pi * .052 * time + phase)
        drift_r = 1 + .0015 * np.sin(2 * np.pi * .061 * time + phase + 1.3)
        ph_l = 2 * np.pi * np.cumsum(frequency * drift_l) / SR
        ph_r = 2 * np.pi * np.cumsum(frequency * drift_r) / SR
        left = .48 * sawtooth(ph_l * .994) + .48 * sawtooth(ph_l * 1.006) + .25 * np.sin(ph_l / 2)
        right = .48 * sawtooth(ph_r * .992) + .48 * sawtooth(ph_r * 1.008) + .25 * np.sin(ph_r / 2)
        attack, release = min(int(1.1 * SR), length), min(int(1.5 * SR), length)
        envelope = np.ones(length, dtype=np.float32)
        envelope[:attack] = np.sin(np.linspace(0, np.pi / 2, attack)) ** 2
        envelope[-release:] *= np.cos(np.linspace(0, np.pi / 2, release)) ** 2
        level = .065 * (.6 + .4 * velocity / 127)
        end = start + length
        output[0, start:end] += left * envelope * level
        output[1, start:end] += right * envelope * level
    return np.tanh(output).astype(np.float32)


def render_synthlead(total_seconds):
    n = int(total_seconds * SR)
    output = np.zeros((2, n), dtype=np.float32)
    active, notes = {}, []
    for event in sorted(timeline["synthlead"], key=lambda item: item[0]):
        position, kind, channel, pitch, velocity = event
        key = (channel, pitch)
        if kind == "on":
            active[key] = (position, velocity)
        elif kind == "off" and key in active:
            start, note_velocity = active.pop(key)
            notes.append((start, position - start, pitch, note_velocity))
    for start, duration, pitch, velocity in notes:
        length = min(duration + int(.55 * SR), n - start)
        time = np.arange(length, dtype=np.float32) / SR
        frequency = 440 * 2 ** ((pitch - 69) / 12)
        left = .68 * np.sin(2 * np.pi * frequency * time) + .32 * sawtooth(
            2 * np.pi * frequency * .997 * time, width=.5)
        right = .68 * np.sin(2 * np.pi * frequency * time) + .32 * sawtooth(
            2 * np.pi * frequency * 1.003 * time, width=.5)
        attack, release = min(int(.12 * SR), length), min(int(.48 * SR), length)
        envelope = np.ones(length, dtype=np.float32)
        envelope[:attack] = np.sin(np.linspace(0, np.pi / 2, attack)) ** 2
        envelope[-release:] *= np.cos(np.linspace(0, np.pi / 2, release)) ** 2
        level = .16 * (.55 + .45 * velocity / 127)
        end = start + length
        output[0, start:end] += left * envelope * level
        output[1, start:end] += right * envelope * level
    return output


def main():
    # 72 bars / roughly 3:47. The pad never leaves.
    sections = [
        (8, False, False, False),  # bass and fog
        (16, True, True, False),   # half-time statement
        (16, True, True, True),    # melody arrives
        (8, False, True, True),    # drums vanish, guitar hangs
        (16, True, True, True),    # complete return
        (8, True, False, False),   # bass/drum outro under the wash
    ]
    bar = 0
    for section_index, (bars, drums, guitar, hook) in enumerate(sections):
        for local in range(bars):
            chord = CHORDS[local % 8]
            # The opening is pad alone; bass makes its first entrance with
            # the drums at bar nine.
            if section_index != 0:
                bass_bar(bar, chord, variation=(local % 2 == 1))
            pad_bar(bar, chord)
            if drums:
                drums_bar(bar, restrained=section_index in (1, 5),
                          fill=local == bars - 1 and section_index in (1, 2, 4))
            if guitar:
                guitar_bar(bar, chord, sparse=section_index in (1, 3))
            if hook and local % 2 == 1:
                hook_bar(bar, chord)
            if section_index == 4:
                synthlead_bar(bar, chord)
            bar += 1

    # Resolve the final dominant to a single low D-minor breath.
    for pitch in CHORDS[0]["pad"]:
        add_note("pad", bar * BAR, BAR * .95, pitch, 44)
    add_note("bass", bar * BAR, BAR * .82, 38, 93, True)
    total_seconds = (bar + 1) * BAR + 6

    bass_sampler = ExsSampler(
        os.path.join(SAMPLES, "PickedRockBass"), sample_rate=SR,
        rng=np.random.default_rng(SEED + 1),
        groups=["Group #3", "Group #4", "Group #5", "Group #6", "Group #7"],
        release=.08,
    )
    guitar_sampler = ExsSampler(
        os.path.join(SAMPLES, "VintageStrat"), sample_rate=SR,
        rng=np.random.default_rng(SEED + 2), groups=["Main"],
        pickup=.20, release=.18,
    )
    bass = stereo(bass_sampler.render(timeline["bass"], total_seconds))
    guitar = stereo(guitar_sampler.render(timeline["guitar"], total_seconds), -.20)
    hook = stereo(guitar_sampler.render(timeline["hook"], total_seconds), .24)
    drums = render_drums(total_seconds)
    pad = render_pad(total_seconds)
    synthlead = render_synthlead(total_seconds)

    amp = load_nam(TWIN)
    amp.input_db = -9
    guitar = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=105),
        LowpassFilter(cutoff_frequency_hz=6100),
        Chorus(rate_hz=.52, depth=.18, centre_delay_ms=13, mix=.46),
        amp,
        Delay(delay_seconds=BEAT * .75, feedback=.26, mix=.16),
        Reverb(room_size=.92, damping=.48, wet_level=.39, dry_level=.72, width=1),
    ])(guitar, SR)
    hook_amp = load_nam(TWIN)
    hook_amp.input_db = -8
    hook = Pedalboard([
        Chorus(rate_hz=.68, depth=.15, centre_delay_ms=11, mix=.42),
        hook_amp,
        Delay(delay_seconds=BEAT, feedback=.32, mix=.19),
        Reverb(room_size=.94, damping=.44, wet_level=.43, dry_level=.68, width=1),
    ])(hook, SR)
    pad = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=125),
        LowpassFilter(cutoff_frequency_hz=2700),
        Chorus(rate_hz=.16, depth=.28, centre_delay_ms=19, mix=.42),
        Reverb(room_size=.97, damping=.46, wet_level=.58, dry_level=.54, width=1),
    ])(pad, SR)
    synthlead = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=240),
        LowpassFilter(cutoff_frequency_hz=4300),
        Chorus(rate_hz=.31, depth=.16, centre_delay_ms=14, mix=.34),
        Delay(delay_seconds=BEAT * .75, feedback=.24, mix=.16),
        Reverb(room_size=.91, damping=.50, wet_level=.39, dry_level=.68, width=1),
    ])(synthlead, SR)
    bass = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=32),
        LowpassFilter(cutoff_frequency_hz=5700),
        Compressor(threshold_db=-18, ratio=4, attack_ms=9, release_ms=120),
        Gain(gain_db=-2.5),
    ])(bass, SR)
    drums = Pedalboard([
        LowpassFilter(cutoff_frequency_hz=8400),
        Compressor(threshold_db=-16, ratio=3.2, attack_ms=5, release_ms=95),
    ])(drums, SR)

    mix = (bass * .60 + drums * .78 + guitar * .66 + hook * .48
           + synthlead * .30 + pad * .46)
    mix = normalize_peak(apply_fades(mix, SR, fade_in=.12, fade_out=5.5), .90)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    wavfile.write(OUT, SR, (mix.T * 32767).astype(np.int16))
    print(f"Wrote {OUT} — {bar + 1} bars, {total_seconds:.1f}s at {BPM} BPM")


if __name__ == "__main__":
    main()
