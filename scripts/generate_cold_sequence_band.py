"""Gary Numan / early Depeche Mode -- live band version.

Clean electric guitar 8th-note arpeggio, rhythm guitar chord hits,
electric bass (pick), and a four-on-the-floor kit with overdrive lead melody.
E minor, 116 BPM. Rendered through FluidR3_GM.sf2 via FluidSynth.
"""

import numpy as np
import fluidsynth
from scipy.io import wavfile

SR = 44100
SF_PATH = '/Users/clint/Desktop/FluidR3_GM.sf2'
BPM = 116
BEAT = 60.0 / BPM
BAR = BEAT * 4

CH_ARP    = 0
CH_RHYTHM = 1
CH_LEAD   = 2
CH_BASS   = 3
CH_DRUMS  = 9

CLEAN_GUITAR    = 27  # GM patch: Electric Guitar (Clean)
OVERDRIVE_GUITAR = 29  # GM patch: Overdriven Guitar
BASS_PICK       = 34  # GM patch: Electric Bass (Pick)

KICK  = 36
SNARE = 38
HH_CL = 42
HH_OP = 46

# E minor: i - iv - VI - III (Em - Am - C - G)
CHORDS = [
    {   # Em
        "arp":     [52, 59, 55, 64, 59, 55, 62, 59],
        "voicing": [52, 55, 59, 64],  # E3 G3 B3 E4
        "bass":    [40, 40, 47, 40, 40, 47, 40, 45],
    },
    {   # Am
        "arp":     [57, 64, 60, 69, 64, 60, 67, 64],
        "voicing": [57, 60, 64, 69],  # A3 C4 E4 A4
        "bass":    [45, 45, 52, 45, 45, 52, 45, 48],
    },
    {   # C
        "arp":     [48, 55, 52, 60, 55, 52, 59, 55],
        "voicing": [48, 52, 55, 60],  # C3 E3 G3 C4
        "bass":    [36, 36, 43, 36, 36, 43, 36, 38],
    },
    {   # G
        "arp":     [55, 62, 59, 67, 62, 59, 57, 62],
        "voicing": [55, 59, 62, 67],  # G3 B3 D4 G4
        "bass":    [43, 43, 50, 43, 43, 50, 43, 40],
    },
]

# 4-bar melody hook (beat_offset, duration_beats, midi)
MELODY_HOOK = [
    (0.0,  1.5, 83), (1.5, 0.5, 81), (2.0, 2.0, 79),
    (4.0,  2.0, 76), (6.0, 1.0, 74), (7.0, 1.0, 76),
    (8.0,  1.0, 83), (9.0, 0.5, 81), (9.5, 0.5, 83), (10.0, 2.0, 79),
    (12.0, 3.5, 71), (15.5, 0.5, 74),
]

_events = []


def _on(t, ch, note, vel):
    _events.append((int(t * SR), 'on', ch, note, vel))


def _off(t, ch, note):
    _events.append((int(t * SR), 'off', ch, note, 0))


def add_note(t, dur, ch, note, vel):
    _on(t, ch, note, vel)
    _off(t + dur, ch, note)


def strum(t, dur, ch, notes, vel=75, spread=0.011):
    for i, note in enumerate(notes):
        add_note(t + i * spread, max(dur - i * spread, 0.05), ch, note, max(vel - i * 3, 40))


def render_bar(bar_t, chord_idx, *, arp=False, rhythm=False, bass=False,
               drums=None, arp_vel=82, rhythm_vel=72):
    chord = CHORDS[chord_idx % 4]
    step = BEAT / 2

    if arp:
        for k, note in enumerate(chord["arp"]):
            add_note(bar_t + k * step, step * 0.87, CH_ARP, note, arp_vel)

    if rhythm:
        strum(bar_t, BAR * 0.62, CH_RHYTHM, chord["voicing"], vel=rhythm_vel)
        strum(bar_t + 2 * BEAT, BAR * 0.33, CH_RHYTHM, chord["voicing"], vel=max(rhythm_vel - 8, 40))

    if bass:
        for k, note in enumerate(chord["bass"]):
            add_note(bar_t + k * step, step * 0.84, CH_BASS, note, 88)

    if drums == "full":
        for beat_i in range(4):
            add_note(bar_t + beat_i * BEAT, 0.05, CH_DRUMS, KICK, 100)
        for beat_i in (1, 3):
            add_note(bar_t + beat_i * BEAT, 0.05, CH_DRUMS, SNARE, 88)
        for k8 in range(8):
            is_open = (k8 == 7)
            add_note(bar_t + k8 * step, 0.05, CH_DRUMS, HH_OP if is_open else HH_CL, 65 if is_open else 55)
    elif drums == "sparse":
        for beat_i in (0, 2):
            add_note(bar_t + beat_i * BEAT, 0.05, CH_DRUMS, KICK, 95)
        add_note(bar_t + 2 * BEAT, 0.05, CH_DRUMS, SNARE, 80)


def render_melody(section_start_t, n_bars):
    for loop_i in range(n_bars // 4):
        loop_t = section_start_t + loop_i * BAR * 4
        for beat_off, dur_b, note in MELODY_HOOK:
            add_note(loop_t + beat_off * BEAT, dur_b * BEAT * 0.90, CH_LEAD, note, 92)


def render_audio(total_secs):
    n_samples = int(total_secs * SR)
    fs = fluidsynth.Synth(samplerate=float(SR))
    sfid = fs.sfload(SF_PATH)
    fs.program_select(CH_ARP,    sfid, 0, CLEAN_GUITAR)
    fs.program_select(CH_RHYTHM, sfid, 0, CLEAN_GUITAR)
    fs.program_select(CH_LEAD,   sfid, 0, OVERDRIVE_GUITAR)
    fs.program_select(CH_BASS,   sfid, 0, BASS_PICK)

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
    sections = [
        dict(n_bars=8,  arp=True, rhythm=False, bass=False, drums=None,     melody=False, arp_vel=62),
        dict(n_bars=8,  arp=True, rhythm=True,  bass=False, drums=None,     melody=False, arp_vel=72, rhythm_vel=55),
        dict(n_bars=8,  arp=True, rhythm=True,  bass=True,  drums="sparse", melody=False),
        dict(n_bars=16, arp=True, rhythm=True,  bass=True,  drums="full",   melody=False),
        dict(n_bars=16, arp=True, rhythm=True,  bass=True,  drums="full",   melody=True),
        dict(n_bars=8,  arp=True, rhythm=True,  bass=False, drums=None,     melody=False, rhythm_vel=65),
        dict(n_bars=8,  arp=True, rhythm=True,  bass=True,  drums="sparse", melody=False),
        dict(n_bars=24, arp=True, rhythm=True,  bass=True,  drums="full",   melody=True),
        dict(n_bars=8,  arp=True, rhythm=True,  bass=False, drums=None,     melody=False, arp_vel=60, rhythm_vel=55),
        dict(n_bars=8,  arp=True, rhythm=False, bass=False, drums=None,     melody=False, arp_vel=42),
    ]

    total_bars = sum(s["n_bars"] for s in sections)
    total_secs = total_bars * BAR + 4.0

    bar_cursor = 0
    for s in sections:
        for bar_i in range(s["n_bars"]):
            render_bar(
                bar_cursor * BAR + bar_i * BAR, bar_i % 4,
                arp=s["arp"], rhythm=s["rhythm"], bass=s["bass"], drums=s["drums"],
                arp_vel=s.get("arp_vel", 82), rhythm_vel=s.get("rhythm_vel", 72),
            )
        if s.get("melody"):
            render_melody(bar_cursor * BAR, s["n_bars"])
        bar_cursor += s["n_bars"]

    print(f"Rendering {total_bars} bars ({total_secs:.1f}s) ...")
    out_l, out_r = render_audio(total_secs)

    n_samples = int(total_secs * SR)
    fade_in  = int(1.5 * SR)
    fade_out = int(4.0 * SR)
    env = np.ones(n_samples)
    env[:fade_in]  = np.linspace(0, 1, fade_in)
    env[-fade_out:] = np.linspace(1, 0, fade_out)
    out_l *= env
    out_r *= env

    peak = max(np.abs(out_l).max(), np.abs(out_r).max(), 1e-9)
    out_l = (out_l / peak * 0.92).clip(-1, 1)
    out_r = (out_r / peak * 0.92).clip(-1, 1)

    stereo = np.stack([out_l, out_r], axis=1)
    wavfile.write("cold_sequence_band.wav", SR, (stereo * 32767).astype(np.int16))
    print(f"Wrote cold_sequence_band.wav: {total_secs:.1f}s, {total_bars} bars at {BPM} BPM")


if __name__ == "__main__":
    main()
