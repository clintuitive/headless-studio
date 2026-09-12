"""Ashen Windows — lean, early-80s-inspired post-punk instrumental.

Melodic picked bass, mechanical drums, cold synth, and clean chorus guitar.
Built from the local sample/plugin rig so every performance is reproducible.
"""

import ctypes.util
import os

import numpy as np
_original_find_library = ctypes.util.find_library
def _find_library(name):
    found = _original_find_library(name)
    fallback = "/opt/homebrew/lib/libfluidsynth.dylib"
    return fallback if not found and name == "fluidsynth" and os.path.exists(fallback) else found
ctypes.util.find_library = _find_library

import fluidsynth
from pedalboard import (
    Chorus, Compressor, Delay, Gain, HighpassFilter, LowpassFilter,
    Pedalboard, Reverb,
)
from scipy.io import wavfile
from scipy.signal import sawtooth

from music_engine import (
    EventTimeline, ExsSampler, Humanizer, apply_fades, load_nam,
    normalize_peak, render_external_instrument, stereo,
)


SR = 44_100
BPM = 104
BEAT = 60.0 / BPM
BAR = BEAT * 4.0
SEED = 83

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SAMPLES = os.path.join(ROOT, "Samples")
AMPS = os.path.join(ROOT, "Amps")
OUT = os.path.join(ROOT, "Tracks", "ashen_windows.wav")

GUITAR_DIR = os.path.join(SAMPLES, "VintageStrat")
KIT_DIR = os.path.join(SAMPLES, "MFB-512")
AMPLE_HELPER = os.path.join(HERE, "render_ample_bass.py")
X86_PYTHON = os.path.expanduser("~/.venvs/x86-audio/bin/python")
TWIN = os.path.join(AMPS, "Fender_TwinVerb_Clean.nam")
SOUNDFONT = os.path.join(ROOT, "Soundfonts", "GeneralUser-GS.sf2")

CHORDS = [
    # Six-bar loop: Em(add9) – Cmaj7 – G – D/F# – Am7 – Bm
    {"name": "Em(add9)", "bass": 40, "gtr": [52, 59, 64, 66], "pad": [52, 59, 66]},
    {"name": "Cmaj7",    "bass": 36, "gtr": [52, 55, 59, 64], "pad": [48, 55, 59]},
    {"name": "G",        "bass": 43, "gtr": [50, 55, 59, 62], "pad": [50, 55, 59]},
    {"name": "D/F#",     "bass": 42, "gtr": [50, 54, 57, 62], "pad": [50, 57, 66]},
    {"name": "Am7",      "bass": 45, "gtr": [52, 57, 60, 64], "pad": [48, 52, 57]},
    {"name": "Bm",       "bass": 47, "gtr": [54, 59, 62, 66], "pad": [47, 54, 59]},
]

# A recurring, singable answer that changes its ending with the harmony.
HOOKS = {
    "Em(add9)": [(0.25, 0.75, 71), (1.25, 0.50, 74), (2.00, 1.50, 76)],
    "Cmaj7":    [(0.25, 0.75, 71), (1.25, 0.50, 67), (2.00, 1.50, 64)],
    "G":        [(0.25, 0.75, 71), (1.25, 0.50, 74), (2.00, 1.50, 79)],
    "D/F#":     [(0.25, 0.75, 69), (1.25, 0.50, 66), (2.00, 1.50, 62)],
    "Am7":      [(0.25, 0.75, 72), (1.25, 0.50, 71), (2.00, 1.50, 69)],
    "Bm":       [(0.25, 0.75, 71), (1.25, 0.50, 74), (2.00, 1.50, 66)],
}

timeline = EventTimeline(SR, ("guitar", "hook", "pad", "drums"))
rng = np.random.default_rng(SEED)
human = Humanizer.seeded(SEED)
bass_notes = []


def note(bus, t, dur, pitch, velocity, *, loose=False):
    if loose:
        t, velocity = human(t, velocity, timing_sd=0.006, velocity_sd=4)
        dur *= float(rng.uniform(0.96, 1.04))
    timeline.note(bus, t, dur, pitch, velocity)


def bass_bar(bar, chord, active=True, lift=False):
    if not active:
        return
    root = chord["bass"]
    pattern = (
        [(0, 0), (.5, 0), (1, 12), (1.5, 7), (2, 0), (2.5, 7), (3, 10), (3.5, 7)]
        if lift else
        [(0, 0), (.5, 0), (1, 7), (1.5, 0), (2, 12), (2.5, 7), (3, 0), (3.5, 5)]
    )
    for beat, interval in pattern:
        t, vel = human(bar * BAR + beat * BEAT, 102 if beat in (0, 2) else 91,
                       timing_sd=0.004, velocity_sd=4)
        bass_notes.append({
            "t": t, "dur": BEAT * 0.41, "note": root + interval, "vel": vel
        })


def guitar_bar(bar, chord, sparse=False):
    order = [0, 2, 1, 3, 2, 1, 2, 3]
    chosen = range(0, 8, 2) if sparse else range(8)
    for step in chosen:
        pitch = chord["gtr"][order[step]]
        note("guitar", bar * BAR + step * BEAT / 2, BEAT * (0.72 if sparse else 0.42),
             pitch, 67 if sparse else 73, loose=True)


def hook_bar(bar, chord):
    for beat, dur, pitch in HOOKS[chord["name"]]:
        note("hook", bar * BAR + beat * BEAT, dur * BEAT, pitch, 78, loose=True)


def pad_bar(bar, chord, velocity=52):
    for i, pitch in enumerate(chord["pad"]):
        note("pad", bar * BAR, BAR * 1.06, pitch, velocity - i * 4)


def drum_hit(t, name, velocity):
    # Store kit hits as lightweight MIDI-style events; note number is a label.
    labels = {"kick": 36, "snare": 38, "hhc": 42, "hho": 46}
    timeline.note("drums", t, 0.04, labels[name], velocity)


def drums_bar(bar, *, full=True, fill=False):
    t0 = bar * BAR
    for beat in (0, 2):
        drum_hit(t0 + beat * BEAT, "kick", 113 if beat == 0 else 101)
    for beat in (1, 3):
        drum_hit(t0 + beat * BEAT, "snare", 108)
    for step in range(8):
        if full or step % 2 == 0:
            drum_hit(t0 + step * BEAT / 2, "hho" if step == 7 else "hhc",
                     66 if step % 2 == 0 else 52)
    if fill:
        for step in (12, 13, 14, 15):
            drum_hit(t0 + step * BEAT / 4, "snare", 70 + (step - 12) * 10)


def render_drums(total_seconds):
    files = {
        36: ("kick.wav", .92), 38: ("snare.wav", .75),
        42: ("hhc.wav", .28), 46: ("hho.wav", .31),
    }
    n = int(total_seconds * SR)
    out = np.zeros((2, n), dtype=np.float32)
    cache = {}
    for pitch, (filename, gain) in files.items():
        _, data = wavfile.read(os.path.join(KIT_DIR, filename))
        data = data.astype(np.float32) / 32768.0
        if data.ndim == 2:
            data = data.mean(axis=1)
        cache[pitch] = data / max(np.max(np.abs(data)), 1e-9) * gain
    for position, kind, _, pitch, velocity in timeline["drums"]:
        if kind != "on":
            continue
        signal = cache[pitch] * (0.55 + 0.45 * velocity / 127.0)
        end = min(position + len(signal), n)
        out[:, position:end] += signal[:end - position]
    return out


def render_soundfont_bass(total_seconds):
    """Portable picked-bass fallback when the Intel Ample AU will not scan."""
    n = int(total_seconds * SR)
    synth = fluidsynth.Synth(samplerate=float(SR))
    synth.setting("synth.gain", .62)
    sfid = synth.sfload(SOUNDFONT)
    synth.program_select(0, sfid, 0, 34)  # GM picked electric bass
    events = []
    for item in bass_notes:
        events.append((int(item["t"] * SR), "on", item["note"], item["vel"]))
        events.append((int((item["t"] + item["dur"]) * SR), "off", item["note"], 0))
    interleaved = np.zeros(n * 2, dtype=np.float32)
    cursor = 0
    for position, kind, pitch, velocity in sorted(events):
        position = min(position, n)
        if position > cursor:
            raw = synth.get_samples(position - cursor).astype(np.float32) / 32768.0
            interleaved[cursor * 2:position * 2] = raw[:(position - cursor) * 2]
            cursor = position
        (synth.noteon(0, pitch, velocity) if kind == "on" else synth.noteoff(0, pitch))
    if cursor < n:
        raw = synth.get_samples(n - cursor).astype(np.float32) / 32768.0
        interleaved[cursor * 2:] = raw[:(n - cursor) * 2]
    synth.delete()
    return np.stack([interleaved[0::2], interleaved[1::2]])


def render_lush_pad(events, total_seconds):
    """Wide, slowly breathing analog-style pad from the pad note timeline."""
    n_samples = int(total_seconds * SR)
    output = np.zeros((2, n_samples), dtype=np.float32)
    open_notes = {}
    notes = []
    for event in sorted(events, key=lambda item: item[0]):
        position, kind, channel, pitch, velocity = event
        key = (channel, pitch)
        if kind == "on":
            open_notes[key] = (position, velocity)
        elif kind == "off" and key in open_notes:
            start, note_velocity = open_notes.pop(key)
            notes.append((start, position - start, pitch, note_velocity))

    for index, (start, duration, pitch, velocity) in enumerate(notes):
        length = min(duration + int(.85 * SR), n_samples - start)
        if length <= 0:
            continue
        t = np.arange(length, dtype=np.float32) / SR
        frequency = 440.0 * 2.0 ** ((pitch - 69) / 12.0)
        phase = float(rng.uniform(0, 2 * np.pi))
        drift_l = 1.0 + .0010 * np.sin(2 * np.pi * .071 * t + phase)
        drift_r = 1.0 + .0010 * np.sin(2 * np.pi * .083 * t + phase + 1.7)
        phase_l = 2 * np.pi * np.cumsum(frequency * drift_l) / SR
        phase_r = 2 * np.pi * np.cumsum(frequency * drift_r) / SR
        left = (
            .42 * sawtooth(phase_l * .9955)
            + .42 * sawtooth(phase_l * 1.0045)
            + .28 * sawtooth(phase_l, width=.5)
            + .18 * np.sin(phase_l * .5)
        )
        right = (
            .42 * sawtooth(phase_r * .9940)
            + .42 * sawtooth(phase_r * 1.0060)
            + .28 * sawtooth(phase_r, width=.5)
            + .18 * np.sin(phase_r * .5)
        )
        attack = min(int(.68 * SR), length)
        release = min(int(.95 * SR), length)
        envelope = np.ones(length, dtype=np.float32)
        envelope[:attack] = np.sin(np.linspace(0, np.pi / 2, attack)) ** 2
        envelope[-release:] *= np.cos(np.linspace(0, np.pi / 2, release)) ** 2
        breathe = .92 + .08 * np.sin(2 * np.pi * .18 * t + index * .7)
        level = .105 * (.55 + .45 * velocity / 127)
        end = start + length
        output[0, start:end] += left * envelope * breathe * level
        output[1, start:end] += right * envelope * breathe * level
    return np.tanh(output * 1.15).astype(np.float32)


def render_song():
    # 72 bars, about 2:46. Each tuple: bars, bass, drums, guitar, hook, pad.
    sections = [
        (6, True,  False, False, False, True),   # bass and distant synth
        (6, True,  True,  True,  False, True),   # statement
        (12, True, True,  True,  True,  False),  # first melody
        (12, True, True,  True,  False, True),   # colder middle
        (6, True,  False, True,  True,  True),   # suspended breakdown
        (18, True, True,  True,  True,  True),   # full return
        (6, True,  True,  False, False, True),   # rhythm outro
        (6, True,  False, False, False, True),   # dissolve
    ]
    bar = 0
    for section_i, (bars, use_bass, use_drums, use_gtr, use_hook, use_pad) in enumerate(sections):
        for local in range(bars):
            chord = CHORDS[local % len(CHORDS)]
            bass_bar(bar, chord, use_bass, lift=section_i in (2, 5))
            if use_drums:
                drums_bar(bar, full=section_i not in (1, 6),
                          fill=local == bars - 1 and section_i in (2, 3, 5))
            if use_gtr:
                guitar_bar(bar, chord, sparse=section_i in (1, 4))
            if use_hook and local % 2 == 1:
                hook_bar(bar, chord)
            if use_pad:
                pad_bar(bar, chord, velocity=46 if section_i in (0, 7) else 54)
            bar += 1

    # Final held Em: a genuine resolution rather than another loop.
    final = CHORDS[0]
    pad_bar(bar - 1, final, velocity=48)
    total_seconds = bar * BAR + 5.0

    strat = ExsSampler(GUITAR_DIR, sample_rate=SR, rng=np.random.default_rng(SEED),
                       pickup=0.20, release=0.16, groups=["Main"])
    guitar = stereo(strat.render(timeline["guitar"], total_seconds), -0.18)
    hook = stereo(strat.render(timeline["hook"], total_seconds), 0.22)
    pad = render_lush_pad(timeline["pad"], total_seconds)
    drums = render_drums(total_seconds)
    bass_timeline = EventTimeline(SR, ("bass",))
    for item in bass_notes:
        bass_timeline.note("bass", item["t"], item["dur"], item["note"], item["vel"])
    picked_bass = ExsSampler(
        os.path.join(SAMPLES, "PickedRockBass"),
        sample_rate=SR,
        rng=np.random.default_rng(SEED + 2),
        groups=["Group #3", "Group #4", "Group #5", "Group #6", "Group #7"],
        release=.07,
    )
    bass = stereo(picked_bass.render(bass_timeline["bass"], total_seconds))

    twin = load_nam(TWIN)
    twin.input_db = -8.0
    guitar = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=115),
        LowpassFilter(cutoff_frequency_hz=6500),
        Chorus(rate_hz=.72, depth=.15, centre_delay_ms=10.5, mix=.43),
        twin,
        Delay(delay_seconds=BEAT * .75, feedback=.20, mix=.11),
        Reverb(room_size=.78, damping=.54, wet_level=.25, dry_level=.75, width=1.0),
    ])(guitar, SR)

    twin_hook = load_nam(TWIN)
    twin_hook.input_db = -7.0
    hook = Pedalboard([
        Chorus(rate_hz=.92, depth=.12, centre_delay_ms=9.0, mix=.38),
        twin_hook,
        Delay(delay_seconds=BEAT, feedback=.22, mix=.14),
        Reverb(room_size=.82, damping=.48, wet_level=.28, dry_level=.72, width=1.0),
    ])(hook, SR)
    pad = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=105),
        LowpassFilter(cutoff_frequency_hz=3400),
        Chorus(rate_hz=.22, depth=.24, centre_delay_ms=17, mix=.38),
        Reverb(room_size=.93, damping=.52, wet_level=.43, dry_level=.65, width=1.0),
    ])(pad, SR)
    drums = Pedalboard([
        LowpassFilter(cutoff_frequency_hz=9200),
        Compressor(threshold_db=-16, ratio=3.0, attack_ms=5, release_ms=85),
    ])(drums, SR)
    bass = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=34),
        Compressor(threshold_db=-18, ratio=4, attack_ms=8, release_ms=105),
        Gain(gain_db=-2.2),
    ])(bass, SR)

    mix = bass * .82 + drums * .82 + guitar * .70 + hook * .55 + pad * .58
    mix = apply_fades(mix, SR, fade_in=.08, fade_out=4.5)
    mix = normalize_peak(mix, .90)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    wavfile.write(OUT, SR, (mix.T * 32767).astype(np.int16))
    print(f"Wrote {OUT} — {bar} bars, {total_seconds:.1f}s at {BPM} BPM")


if __name__ == "__main__":
    render_song()
