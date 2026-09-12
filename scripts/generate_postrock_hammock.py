"""The ambient demo transformed into Hammock / pg.lost post-rock, every
voice a real recording -- no GM soundfont anywhere.

The demo (Sources/ambient_demo.mp3) stays the track's heart: its real
fade-in opens, its body loops under everything with 6s equal-power
crossfades, its own fade-out ends the piece. Around it, from the
GarageBand/Logic factory library via exs_extract.py:

- Steinway Grand piano -- the recurring theme, stated alone over the wash,
  returning in the false calm and the afterglow; hammered low octaves
  inside the final wall.
- Mellotron tapes: String Section swells (soft tapes in the builds, loud
  tapes soaring over the walls), Cello under the piano, 8 Choir flooding
  the calms, Flute answering the second statement of the theme.
- Acoustic Guitar fingerpicking in the calms (per-string zone map acts
  as natural round-robin).
- Warm Electric + Vintage Strat, clean into NAM captures: neck-pickup
  arps into the Twin, Hammock volume-swell washes (zero-attack CC curves
  into a wet-only plate), four independently-performed wall guitars
  through four different amps for the pg.lost climaxes.
- Ample Bass (Rosetta) with the dUg grit path; Brooklyn kit drums.

A minor, 68 BPM. Main progression Am-F-C-G; the calms breathe in
F-C-Dm-Am. ~8 minutes.
"""

import json
import os
import subprocess
import tempfile

import numpy as np
from scipy.io import wavfile

from music_engine import (
    DrumSampler as EngineDrumSampler,
    ExsSampler as EngineExsSampler,
    cc_curve as engine_cc_curve,
    load_nam,
    normalize_peak as engine_normalize_peak,
    render_external_instrument,
    stereo as engine_stereo,
)
from pedalboard import (Pedalboard, Chorus, Delay, Reverb, Compressor, Gain,
                        HighpassFilter, HighShelfFilter, LowpassFilter, LowShelfFilter, PeakFilter, Mix, Chain,
                        Convolution)

SR = 44100
BPM = 68  # the demo's own weak internal pulse
BEAT = 60.0 / BPM
BAR = BEAT * 4
SEED = 73

rng = np.random.default_rng(SEED)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(SCRIPT_DIR, "..", "Tracks", "postrock_hammock.wav")
DEMO_MP3 = os.path.join(SCRIPT_DIR, "..", "Sources", "ambient_demo.mp3")
SAMPLES = os.path.join(SCRIPT_DIR, "..", "Samples")
AMPS = os.path.join(SCRIPT_DIR, "..", "Amps")
ROOM_IR = os.path.join(SCRIPT_DIR, "..", "IRs", "Highly Damped Large Room.wav")
CHURCH_IR = os.path.join(SCRIPT_DIR, "..", "IRs", "St Nicolaes Church.wav")
CAB_IR = os.path.join(SCRIPT_DIR, "..", "IRs", "Direct Cabinet N3.wav")
X86_PYTHON = os.path.expanduser("~/.venvs/x86-audio/bin/python")
AMPLE_HELPER = os.path.join(SCRIPT_DIR, "render_ample_bass.py")
BROOKLYN_DIR = os.path.join(SAMPLES, "Brooklyn")

# Drum notes -- match the Brooklyn kit's zone map.
KICK, SNARE, STICK, T_LOW, T_FLR, T_MID, T_HI = 36, 38, 37, 43, 43, 47, 48
RIDE, BELL, CRASH, CRASH2, HH_PEDAL = 51, 53, 49, 57, 44

# Mellotron tape velocity bands: 0-45 = soft tapes, 82-127 = loud tapes.
MELLO_SOFT, MELLO_LOUD = 40, 100

# Two progressions, both fully diatonic to the demo's white-note pool.
# The walls churn on Am-F-C-G; the calms breathe in F-C-Dm-Am.
PROGS = {"main": ["Am", "F", "C", "G"], "calm": ["F", "C", "Dm", "Am"]}
CHORDS = {
    "Am": {"bass": 33, "wall": [45, 52, 57], "arp": [57, 60, 64, 69, 72], "pad": [57, 64, 69], "fill": 10},
    "F":  {"bass": 29, "wall": [41, 48, 53], "arp": [53, 57, 60, 65, 69], "pad": [53, 60, 65], "fill": 11},
    "C":  {"bass": 36, "wall": [48, 55, 60], "arp": [55, 60, 64, 67, 72], "pad": [55, 60, 64], "fill": 11},
    "G":  {"bass": 31, "wall": [43, 50, 55], "arp": [55, 59, 62, 67, 71], "pad": [55, 62, 67], "fill": 10},
    "Dm": {"bass": 38, "wall": [38, 45, 50], "arp": [50, 53, 57, 62, 65], "pad": [50, 57, 62], "fill": 10},
}

# Lead guitar phrases over one 8-bar main cycle: (bar, beat, dur_beats, midi).
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

# The piano theme -- the track's voice, stated over the calm progression
# (F C Dm Am). Same falling DNA as the lead melody, resolving home to A.
PIANO_THEME = [
    (0, 0.0, 3.0, 81), (0, 3.0, 1.0, 79),
    (1, 0.0, 2.0, 77), (1, 2.0, 2.0, 72),
    (2, 0.0, 3.0, 79), (2, 3.0, 1.0, 76),
    (3, 0.0, 4.0, 72),
    (4, 0.0, 3.0, 77), (4, 3.0, 1.0, 74),
    (5, 0.0, 2.0, 74), (5, 2.0, 2.0, 69),
    (6, 0.0, 3.0, 76), (6, 3.0, 1.0, 72),
    (7, 0.0, 4.0, 69),
]

# Mellotron flute answer, second statement of the theme: long lonely notes.
FLUTE_LINE = [
    (0, 2.0, 2.0, 72), (2, 0.0, 3.0, 76), (4, 2.0, 2.0, 74),
    (6, 0.0, 3.0, 72), (7, 0.0, 2.5, 69),
]

THIRD_UP = {9: 3, 11: 3, 0: 4, 2: 3, 4: 3, 5: 4, 7: 4}  # A natural minor
SIXTH_UP = {9: 8, 11: 8, 0: 9, 2: 9, 4: 8, 5: 9, 7: 9}

EVENTS = {k: [] for k in ("arp", "gswell", "lead", "wallL", "wallR", "wallL2", "wallR2", "wallF",
                          "piano", "acoustic", "mstrL", "mstrR", "choir", "cello", "flute", "drums")}
AMPLE_NOTES = []


def human(t, vel, t_sd=0.006, v_sd=8):
    t = max(t + float(np.clip(rng.normal(0, t_sd), -2.5 * t_sd, 2.5 * t_sd)), 0.0)
    vel = int(np.clip(vel + rng.normal(0, v_sd), 1, 127))
    return t, vel


def add_note(bus, t, dur, note, vel, ch=0):
    # ch only disambiguates overlapping same-note voices for the sampler's
    # open-note tracking (e.g. gswell re-strikes); it selects nothing.
    EVENTS[bus].append((int(t * SR), "on", ch, note, vel))
    EVENTS[bus].append((int((t + dur) * SR), "off", ch, note, 0))


def add_cc(bus, t, num, val):
    EVENTS[bus].append((int(t * SR), "cc", 0, num, int(np.clip(val, 0, 127))))


# ---- parts -------------------------------------------------------------------

def render_arp(bar_t, chord, mode):
    """16th-note electric picking, fixed palindrome, breath of drift."""
    step = BEAT / 4
    tones = chord["arp"]
    pattern = [0, 1, 2, 3, 4, 3, 2, 1]
    n = 8 if mode == "sparse" else 16
    stride = 2 if mode == "sparse" else 1
    base_vel = 54 if mode == "sparse" else 62
    for k in range(n):
        t, vel = human(bar_t + k * step * stride, base_vel, t_sd=0.003, v_sd=3)
        add_note("arp", t, step * 2.2, tones[pattern[k % 8]], vel)


def render_acoustic(bar_t, chord):
    """Fingerpicked eighths on the acoustic: thumb alternates root/fifth,
    fingers roll the upper tones -- the calm's heartbeat."""
    tones = chord["arp"]
    pattern = [0, 2, 4, 3, 1, 3, 4, 2]
    for k in range(8):
        t, vel = human(bar_t + k * BEAT / 2, 56 if k % 4 == 0 else 48, t_sd=0.004, v_sd=3)
        add_note("acoustic", t, BEAT * 0.9, tones[pattern[k]], vel)


def render_gswell(bar_t, chord):
    """Hammock signature: a two-bar volume swell. The chord is re-struck
    every half bar under a CC11 curve that starts at true zero and eases
    up across ~85% of the phrase -- no pick attack survives, the plate
    smears the re-strikes into one continuous bloom."""
    tones = [chord["arp"][0], chord["arp"][2], chord["arp"][4]]
    dur = BAR * 2.0
    att = dur * 0.85
    for k in range(16):
        frac = (k / 15) ** 1.6
        add_cc("gswell", bar_t + att * k / 15, 11, int(105 * frac))
    add_cc("gswell", bar_t + dur * 0.99, 11, 8)
    for half in range(4):
        for i, note in enumerate(tones):
            t, v = human(bar_t + half * BAR / 2 + 0.03 + i * 0.05, 74, t_sd=0.006, v_sd=3)
            add_note("gswell", t, dur - half * BAR / 2, note, v, ch=half)


def render_lead_swells(bar_t, chord):
    """A whole-note lead swell blooming out of silence via CC11 ramps."""
    note = chord["pad"][2]
    t, vel = human(bar_t + 0.05, 96, t_sd=0.01)
    dur = BAR * 1.9
    att = dur * 0.65
    for k in range(14):
        add_cc("lead", t + att * k / 13, 11, 25 + 95 * k / 13)
    add_note("lead", t, dur, note, vel)


def render_melody(start_bar, n_bars, phrase, harmonize=False):
    for cyc in range(0, n_bars, 8):
        for bar_off, beat, dur_b, note in phrase:
            if cyc + bar_off >= n_bars:
                continue
            t0 = (start_bar + cyc + bar_off) * BAR + beat * BEAT
            t0, vel = human(t0, 96, t_sd=0.012, v_sd=3)
            add_cc("lead", t0 - 0.01, 11, 115)
            add_note("lead", t0, dur_b * BEAT * 0.97, note, vel)
            if harmonize:
                roll = rng.random()
                if roll < 0.15:
                    pass  # rests -- the lines breathe apart
                elif roll < 0.8:
                    h = note + THIRD_UP.get(note % 12, 3)
                    th, vh = human(t0 + 0.015, 86, t_sd=0.01, v_sd=3)
                    add_note("lead", th, dur_b * BEAT * 0.95, h, vh)
                else:
                    h = note + SIXTH_UP.get(note % 12, 9)
                    th, vh = human(t0 + 0.25 * BEAT, 84, t_sd=0.015, v_sd=3)
                    add_note("lead", th, dur_b * BEAT * 0.75, h, vh)


def render_piano_theme(start_bar, n_bars):
    """The Steinway states the theme: right hand sings it, left hand lays
    root octaves under each chord change."""
    for cyc in range(0, n_bars, 8):
        for bar_off, beat, dur_b, note in PIANO_THEME:
            if cyc + bar_off >= n_bars:
                continue
            t0 = (start_bar + cyc + bar_off) * BAR + beat * BEAT
            t0, vel = human(t0, 64, t_sd=0.010, v_sd=4)
            add_note("piano", t0, dur_b * BEAT * 1.05, note, vel)
        for ch_i in range(4):  # LH: one low octave per chord (every 2 bars)
            if cyc + ch_i * 2 >= n_bars:
                continue
            chord = CHORDS[PROGS["calm"][ch_i]]
            t0 = (start_bar + cyc + ch_i * 2) * BAR
            lo = chord["bass"] + 24
            t, v = human(t0, 52, t_sd=0.012, v_sd=3)
            add_note("piano", t, BAR * 1.9, lo, v)
            t, v = human(t0 + 0.02, 46, t_sd=0.012, v_sd=3)
            add_note("piano", t, BAR * 1.9, lo + 12, v)


def render_piano_chime(bar_t, chord):
    """A single high bell-note riding above the band, once per chord."""
    t, vel = human(bar_t, 58, t_sd=0.012, v_sd=4)
    add_note("piano", t, BAR * 1.8, chord["pad"][2] + 12, vel)


def render_piano_low(bar_t, chord):
    """Hammered low octaves inside the final wall -- percussive weight."""
    root = chord["bass"] + 12
    for b in (0.0, 2.0):
        t, vel = human(bar_t + b * BEAT, 100, t_sd=0.006, v_sd=5)
        add_note("piano", t, BEAT * 1.9, root, vel)
        t2, v2 = human(bar_t + b * BEAT + 0.012, 92, t_sd=0.006, v_sd=5)
        add_note("piano", t2, BEAT * 1.9, root + 12, v2)


def render_mello_strings(bar_t, chord, level):
    """Mellotron String Section, one swell per chord. Soft tapes under the
    builds; loud tapes with the octave doubled over the walls."""
    vel = MELLO_SOFT if level < 0.6 else MELLO_LOUD
    notes = list(chord["pad"])
    if level >= 0.6:
        notes.append(chord["pad"][2] + 12)
    for side, buf in (("mstrL", 0.0), ("mstrR", 0.04)):
        for i, note in enumerate(notes):
            t, v = human(bar_t + buf + i * 0.03, vel, t_sd=0.015, v_sd=2)
            add_note(side, t, BAR * 1.92, note, v)


def render_choir(bar_t, chord, level):
    """Mellotron 8 Choir: the top two chord voices, swelling."""
    vel = MELLO_SOFT if level < 0.6 else MELLO_LOUD
    notes = chord["pad"][1:]
    if level >= 0.6:
        notes = notes + [chord["pad"][0] + 12]
    for i, note in enumerate(notes):
        t, v = human(bar_t + 0.05 + i * 0.04, vel, t_sd=0.02, v_sd=2)
        add_note("choir", t, BAR * 1.9, note, v)


def render_cello(bar_t, chord, level):
    """Mellotron cello pedals the root under the piano."""
    note = chord["pad"][0] if chord["pad"][0] >= 53 else chord["pad"][0] + 12
    vel = MELLO_SOFT if level < 0.6 else MELLO_LOUD
    t, v = human(bar_t + 0.03, vel, t_sd=0.015, v_sd=2)
    add_note("cello", t, BAR * 1.9, note, v)


STRUM_PATTERNS = {
    "sustain": [(0.0, "D", 1.0), (1.0, "D", 0.85), (1.5, "U", 0.7),
                (2.0, "D", 0.95), (3.0, "D", 0.85), (3.5, "U", 0.7)],
    "double":  [(0.0, "D", 1.0), (0.5, "U", 0.7), (1.0, "D", 0.85), (1.5, "U", 0.7),
                (2.0, "D", 0.95), (2.5, "U", 0.7), (3.0, "D", 0.85), (3.5, "U", 0.75)],
}


def render_wall(bar_t, chord, mode, bus):
    """Strummed power chords, four independently-humanized performances."""
    pattern = STRUM_PATTERNS[mode]
    for si, (beat_off, direction, accent) in enumerate(pattern):
        nxt = pattern[si + 1][0] if si + 1 < len(pattern) else 4.0
        dur = (nxt - beat_off) * BEAT * 0.92
        vel_base = int(112 * accent)
        notes = list(chord["wall"])
        if mode == "double" and beat_off in (0.0, 2.0):
            notes.append(notes[-1] + 12)
        order = notes if direction == "D" else list(reversed(notes))
        stagger = 0.014 if direction == "D" else 0.009
        vel_adj = 0 if direction == "D" else -10
        for i, note in enumerate(order):
            t, vel = human(bar_t + beat_off * BEAT + i * stagger, vel_base + vel_adj, t_sd=0.006, v_sd=5)
            add_note(bus, t, dur, note, vel)


def render_wall_fills(bar_t, chord):
    """Quick octave fills answering at the end of each chord's second bar;
    the neighbor tone is the chord's own diatonic step."""
    root = chord["wall"][0] + 12
    for beat_off, dur_b, note in [(2.5, 0.45, root + 12), (3.0, 0.45, root + chord["fill"]), (3.5, 0.5, root + 12)]:
        t, vel = human(bar_t + beat_off * BEAT, 106, t_sd=0.008, v_sd=5)
        add_note("wallF", t, dur_b * BEAT, note, vel)
        t2, v2 = human(bar_t + beat_off * BEAT, 96, t_sd=0.009, v_sd=5)
        add_note("wallF", t2, dur_b * BEAT, note - 12, v2)


def render_bass_bar(bar_t, chord, mode, phrase_bar=0):
    root = chord["bass"]
    if mode == "long":
        t, vel = human(bar_t, 92, t_sd=0.006)
        AMPLE_NOTES.append({"t": t, "dur": BAR * 0.95, "note": root, "vel": vel})
    elif mode == "melodic":
        if phrase_bar % 2 == 0:
            notes = [(0.0, 3.8, root)]
        else:
            top = root + (10 if rng.random() < 0.3 else 12)
            notes = [(0.0, 1.9, root), (2.0, 0.95, root + 7), (3.0, 0.9, top)]
        for beat_off, dur_b, note in notes:
            t, vel = human(bar_t + beat_off * BEAT, 94, t_sd=0.006)
            AMPLE_NOTES.append({"t": t, "dur": dur_b * BEAT, "note": note, "vel": vel})
    elif mode == "build":
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
    add_note("drums", t, 0.08, note, vel)


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
        if phrase_bar % 8 == 7:
            drum(bar_t + 3.5 * BEAT, T_MID, 62)
            drum(bar_t + 3.75 * BEAT, T_LOW, 58)

    elif mode == "ride2":
        for k in range(8):
            drum(bar_t + k * BEAT / 2, RIDE, 60 if k % 2 else 68)
        for b in (0.75, 2.75):
            drum(bar_t + b * BEAT, RIDE, 42)
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
        if rng.random() < 0.85:
            drum(bar_t + rng.choice([1.75, 2.25, 3.75]) * BEAT, SNARE, 26, v_sd=4)
        if rng.random() < 0.4:
            drum(bar_t + 1.75 * BEAT, KICK, 80)
        if phrase_bar % 8 == 0:
            drum(bar_t, CRASH, 96)
        if phrase_bar % 4 == 3 and phrase_bar % 8 != 7:
            drum(bar_t + 3.5 * BEAT, SNARE, 70)
            drum(bar_t + 3.75 * BEAT, T_MID, 74)
        if phrase_bar % 8 == 7:
            for j, tom in enumerate([SNARE, T_HI, T_MID, T_MID, T_LOW, T_LOW, T_FLR, T_FLR]):
                drum(bar_t + (2 + j * 0.25) * BEAT, tom, 78 + j * 3)

    elif mode == "toms":
        for b, tom, v in [(0.0, T_FLR, 82), (0.75, T_FLR, 60), (1.5, T_LOW, 74),
                          (2.0, T_FLR, 82), (2.75, T_FLR, 60), (3.5, T_LOW, 70)]:
            drum(bar_t + b * BEAT, tom, v)
        drum(bar_t + 1.0 * BEAT, HH_PEDAL, 50)
        drum(bar_t + 3.0 * BEAT, HH_PEDAL, 50)

    elif mode in ("big", "big16"):
        crash = CRASH if phrase_bar % 2 == 0 else CRASH2
        drum(bar_t, crash, 104)
        if phrase_bar % 2 == 0:
            drum(bar_t + 2 * BEAT, CRASH2, 80)
        kicks = np.arange(0, 4, 0.5) if mode == "big16" else [0.0, 1.5, 2.0, 3.5]
        for b in kicks:
            drum(bar_t + b * BEAT, KICK, 106 if b % 1 == 0 else 96)
        for b in (1.0, 3.0):
            drum(bar_t + (b - 0.25) * BEAT, SNARE, 42)
            drum(bar_t + b * BEAT - 0.03, SNARE, 74)
            drum(bar_t + b * BEAT, SNARE, 118)
        for k in range(8):
            drum(bar_t + k * BEAT / 2, RIDE, 72)
        if phrase_bar % 8 == 7:
            for j, tom in enumerate([T_HI, T_HI, T_MID, T_MID, T_LOW, T_FLR, SNARE, SNARE]):
                drum(bar_t + (2 + j * 0.25) * BEAT, tom, 84 + j * 3)


def render_roll(bar_t):
    """Two-bar full-kit crescendo: snare 16ths densify into 32nds, kick
    quarters drive into eighths with floor tom, crash swell underneath."""
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
    """The demo itself as the drone layer: real fade-in at the top, body
    (12s-133s) looping with 6s equal-power crossfades, its own fade-out
    placed to end the track. Gain breakpoints duck it under the band."""
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


class ExsSampler:
    """Pitched playback of an extracted EXS instrument: zone selection by
    note and velocity (same-range zones act as round-robins), linear-
    interpolation resampling to exact pitch, natural sample decay with a
    release fade at note-off. `groups` filters the zone map by group-name
    substring -- how one Mellotron extraction serves as strings, cello,
    choir and flute, and how the acoustic guitar drops its palm-mute zones."""

    def __init__(self, sample_dir, pickup=None, deterministic=False, groups=None):
        self.dir = sample_dir
        self.pickup = pickup
        self.deterministic = deterministic
        with open(os.path.join(sample_dir, "manifest.json")) as f:
            self.zones = json.load(f)
        if groups:
            self.zones = [z for z in self.zones if any(g in z.get("group", "") for g in groups)]
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
    n = int(total_secs * SR)
    pts_t, pts_v = [0], [110 / 127]
    for ev in sorted(events, key=lambda e: e[0]):
        if ev[1] == "cc" and ev[3] == 11:
            pts_t.append(ev[0])
            pts_v.append(ev[4] / 127)
    return np.interp(np.arange(n), pts_t, pts_v).astype(np.float32)


def norm_peak(bus, target):
    return bus / max(np.abs(bus).max(), 1e-9) * target


def render_brooklyn(events, total_secs):
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
        z = matches[int(rng.integers(len(matches)))]
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


# Shared-engine compatibility layer.  The names stay stable for older scripts
# that import them from this module, while all new rendering runs through
# music_engine.
ExsSampler = EngineExsSampler
stereo = engine_stereo


def cc11_curve(events, total_secs):
    return engine_cc_curve(events, total_secs, sample_rate=SR)


def norm_peak(bus, target):
    return engine_normalize_peak(bus, target)


_brooklyn_sampler = EngineDrumSampler(
    BROOKLYN_DIR,
    sample_rate=SR,
    rng=rng,
    output_gain=1.3,
)


def render_brooklyn(events, total_secs):
    return _brooklyn_sampler.render(events, total_secs)


def render_ample_bass(total_secs):
    return render_external_instrument(
        AMPLE_NOTES,
        total_secs,
        python_path=X86_PYTHON,
        helper_path=AMPLE_HELPER,
        sample_rate=SR,
        architecture="x86_64",
        label="Ample Bass",
    )


# ---- arrangement --------------------------------------------------------------

def main():
    movements = [
        # I. The demo's real fade-in, alone.
        dict(n_bars=4, bed=1.0, prog="calm"),
        # II. The piano states the theme over the wash; a cello shadow.
        dict(n_bars=8, bed=0.85, prog="calm", piano="theme", cello=0.4),
        # III. Second statement: swell-guitars bloom, the flute answers.
        dict(n_bars=8, bed=0.75, prog="calm", piano="theme", gswell=True, flute=True, cello=0.4),
        # IV. The band arrives: acoustic picking, bass, ride, soft strings.
        dict(n_bars=16, bed=0.6, prog="main", arp="full", acoustic=True, bass="melodic",
             drums="ride", strings=0.35, piano="chime"),
        # V. Leaning forward: lead swells, busier kit, swell washes return.
        dict(n_bars=16, bed=0.55, prog="main", arp="full", bass="melodic", drums="ride2",
             lead="swell", strings=0.45, gswell=True, piano="chime"),
        # VI. The theme on electric, kit opens, momentum gathers; roll in.
        dict(n_bars=16, bed=0.5, prog="main", arp="full", bass="build", drums="groove",
             lead="melodyA", strings=0.5, roll_out=True),
        # VII. FIRST WALL: loud tapes soar over four guitar stacks.
        dict(n_bars=16, bed=0.4, prog="main", bass="drive", drums="big", wall="sustain",
             strings=1.0, choir=0.4),
        # VIII. False calm: the wash floods back; choir, piano, floor toms.
        dict(n_bars=16, bed=0.85, prog="calm", piano="theme", acoustic=True, bass="long",
             drums="toms", choir=0.45, cello=0.4, gswell=True, roll_out=True),
        # IX. FINAL WALL: 16th kicks, harmonized melody, choir and strings
        # at full sail, the Steinway hammering low octaves inside it.
        dict(n_bars=24, bed=0.45, prog="main", bass="drive", drums="big16", wall="double",
             wall_fills=True, lead="melodyB", harmonize=True, strings=1.0, choir=1.0, piano="low"),
        # X. Afterglow: the theme once more, almost alone.
        dict(n_bars=8, bed=0.9, prog="calm", piano="theme", cello=0.4, choir=0.35),
        # XI. The demo's own fade-out ends the track.
        dict(n_bars=4, bed=1.0, prog="calm"),
    ]

    total_bars = sum(m["n_bars"] for m in movements)
    total_secs = total_bars * BAR + 2.0
    print(f"{total_bars} bars, {total_secs/60:.1f} minutes")

    bed_bp = [(0, 1.0)]
    bar_cursor = 0
    for m in movements:
        bed_bp.append((bar_cursor + 1.5, m["bed"]))
        bed_bp.append((bar_cursor + m["n_bars"] - 0.5, m["bed"]))
        prog = PROGS[m.get("prog", "main")]
        for bar_i in range(m["n_bars"]):
            bar_t = (bar_cursor + bar_i) * BAR
            chord = CHORDS[prog[(bar_i // 2) % 4]]
            chord_start = bar_i % 2 == 0
            phrase_bar = bar_i
            if m.get("arp"):
                render_arp(bar_t, chord, m["arp"])
            if m.get("acoustic"):
                render_acoustic(bar_t, chord)
            if m.get("gswell") and chord_start:
                render_gswell(bar_t, chord)
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
            if m.get("lead") == "swell" and chord_start:
                render_lead_swells(bar_t, chord)
            if m.get("strings") and chord_start:
                render_mello_strings(bar_t, chord, m["strings"])
            if m.get("choir") and chord_start:
                render_choir(bar_t, chord, m["choir"])
            if m.get("cello") and chord_start:
                render_cello(bar_t, chord, m["cello"])
            if m.get("piano") == "chime" and chord_start:
                render_piano_chime(bar_t, chord)
            if m.get("piano") == "low":
                render_piano_low(bar_t, chord)
        if m.get("piano") == "theme":
            render_piano_theme(bar_cursor, m["n_bars"])
        if m.get("flute"):
            for cyc in range(0, m["n_bars"], 8):
                for bar_off, beat, dur_b, note in FLUTE_LINE:
                    if cyc + bar_off >= m["n_bars"]:
                        continue
                    t, v = human((bar_cursor + cyc + bar_off) * BAR + beat * BEAT, MELLO_SOFT,
                                 t_sd=0.02, v_sd=2)
                    add_note("flute", t, dur_b * BEAT, note, v)
        if m.get("roll_out"):
            render_roll((bar_cursor + m["n_bars"] - 2) * BAR)
        if m.get("lead") in ("melodyA", "melodyB"):
            render_melody(bar_cursor, m["n_bars"], MELODY_A if m["lead"] == "melodyA" else MELODY_B,
                          harmonize=m.get("harmonize", False))
        bar_cursor += m["n_bars"]

    print("Rendering buses ...")
    warm = ExsSampler(os.path.join(SAMPLES, "WarmElectric"), rng=rng)
    strat = ExsSampler(os.path.join(SAMPLES, "VintageStrat"), rng=rng)
    strat_neck = ExsSampler(
        os.path.join(SAMPLES, "VintageStrat"),
        rng=rng,
        pickup=0.27,
        deterministic=True,
    )
    strat_lead = ExsSampler(
        os.path.join(SAMPLES, "VintageStrat"),
        rng=rng,
        deterministic=True,
    )
    piano_smp = ExsSampler(os.path.join(SAMPLES, "SteinwayPiano"), rng=rng)
    acoustic_smp = ExsSampler(
        os.path.join(SAMPLES, "AcousticGuitar"),
        rng=rng,
        groups=["Main"],
    )
    mello = os.path.join(SAMPLES, "Mellotron")
    mstr_smp = ExsSampler(mello, rng=rng, groups=["String Section"])
    cello_smp = ExsSampler(mello, rng=rng, groups=["Cello"])
    choir_smp = ExsSampler(mello, rng=rng, groups=["8 Choir"])
    flute_smp = ExsSampler(mello, rng=rng, groups=["Flute"])

    arp = stereo(strat_neck.render(EVENTS["arp"], total_secs), pan=-0.25)
    gswell_mono = strat_neck.render(EVENTS["gswell"], total_secs, attack=0.3)
    gswell = stereo(gswell_mono * cc11_curve(EVENTS["gswell"], total_secs), pan=0.15)
    lead_mono = strat_lead.render(EVENTS["lead"], total_secs)
    lead = stereo(lead_mono * cc11_curve(EVENTS["lead"], total_secs), pan=0.2)
    wall_l = stereo(warm.render(EVENTS["wallL"], total_secs), pan=-0.85)
    wall_r = stereo(strat.render(EVENTS["wallR"], total_secs), pan=0.85)
    wall_l2 = stereo(strat.render(EVENTS["wallL2"], total_secs), pan=-0.45)
    wall_r2 = stereo(warm.render(EVENTS["wallR2"], total_secs), pan=0.45)
    wall_f = stereo(warm.render(EVENTS["wallF"], total_secs), pan=0.1)
    piano = stereo(piano_smp.render(EVENTS["piano"], total_secs), pan=-0.12)
    acoustic = stereo(acoustic_smp.render(EVENTS["acoustic"], total_secs), pan=0.35)
    # Two independent string renders (round-robin tape picks) panned wide:
    # a section, not a sampler.
    mstr = (stereo(mstr_smp.render(EVENTS["mstrL"], total_secs, attack=0.7), pan=-0.5)
            + stereo(mstr_smp.render(EVENTS["mstrR"], total_secs, attack=0.7), pan=0.5))
    choir = stereo(choir_smp.render(EVENTS["choir"], total_secs, attack=0.6), pan=0.0)
    cello = stereo(cello_smp.render(EVENTS["cello"], total_secs, attack=0.5), pan=-0.3)
    flute = stereo(flute_smp.render(EVENTS["flute"], total_secs, attack=0.25), pan=0.25)

    arp = norm_peak(arp, 0.30)
    gswell = norm_peak(gswell, 0.35)
    lead = norm_peak(lead, 0.40)
    wall_l = norm_peak(wall_l, 0.55)
    wall_r = norm_peak(wall_r, 0.55)
    wall_l2 = norm_peak(wall_l2, 0.5)
    wall_r2 = norm_peak(wall_r2, 0.5)
    wall_f = norm_peak(wall_f, 0.5)

    drums = render_brooklyn(EVENTS["drums"], total_secs)
    bed = render_ambient_bed(total_secs, bed_bp)
    bass = render_ample_bass(total_secs)
    if bass is None:
        raise SystemExit("Ample bass required for this one -- helper failed")

    print("Applying effects ...")
    twin = load_nam(os.path.join(AMPS, "Fender_TwinVerb_Clean.nam"))
    twin.input_db = -4.0
    twin.output_db = 20.0
    twin2 = load_nam(os.path.join(AMPS, "Fender_TwinVerb_Clean.nam"))
    twin2.input_db = -4.0
    twin2.output_db = 20.0
    ac15_lead = load_nam(os.path.join(AMPS, "Vox_AC15_TopBoost.nam")); ac15_lead.input_db = 0.0
    orange = load_nam(os.path.join(AMPS, "Orange_Rockerverb.nam")); orange.input_db = 0.0
    jcm = load_nam(os.path.join(AMPS, "JCM2000_Lead_Boosted.nam")); jcm.input_db = 0.0
    jcm9 = load_nam(os.path.join(AMPS, "JCM900_ChB_G12.nam")); jcm9.input_db = 0.0
    dug = load_nam(os.path.join(AMPS, "Tech21_dUg_BassPreamp.nam")); dug.input_db = -6.0

    # Clean arp: neck-pickup voicing into a spotless Twin + real cab.
    arp = Pedalboard([
        PeakFilter(cutoff_frequency_hz=1000, gain_db=-4.5, q=1.1),
        LowShelfFilter(cutoff_frequency_hz=220, gain_db=2.0),
        LowpassFilter(cutoff_frequency_hz=5000),
        twin,
        Convolution(CAB_IR, mix=1.0),
        Gain(gain_db=16.0),
        LowpassFilter(cutoff_frequency_hz=5600),
        Delay(delay_seconds=BEAT * 0.75, feedback=0.25, mix=0.1),
    ])(arp, SR)
    plate = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=150),
        Reverb(room_size=0.8, damping=0.15, wet_level=1.0, dry_level=0.0, width=1.0),
        Chorus(rate_hz=0.6, depth=0.25, centre_delay_ms=9.0, mix=0.7),
    ])(arp, SR)
    arp = arp * 0.8 + plate * 0.3
    # Hammock wash: the swell bus through the same Twin, then a long
    # dotted delay into a wet-only cavern -- pure bloom, no attack.
    gswell = Pedalboard([
        PeakFilter(cutoff_frequency_hz=1000, gain_db=-4.5, q=1.1),
        LowpassFilter(cutoff_frequency_hz=4800),
        twin2,
        Convolution(CAB_IR, mix=1.0),
        Gain(gain_db=16.0),
        Delay(delay_seconds=BEAT * 1.5, feedback=0.45, mix=0.35),
        Reverb(room_size=0.985, damping=0.12, wet_level=0.85, dry_level=0.25, width=1.0),
    ])(gswell, SR)
    lead = Pedalboard([
        Chorus(rate_hz=1.35, depth=0.25, centre_delay_ms=14.0, mix=0.5), ac15_lead,
        Delay(delay_seconds=BEAT * 1.0, feedback=0.45, mix=0.3),
        Reverb(room_size=0.9, damping=0.4, wet_level=0.3, dry_level=0.7),
    ])(lead, SR)
    wall_fx = lambda amp: Pedalboard([
        HighpassFilter(cutoff_frequency_hz=82), amp,
    ])

    def wall_space(bus):
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

    # Steinway: intimate close voice, plate behind it.
    piano = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=45),
        Compressor(threshold_db=-24, ratio=2.5, attack_ms=12, release_ms=180),
        Reverb(room_size=0.86, damping=0.35, wet_level=0.3, dry_level=0.75, width=1.0),
    ])(piano, SR)
    acoustic = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=90),
        Compressor(threshold_db=-22, ratio=2.5, attack_ms=8, release_ms=140),
        Reverb(room_size=0.6, damping=0.5, wet_level=0.16, dry_level=0.88),
    ])(acoustic, SR)
    # Mellotron tapes: keep the wobble, clear the mud, set them deep.
    mstr = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=110),
        LowpassFilter(cutoff_frequency_hz=7500),
        Chorus(rate_hz=0.3, depth=0.2, centre_delay_ms=16.0, mix=0.25),
        Reverb(room_size=0.9, damping=0.4, wet_level=0.32, dry_level=0.7),
    ])(mstr, SR)
    choir = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=180),
        LowpassFilter(cutoff_frequency_hz=6800),
        Reverb(room_size=0.92, damping=0.35, wet_level=0.4, dry_level=0.65),
    ])(choir, SR)
    cello = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=58),
        LowpassFilter(cutoff_frequency_hz=4200),
        Reverb(room_size=0.8, damping=0.5, wet_level=0.22, dry_level=0.8),
    ])(cello, SR)
    flute = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=220),
        Delay(delay_seconds=BEAT * 1.5, feedback=0.35, mix=0.22),
        Reverb(room_size=0.9, damping=0.3, wet_level=0.35, dry_level=0.7),
    ])(flute, SR)
    bass = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=32),
        Mix([Chain([Gain(gain_db=0.0)]), Chain([dug, Gain(gain_db=-10.0)])]),
        Compressor(threshold_db=-18, ratio=4, attack_ms=6, release_ms=120),
    ])(bass, SR)
    drums = Pedalboard([
        Compressor(threshold_db=-14, ratio=3, attack_ms=5, release_ms=220),
        PeakFilter(cutoff_frequency_hz=3000, gain_db=-3.5, q=0.9),
        HighShelfFilter(cutoff_frequency_hz=9000, gain_db=-1.5),
    ])(drums, SR)
    bed = Pedalboard([HighpassFilter(cutoff_frequency_hz=65)])(bed, SR)

    bass *= 1.02; drums *= 0.78; arp *= 0.52; lead *= 0.85; gswell *= 0.5
    piano *= 0.8; acoustic *= 0.55; mstr *= 0.5; choir *= 0.42; cello *= 0.48
    flute *= 0.4; bed *= 0.5
    # Walls as texture, not volume: gain-solve so the five wall layers add
    # only ~0.2 dB to the wall sections.
    base = (bass + drums + arp + lead + gswell + piano + acoustic
            + mstr + choir + cello + flute + bed)
    walls = wall_l + wall_r + wall_l2 + wall_r2 + wall_f
    active = np.abs(walls).max(axis=0) > 1e-4
    p_base = float((base[:, active] ** 2).mean())
    p_wall = float((walls[:, active] ** 2).mean())
    g = float(np.sqrt((10 ** 0.06 - 1) * p_base / max(p_wall, 1e-12)))
    walls *= g
    print(f"wall texture gain: {g:.3f}")
    dry = base + walls

    rms = lambda a: np.sqrt((a ** 2).mean())
    room_send = (0.65 * drums + 0.5 * (arp + walls) + 0.4 * (lead + acoustic)
                 + 0.3 * piano + 0.2 * bass).astype(np.float32)
    room = Convolution(ROOM_IR, mix=1.0)(room_send, SR)
    room *= 0.2 * rms(dry) / max(rms(room), 1e-9)
    church_send = (0.8 * lead + 0.6 * (mstr + gswell) + 0.8 * choir + 0.7 * flute
                   + 0.35 * (piano + arp) + 0.2 * bed).astype(np.float32)
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
