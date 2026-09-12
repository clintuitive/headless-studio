"""THE QUIET HOURS -- an album of twelve Steinway pieces for reading and
driving. Just piano, with Mellotron tape strings folded gently under
about half the tracks. Soothing, melodic, background-friendly.

One composition engine, twelve hand-written track specs. Each track has
its own key, mode, tempo, meter, progressions, and an 8-bar hook with a
distinct rhythmic identity. Shared form gives every piece movements:

  intro (LH alone) -> A (theme) -> A2 (theme again, strings enter,
  fuller LH) -> breath -> B (contrast phrase) -> breath -> A3 (theme an
  octave up with added thirds, fullest) -> outro (a fragment, slowing)

Long tracks add a second B and a final A. Everything is diatonic to the
track's mode; melodies are written in scale degrees and realized against
the key, so each piece is consonant by construction. Tracks are
loudness-matched so the album plays evenly.

Output: Tracks/The Quiet Hours/NN Title.wav
"""

import os

import numpy as np
from scipy.io import wavfile

from music_engine import ExsSampler, stereo

SR = 44100
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLES = os.path.join(SCRIPT_DIR, "..", "Samples")
OUT_DIR = os.path.join(SCRIPT_DIR, "..", "Tracks", "The Quiet Hours")
ROOM_IR = os.path.join(SCRIPT_DIR, "..", "IRs", "Highly Damped Large Room.wav")

MODES = {"ion": [0, 2, 4, 5, 7, 9, 11], "dor": [0, 2, 3, 5, 7, 9, 10],
         "aeo": [0, 2, 3, 5, 7, 8, 10], "lyd": [0, 2, 4, 6, 7, 9, 11],
         "mix": [0, 2, 4, 5, 7, 9, 10]}

# ---- the twelve tracks --------------------------------------------------------
# hook/hook_b: (bar, beat, dur_beats, scale_degree). Degrees are relative
# to the tonic; 7 = the octave. prog: one chord degree per bar, cycled.

TRACKS = [
    dict(num=1, title="First Light", root=0, mode="ion", bpm=66, meter=4,
         lh="drift", strings=None, long=False,
         prog_a=[0, 4, 5, 3], prog_b=[3, 4, 0, 4],
         hook=[(0,0,2,0),(0,2,2,1),(1,0,2,2),(1,2,2,4),(2,0,3,4),(2,3,1,3),(3,0,4,4),
               (4,0,2,7),(4,2,2,8),(5,0,2,9),(5,2,2,11),(6,0,3,10),(6,3,1,9),(7,0,4,7)],
         hook_b=[(0,0,2,5),(0,2,1,4),(0,3,1,3),(1,0,3,4),(1,3,1,2),(2,0,2,2),(2,2,2,4),(3,0,4,4),
                 (4,0,2,5),(4,2,1,6),(4,3,1,5),(5,0,3,6),(5,3,1,4),(6,0,2,7),(6,2,2,8),(7,0,4,7)]),

    dict(num=2, title="Slow Rain", root=9, mode="aeo", bpm=60, meter=4,
         lh="arp", strings=("Cello", 36), long=False,
         prog_a=[0, 5, 2, 6], prog_b=[3, 2, 5, 4],
         hook=[(0,0,0.5,7),(0,0.5,0.5,6),(0,1,1,5),(0,2,2,4),(1,0,0.5,5),(1,0.5,0.5,4),(1,1,1,2),(1,2,2,0),
               (2,0,0.5,4),(2,0.5,0.5,2),(2,1,1,1),(2,2,2,2),(3,0,4,2),
               (4,0,0.5,7),(4,0.5,0.5,6),(4,1,1,5),(4,2,2,4),(5,0,0.5,5),(5,0.5,0.5,4),(5,1,1,2),(5,2,2,4),
               (6,0,0.5,4),(6,0.5,0.5,5),(6,1,1,6),(6,2,2,4),(7,0,4,7)],
         hook_b=[(0,0,3,5),(0,3,1,4),(1,0,3,4),(1,3,1,2),(2,0,2,4),(2,2,2,5),(3,0,4,6),
                 (4,0,3,5),(4,3,1,4),(5,0,3,2),(5,3,1,1),(6,0,2,2),(6,2,2,1),(7,0,4,0)]),

    dict(num=3, title="Window Seat", root=7, mode="ion", bpm=72, meter=4,
         lh="drift", strings=("String Section", 38), long=False,
         prog_a=[0, 4, 5, 3], prog_b=[3, 0, 1, 4],
         hook=[(0,0,1,4),(0,1,1,5),(0,2,2,6),(1,0,1,5),(1,1,1,4),(1,2,2,2),(2,0,1,4),(2,1,1,6),(2,2,2,7),(3,0,4,4),
               (4,0,1,4),(4,1,1,5),(4,2,2,6),(5,0,1,7),(5,1,1,6),(5,2,2,5),(6,0,2,7),(6,2,2,8),(7,0,4,7)],
         hook_b=[(0,0,2,9),(0,2,2,7),(1,0,4,6),(2,0,2,7),(2,2,2,8),(3,0,4,6),
                 (4,0,2,5),(4,2,2,4),(5,0,4,2),(6,0,2,4),(6,2,2,5),(7,0,4,4)]),

    dict(num=4, title="Mile Markers", root=2, mode="dor", bpm=76, meter=4,
         lh="arp", strings=("Cello", 34), long=True,
         prog_a=[0, 5, 3, 4], prog_b=[5, 3, 0, 4],
         hook=[(0,0,1,4),(0,1,1,5),(0,2,1,4),(0,3,1,2),(1,0,2,4),(1,2,2,5),
               (2,0,1,7),(2,1,1,6),(2,2,1,5),(2,3,1,4),(3,0,4,2),
               (4,0,1,4),(4,1,1,5),(4,2,1,4),(4,3,1,6),(5,0,2,7),(5,2,2,8),
               (6,0,1,7),(6,1,1,6),(6,2,2,5),(7,0,4,4)],
         hook_b=[(0,0,2,9),(0,2,2,8),(1,0,4,7),(2,0,2,8),(2,2,2,9),(3,0,4,7),
                 (4,0,2,5),(4,2,2,6),(5,0,4,4),(6,0,2,2),(6,2,2,4),(7,0,4,4)]),

    dict(num=5, title="Paper Boats", root=2, mode="dor", bpm=63, meter=3,
         lh="waltz", strings=("3 Violins", 34), long=False,
         prog_a=[0, 3, 0, 4], prog_b=[5, 3, 6, 4],
         hook=[(0,0,1,4),(0,1,2,5),(1,0,1,4),(1,1,2,2),(2,0,1,4),(2,1,1,5),(2,2,1,6),(3,0,3,4),
               (4,0,1,7),(4,1,2,8),(5,0,1,7),(5,1,2,5),(6,0,1,4),(6,1,1,2),(6,2,1,1),(7,0,3,0)],
         hook_b=[(0,0,2,9),(0,2,1,8),(1,0,3,7),(2,0,2,8),(2,2,1,7),(3,0,3,6),
                 (4,0,2,5),(4,2,1,4),(5,0,3,4),(6,0,1,2),(6,1,1,3),(6,2,1,4),(7,0,3,4)]),

    dict(num=6, title="The Small Hours", root=4, mode="aeo", bpm=55, meter=4,
         lh="wide", strings=("Cello", 34), long=False,
         prog_a=[0, 5, 0, 4], prog_b=[3, 5, 1, 4],
         hook=[(0,0,4,4),(1,0,3,2),(1,3,1,0),(2,0,4,2),(3,0,3,1),(3,3,1,2),
               (4,0,4,4),(5,0,3,5),(5,3,1,4),(6,0,4,2),(7,0,4,0)],
         hook_b=[(0,0,4,5),(1,0,3,4),(1,3,1,5),(2,0,4,6),(3,0,4,4),
                 (4,0,4,3),(5,0,3,2),(5,3,1,3),(6,0,4,4),(7,0,4,2)]),

    dict(num=7, title="Northbound", root=2, mode="ion", bpm=78, meter=4,
         lh="arp", strings=("String Section", 36), long=True,
         prog_a=[0, 4, 3, 4], prog_b=[5, 4, 3, 4],
         hook=[(0,0,0.5,4),(0,0.5,0.5,5),(0,1,1,6),(0,2,2,7),(1,0,0.5,6),(1,0.5,0.5,5),(1,1,1,6),(1,2,2,4),
               (2,0,0.5,5),(2,0.5,0.5,6),(2,1,1,7),(2,2,2,8),(3,0,4,6),
               (4,0,0.5,4),(4,0.5,0.5,5),(4,1,1,6),(4,2,2,7),(5,0,0.5,8),(5,0.5,0.5,7),(5,1,1,8),(5,2,2,9),
               (6,0,2,8),(6,2,2,6),(7,0,4,7)],
         hook_b=[(0,0,3,9),(0,3,1,8),(1,0,3,7),(1,3,1,8),(2,0,2,9),(2,2,2,10),(3,0,4,8),
                 (4,0,3,7),(4,3,1,6),(5,0,3,5),(5,3,1,6),(6,0,2,7),(6,2,2,5),(7,0,4,4)]),

    dict(num=8, title="Marginalia", root=5, mode="ion", bpm=68, meter=4,
         lh="drift", strings=None, long=False,
         prog_a=[0, 3, 4, 5], prog_b=[5, 3, 0, 4],
         hook=[(0,0,2,0),(0,2,2,2),(1,0,2,4),(1,2,2,2),(2,0,3,4),(2,3,1,5),(3,0,4,4),
               (4,0,2,4),(4,2,2,6),(5,0,2,7),(5,2,2,6),(6,0,3,4),(6,3,1,2),(7,0,4,0)],
         hook_b=[(0,0,2,5),(0,2,2,4),(1,0,4,2),(2,0,2,4),(2,2,2,5),(3,0,4,4),
                 (4,0,2,7),(4,2,2,6),(5,0,4,4),(6,0,2,2),(6,2,2,4),(7,0,4,0)]),

    dict(num=9, title="The Long Way Home", root=7, mode="ion", bpm=66, meter=3,
         lh="waltz", strings=("3 Violins", 34), long=True,
         prog_a=[0, 4, 5, 3], prog_b=[3, 0, 4, 4],
         hook=[(0,0,1,4),(0,1,2,5),(1,0,1,6),(1,1,2,4),(2,0,1,2),(2,1,2,4),(3,0,3,2),
               (4,0,1,4),(4,1,2,5),(5,0,1,7),(5,1,2,6),(6,0,1,5),(6,1,2,4),(7,0,3,4)],
         hook_b=[(0,0,1,7),(0,1,2,8),(1,0,3,7),(2,0,1,6),(2,1,2,5),(3,0,3,4),
                 (4,0,1,5),(4,1,2,6),(5,0,3,4),(6,0,1,2),(6,1,2,4),(7,0,3,2)]),

    dict(num=10, title="Inland Sea", root=2, mode="aeo", bpm=57, meter=4,
         lh="wide", strings=("Cello", 36), long=False,
         prog_a=[0, 5, 3, 6], prog_b=[3, 5, 0, 4],
         hook=[(0,0,4,4),(1,0,3,5),(1,3,1,4),(2,0,4,2),(3,0,4,0),
               (4,0,4,4),(5,0,3,2),(5,3,1,4),(6,0,4,5),(7,0,4,4)],
         hook_b=[(0,0,4,6),(1,0,4,5),(2,0,4,4),(3,0,4,2),
                 (4,0,4,3),(5,0,3,4),(5,3,1,2),(6,0,4,1),(7,0,4,0)]),

    dict(num=11, title="Evening Glass", root=10, mode="ion", bpm=64, meter=3,
         lh="waltz", strings=("3 Violins", 34), long=False,
         prog_a=[0, 5, 3, 4], prog_b=[3, 1, 4, 4],
         hook=[(0,0,1,7),(0,1,2,5),(1,0,1,6),(1,1,2,4),(2,0,1,5),(2,1,2,2),(3,0,3,4),
               (4,0,1,7),(4,1,2,6),(5,0,1,5),(5,1,2,4),(6,0,1,4),(6,1,2,2),(7,0,3,0)],
         hook_b=[(0,0,1,5),(0,1,2,6),(1,0,3,7),(2,0,1,6),(2,1,2,4),(3,0,3,5),
                 (4,0,1,4),(4,1,2,5),(5,0,3,4),(6,0,1,2),(6,1,2,3),(7,0,3,4)]),

    dict(num=12, title="Last Page", root=0, mode="ion", bpm=54, meter=4,
         lh="wide", strings=("String Section", 34), long=False,
         prog_a=[0, 4, 5, 3], prog_b=[3, 4, 0, 4],
         hook=[(0,0,4,7),(1,0,3,6),(1,3,1,5),(2,0,4,4),(3,0,4,2),
               (4,0,4,4),(5,0,3,3),(5,3,1,2),(6,0,4,1),(7,0,4,0)],
         hook_b=[(0,0,4,5),(1,0,4,4),(2,0,4,2),(3,0,4,0),
                 (4,0,4,4),(5,0,3,5),(5,3,1,4),(6,0,4,2),(7,0,4,0)]),
]


# ---- engine -------------------------------------------------------------------

class TrackWriter:
    def __init__(self, spec):
        self.s = spec
        self.beat = 60.0 / spec["bpm"]
        self.bar = self.beat * spec["meter"]
        self.rng = np.random.default_rng(100 + spec["num"])
        self.piano, self.mello = [], []

    def deg(self, degree, base_oct=5):
        iv = MODES[self.s["mode"]]
        return 12 * (base_oct + degree // 7) + self.s["root"] + iv[degree % 7]

    def human(self, t, vel, t_sd=0.012, v_sd=4):
        t = max(t + float(np.clip(self.rng.normal(0, t_sd), -2.5 * t_sd, 2.5 * t_sd)), 0.0)
        return t, int(np.clip(vel + self.rng.normal(0, v_sd), 1, 127))

    def note(self, t, dur, midi, vel, ch=0):
        self.piano.append((int(t * SR), "on", ch, midi, vel))
        self.piano.append((int((t + dur) * SR), "off", ch, midi, 0))

    def mnote(self, t, dur, midi, vel):
        while midi < 55: midi += 12
        while midi > 89: midi -= 12
        dur = min(dur, 7.0)
        self.mello.append((int(t * SR), "on", 0, midi, vel))
        self.mello.append((int((t + dur) * SR), "off", 0, midi, 0))

    # left-hand styles ---------------------------------------------------------
    def lh_bar(self, bar_t, chord_deg, style, level):
        root = self.deg(chord_deg, base_oct=3)
        fifth = self.deg(chord_deg + 4, base_oct=3)
        tenth = self.deg(chord_deg + 9, base_oct=3)
        v = 40 + level * 6
        if style == "drift":
            t, vv = self.human(bar_t, v); self.note(t, self.bar * 0.95, root, vv, ch=1)
            t, vv = self.human(bar_t + 2 * self.beat, v - 6); self.note(t, self.bar * 0.45, fifth, vv, ch=1)
        elif style == "wide":
            for i, m in enumerate((root, fifth, tenth)):
                t, vv = self.human(bar_t + i * 0.08, v - 4 - i * 3)
                self.note(t, self.bar * 0.95, m, vv, ch=1)
        elif style == "arp":
            seq = [root, fifth, root + 12, fifth] if level < 2 else [root, fifth, root + 12, tenth]
            for i, m in enumerate(seq[:self.s["meter"]]):
                t, vv = self.human(bar_t + i * self.beat, v - 6)
                self.note(t, self.beat * 1.8, m, vv, ch=1)
        elif style == "pulse":
            for i in range(self.s["meter"]):
                m = root if i % 2 == 0 else root + 12
                t, vv = self.human(bar_t + i * self.beat, v - 6 + (4 if i == 0 else 0))
                self.note(t, self.beat * 1.5, m, vv, ch=1)
        elif style == "waltz":
            t, vv = self.human(bar_t, v); self.note(t, self.beat * 2.6, root, vv, ch=1)
            third = self.deg(chord_deg + 2, base_oct=4)
            for b in (1, 2):
                t, vv = self.human(bar_t + b * self.beat, v - 10)
                self.note(t, self.beat * 0.85, third, vv, ch=2)
                t, vv = self.human(bar_t + b * self.beat + 0.015, v - 12)
                self.note(t, self.beat * 0.85, self.deg(chord_deg + 4, base_oct=4), vv, ch=3)
        elif style == "arp68":
            seq = [root, fifth, root + 12, fifth, self.deg(chord_deg + 2, base_oct=4), fifth]
            for i, m in enumerate(seq):
                t, vv = self.human(bar_t + i * self.beat, v - 8 + (6 if i in (0, 3) else 0))
                self.note(t, self.beat * 1.7, m, vv, ch=1)

    # melody -------------------------------------------------------------------
    def melody(self, start_bar, phrase, vel, oct_up=False, thirds=False):
        for bar_off, beat, dur_b, degree in phrase:
            t0 = (start_bar + bar_off) * self.bar + beat * self.beat
            d = degree + (7 if oct_up else 0)
            t, v = self.human(t0, vel)
            self.note(t, dur_b * self.beat * 1.05, self.deg(d), v)
            if thirds and dur_b >= 2:
                t, v = self.human(t0 + 0.02, vel - 10)
                self.note(t, dur_b * self.beat, self.deg(d - 2), v, ch=2)

    def strings_bar(self, bar_t, chord_deg, vel):
        self.mnote(bar_t + 0.05, self.bar * 1.9, self.deg(chord_deg, base_oct=4), vel)
        self.mnote(bar_t + 0.12, self.bar * 1.9, self.deg(chord_deg + 2, base_oct=4), vel - 4)

    # form ---------------------------------------------------------------------
    def build(self):
        s = self.s
        sections = ["intro", "A", "A2", "breath", "B", "A3", "breath", "B2", "A4", "outro"]
        if s["long"]:
            sections = ["intro", "A", "A2", "breath", "B", "A3", "breath",
                        "B2", "A4", "breath", "B3", "A5", "outro"]

        bar_cursor = 0
        for sec in sections:
            if sec == "intro":
                for i in range(4):
                    self.lh_bar(bar_cursor * self.bar + i * self.bar,
                                s["prog_a"][i % 4], s["lh"], 0)
                bar_cursor += 4
            elif sec == "breath":
                for i in range(2):
                    self.lh_bar((bar_cursor + i) * self.bar, s["prog_a"][i % 4], s["lh"], 0)
                bar_cursor += 2
            elif sec in ("A", "A2", "A3", "A4", "A5"):
                level = {"A": 1, "A2": 2, "A3": 3, "A4": 3, "A5": 3}[sec]
                vel = {1: 56, 2: 58, 3: 62}[level]
                oct_up = sec in ("A3", "A5")
                thirds = sec in ("A3", "A4", "A5")
                for i in range(8):
                    self.lh_bar((bar_cursor + i) * self.bar, s["prog_a"][i % 4], s["lh"], level)
                    if s["strings"] and level >= 2 and i % 2 == 0:
                        self.strings_bar((bar_cursor + i) * self.bar, s["prog_a"][i % 4], s["strings"][1])
                self.melody(bar_cursor, s["hook"], vel, oct_up=oct_up, thirds=thirds)
                bar_cursor += 8
            elif sec in ("B", "B2", "B3"):
                for i in range(8):
                    self.lh_bar((bar_cursor + i) * self.bar, s["prog_b"][i % 4], s["lh"], 2)
                    if s["strings"] and i % 2 == 0:
                        self.strings_bar((bar_cursor + i) * self.bar, s["prog_b"][i % 4], s["strings"][1])
                if s["hook_b"]:
                    self.melody(bar_cursor, s["hook_b"], 58, oct_up=(sec in ("B2", "B3")))
                bar_cursor += 8
            elif sec == "outro":
                t0 = bar_cursor * self.bar
                first_deg = s["hook"][0][3]
                t, v = self.human(t0, 48)
                self.note(t, self.bar * 1.9, self.deg(first_deg), v)
                for i, d in enumerate((0, 2, 4)):  # rolled tonic
                    t, v = self.human(t0 + 2 * self.bar + i * 0.09, 44 - i * 2)
                    self.note(t, self.bar * 2.2, self.deg(d, base_oct=4), v, ch=2)
                t, v = self.human(t0 + 4 * self.bar, 40)
                self.note(t, self.bar * 1.9, self.deg(0, base_oct=3), v, ch=1)
                if s["strings"]:
                    self.mnote(t0 + 2 * self.bar, self.bar * 2.5, self.deg(0, base_oct=4), s["strings"][1] - 4)
                bar_cursor += 6
        return bar_cursor * self.bar + 6.0


def main():
    from pedalboard import Pedalboard, Reverb, LowpassFilter, HighpassFilter, Convolution
    os.makedirs(OUT_DIR, exist_ok=True)
    sample_rng = np.random.default_rng(73)
    piano_smp = ExsSampler(os.path.join(SAMPLES, "SteinwayPiano"), rng=sample_rng)
    mello_cache = {}
    room = Convolution(ROOM_IR, mix=1.0)

    for spec in TRACKS:
        w = TrackWriter(spec)
        total_secs = w.build()
        piano = stereo(piano_smp.render(w.piano, total_secs), pan=-0.05)
        peak = max(np.abs(piano).max(), 1e-9)
        piano = piano / peak * 0.5
        piano = Pedalboard([
            LowpassFilter(cutoff_frequency_hz=9500),
            Reverb(room_size=0.88, damping=0.5, wet_level=0.3, dry_level=0.7, width=1.0),
        ])(piano, SR)

        mix = piano
        if spec["strings"] and w.mello:
            bank = spec["strings"][0]
            if bank not in mello_cache:
                mello_cache[bank] = ExsSampler(
                    os.path.join(SAMPLES, "Mellotron"),
                    rng=sample_rng,
                    groups=[bank],
                )
            mstr = stereo(mello_cache[bank].render(w.mello, total_secs, attack=0.28), pan=0.15)
            mstr = mstr / max(np.abs(mstr).max(), 1e-9) * 0.21
            mstr = Pedalboard([
                HighpassFilter(cutoff_frequency_hz=140),
                LowpassFilter(cutoff_frequency_hz=5000),
                Reverb(room_size=0.92, damping=0.4, wet_level=0.42, dry_level=0.58, width=1.0),
            ])(mstr, SR)
            mix = mix + mstr

        rms = lambda a: np.sqrt((a ** 2).mean())
        wet = room((mix * 0.6).astype(np.float32), SR)
        mix = mix + wet * (0.16 * rms(mix) / max(rms(wet), 1e-9))

        n = mix.shape[1]
        env = np.ones(n, dtype=np.float32)
        fi, fo = int(0.8 * SR), int(5.0 * SR)
        env[:fi] = np.linspace(0, 1, fi)
        env[-fo:] = np.linspace(1, 0, fo)
        mix *= env

        # album-level loudness match: RMS target with a peak safety
        scale = min(0.055 / max(rms(mix), 1e-9), 0.9 / max(np.abs(mix).max(), 1e-9))
        mix *= scale

        fname = f"{spec['num']:02d} {spec['title']}.wav"
        wavfile.write(os.path.join(OUT_DIR, fname), SR, (mix.T * 32767).astype(np.int16))
        print(f"{fname}: {total_secs/60:.1f} min")

    print("Album complete: The Quiet Hours")


if __name__ == "__main__":
    main()
