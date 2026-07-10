"""Transform Sources/ambient_demo.mp3 into an epic post-rock track.

The demo (147s beatless wash, white-note diatonic centered on A minor,
weak ~68 BPM internal pulse, dark ~480Hz centroid) IS the drone bed:
its real fade-in opens the track, its body loops under the whole
arrangement with 6s equal-power crossfades, and its natural fade-out is
the ending -- the band rises out of the recording and sinks back into it.

Everything else is the go-to band pipeline, post-rock voicing (see
generate_postrock_epic.py): Strat neck-pickup clean arps into a spotless
Twin, four independently-performed wall guitars through four different
amp captures, CC11 lead swells into the church IR, Ample bass with the
dUg grit path, live-kit Brooklyn drums with rolls and fills, one shared
room. A minor, 68 BPM, Am - F - C - G, ~6.9 minutes.
"""

import json
import os
import subprocess
import tempfile

import numpy as np
from scipy.io import wavfile

from generate_modern_darkwave_band import load_nam  # also shims libfluidsynth
import fluidsynth
from pedalboard import (Pedalboard, Chorus, Delay, Reverb, Compressor, Gain,
                        HighpassFilter, HighShelfFilter, LowpassFilter, LowShelfFilter, PeakFilter, Mix, Chain,
                        Convolution)

SR = 44100
BPM = 68  # the demo's own weak internal pulse
BEAT = 60.0 / BPM
BAR = BEAT * 4
SEED = 41

rng = np.random.default_rng(SEED)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SF_PATH = os.path.join(SCRIPT_DIR, "..", "Soundfonts", "GeneralUser-GS.sf2")
OUT_PATH = os.path.join(SCRIPT_DIR, "..", "Tracks", "postrock_ambient.wav")
DEMO_MP3 = os.path.join(SCRIPT_DIR, "..", "Sources", "ambient_demo.mp3")
AMPS = os.path.join(SCRIPT_DIR, "..", "Amps")
ROOM_IR = os.path.join(SCRIPT_DIR, "..", "IRs", "Highly Damped Large Room.wav")
CHURCH_IR = os.path.join(SCRIPT_DIR, "..", "IRs", "St Nicolaes Church.wav")
CAB_IR = os.path.join(SCRIPT_DIR, "..", "IRs", "Direct Cabinet N3.wav")
X86_PYTHON = os.path.expanduser("~/.venvs/x86-audio/bin/python")
AMPLE_HELPER = os.path.join(SCRIPT_DIR, "render_ample_bass.py")

CH_ARP, CH_LEAD, CH_WALL, CH_PAD, CH_STR, CH_DRUMS = 0, 1, 2, 3, 4, 9
WARM_PAD, STRINGS = 89, 48

# Drum notes -- match the Brooklyn kit's zone map (3 toms: 43/47/48).
KICK, SNARE, STICK, T_LOW, T_FLR, T_MID, T_HI = 36, 38, 37, 43, 43, 47, 48
RIDE, BELL, CRASH, CRASH2, HH_PEDAL = 51, 53, 49, 57, 44

BROOKLYN_DIR = os.path.join(SCRIPT_DIR, "..", "Samples", "Brooklyn")

# A minor, chords change every 2 bars: Am - F - C - G. Fully diatonic to
# the demo's white-note pitch pool, so the bed fuses with every chord.
# "fill" is the diatonic lower-neighbor offset for the octave-fill part.
PROG = ["Am", "F", "C", "G"]
CHORDS = {
    "Am": {"bass": 33, "wall": [45, 52, 57], "arp": [57, 60, 64, 69, 72], "pad": [57, 64, 69], "fill": 10},
    "F":  {"bass": 29, "wall": [41, 48, 53], "arp": [53, 57, 60, 65, 69], "pad": [53, 60, 65], "fill": 11},
    "C":  {"bass": 36, "wall": [48, 55, 60], "arp": [55, 60, 64, 67, 72], "pad": [55, 60, 64], "fill": 11},
    "G":  {"bass": 31, "wall": [43, 50, 55], "arp": [55, 59, 62, 67, 71], "pad": [55, 62, 67], "fill": 10},
}

# Lead phrases over one 8-bar chord cycle: (bar, beat, dur_beats, midi).
# Odd bars carry the riff cell (two 8ths, quarter, half); even bars hold
# the chord's color tone. Bar 7 walks G-B-D so every cycle's downbeat
# lands the lead on E5 as Am returns.
MELODY_A = [
    (0, 0.0, 3.0, 76), (0, 3.0, 1.0, 74),
    (1, 0.0, 0.5, 76), (1, 0.5, 0.5, 74), (1, 1.0, 1.0, 72), (1, 2.0, 2.0, 69),
    (2, 0.0, 3.0, 72), (2, 3.0, 1.0, 69),
    (3, 0.0, 0.5, 72), (3, 0.5, 0.5, 69), (3, 1.0, 1.0, 67), (3, 2.0, 2.0, 65),
    (4, 0.0, 3.0, 67), (4, 3.0, 1.0, 64),
    (5, 0.0, 0.5, 67), (5, 0.5, 0.5, 64), (5, 1.0, 1.0, 62), (5, 2.0, 2.0, 60),
    (6, 0.0, 3.0, 71), (6, 3.0, 1.0, 67),
    (7, 0.0, 1.0, 67), (7, 1.0, 1.0, 71), (7, 2.0, 2.0, 74),
]
# Same riff DNA up top for the final wall: arrives on A5 each cycle,
# leans on each chord's third (E5 held over C is the lift), then climbs
# D-E-G back home.
MELODY_B = [
    (0, 0.0, 3.0, 81), (0, 3.0, 1.0, 79),
    (1, 0.0, 0.5, 81), (1, 0.5, 0.5, 79), (1, 1.0, 1.0, 76), (1, 2.0, 2.0, 79),
    (2, 0.0, 3.0, 77), (2, 3.0, 1.0, 76),
    (3, 0.0, 0.5, 77), (3, 0.5, 0.5, 76), (3, 1.0, 1.0, 72), (3, 2.0, 2.0, 72),
    (4, 0.0, 4.0, 76),
    (5, 0.0, 0.5, 76), (5, 0.5, 0.5, 74), (5, 1.0, 1.0, 72), (5, 2.0, 2.0, 67),
    (6, 0.0, 3.0, 79), (6, 3.0, 1.0, 74),
    (7, 0.0, 1.0, 74), (7, 1.0, 1.0, 76), (7, 2.0, 2.0, 79),
]

THIRD_UP = {9: 3, 11: 3, 0: 4, 2: 3, 4: 3, 5: 4, 7: 4}  # A natural minor diatonic thirds
SIXTH_UP = {9: 8, 11: 8, 0: 9, 2: 9, 4: 8, 5: 9, 7: 9}   # diatonic sixths

EVENTS = {"arp": [], "gswell": [], "lead": [], "wallL": [], "wallR": [], "wallL2": [], "wallR2": [], "wallF": [], "pad": [], "drums": []}
AMPLE_NOTES = []


def human(t, vel, t_sd=0.006, v_sd=8):
    t = max(t + float(np.clip(rng.normal(0, t_sd), -2.5 * t_sd, 2.5 * t_sd)), 0.0)
    vel = int(np.clip(vel + rng.normal(0, v_sd), 1, 127))
    return t, vel


def add_note(bus, t, dur, ch, note, vel):
    EVENTS[bus].append((int(t * SR), "on", ch, note, vel))
    EVENTS[bus].append((int((t + dur) * SR), "off", ch, note, 0))


def add_cc(bus, t, ch, num, val):
    EVENTS[bus].append((int(t * SR), "cc", ch, num, int(np.clip(val, 0, 127))))


# ---- parts -------------------------------------------------------------------

def render_arp(bar_t, chord, mode):
    """16th-note picking in a fixed palindrome that repeats identically
    every bar -- steady enough to hypnotize, loose enough to not sound
    sequenced."""
    step = BEAT / 4
    tones = chord["arp"]
    pattern = [0, 1, 2, 3, 4, 3, 2, 1]
    n = 8 if mode == "sparse" else 16
    stride = 2 if mode == "sparse" else 1
    base_vel = 54 if mode == "sparse" else 62
    for k in range(n):
        t, vel = human(bar_t + k * step * stride, base_vel, t_sd=0.003, v_sd=3)
        add_note("arp", t, step * 2.2, CH_ARP, tones[pattern[k % 8]], vel)


def render_lead_swells(bar_t, chord):
    """A whole-note swell blooming out of silence: CC11 ramps under the note."""
    note = chord["pad"][2]
    t, vel = human(bar_t + 0.05, 96, t_sd=0.01)
    dur = BAR * 1.9
    att = dur * 0.65
    for k in range(14):
        add_cc("lead", t + att * k / 13, CH_LEAD, 11, 25 + 95 * k / 13)
    add_note("lead", t, dur, CH_LEAD, note, vel)


def render_melody(start_bar, n_bars, phrase, harmonize=False):
    phrases = phrase if isinstance(phrase[0], list) else [phrase]
    for cyc in range(0, n_bars, 8):
        for bar_off, beat, dur_b, note in phrases[(cyc // 8) % len(phrases)]:
            if cyc + bar_off >= n_bars:
                continue
            t0 = (start_bar + cyc + bar_off) * BAR + beat * BEAT
            t0, vel = human(t0, 96, t_sd=0.012, v_sd=3)
            add_cc("lead", t0 - 0.01, CH_LEAD, 11, 115)
            add_note("lead", t0, dur_b * BEAT * 0.97, CH_LEAD, note, vel)
            if harmonize:
                # A second player, not a harmonizer pedal: mostly thirds,
                # sometimes a sixth entering late, sometimes laying out.
                roll = rng.random()
                if roll < 0.15:
                    pass  # rests -- the lines breathe apart
                elif roll < 0.8:
                    h = note + THIRD_UP.get(note % 12, 3)
                    th, vh = human(t0 + 0.015, 86, t_sd=0.01, v_sd=3)
                    add_note("lead", th, dur_b * BEAT * 0.95, CH_LEAD, h, vh)
                else:
                    h = note + SIXTH_UP.get(note % 12, 9)
                    th, vh = human(t0 + 0.25 * BEAT, 84, t_sd=0.015, v_sd=3)
                    add_note("lead", th, dur_b * BEAT * 0.75, CH_LEAD, h, vh)


# Wall strum patterns: (beat, direction, accent). 'sustain' drives a
# syncopated D-DU-D-DU figure; 'double' is straight eighths -- the final
# wall churns.
STRUM_PATTERNS = {
    "sustain": [(0.0, "D", 1.0), (1.0, "D", 0.85), (1.5, "U", 0.7),
                (2.0, "D", 0.95), (3.0, "D", 0.85), (3.5, "U", 0.7)],
    "double":  [(0.0, "D", 1.0), (0.5, "U", 0.7), (1.0, "D", 0.85), (1.5, "U", 0.7),
                (2.0, "D", 0.95), (2.5, "U", 0.7), (3.0, "D", 0.85), (3.5, "U", 0.75)],
}


def render_wall(bar_t, chord, mode, bus):
    """Strummed power chords. Downstrokes rake low-to-high, upstrokes snap
    back softer. Each bus gets independent humanization: four distinct
    performances."""
    pattern = STRUM_PATTERNS[mode]
    for si, (beat_off, direction, accent) in enumerate(pattern):
        nxt = pattern[si + 1][0] if si + 1 < len(pattern) else 4.0
        dur = (nxt - beat_off) * BEAT * 0.92
        vel_base = int(112 * accent)
        notes = list(chord["wall"])
        if mode == "double" and beat_off in (0.0, 2.0):
            notes.append(notes[-1] + 12)  # octave sparkle on the accents
        order = notes if direction == "D" else list(reversed(notes))
        stagger = 0.014 if direction == "D" else 0.009
        vel_adj = 0 if direction == "D" else -10
        for i, note in enumerate(order):
            t, vel = human(bar_t + beat_off * BEAT + i * stagger, vel_base + vel_adj, t_sd=0.006, v_sd=5)
            add_note(bus, t, dur, CH_WALL, note, vel)


def render_wall_fills(bar_t, chord):
    """A second distorted guitarist: quick octave fills answering at the
    end of each chord's second bar. The neighbor tone is the chord's own
    diatonic step so nothing rubs against the white-note bed."""
    root = chord["wall"][0] + 12
    for beat_off, dur_b, note in [(2.5, 0.45, root + 12), (3.0, 0.45, root + chord["fill"]), (3.5, 0.5, root + 12)]:
        t, vel = human(bar_t + beat_off * BEAT, 106, t_sd=0.008, v_sd=5)
        add_note("wallF", t, dur_b * BEAT, CH_WALL, note, vel)
        t2, v2 = human(bar_t + beat_off * BEAT, 96, t_sd=0.009, v_sd=5)
        add_note("wallF", t2, dur_b * BEAT, CH_WALL, note - 12, v2)


def render_bass_bar(bar_t, chord, mode, phrase_bar=0):
    root = chord["bass"]
    if mode == "long":
        t, vel = human(bar_t, 92, t_sd=0.006)
        AMPLE_NOTES.append({"t": t, "dur": BAR * 0.95, "note": root, "vel": vel})
    elif mode == "melodic":
        # Whole note on the chord bar, then a walking answer -- the bass
        # carries the interest while the guitar glimmers.
        if phrase_bar % 2 == 0:
            notes = [(0.0, 3.8, root)]
        else:
            top = root + (10 if rng.random() < 0.3 else 12)
            notes = [(0.0, 1.9, root), (2.0, 0.95, root + 7), (3.0, 0.9, top)]
        for beat_off, dur_b, note in notes:
            t, vel = human(bar_t + beat_off * BEAT, 94, t_sd=0.006)
            AMPLE_NOTES.append({"t": t, "dur": dur_b * BEAT, "note": note, "vel": vel})
    elif mode == "build":
        # Legato with eighth-note pickups: momentum gathering.
        for beat_off, dur_b, note in [(0.0, 1.4, root), (1.5, 0.45, root),
                                      (2.0, 0.95, root + 7), (3.0, 0.45, root + 12),
                                      (3.5, 0.45, root + 7)]:
            t, vel = human(bar_t + beat_off * BEAT, 98, t_sd=0.005)
            AMPLE_NOTES.append({"t": t, "dur": dur_b * BEAT, "note": note, "vel": vel})
    elif mode == "drive":
        for k in range(8):
            note = root if k < 7 else root + (7 if rng.random() < 0.5 else 12)
            t, vel = human(bar_t + k * BEAT / 2, 112 if k % 4 == 0 else 103, t_sd=0.005)
            AMPLE_NOTES.append({"t": t, "dur": BEAT * 0.46, "note": note, "vel": vel})


def drum(t, note, vel, t_sd=0.006, v_sd=8):
    t, vel = human(t, vel, t_sd=t_sd, v_sd=v_sd)
    add_note("drums", t, 0.08, CH_DRUMS, note, vel)


def render_drums_bar(bar_t, mode, phrase_bar):
    if mode == "ride":
        for k in range(8):
            drum(bar_t + k * BEAT / 2, RIDE, 58 if k % 2 else 66)
        if phrase_bar % 2 == 0:
            drum(bar_t, BELL, 54)
        drum(bar_t, KICK, 88)
        if phrase_bar % 2 == 0:
            drum(bar_t + 2.5 * BEAT, KICK, 78)
        else:
            drum(bar_t + 2.75 * BEAT, KICK, 74)
        for b in (1.0, 3.0):
            drum(bar_t + b * BEAT, STICK, 60)
        if phrase_bar % 8 == 7:  # soft tom answer at phrase end
            drum(bar_t + 3.5 * BEAT, T_MID, 62)
            drum(bar_t + 3.75 * BEAT, T_LOW, 58)

    elif mode == "ride2":
        # Busier: syncopated kick, 16th ride pickups, ghosts and sidestick
        # -- the drummer leaning forward before the snare arrives.
        for k in range(8):
            drum(bar_t + k * BEAT / 2, RIDE, 60 if k % 2 else 68)
        for b in (0.75, 2.75):
            drum(bar_t + b * BEAT, RIDE, 42)  # 16th pickups
        if phrase_bar % 2 == 0:
            drum(bar_t, BELL, 56)
        for b in (0.0, 2.5, 3.75):
            drum(bar_t + b * BEAT, KICK, 90 if b == 0 else 78)
        for b in (1.0, 3.0):
            drum(bar_t + b * BEAT, STICK, 64)
        if rng.random() < 0.5:
            drum(bar_t + rng.choice([1.75, 3.25]) * BEAT, SNARE, 24, v_sd=4)
        if phrase_bar % 8 == 7:
            for j, tom in enumerate([T_HI, T_MID, T_LOW, T_FLR]):
                drum(bar_t + (3 + j * 0.25) * BEAT, tom, 64 + j * 4)

    elif mode == "groove":
        for k in range(8):
            drum(bar_t + k * BEAT / 2, RIDE, 66 if k in (0, 4) else 56)
        for b in (0.0, 2.5, 3.5):
            drum(bar_t + b * BEAT, KICK, 92)
        for b in (1.0, 3.0):
            drum(bar_t + b * BEAT, SNARE, 96)
        if rng.random() < 0.85:  # ghost notes breathe
            drum(bar_t + rng.choice([1.75, 2.25, 3.75]) * BEAT, SNARE, 26, v_sd=4)
        if rng.random() < 0.4:  # extra syncopated kick
            drum(bar_t + 1.75 * BEAT, KICK, 80)
        if phrase_bar % 8 == 0:
            drum(bar_t, CRASH, 96)
        if phrase_bar % 4 == 3 and phrase_bar % 8 != 7:  # small mid-phrase fill
            drum(bar_t + 3.5 * BEAT, SNARE, 70)
            drum(bar_t + 3.75 * BEAT, T_MID, 74)
        if phrase_bar % 8 == 7:  # phrase-end tom fill, last two beats
            for j, tom in enumerate([SNARE, T_HI, T_MID, T_MID, T_LOW, T_LOW, T_FLR, T_FLR]):
                drum(bar_t + (2 + j * 0.25) * BEAT, tom, 78 + j * 3)

    elif mode == "toms":  # false-calm floor-tom pulse
        for b, tom, v in [(0.0, T_FLR, 82), (0.75, T_FLR, 60), (1.5, T_LOW, 74),
                          (2.0, T_FLR, 82), (2.75, T_FLR, 60), (3.5, T_LOW, 70)]:
            drum(bar_t + b * BEAT, tom, v)
        drum(bar_t + 1.0 * BEAT, HH_PEDAL, 50)
        drum(bar_t + 3.0 * BEAT, HH_PEDAL, 50)

    elif mode in ("big", "big16"):
        crash = CRASH if phrase_bar % 2 == 0 else CRASH2
        drum(bar_t, crash, 104)
        if phrase_bar % 2 == 0:  # answering crash every other bar only
            drum(bar_t + 2 * BEAT, CRASH2, 80)
        kicks = np.arange(0, 4, 0.5) if mode == "big16" else [0.0, 1.5, 2.0, 3.5]
        for b in kicks:
            drum(bar_t + b * BEAT, KICK, 106 if b % 1 == 0 else 96)
        for b in (1.0, 3.0):
            drum(bar_t + (b - 0.25) * BEAT, SNARE, 42)  # 16th drag into the hit
            drum(bar_t + b * BEAT - 0.03, SNARE, 74)    # flam grace
            drum(bar_t + b * BEAT, SNARE, 118)
        for k in range(8):
            drum(bar_t + k * BEAT / 2, RIDE, 72)
        if phrase_bar % 8 == 7:
            for j, tom in enumerate([T_HI, T_HI, T_MID, T_MID, T_LOW, T_FLR, SNARE, SNARE]):
                drum(bar_t + (2 + j * 0.25) * BEAT, tom, 84 + j * 3)


def render_roll(bar_t):
    """Two-bar full-kit crescendo into the wall: the snare roll densifies
    from 16ths into 32nds, the kick moves from quarters to driving
    eighths with the floor tom doubling in, and a soft crash swell rises
    under the last bar."""
    steps = [bar_t + k * BEAT / 4 for k in range(28)]
    steps += [bar_t + 7 * BEAT + k * BEAT / 8 for k in range(8)]
    n = len(steps)
    for k, t in enumerate(steps):
        vel = 30 + int(96 * (k / (n - 1)) ** 1.4)
        drum(t, SNARE, vel, t_sd=0.003)
    for k in range(4):
        drum(bar_t + k * BEAT, KICK, 84 + k * 4)
    for k in range(8):
        drum(bar_t + 4 * BEAT + k * BEAT / 2, KICK, 92 + int(k * 3.5))
        if k % 2 == 0:
            drum(bar_t + 4 * BEAT + k * BEAT / 2, T_FLR, 78 + k * 4)
    for k, vel in enumerate((36, 48, 62, 78)):
        drum(bar_t + 4 * BEAT + k * BEAT, CRASH2, vel)
    drum(bar_t + 2 * BAR - 0.02, CRASH, 112)


# ---- the ambient bed -----------------------------------------------------------

def render_ambient_bed(total_secs, gain_bp):
    """The demo itself as the drone layer. Its real fade-in stays at the
    top of the track; the sustained body (12s-133s) loops under the band
    with 6s equal-power crossfades; the demo's own fade-out is placed to
    end exactly at the end of the track. Gain breakpoints (bar, gain)
    duck it under the band and open it back up in the calms."""
    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, "demo.wav")
        subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@44100", DEMO_MP3, wav],
                       check=True, capture_output=True)
        _, d = wavfile.read(wav)
    demo = (d.astype(np.float32) / 32768.0).T
    demo /= max(np.abs(demo).max(), 1e-9)

    head_n, tail_n, xf = int(12.0 * SR), int(14.0 * SR), int(6.0 * SR)
    body = demo[:, head_n:demo.shape[1] - tail_n]
    tail = demo[:, demo.shape[1] - tail_n:]
    up = np.sin(np.linspace(0, np.pi / 2, xf, dtype=np.float32)) ** 2
    down = 1.0 - up

    n_total = int(total_secs * SR)
    bed = np.zeros((2, n_total), dtype=np.float32)
    # head + first body pass are contiguous in the original: no seam.
    first = demo[:, :head_n + body.shape[1]]
    bed[:, :first.shape[1]] = first
    pos = first.shape[1]
    tail_start = n_total - tail_n
    while pos < tail_start + xf:
        s = pos - xf
        seg = body[:, :min(body.shape[1], n_total - s)].copy()
        n_up = min(xf, seg.shape[1])
        bed[:, s:s + n_up] *= down[:n_up]
        seg[:, :n_up] *= up[:n_up]
        bed[:, s:s + seg.shape[1]] += seg
        pos = s + seg.shape[1]
    # the demo's own ending, crossfaded over whatever is ringing there
    bed[:, tail_start:tail_start + xf] *= down
    bed[:, tail_start + xf:] = 0.0
    tail = tail.copy()
    tail[:, :xf] *= up
    bed[:, tail_start:tail_start + tail.shape[1]] += tail

    gain_bp = sorted(gain_bp)
    t = np.arange(n_total, dtype=np.float64) / SR
    times = np.array([bp[0] * BAR for bp in gain_bp])
    gains = np.array([bp[1] for bp in gain_bp])
    env = np.interp(t, times, gains).astype(np.float32)
    return bed * env


# ---- FluidSynth bus rendering (with CC support) -------------------------------

def render_bus(events, total_secs, setup):
    n_samples = int(total_secs * SR)
    fs = fluidsynth.Synth(samplerate=float(SR))
    fs.setting("synth.gain", 0.6)
    sfid = fs.sfload(SF_PATH)
    setup(fs, sfid)
    audio = np.zeros(n_samples * 2, dtype=np.float32)
    pos = 0
    for ev in sorted(events, key=lambda e: e[0]):
        sp = min(ev[0], n_samples)
        if sp > pos:
            raw = fs.get_samples(sp - pos)
            end = min(pos * 2 + len(raw), len(audio))
            audio[pos * 2:end] += raw[:end - pos * 2].astype(np.float32) / 32768.0
            pos = sp
        if ev[1] == "on":
            fs.noteon(ev[2], ev[3], ev[4])
        elif ev[1] == "off":
            fs.noteoff(ev[2], ev[3])
        else:
            fs.cc(ev[2], ev[3], ev[4])
    if pos < n_samples:
        raw = fs.get_samples(n_samples - pos)
        end = min(pos * 2 + len(raw), len(audio))
        audio[pos * 2:end] += raw[:end - pos * 2].astype(np.float32) / 32768.0
    fs.delete()
    return np.stack([audio[0::2], audio[1::2]])


def setup_pad(fs, sfid):
    fs.program_select(CH_PAD, sfid, 0, WARM_PAD)
    fs.program_select(CH_STR, sfid, 0, STRINGS)
    fs.cc(CH_PAD, 10, 54)
    fs.cc(CH_STR, 10, 74)


class ExsSampler:
    """Pitched playback of an extracted EXS instrument: zone selection by
    note and velocity (same-range zones act as round-robins), linear-
    interpolation resampling to exact pitch, natural sample decay with a
    release fade at note-off."""

    def __init__(self, sample_dir, pickup=None, deterministic=False):
        # pickup: optional pickup position as a fraction of string length
        # from the bridge (neck ~0.27). Imposes that position's comb
        # response per note -- notches depend on each note's fundamental,
        # which static EQ can't reproduce.
        self.dir = sample_dir
        self.pickup = pickup
        self.deterministic = deterministic  # no round-robin randomness
        with open(os.path.join(sample_dir, "manifest.json")) as f:
            self.zones = json.load(f)
        self.cache = {}

    def _zone(self, note, vel):
        c = [z for z in self.zones if z["keylo"] <= note <= z["keyhi"]]
        if not c:
            c = sorted(self.zones, key=lambda z: abs(z["root"] - note))[:3]
        cv = [z for z in c if z["vello"] <= vel <= z["velhi"]] or c
        if self.deterministic:
            return cv[0]
        return cv[int(rng.integers(len(cv)))]

    def _load(self, fname):
        if fname not in self.cache:
            _, d = wavfile.read(os.path.join(self.dir, fname))
            d = d.astype(np.float32) / 32768.0
            if d.ndim == 2:
                d = d.mean(axis=1)
            self.cache[fname] = d
        return self.cache[fname]

    def render(self, events, total_secs, attack=0.0):
        n_samples = int(total_secs * SR)
        out = np.zeros(n_samples, dtype=np.float32)
        open_notes, notes = {}, []
        for ev in sorted(events, key=lambda e: e[0]):
            if ev[1] == "on":
                open_notes[(ev[2], ev[3])] = (ev[0], ev[4])
            elif ev[1] == "off" and (ev[2], ev[3]) in open_notes:
                pos, vel = open_notes.pop((ev[2], ev[3]))
                notes.append((pos, ev[0] - pos, ev[3], vel))
        for pos, dur_smp, note, vel in notes:
            z = self._zone(note, vel)
            data = self._load(z["file"])
            ratio = 2.0 ** ((note - z["root"]) / 12.0)
            n_out = int(len(data) / ratio)
            idx = np.arange(n_out) * ratio
            i0 = np.floor(idx).astype(int)
            i1 = np.minimum(i0 + 1, len(data) - 1)
            frac = (idx - i0).astype(np.float32)
            sig = data[i0] * (1 - frac) + data[i1] * frac
            rel = int(0.09 * SR)
            length = min(len(sig), dur_smp + rel)
            sig = sig[:length].copy()
            if length > rel:
                sig[-rel:] *= np.linspace(1, 0, rel, dtype=np.float32)
            if self.pickup:
                freq = 440.0 * 2.0 ** ((note - 69) / 12.0)
                D = max(int(self.pickup * SR / freq), 1)
                if D < len(sig):
                    comb = sig.copy()
                    comb[D:] -= sig[:-D]
                    sig = comb * 0.8
            sig *= 0.45 + 0.55 * vel / 127.0
            if attack > 0:
                n_att = min(int(attack * SR), len(sig))
                sig[:n_att] *= np.sin(np.linspace(0, np.pi / 2, n_att, dtype=np.float32)) ** 2
            end = min(pos + len(sig), n_samples)
            if end > pos:
                out[pos:end] += sig[:end - pos]
        return out


def stereo(sig, pan=0.0):
    l = np.sqrt(0.5 * (1 - pan))
    r = np.sqrt(0.5 * (1 + pan))
    return np.stack([sig * l, sig * r])


def cc11_curve(events, total_secs):
    """Expression automation as a gain curve -- applied to the rendered
    bus, replacing FluidSynth's CC handling for sampled instruments."""
    n = int(total_secs * SR)
    pts_t, pts_v = [0], [110 / 127]
    for ev in sorted(events, key=lambda e: e[0]):
        if ev[1] == "cc" and ev[3] == 11:
            pts_t.append(ev[0])
            pts_v.append(ev[4] / 127)
    return np.interp(np.arange(n), pts_t, pts_v).astype(np.float32)


def norm_peak(bus, target):
    """Normalize a bus's peak before it hits an amp -- keeps the drive
    predictable regardless of the source instrument's recorded level."""
    return bus / max(np.abs(bus).max(), 1e-9) * target


def render_brooklyn(events, total_secs):
    """Play the drum events through the Brooklyn kit's real recordings:
    velocity picks the recorded layer (the samples encode the dynamics),
    same-range zones act as round-robins, and a light gain curve rides on
    top for continuity between layers."""
    with open(os.path.join(BROOKLYN_DIR, "manifest.json")) as f:
        zones = json.load(f)
    by_key = {}
    for z in zones:
        by_key.setdefault(z["keylo"], []).append(z)
    cache = {}
    n_samples = int(total_secs * SR)
    bus = np.zeros((2, n_samples), dtype=np.float32)
    for ev in sorted(events, key=lambda e: e[0]):
        if ev[1] != "on":
            continue
        pos_s, _, _, note, vel = ev
        zs = by_key.get(note)
        if not zs:
            continue
        matches = [z for z in zs if z["vello"] <= vel <= z["velhi"]]
        if not matches:
            matches = [min(zs, key=lambda z: abs(z["vello"] - vel))]
        z = matches[int(rng.integers(len(matches)))]  # round-robin
        if z["file"] not in cache:
            _, d = wavfile.read(os.path.join(BROOKLYN_DIR, z["file"]))
            d = d.astype(np.float32) / 32768.0
            cache[z["file"]] = np.stack([d, d]) if d.ndim == 1 else d.T
        s = cache[z["file"]] * (0.55 + 0.45 * vel / 127.0)
        end = min(pos_s + s.shape[1], n_samples)
        if end > pos_s:
            bus[:, pos_s:end] += s[:, :end - pos_s]
    return bus * 1.3


def render_ample_bass(total_secs):
    if not (os.path.exists(X86_PYTHON) and AMPLE_NOTES):
        return None
    with tempfile.TemporaryDirectory() as td:
        events_path = os.path.join(td, "bass.json")
        stem_path = os.path.join(td, "bass.wav")
        with open(events_path, "w") as f:
            json.dump({"duration": total_secs, "notes": AMPLE_NOTES}, f)
        result = subprocess.run(
            ["arch", "-x86_64", X86_PYTHON, AMPLE_HELPER, events_path, stem_path],
            capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Ample Bass helper failed:\n{result.stderr.strip()}")
            return None
        print(result.stdout.strip())
        _, data = wavfile.read(stem_path)
    audio = (data.astype(np.float32) / 32768.0).T
    n_samples = int(total_secs * SR)
    if audio.shape[1] < n_samples:
        audio = np.pad(audio, ((0, 0), (0, n_samples - audio.shape[1])))
    return audio[:, :n_samples]


# ---- arrangement --------------------------------------------------------------

def main():
    movements = [
        # The demo's real fade-in, alone: the source material introduces itself.
        dict(n_bars=4, bed=1.0),
        # The clean arp surfaces out of the wash, pads shadowing the changes.
        dict(n_bars=8, bed=0.8, arp="full", pad_gain=0.3),
        # Bass and ride cymbal arrive; the bass carries the melody now.
        dict(n_bars=16, bed=0.6, arp="full", bass="melodic", drums="ride", pad_gain=0.15),
        # Lead swells bloom; the kit leans forward, bass keeps walking.
        dict(n_bars=16, bed=0.55, arp="full", bass="melodic", drums="ride2", lead="swell", pad_gain=0.25),
        # The kit opens up, melody states the theme; roll into the wall.
        dict(n_bars=16, bed=0.5, arp="full", bass="build", drums="groove", lead="melodyA", pad_gain=0.35, roll_out=True),
        # FIRST WALL.
        dict(n_bars=16, bed=0.38, bass="drive", drums="big", wall="sustain", pad_gain=0.9),
        # False calm: walls cut dead, the wash floods back over floor toms.
        dict(n_bars=12, bed=0.85, arp="sparse", bass="long", drums="toms", lead="swell", pad_gain=0.3, roll_out=True),
        # FINAL WALL: double-struck chords, 16th kicks, harmonized melody.
        dict(n_bars=24, bed=0.45, bass="drive", drums="big16", wall="double", wall_fills=True, lead="melodyB", harmonize=True, pad_gain=1.0),
        # Everything cuts; the demo's own fade-out ends the track.
        dict(n_bars=4, bed=1.0, chord="Am", pad_root_only=True, pad_gain=0.4),
    ]

    total_bars = sum(m["n_bars"] for m in movements)
    total_secs = total_bars * BAR + 2.0
    print(f"{total_bars} bars, {total_secs/60:.1f} minutes")

    bed_bp = [(0, 1.0)]
    bar_cursor = 0
    for m in movements:
        bed_bp.append((bar_cursor + 1.5, m["bed"]))
        bed_bp.append((bar_cursor + m["n_bars"] - 0.5, m["bed"]))
        for bar_i in range(m["n_bars"]):
            bar_t = (bar_cursor + bar_i) * BAR
            chord = CHORDS[m["chord"]] if m.get("chord") else CHORDS[PROG[(bar_i // 2) % 4]]
            phrase_bar = bar_i
            if m.get("arp"):
                render_arp(bar_t, chord, m["arp"])
            if m.get("bass"):
                render_bass_bar(bar_t, chord, m["bass"], phrase_bar)
            rolling = m.get("roll_out") and bar_i >= m["n_bars"] - 2
            if m.get("drums") and not rolling:
                render_drums_bar(bar_t, m["drums"], phrase_bar)
            if m.get("wall"):
                for bus in ("wallL", "wallR", "wallL2", "wallR2"):
                    render_wall(bar_t, chord, m["wall"], bus)
                if m.get("wall_fills") and bar_i % 2 == 1:
                    render_wall_fills(bar_t, chord)
            if m.get("lead") == "swell" and bar_i % 2 == 0:
                render_lead_swells(bar_t, chord)
            if m.get("pad_gain", 0) > 0:
                pad_notes = chord["pad"][:1] if m.get("pad_root_only") else chord["pad"]
                for j, note in enumerate(pad_notes):
                    v = int((46 + m["pad_gain"] * 65) * (1 - j * 0.1))
                    add_note("pad", bar_t, BAR * 1.9, CH_PAD, note, v)
                    if m["pad_gain"] >= 0.4:
                        add_note("pad", bar_t, BAR * 1.9, CH_STR, note + 12, int(v * 0.75))
        if m.get("roll_out"):
            render_roll((bar_cursor + m["n_bars"] - 2) * BAR)
        if m.get("lead") in ("melodyA", "melodyB"):
            render_melody(bar_cursor, m["n_bars"], MELODY_A if m["lead"] == "melodyA" else MELODY_B, harmonize=m.get("harmonize", False))
        bar_cursor += m["n_bars"]

    print("Rendering buses ...")
    # Real sampled guitars, all CLEAN into the captures -- the amps supply
    # the dirt. Warm Electric and Vintage Strat split the walls like a
    # real double-tracking session.
    warm = ExsSampler(os.path.join(SCRIPT_DIR, "..", "Samples", "WarmElectric"))
    strat = ExsSampler(os.path.join(SCRIPT_DIR, "..", "Samples", "VintageStrat"))
    strat_neck = ExsSampler(os.path.join(SCRIPT_DIR, "..", "Samples", "VintageStrat"), pickup=0.27, deterministic=True)
    arp_mono = strat_neck.render(EVENTS["arp"], total_secs)
    arp = stereo(arp_mono * cc11_curve(EVENTS["arp"], total_secs), pan=-0.25)
    strat_lead = ExsSampler(os.path.join(SCRIPT_DIR, "..", "Samples", "VintageStrat"), deterministic=True)
    lead_mono = strat_lead.render(EVENTS["lead"], total_secs)
    lead = stereo(lead_mono * cc11_curve(EVENTS["lead"], total_secs), pan=0.2)
    wall_l = stereo(warm.render(EVENTS["wallL"], total_secs), pan=-0.85)
    wall_r = stereo(strat.render(EVENTS["wallR"], total_secs), pan=0.85)
    wall_l2 = stereo(strat.render(EVENTS["wallL2"], total_secs), pan=-0.45)
    wall_r2 = stereo(warm.render(EVENTS["wallR2"], total_secs), pan=0.45)
    wall_f = stereo(warm.render(EVENTS["wallF"], total_secs), pan=0.1)
    arp = norm_peak(arp, 0.30)
    lead = norm_peak(lead, 0.40)
    wall_l = norm_peak(wall_l, 0.55)
    wall_r = norm_peak(wall_r, 0.55)
    wall_l2 = norm_peak(wall_l2, 0.5)
    wall_r2 = norm_peak(wall_r2, 0.5)
    wall_f = norm_peak(wall_f, 0.5)
    pad = render_bus(EVENTS["pad"], total_secs, setup_pad)
    drums = render_brooklyn(EVENTS["drums"], total_secs)
    bed = render_ambient_bed(total_secs, bed_bp)
    bass = render_ample_bass(total_secs)
    if bass is None:
        raise SystemExit("Ample bass required for this one -- helper failed")

    print("Applying effects ...")
    # The Twin capture is ~25dB quiet and the cab IR ~13dB more -- makeup
    # gain inside the amp and after the cab brings the chain to unity.
    twin = load_nam(os.path.join(AMPS, "Fender_TwinVerb_Clean.nam"))
    twin.input_db = -4.0
    twin.output_db = 20.0
    ac15_lead = load_nam(os.path.join(AMPS, "Vox_AC15_TopBoost.nam")); ac15_lead.input_db = 0.0
    orange = load_nam(os.path.join(AMPS, "Orange_Rockerverb.nam")); orange.input_db = 0.0
    jcm = load_nam(os.path.join(AMPS, "JCM2000_Lead_Boosted.nam")); jcm.input_db = 0.0
    jcm9 = load_nam(os.path.join(AMPS, "JCM900_ChB_G12.nam")); jcm9.input_db = 0.0
    dug = load_nam(os.path.join(AMPS, "Tech21_dUg_BassPreamp.nam")); dug.input_db = -6.0

    # Strat neck-pickup voicing: notch the quack band, warm the lows,
    # keep the top glassy -- into a spotless Twin + real cab IR.
    arp = Pedalboard([
        PeakFilter(cutoff_frequency_hz=1000, gain_db=-4.5, q=1.1), # de-quack
        LowShelfFilter(cutoff_frequency_hz=220, gain_db=2.0),      # neck warmth
        LowpassFilter(cutoff_frequency_hz=5000),                   # bright but round
        twin,
        Convolution(CAB_IR, mix=1.0),
        Gain(gain_db=16.0),                                        # cab IR makeup
        LowpassFilter(cutoff_frequency_hz=5600),                   # speaker edge
        Delay(delay_seconds=BEAT * 0.75, feedback=0.25, mix=0.1),
    ])(arp, SR)
    # Modulated plate: bright dense tail, lows rolled like a real plate,
    # slow chorus modulation in the wet path only, ~0.3 wet.
    plate = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=150),
        Reverb(room_size=0.8, damping=0.15, wet_level=1.0, dry_level=0.0, width=1.0),
        Chorus(rate_hz=0.6, depth=0.25, centre_delay_ms=9.0, mix=0.7),
    ])(arp, SR)
    arp = arp * 0.8 + plate * 0.3
    # Lead: AC15 pushed into real breakup, chorus warble.
    lead = Pedalboard([
        Chorus(rate_hz=1.35, depth=0.25, centre_delay_ms=14.0, mix=0.5), ac15_lead,
        Delay(delay_seconds=BEAT * 1.0, feedback=0.45, mix=0.3),
        Reverb(room_size=0.9, damping=0.4, wet_level=0.3, dry_level=0.7),
    ])(lead, SR)
    wall_fx = lambda amp: Pedalboard([
        HighpassFilter(cutoff_frequency_hz=82), amp,
    ])

    def wall_space(bus):
        # Modulated plate on the walls too: takes the dry harsh edge off
        # the distortion and sets it into the same lush space as the
        # clean guitar.
        wet = Pedalboard([
            HighpassFilter(cutoff_frequency_hz=160),
            Reverb(room_size=0.85, damping=0.22, wet_level=1.0, dry_level=0.0, width=1.0),
            Chorus(rate_hz=0.5, depth=0.3, centre_delay_ms=10.0, mix=0.6),
        ])(bus, SR)
        return bus * 0.8 + wet * 0.3

    wall_l = wall_space(wall_fx(orange)(wall_l, SR))
    wall_r = wall_space(wall_fx(jcm)(wall_r, SR))
    wall_l2 = wall_space(wall_fx(jcm9)(wall_l2, SR))
    wall_r2 = wall_space(wall_fx(jcm9)(wall_r2, SR))
    wall_f = wall_space(wall_fx(orange)(wall_f, SR))
    pad = Pedalboard([
        Chorus(rate_hz=0.3, depth=0.25, centre_delay_ms=16.0, mix=0.3),
        Reverb(room_size=0.92, damping=0.5, wet_level=0.42, dry_level=0.58),
    ])(pad, SR)
    bass = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=32),
        Mix([Chain([Gain(gain_db=0.0)]), Chain([dug, Gain(gain_db=-10.0)])]),
        Compressor(threshold_db=-18, ratio=4, attack_ms=6, release_ms=120),
    ])(bass, SR)
    drums = Pedalboard([
        Compressor(threshold_db=-14, ratio=3, attack_ms=5, release_ms=220),
        PeakFilter(cutoff_frequency_hz=3000, gain_db=-3.5, q=0.9),  # bell ping
        HighShelfFilter(cutoff_frequency_hz=9000, gain_db=-1.5),    # cymbal sizzle
    ])(drums, SR)
    # The bed keeps its own character; just clear the band's low end.
    bed = Pedalboard([HighpassFilter(cutoff_frequency_hz=65)])(bed, SR)

    bass *= 1.02; drums *= 0.78; arp *= 0.52; lead *= 0.85
    pad *= 0.42; bed *= 0.5
    # Walls as texture, not volume: solve for the gain that lets all five
    # wall layers raise the wall sections by only ~0.2 dB total.
    base = bass + drums + arp + lead + pad + bed
    walls = wall_l + wall_r + wall_l2 + wall_r2 + wall_f
    active = np.abs(walls).max(axis=0) > 1e-4
    p_base = float((base[:, active] ** 2).mean())
    p_wall = float((walls[:, active] ** 2).mean())
    g = float(np.sqrt((10 ** 0.06 - 1) * p_base / max(p_wall, 1e-12)))
    walls *= g
    print(f"wall texture gain: {g:.3f}")
    dry = base + walls

    rms = lambda a: np.sqrt((a ** 2).mean())
    room_send = (0.65 * drums + 0.5 * (arp + walls) + 0.4 * lead + 0.2 * bass).astype(np.float32)
    room = Convolution(ROOM_IR, mix=1.0)(room_send, SR)
    room *= 0.2 * rms(dry) / max(rms(room), 1e-9)
    church_send = (0.8 * lead + 0.5 * pad + 0.2 * bed + 0.35 * arp).astype(np.float32)
    church = Convolution(CHURCH_IR, mix=1.0)(church_send, SR)
    church *= 0.14 * rms(dry) / max(rms(church), 1e-9)

    master = dry + room + church
    n_samples = master.shape[1]
    fade = int(1.5 * SR)  # safety only -- the demo's own fade-out ends the track
    env = np.ones(n_samples, dtype=np.float32)
    env[-fade:] = np.linspace(1, 0, fade)
    master *= env
    master = master / max(np.abs(master).max(), 1e-9) * 0.9

    wavfile.write(OUT_PATH, SR, (master.T * 32767).astype(np.int16))
    print(f"Wrote {os.path.normpath(OUT_PATH)}: {total_secs/60:.1f} min, {total_bars} bars at {BPM} BPM")


if __name__ == "__main__":
    main()
