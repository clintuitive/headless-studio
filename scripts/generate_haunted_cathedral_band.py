"""The Cure 'Faith' era -- live band version.

Jazz guitar ascending/descending arpeggio, slow strummed chord rhythm guitar,
warm finger-style bass, and sparse kick/snare kit with a haunting clean lead.
B minor, 72 BPM. Rendered through FluidR3_GM.sf2 via FluidSynth.
"""

import os
import numpy as np
import fluidsynth
from scipy.io import wavfile

SR = 44100
SF_PATH = os.path.expanduser("~/.headless-studio/soundfonts/FluidR3_GM.sf2")
BPM = 72
BEAT = 60.0 / BPM
BAR = BEAT * 4

CH_ARP    = 0
CH_RHYTHM = 1
CH_LEAD   = 2
CH_BASS   = 3
CH_DRUMS  = 9

JAZZ_GUITAR   = 26  # GM: Electric Guitar (Jazz)
CLEAN_GUITAR  = 27  # GM: Electric Guitar (Clean)
BASS_FINGER   = 33  # GM: Electric Bass (Finger)

KICK  = 36
SNARE = 38
HH_CL = 42

# B minor: i - VI - iv - VII (Bm - G - Em - A)
CHORDS = {
    "Bm": {
        "arp":     [59, 62, 66, 71, 66, 62, 59, 62],
        "voicing": [59, 62, 66, 71],   # B3 D4 F#4 B4
        "bass_r":  47,                 # B2
        "bass_5":  54,                 # F#3
    },
    "G": {
        "arp":     [55, 59, 62, 67, 62, 59, 55, 59],
        "voicing": [55, 59, 62, 67],   # G3 B3 D4 G4
        "bass_r":  43,
        "bass_5":  50,
    },
    "Em": {
        "arp":     [52, 55, 59, 64, 59, 55, 52, 55],
        "voicing": [52, 55, 59, 64],   # E3 G3 B3 E4
        "bass_r":  40,
        "bass_5":  47,
    },
    "A": {
        "arp":     [57, 61, 64, 69, 64, 61, 57, 61],
        "voicing": [57, 61, 64, 69],   # A3 C#4 E4 A4
        "bass_r":  45,
        "bass_5":  52,
    },
}
PROG = ["Bm", "G", "Em", "A"]

# 4-bar haunting lead melody (beat_offset, duration_beats, midi)
LEAD_MELODY = [
    (0.0,  2.5, 78), (2.5, 0.5, 76), (3.0, 1.0, 74),
    (4.0,  2.0, 71), (6.0, 1.5, 73), (7.5, 0.5, 71),
    (8.0,  2.0, 76), (10.0, 1.0, 74), (11.0, 1.0, 73),
    (12.0, 3.5, 66), (15.5, 0.5, 71),
]

_events = []


def _on(t, ch, note, vel):
    _events.append((int(t * SR), 'on', ch, note, vel))


def _off(t, ch, note):
    _events.append((int(t * SR), 'off', ch, note, 0))


def add_note(t, dur, ch, note, vel):
    _on(t, ch, note, vel)
    _off(t + dur, ch, note)


def strum(t, dur, ch, notes, vel=70, spread=0.016):
    for i, note in enumerate(notes):
        add_note(t + i * spread, max(dur - i * spread, 0.1), ch, note, max(vel - i * 4, 35))


def render_bar(bar_t, chord_name, *, arp=False, rhythm=False, bass=False,
               drums=None, arp_vel=78, rhythm_vel=65):
    chord = CHORDS[chord_name]
    step = BEAT / 2

    if arp:
        for k, note in enumerate(chord["arp"]):
            add_note(bar_t + k * step, step * 0.9, CH_ARP, note, arp_vel)

    if rhythm:
        # One slow strum per bar -- very Cure-like, let it ring
        strum(bar_t, BAR * 0.88, CH_RHYTHM, chord["voicing"], vel=rhythm_vel)

    if bass:
        # Root held, fifth on beat 2, root again on beat 3
        add_note(bar_t,              BEAT * 1.85, CH_BASS, chord["bass_r"], 88)
        add_note(bar_t + 2 * BEAT,  BEAT * 0.85, CH_BASS, chord["bass_5"], 80)
        add_note(bar_t + 3 * BEAT,  BEAT * 0.85, CH_BASS, chord["bass_r"], 84)

    if drums == "sparse":
        add_note(bar_t,          0.05, CH_DRUMS, KICK,  90)
        add_note(bar_t + 2 * BEAT, 0.05, CH_DRUMS, SNARE, 78)
    elif drums == "full":
        for beat_i in (0, 2):
            add_note(bar_t + beat_i * BEAT, 0.05, CH_DRUMS, KICK, 92)
        add_note(bar_t + 2 * BEAT, 0.05, CH_DRUMS, SNARE, 80)
        for beat_i in (1, 3):
            add_note(bar_t + beat_i * BEAT, 0.05, CH_DRUMS, HH_CL, 52)


def render_lead(section_start_t, n_bars):
    for loop_i in range(n_bars // 4):
        loop_t = section_start_t + loop_i * BAR * 4
        for beat_off, dur_b, note in LEAD_MELODY:
            add_note(loop_t + beat_off * BEAT, dur_b * BEAT * 0.92, CH_LEAD, note, 90)


def render_audio(total_secs):
    n_samples = int(total_secs * SR)
    fs = fluidsynth.Synth(samplerate=float(SR))
    sfid = fs.sfload(SF_PATH)
    fs.program_select(CH_ARP,    sfid, 0, JAZZ_GUITAR)
    fs.program_select(CH_RHYTHM, sfid, 0, JAZZ_GUITAR)
    fs.program_select(CH_LEAD,   sfid, 0, CLEAN_GUITAR)
    fs.program_select(CH_BASS,   sfid, 0, BASS_FINGER)

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
        dict(n_bars=8,  arp=True,  rhythm=False, bass=False, drums=None,     lead=False, arp_vel=60),
        dict(n_bars=8,  arp=True,  rhythm=True,  bass=False, drums=None,     lead=False, arp_vel=70, rhythm_vel=58),
        dict(n_bars=8,  arp=True,  rhythm=True,  bass=True,  drums="sparse", lead=False),
        dict(n_bars=16, arp=True,  rhythm=True,  bass=True,  drums="sparse", lead=True),
        dict(n_bars=8,  arp=True,  rhythm=False, bass=True,  drums=None,     lead=False),
        dict(n_bars=24, arp=True,  rhythm=True,  bass=True,  drums="full",   lead=True),
        dict(n_bars=8,  arp=True,  rhythm=True,  bass=False, drums=None,     lead=False, rhythm_vel=58),
        dict(n_bars=16, arp=True,  rhythm=False, bass=False, drums=None,     lead=False, arp_vel=50),
    ]

    total_bars = sum(m["n_bars"] for m in movements)
    total_secs = total_bars * BAR + 6.0

    bar_cursor = 0
    for m in movements:
        for bar_i in range(m["n_bars"]):
            chord_name = PROG[bar_i % len(PROG)]
            render_bar(
                bar_cursor * BAR + bar_i * BAR, chord_name,
                arp=m["arp"], rhythm=m["rhythm"], bass=m["bass"], drums=m["drums"],
                arp_vel=m.get("arp_vel", 78), rhythm_vel=m.get("rhythm_vel", 65),
            )
        if m.get("lead"):
            render_lead(bar_cursor * BAR, m["n_bars"])
        bar_cursor += m["n_bars"]

    print(f"Rendering {total_bars} bars ({total_secs:.1f}s) ...")
    out_l, out_r = render_audio(total_secs)

    n_samples = int(total_secs * SR)
    fade_in  = int(2.5 * SR)
    fade_out = int(6.0 * SR)
    env = np.ones(n_samples)
    env[:fade_in]   = np.linspace(0, 1, fade_in)
    env[-fade_out:] = np.linspace(1, 0, fade_out)
    out_l *= env
    out_r *= env

    peak = max(np.abs(out_l).max(), np.abs(out_r).max(), 1e-9)
    out_l = (out_l / peak * 0.92).clip(-1, 1)
    out_r = (out_r / peak * 0.92).clip(-1, 1)

    stereo = np.stack([out_l, out_r], axis=1)
    wavfile.write("haunted_cathedral_band.wav", SR, (stereo * 32767).astype(np.int16))
    print(f"Wrote haunted_cathedral_band.wav: {total_secs:.1f}s, {total_bars} bars at {BPM} BPM")


if __name__ == "__main__":
    main()
