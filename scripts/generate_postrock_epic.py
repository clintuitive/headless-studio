"""Slow-build epic post-rock in the vein of pg.lost -- long drone intro,
layer-by-layer accumulation, a false calm, then walls of distorted
guitars. E minor, 72 BPM, ~8 minutes.

Built on the go-to band pipeline (see generate_modern_darkwave_band.py):
FluidSynth sampled instruments per bus, NAM amp captures, Ample Bass in a
Rosetta subprocess, humanized hands over an exactly-gridded... no, not
this time -- the drummer is human here too, and gets looser jitter than
anyone. New tricks for this track:

- Two independently-humanized wall-guitar buses, panned hard and run
  through DIFFERENT amp captures (Orange Rockerverb left, TS-boosted
  JCM2000 lead channel right) -- real double-tracking, not a copied take.
- Lead guitar volume swells via MIDI CC11 ramps (the render engine now
  handles 'cc' events), blooming into a long delay and a church IR.
- A synthesized low-E drone bed (detuned saws + sub sine, slow tremolo)
  that pedals under every chord, faded by section.
- A live-kit drum part on the GM standard kit: ride patterns, ghost
  notes, flams, tom grooves, phrase-end fills, and snare-roll crescendos
  into the walls. Complexity scales with the arrangement.
- Two convolution sends: a damped large room gluing the band, and a
  church wash on lead/pad/drone for the epic halo.
"""

import json
import os
import subprocess
import sys
import tempfile

import numpy as np
from scipy.signal import sawtooth, butter, lfilter
from scipy.io import wavfile

from generate_modern_darkwave_band import load_nam  # also shims libfluidsynth
import fluidsynth
from pedalboard import (Pedalboard, Chorus, Delay, Reverb, Compressor, Gain,
                        HighpassFilter, HighShelfFilter, LowpassFilter, LowShelfFilter, PeakFilter, Mix, Chain,
                        Convolution)

SR = 44100
BPM = 72
BEAT = 60.0 / BPM
BAR = BEAT * 4
SEED = 19

rng = np.random.default_rng(SEED)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SF_PATH = os.path.join(SCRIPT_DIR, "..", "Soundfonts", "GeneralUser-GS.sf2")
OUT_PATH = os.path.join(SCRIPT_DIR, "..", "Tracks", "postrock_epic.wav")
AMPS = os.path.join(SCRIPT_DIR, "..", "Amps")
ROOM_IR = os.path.join(SCRIPT_DIR, "..", "IRs", "Highly Damped Large Room.wav")
CHURCH_IR = os.path.join(SCRIPT_DIR, "..", "IRs", "St Nicolaes Church.wav")
CAB_IR = os.path.join(SCRIPT_DIR, "..", "IRs", "Direct Cabinet N3.wav")
X86_PYTHON = os.path.expanduser("~/.venvs/x86-audio/bin/python")
AMPLE_HELPER = os.path.join(SCRIPT_DIR, "render_ample_bass.py")

CH_ARP, CH_LEAD, CH_WALL, CH_PAD, CH_STR, CH_DRUMS = 0, 1, 2, 3, 4, 9
CLEAN_GUITAR, OVERDRIVE_GUITAR, WARM_PAD, STRINGS = 27, 29, 89, 48

# Drum notes -- match the Brooklyn kit's zone map (3 toms: 43/47/48).
KICK, SNARE, STICK, T_LOW, T_FLR, T_MID, T_HI = 36, 38, 37, 43, 43, 47, 48
RIDE, BELL, CRASH, CRASH2, HH_PEDAL = 51, 53, 49, 57, 44

# Brooklyn Drum Kit Designer kit, extracted from the GarageBand/Logic
# factory library by exs_extract.py: 1705 zones of real multi-velocity
# studio recordings, keyed by MIDI note with velocity-layer ranges.
BROOKLYN_DIR = os.path.join(SCRIPT_DIR, "..", "Samples", "Brooklyn")

# E minor, chords change every 2 bars: Em - C - G - D.
PROG = ["Em", "C", "G", "D"]
CHORDS = {
    "Em": {"bass": 28, "wall": [40, 47, 52], "arp": [52, 55, 59, 64, 67], "pad": [52, 59, 64]},
    "C":  {"bass": 36, "wall": [36, 43, 48], "arp": [48, 52, 55, 60, 64], "pad": [48, 55, 60]},
    "G":  {"bass": 31, "wall": [43, 50, 55], "arp": [50, 55, 59, 62, 67], "pad": [50, 55, 62]},
    "D":  {"bass": 38, "wall": [38, 45, 50], "arp": [50, 54, 57, 62, 66], "pad": [50, 57, 62]},
}

# Lead phrases over one 8-bar chord cycle: (bar, beat, dur_beats, midi).
# One 8-bar phrase, repeated every cycle -- the riff IS the identity.
# Odd bars carry the rhythmic riff cell (two 8ths, quarter, half); even
# bars hold the chord's color tone. Bar 7 walks A-B-D so the downbeat of
# every cycle lands the lead on E5 exactly as the progression resolves.
MELODY_A = [
    (0, 0.0, 3.0, 76), (0, 3.0, 1.0, 74),
    (1, 0.0, 0.5, 76), (1, 0.5, 0.5, 74), (1, 1.0, 1.0, 71), (1, 2.0, 2.0, 67),
    (2, 0.0, 3.0, 72), (2, 3.0, 1.0, 69),
    (3, 0.0, 0.5, 72), (3, 0.5, 0.5, 71), (3, 1.0, 1.0, 69), (3, 2.0, 2.0, 64),
    (4, 0.0, 3.0, 71), (4, 3.0, 1.0, 69),
    (5, 0.0, 0.5, 71), (5, 0.5, 0.5, 69), (5, 1.0, 1.0, 67), (5, 2.0, 2.0, 62),
    (6, 0.0, 3.0, 66), (6, 3.0, 1.0, 67),
    (7, 0.0, 1.0, 69), (7, 1.0, 1.0, 71), (7, 2.0, 2.0, 74),
]
# Same riff DNA an octave up for the final wall: arrives on G5 at each
# resolution, holds each chord's third (F#5 over D is the gut-punch),
# then climbs D-E-F# back home.
MELODY_B = [
    (0, 0.0, 3.0, 79), (0, 3.0, 1.0, 76),
    (1, 0.0, 0.5, 79), (1, 0.5, 0.5, 76), (1, 1.0, 1.0, 74), (1, 2.0, 2.0, 76),
    (2, 0.0, 3.0, 76), (2, 3.0, 1.0, 74),
    (3, 0.0, 0.5, 76), (3, 0.5, 0.5, 74), (3, 1.0, 1.0, 72), (3, 2.0, 2.0, 72),
    (4, 0.0, 4.0, 74),
    (5, 0.0, 0.5, 74), (5, 0.5, 0.5, 72), (5, 1.0, 1.0, 71), (5, 2.0, 2.0, 67),
    (6, 0.0, 3.0, 78), (6, 3.0, 1.0, 74),
    (7, 0.0, 1.0, 74), (7, 1.0, 1.0, 76), (7, 2.0, 2.0, 78),
]

EVENTS = {"arp": [], "gswell": [], "lead": [], "wallL": [], "wallR": [], "wallL2": [], "wallR2": [], "wallF": [], "pad": [], "drums": [], "drums_lofi": []}
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
    every bar, played with just a breath of human drift -- steady enough
    to hypnotize, loose enough to not sound sequenced."""
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


def render_gtr_swell(bar_t, chord):
    """One chord swell spanning the full two bars: the expression curve
    starts at true zero and eases up across ~85% of the phrase (a slow
    volume-knob swell into the amp), while each voice is quietly
    re-struck every half bar underneath so there is always fresh string
    energy for the envelope to reveal -- the plate smears the re-strikes
    into one continuous bloom. The pick attacks live under the silent
    part of the curve, so no strum is heard."""
    tones = [chord["arp"][0], chord["arp"][2], chord["arp"][4]]
    dur = BAR * 2.0
    att = dur * 0.85
    for k in range(16):
        frac = (k / 15) ** 1.6
        add_cc("arp", bar_t + att * k / 15, CH_ARP, 11, int(105 * frac))
    add_cc("arp", bar_t + dur * 0.99, CH_ARP, 11, 12)
    for i, note in enumerate(tones):
        t, v = human(bar_t + 0.03 + i * 0.05, 74, t_sd=0.006, v_sd=3)
        add_note("gswell", t, dur, CH_ARP, note, v)


THIRD_UP = {4: 3, 6: 3, 7: 4, 9: 3, 11: 3, 0: 4, 2: 4}  # E natural minor diatonic thirds
SIXTH_UP = {4: 8, 6: 8, 7: 9, 9: 9, 11: 8, 0: 9, 2: 9}   # diatonic sixths


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
# syncopated D-DU-D-DU figure; 'double' is straight eighths, accents on
# the beats -- the final wall churns.
STRUM_PATTERNS = {
    "sustain": [(0.0, "D", 1.0), (1.0, "D", 0.85), (1.5, "U", 0.7),
                (2.0, "D", 0.95), (3.0, "D", 0.85), (3.5, "U", 0.7)],
    "double":  [(0.0, "D", 1.0), (0.5, "U", 0.7), (1.0, "D", 0.85), (1.5, "U", 0.7),
                (2.0, "D", 0.95), (2.5, "U", 0.7), (3.0, "D", 0.85), (3.5, "U", 0.75)],
}


def render_wall(bar_t, chord, mode, bus):
    """Strummed power chords -- a driving pattern, not held whole notes.
    Downstrokes rake low-to-high, upstrokes snap back high-to-low and
    softer. Note-offs land just short of the next strum so the sampler
    never chops a re-struck string. Each bus still gets independent
    humanization: four distinct performances."""
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
    end of each chord's second bar -- different material, not a double."""
    root = chord["wall"][0] + 12
    for beat_off, dur_b, note in [(2.5, 0.45, root + 12), (3.0, 0.45, root + 10), (3.5, 0.5, root + 12)]:
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


DRUM_BUS = ["drums"]  # switchable target: the lo-fi preview borrows the writer


def drum(t, note, vel, t_sd=0.006, v_sd=8):
    t, vel = human(t, vel, t_sd=t_sd, v_sd=v_sd)
    add_note(DRUM_BUS[0], t, 0.08, CH_DRUMS, note, vel)


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
    under the last bar -- the drummer standing up out of the seat."""
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


def render_drone(total_secs, gain_bp):
    """Low-E pedal drone: detuned saws + sub sine, slow tremolo and a dark
    lowpass, faded between sections via gain breakpoints (bar, gain)."""
    n = int(total_secs * SR)
    t = np.arange(n, dtype=np.float64) / SR
    f = 41.2
    osc = (0.4 * sawtooth(2 * np.pi * f * 0.9965 * t)
           + 0.4 * sawtooth(2 * np.pi * f * 1.0035 * t)
           + 0.5 * np.sin(2 * np.pi * f * t)
           + 0.25 * np.sin(2 * np.pi * f * 2 * t)
           + 0.12 * np.sin(2 * np.pi * f * 3.01 * t))
    b, a = butter(2, 320 / (SR / 2), btype="low")
    osc = lfilter(b, a, osc)
    osc *= 1 + 0.18 * np.sin(2 * np.pi * 0.05 * t)          # slow tremolo
    gain_bp = sorted(gain_bp)
    times = np.array([bp[0] * BAR for bp in gain_bp])
    gains = np.array([bp[1] for bp in gain_bp])
    env = np.interp(t, times, gains)
    sig = (osc * env).astype(np.float32)
    return np.stack([sig, sig])


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
        # Drone alone, a sparse guitar figure surfacing out of it.
        dict(n_bars=2, drone=0.42, pad_gain=0.4, chord="Em", pad_root_only=True),
        # ...then the beat arrives down the hall, pads walking the changes.
        dict(n_bars=8, drone=0.42, lofi_preview="full", pad_gain=0.4),
        # Bass and ride cymbal enter; the bass carries the melody now.
        dict(n_bars=16, drone=0.5, arp="full", bass="melodic", drums="ride", pad_gain=0.15),
        # Lead swells bloom; the kit leans forward, bass keeps walking.
        dict(n_bars=16, drone=0.45, arp="full", bass="melodic", drums="ride2", lead="swell", pad_gain=0.3),
        # The kit opens up, melody states the theme; roll into the wall.
        dict(n_bars=16, drone=0.35, arp="full", bass="build", drums="groove", lead="melodyA", pad_gain=0.4, roll_out=True),
        # FIRST WALL.
        dict(n_bars=16, drone=0.3, bass="drive", drums="big", wall="sustain", pad_gain=0.95),
        # False calm: walls cut dead, floor toms pulse, swells return; roll out.
        dict(n_bars=16, drone=0.45, arp="sparse", bass="long", drums="toms", lead="swell", pad_gain=0.35, roll_out=True),
        # FINAL WALL: double-struck chords, 16th kicks, soaring melody.
        dict(n_bars=24, drone=0.4, bass="drive", drums="big16", wall="double", wall_fills=True, lead="melodyB", pad_gain=1.0),
        # Everything cuts mid-ring: drone and one held pad note on E,
        # a measure to breathe, done.
        dict(n_bars=2, drone=0.55, pad_gain=0.5, chord="Em", pad_root_only=True),
    ]

    total_bars = sum(m["n_bars"] for m in movements)
    total_secs = total_bars * BAR + 10.0
    print(f"{total_bars} bars, {total_secs/60:.1f} minutes")

    drone_bp = [(0, 0.0)]
    bar_cursor = 0
    for m in movements:
        drone_bp.append((bar_cursor + 2, m["drone"]))
        drone_bp.append((bar_cursor + m["n_bars"] - 1, m["drone"]))
        for bar_i in range(m["n_bars"]):
            bar_t = (bar_cursor + bar_i) * BAR
            chord = CHORDS[m["chord"]] if m.get("chord") else CHORDS[PROG[(bar_i // 2) % 4]]
            phrase_bar = bar_i
            if m.get("gtr_swell") and bar_i % 2 == 0:
                render_gtr_swell(bar_t, chord)
                if bar_i == m["n_bars"] - 2:
                    add_cc("arp", (bar_cursor + m["n_bars"]) * BAR - 0.02, CH_ARP, 11, 110)
            if m.get("arp"):
                render_arp(bar_t, chord, m["arp"])
            if m.get("bass"):
                render_bass_bar(bar_t, chord, m["bass"], phrase_bar)
            rolling = m.get("roll_out") and bar_i >= m["n_bars"] - 2
            lofi_from = 0 if m.get("lofi_preview") == "full" else m["n_bars"] // 2
            if m.get("lofi_preview") and bar_i >= lofi_from:
                # the whole second progression cycle: the coming beat,
                # heard through a cheap speaker
                DRUM_BUS[0] = "drums_lofi"
                render_drums_bar(bar_t, "ride", bar_i)
                DRUM_BUS[0] = "drums"
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
    drone_bp.append((total_bars + 2, 0.0))

    print("Rendering buses ...")
    # Real sampled guitars: Warm Electric on the clean bed and left wall,
    # Vintage Strat on the lead and right wall -- different guitars per
    # side, like a real double-tracking session. All sources are CLEAN;
    # the amp captures supply the distortion, which is what keeps the
    # heavy voicing natural.
    warm = ExsSampler(os.path.join(SCRIPT_DIR, "..", "Samples", "WarmElectric"))
    strat = ExsSampler(os.path.join(SCRIPT_DIR, "..", "Samples", "VintageStrat"))
    strat_neck = ExsSampler(os.path.join(SCRIPT_DIR, "..", "Samples", "VintageStrat"), pickup=0.27, deterministic=True)
    gswell_mono = strat_neck.render(EVENTS["gswell"], total_secs, attack=0.3)
    gswell_wash = Pedalboard([
        Reverb(room_size=0.985, damping=0.12, wet_level=1.0, dry_level=0.09, width=0.0),
    ])(np.stack([gswell_mono, gswell_mono]), SR)[0]
    arp_mono = strat_neck.render(EVENTS["arp"], total_secs) + gswell_wash * 1.4
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
    lofi = render_brooklyn(EVENTS["drums_lofi"], total_secs)
    lofi = np.stack([lofi.mean(axis=0)] * 2)  # cheap speakers are mono
    drone = render_drone(total_secs, drone_bp)
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

    # Arp: Tele Deluxe bridge voicing (wide-range humbucker mids, tone
    # knob rolled) into a spotless Twin + real cab IR, drowned in reverb.
    # Strat neck-pickup voicing: notch the quack band, warm the lows,
    # keep the top glassy -- then drown it in a cavernous reverb.
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
    # slow chorus modulation in the wet path only. Dialed back vs the
    # cavernous version.
    plate = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=150),
        Reverb(room_size=0.8, damping=0.15, wet_level=1.0, dry_level=0.0, width=1.0),
        Chorus(rate_hz=0.6, depth=0.25, centre_delay_ms=9.0, mix=0.7),
    ])(arp, SR)
    arp = arp * 0.8 + plate * 0.3
    # Lead: AC15 pushed into real breakup, chorus warble restored.
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
        # clean guitar, breathing with the same slow modulation.
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
    drone_wet = Pedalboard([LowpassFilter(cutoff_frequency_hz=900)])(drone, SR)
    from pedalboard import Bitcrush, Resample
    lofi = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=500),
        LowpassFilter(cutoff_frequency_hz=2400),
        Resample(target_sample_rate=11025),
        Bitcrush(bit_depth=8),
        Compressor(threshold_db=-20, ratio=6, attack_ms=1, release_ms=50),
    ])(lofi, SR)

    bass *= 1.02; drums *= 0.78; arp *= 0.52; lead *= 0.85
    pad *= 0.5; drone_wet *= 0.38
    # Walls as texture, not volume: solve for the gain that lets all five
    # wall layers raise the wall sections by only ~0.2 dB total. They fill
    # the spectrum, not the meter -- and stay calibrated no matter how
    # many takes we stack or how the band levels change.
    base = bass + drums + arp + lead + pad + drone_wet
    walls = wall_l + wall_r + wall_l2 + wall_r2 + wall_f
    active = np.abs(walls).max(axis=0) > 1e-4
    p_base = float((base[:, active] ** 2).mean())
    p_wall = float((walls[:, active] ** 2).mean())
    g = float(np.sqrt((10 ** 0.06 - 1) * p_base / max(p_wall, 1e-12)))
    walls *= g
    print(f"wall texture gain: {g:.3f}")
    dry = base + walls + lofi * 0.5

    rms = lambda a: np.sqrt((a ** 2).mean())
    room_send = (0.65 * drums + 0.5 * (arp + walls) + 0.4 * lead + 0.2 * bass).astype(np.float32)
    room = Convolution(ROOM_IR, mix=1.0)(room_send, SR)
    room *= 0.2 * rms(dry) / max(rms(room), 1e-9)
    church_send = (0.8 * lead + 0.5 * pad + 0.35 * drone_wet + 0.35 * arp).astype(np.float32)
    church = Convolution(CHURCH_IR, mix=1.0)(church_send, SR)
    church *= 0.14 * rms(dry) / max(rms(church), 1e-9)

    master = dry + room + church
    n_samples = master.shape[1]
    fade = int(6.0 * SR)
    env = np.ones(n_samples, dtype=np.float32)
    env[-fade:] = np.linspace(1, 0, fade)
    master *= env
    norm = 0.9 / max(np.abs(master).max(), 1e-9)
    master *= norm

    if "--stems" in sys.argv:
        # Time-aligned stems at final-mix levels: same fade, same master
        # normalization, so importing all at unity gain reproduces the mix.
        stem_dir = os.path.join(SCRIPT_DIR, "..", "Tracks", "postrock_epic Stems")
        os.makedirs(stem_dir, exist_ok=True)
        stems = {
            "01 Bass": bass, "02 Drums": drums, "03 Lofi Drums": lofi * 0.5,
            "04 Clean Guitar": arp, "05 Lead Guitar": lead,
            "06 Wall L Orange": wall_l * g, "07 Wall R JCM2000": wall_r * g,
            "08 Wall Inner L": wall_l2 * g, "09 Wall Inner R": wall_r2 * g,
            "10 Wall Fills": wall_f * g,
            "11 Pads": pad, "12 Drone": drone_wet,
            "13 Room Reverb Return": room, "14 Church Reverb Return": church,
        }
        for name, bus in stems.items():
            out = np.clip(bus * env * norm, -1, 1)
            wavfile.write(os.path.join(stem_dir, f"{name}.wav"), SR,
                          (out.T * 32767).astype(np.int16))
        print(f"wrote {len(stems)} stems to {os.path.normpath(stem_dir)}")

    wavfile.write(OUT_PATH, SR, (master.T * 32767).astype(np.int16))
    print(f"Wrote {os.path.normpath(OUT_PATH)}: {total_secs/60:.1f} min, {total_bars} bars at {BPM} BPM")


if __name__ == "__main__":
    main()
