"""Kraftwerk meets Joy Division -- live band version.

Mechanical clean-guitar 8th-note riff, muted-guitar off-beat stabs,
Peter Hook-style high melodic bass, and a motorik kick/snare kit.
F minor, 100 BPM. Rendered through FluidR3_GM.sf2 via FluidSynth.
"""

import os
import numpy as np
import fluidsynth
from scipy.io import wavfile

SR = 44100
SF_PATH = os.path.expanduser("~/.headless-studio/soundfonts/FluidR3_GM.sf2")
BPM = 100
BEAT = 60.0 / BPM
BAR = BEAT * 4

CH_SEQ    = 0
CH_STAB   = 1
CH_BASS   = 3
CH_DRUMS  = 9

CLEAN_GUITAR  = 27  # GM: Electric Guitar (Clean)
MUTED_GUITAR  = 28  # GM: Electric Guitar (Muted)
BASS_PICK     = 34  # GM: Electric Bass (Pick)

KICK  = 36
SNARE = 38
HH_CL = 42
HH_OP = 46

# F minor: i - bVI - bIII - bVII (Fm - Db - Ab - Eb)
CHORDS = [
    {   # Fm
        "seq":   [53, 60, 56, 65, 60, 56, 53, 63],
        "stab":  [53, 56, 60],   # F3 Ab3 C4
    },
    {   # Db
        "seq":   [49, 56, 53, 61, 56, 53, 49, 60],
        "stab":  [49, 53, 56],   # Db3 F3 Ab3
    },
    {   # Ab
        "seq":   [56, 63, 60, 68, 63, 60, 56, 65],
        "stab":  [56, 60, 63],   # Ab3 C4 Eb4
    },
    {   # Eb
        "seq":   [51, 58, 55, 63, 58, 55, 51, 58],
        "stab":  [51, 55, 58],   # Eb3 G3 Bb3
    },
]

# 4-bar Peter Hook melodic bass hook (beat_offset, duration_beats, midi)
BASS_HOOK = [
    (0.0,  0.5, 65), (0.5,  0.5, 63), (1.0,  0.5, 60), (1.5,  0.5, 58),
    (2.0,  0.5, 56), (2.5,  0.5, 55), (3.0,  1.0, 56),
    (4.0,  0.5, 60), (4.5,  0.5, 63), (5.0,  0.5, 65), (5.5,  0.5, 67),
    (6.0,  2.0, 65),
    (8.0,  0.5, 61), (8.5,  0.5, 60), (9.0,  0.5, 58), (9.5,  0.5, 56),
    (10.0, 0.5, 53), (10.5, 0.5, 56), (11.0, 1.0, 58),
    (12.0, 0.5, 56), (12.5, 0.5, 60), (13.0, 0.5, 63), (13.5, 0.5, 65),
    (14.0, 0.5, 63), (14.5, 0.5, 60), (15.0, 1.0, 58),
]

_events = []


def _on(t, ch, note, vel):
    _events.append((int(t * SR), 'on', ch, note, vel))


def _off(t, ch, note):
    _events.append((int(t * SR), 'off', ch, note, 0))


def add_note(t, dur, ch, note, vel):
    _on(t, ch, note, vel)
    _off(t + dur, ch, note)


def render_bar(bar_t, chord_idx, *, seq=False, stabs=False, drums=None, seq_vel=80):
    chord = CHORDS[chord_idx % 4]
    step = BEAT / 2

    if seq:
        for k, note in enumerate(chord["seq"]):
            add_note(bar_t + k * step, step * 0.84, CH_SEQ, note, seq_vel)

    if stabs:
        # Off-beat stabs on the "and" of beats 1 and 3
        for beat_off in (1.5, 3.5):
            t0 = bar_t + beat_off * BEAT
            for i, note in enumerate(chord["stab"]):
                add_note(t0 + i * 0.008, BEAT * 0.18, CH_STAB, note, 82 - i * 4)

    if drums == "full":
        # Motorik: 4-on-floor kick, snare on 2+4, 8th hi-hats
        for beat_i in range(4):
            add_note(bar_t + beat_i * BEAT, 0.05, CH_DRUMS, KICK, 100)
        for beat_i in (1, 3):
            add_note(bar_t + beat_i * BEAT, 0.05, CH_DRUMS, SNARE, 88)
        for k8 in range(8):
            is_open = (k8 == 7)
            add_note(bar_t + k8 * step, 0.05, CH_DRUMS, HH_OP if is_open else HH_CL, 62 if is_open else 52)


def render_bass(section_start_t, n_bars):
    for loop_i in range(n_bars // 4):
        loop_t = section_start_t + loop_i * BAR * 4
        for beat_off, dur_b, note in BASS_HOOK:
            add_note(loop_t + beat_off * BEAT, dur_b * BEAT * 0.88, CH_BASS, note, 90)


def render_audio(total_secs):
    n_samples = int(total_secs * SR)
    fs = fluidsynth.Synth(samplerate=float(SR))
    sfid = fs.sfload(SF_PATH)
    fs.program_select(CH_SEQ,  sfid, 0, CLEAN_GUITAR)
    fs.program_select(CH_STAB, sfid, 0, MUTED_GUITAR)
    fs.program_select(CH_BASS, sfid, 0, BASS_PICK)

    audio = np.zeros(n_samples * 2, dtype=np.float32)
    pos = 0
    for ev in sorted(_events, key=lambda e: e[0]):
        sp = min(ev[0], n_samples)
        if sp > pos:
            raw = fs.get_samples(sp - pos)
            end = min(pos * 2 + len(raw), len(audio))
            audio[pos * 2:end] += raw[:end - pos * 2].astype(np.float32) / 32768.0
            pos = sp
        if ev[1] == 'on':
            fs.noteon(ev[2], ev[3], ev[4])
        else:
            fs.noteoff(ev[2], ev[3])
    if pos < n_samples:
        raw = fs.get_samples(n_samples - pos)
        end = min(pos * 2 + len(raw), len(audio))
        audio[pos * 2:end] += raw[:end - pos * 2].astype(np.float32) / 32768.0
    fs.delete()
    return audio[0::2], audio[1::2]


def main():
    movements = [
        dict(n_bars=8,  seq=True,  stabs=False, bass=False, drums=None,   seq_vel=68),
        dict(n_bars=8,  seq=True,  stabs=False, bass=True,  drums=None,   seq_vel=75),
        dict(n_bars=8,  seq=True,  stabs=False, bass=True,  drums="full"),
        dict(n_bars=8,  seq=True,  stabs=True,  bass=True,  drums="full"),
        dict(n_bars=16, seq=True,  stabs=True,  bass=True,  drums="full"),
        dict(n_bars=16, seq=True,  stabs=True,  bass=True,  drums="full"),
        dict(n_bars=8,  seq=True,  stabs=False, bass=True,  drums=None,   seq_vel=72),
        dict(n_bars=16, seq=True,  stabs=True,  bass=True,  drums="full"),
        dict(n_bars=8,  seq=True,  stabs=False, bass=False, drums=None,   seq_vel=45),
    ]

    total_bars = sum(m["n_bars"] for m in movements)
    total_secs = total_bars * BAR + 4.0

    bar_cursor = 0
    for m in movements:
        for bar_i in range(m["n_bars"]):
            render_bar(
                bar_cursor * BAR + bar_i * BAR, bar_i % 4,
                seq=m["seq"], stabs=m["stabs"], drums=m["drums"],
                seq_vel=m.get("seq_vel", 80),
            )
        if m["bass"]:
            render_bass(bar_cursor * BAR, m["n_bars"])
        bar_cursor += m["n_bars"]

    print(f"Rendering {total_bars} bars ({total_secs:.1f}s) ...")
    out_l, out_r = render_audio(total_secs)

    n_samples = int(total_secs * SR)
    fade_in  = int(1.5 * SR)
    fade_out = int(4.0 * SR)
    env = np.ones(n_samples)
    env[:fade_in]   = np.linspace(0, 1, fade_in)
    env[-fade_out:] = np.linspace(1, 0, fade_out)
    out_l *= env
    out_r *= env

    peak = max(np.abs(out_l).max(), np.abs(out_r).max(), 1e-9)
    out_l = (out_l / peak * 0.92).clip(-1, 1)
    out_r = (out_r / peak * 0.92).clip(-1, 1)

    stereo = np.stack([out_l, out_r], axis=1)
    wavfile.write("berlin_sequence_band.wav", SR, (stereo * 32767).astype(np.int16))
    print(f"Wrote berlin_sequence_band.wav: {total_secs:.1f}s, {total_bars} bars at {BPM} BPM")


if __name__ == "__main__":
    main()
