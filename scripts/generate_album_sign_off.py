"""SIGN-OFF -- twelve nostalgic synth pieces, haunting but calm. The
world of this album is a night in the early 80s: sodium streetlights,
the last broadcast of the evening, a TV warming the room after everyone
else is asleep.

Every melodic voice is synthesized from oscillators -- no samples --
because that's what the era was: detuned analog saws for pads (with tape
wow: every voice's pitch drifts on two slow LFOs), a triangle/saw lead
with portamento and late vibrato, DX-style FM bells (it's 1983 --
the DX7 just came out), square-wave arps, and a sine sub bass. A faint
tape-hiss bed breathes under everything. Percussion is the real
machines: CR-8000, LinnDrum, TR-808, Drumtraks, MFB-512 one-shots,
played lightly, a different box per track.

Same album architecture as The Quiet Hours: a composition engine with
hand-written specs -- key, mode, tempo, progressions, a hook with its
own rhythmic identity -- and a shared form for movements:
  intro (pad+hiss) -> A (lead theme) -> A2 (+arp, +percussion) ->
  breath -> B (harmonic shift; lead rests or answers) -> A3 (fullest,
  bell doubling) -> outro (pad decays into the hiss).
Tracks are loudness-matched. Output: Tracks/Sign-Off/NN Title.wav
"""

import os

import numpy as np
from scipy.signal import sawtooth, butter, lfilter
from scipy.io import wavfile

from pedalboard import (Pedalboard, Chorus, Delay, Reverb, Compressor,
                        HighpassFilter, HighShelfFilter, LowpassFilter,
                        Convolution)

SR = 44100
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(SCRIPT_DIR, "..", "Tracks", "Sign-Off")
SAMPLES = os.path.join(SCRIPT_DIR, "..", "Samples")
ROOM_IR = os.path.join(SCRIPT_DIR, "..", "IRs", "Highly Damped Large Room.wav")

MODES = {"ion": [0, 2, 4, 5, 7, 9, 11], "dor": [0, 2, 3, 5, 7, 9, 10],
         "aeo": [0, 2, 3, 5, 7, 8, 10]}

KITS = {
    "CR-8000":   ("CR-8000", "kick.wav", "snare.wav", "hhc.wav", "hho.wav"),
    "TR-808":    ("TR-808", "kick.wav", "snare.wav", "hhc.wav", "hho.wav"),
    "MFB-512":   ("MFB-512", "kick.wav", "snare.wav", "hhc.wav", "hho.wav"),
    "LM-2":      ("LM-2", "kick.wav", "snare-m.wav", "hhclosed.wav", "hhopen.wav"),
    "Drumtraks": ("Drumtraks", "DT_Kick.wav", "DT_Snare.wav", "DT_Closedhat.wav", "DT_Openhat.wav"),
}

# ---- the twelve tracks --------------------------------------------------------

TRACKS = [
    dict(num=1, title="Test Pattern", root=9, mode="dor", bpm=78,
         kit="LM-2", beat_style="linn", arp=True, lead="lead", long=False,
         prog_a=[0, 3, 5, 4], prog_b=[5, 3, 0, 4], wobble=1.0,
         hook=[(0,0,1,7),(0,1,0.5,6),(0,1.5,0.5,5),(0,2,2,4),(1,0,1,5),(1,1,1,4),(1,2,2,2),
               (2,0,1,4),(2,1,0.5,5),(2,1.5,0.5,6),(2,2,2,4),(3,0,4,2),
               (4,0,1,7),(4,1,0.5,8),(4,1.5,0.5,7),(4,2,2,5),(5,0,1,6),(5,1,1,5),(5,2,2,4),
               (6,0,2,5),(6,2,2,7),(7,0,4,4)],
         hook_b=[(0,0,3,9),(0,3,1,8),(1,0,4,7),(2,0,3,8),(2,3,1,7),(3,0,4,6),
                 (4,0,3,7),(4,3,1,5),(5,0,4,4),(6,0,2,5),(6,2,2,6),(7,0,4,7)]),

    dict(num=2, title="Sodium Lights", root=2, mode="dor", bpm=82,
         kit="LM-2", beat_style="linn", arp=True, lead="lead", long=False,
         prog_a=[0, 3, 5, 4], prog_b=[5, 3, 0, 4], wobble=1.0,
         hook=[(0,0,1,7),(0,1,0.5,6),(0,1.5,0.5,5),(0,2,2,4),(1,0,1,5),(1,1,0.5,4),(1,1.5,0.5,2),(1,2,2,4),
               (2,0,1,7),(2,1,0.5,6),(2,1.5,0.5,5),(2,2,2,6),(3,0,4,4),
               (4,0,1,7),(4,1,0.5,8),(4,1.5,0.5,7),(4,2,2,6),(5,0,1,5),(5,1,0.5,4),(5,1.5,0.5,5),(5,2,2,6),
               (6,0,2,7),(6,2,2,5),(7,0,4,4)],
         hook_b=[(0,0,3,9),(0,3,1,8),(1,0,4,7),(2,0,3,8),(2,3,1,7),(3,0,4,6),
                 (4,0,3,7),(4,3,1,5),(5,0,4,4),(6,0,2,5),(6,2,2,6),(7,0,4,7)]),

    dict(num=3, title="Rabbit Ears", root=4, mode="aeo", bpm=60,
         kit=None, beat_style=None, arp=False, lead="bell", long=False,
         prog_a=[0, 5, 3, 6], prog_b=[3, 6, 5, 4], wobble=1.5,
         hook=[(0,0,4,4),(1,0,4,7),(2,0,4,5),(3,0,4,4),
               (4,0,4,7),(5,0,4,9),(6,0,4,7),(7,0,4,4)],
         hook_b=None),

    dict(num=4, title="Late Forecast", root=6, mode="aeo", bpm=84,
         kit="MFB-512", beat_style="pulse", arp=True, lead="lead", long=True,
         prog_a=[0, 6, 5, 4], prog_b=[3, 6, 0, 4], wobble=0.9,
         hook=[(0,0,2,4),(0,2,1,4),(0,3,1,5),(1,0,2,4),(1,2,2,2),(2,0,2,5),(2,2,1,4),(2,3,1,2),(3,0,4,4),
               (4,0,2,7),(4,2,1,7),(4,3,1,8),(5,0,2,7),(5,2,2,5),(6,0,2,4),(6,2,1,5),(6,3,1,4),(7,0,4,2)],
         hook_b=[(0,0,3,9),(0,3,1,8),(1,0,3,7),(1,3,1,8),(2,0,4,9),(3,0,4,7),
                 (4,0,3,5),(4,3,1,4),(5,0,3,2),(5,3,1,4),(6,0,4,5),(7,0,4,4)]),

    dict(num=5, title="Polaroid Summer", root=10, mode="ion", bpm=72,
         kit="LM-2", beat_style="linn", arp=True, lead="lead", long=False,
         prog_a=[0, 5, 3, 4], prog_b=[1, 4, 5, 3], wobble=0.8,
         hook=[(0,0,2,4),(0,2,1,5),(0,3,1,4),(1,0,2,2),(1,2,2,4),(2,0,2,5),(2,2,1,6),(2,3,1,5),(3,0,4,4),
               (4,0,2,4),(4,2,1,5),(4,3,1,6),(5,0,2,7),(5,2,2,6),(6,0,2,5),(6,2,2,4),(7,0,4,2)],
         hook_b=[(0,0,3,5),(0,3,1,6),(1,0,4,7),(2,0,3,6),(2,3,1,5),(3,0,4,4),
                 (4,0,3,3),(4,3,1,4),(5,0,4,5),(6,0,2,4),(6,2,2,3),(7,0,4,2)]),

    dict(num=6, title="Drive Home, 1983", root=1, mode="aeo", bpm=88,
         kit="TR-808", beat_style="pulse", arp=True, lead="lead", long=True,
         prog_a=[0, 6, 5, 4], prog_b=[3, 6, 0, 4], wobble=0.9,
         hook=[(0,0,2,4),(0,2,1,4),(0,3,1,5),(1,0,2,4),(1,2,2,2),(2,0,2,4),(2,2,1,4),(2,3,1,5),(3,0,4,6),
               (4,0,2,7),(4,2,1,7),(4,3,1,8),(5,0,2,7),(5,2,2,5),(6,0,2,4),(6,2,1,5),(6,3,1,4),(7,0,4,2)],
         hook_b=[(0,0,3,9),(0,3,1,8),(1,0,3,7),(1,3,1,8),(2,0,4,9),(3,0,4,7),
                 (4,0,3,5),(4,3,1,4),(5,0,3,2),(5,3,1,4),(6,0,4,5),(7,0,4,4)]),

    dict(num=7, title="Static Bloom", root=7, mode="aeo", bpm=58,
         kit=None, beat_style=None, arp=False, lead="bell", long=False,
         prog_a=[0, 3, 5, 4], prog_b=[5, 3, 0, 0], wobble=1.6,
         hook=[(0,0,4,4),(1,0,4,2),(2,0,4,3),(3,0,4,0),
               (4,0,4,4),(5,0,4,7),(6,0,4,5),(7,0,4,4)],
         hook_b=None),

    dict(num=8, title="The Arcade After Close", root=4, mode="dor", bpm=86,
         kit="Drumtraks", beat_style="linn", arp=True, lead="lead", long=True,
         prog_a=[0, 3, 0, 4], prog_b=[5, 3, 6, 4], wobble=0.8,
         hook=[(0,0,0.5,7),(0,0.5,0.5,8),(0,1,1,7),(0,2,2,5),(1,0,0.5,4),(1,0.5,0.5,5),(1,1,1,4),(1,2,2,2),
               (2,0,0.5,7),(2,0.5,0.5,8),(2,1,1,9),(2,2,2,7),(3,0,4,6),
               (4,0,0.5,7),(4,0.5,0.5,8),(4,1,1,7),(4,2,2,5),(5,0,0.5,6),(5,0.5,0.5,5),(5,1,1,6),(5,2,2,4),
               (6,0,2,5),(6,2,2,6),(7,0,4,7)],
         hook_b=[(0,0,3,9),(0,3,1,10),(1,0,4,9),(2,0,3,8),(2,3,1,9),(3,0,4,8),
                 (4,0,3,7),(4,3,1,6),(5,0,4,5),(6,0,2,6),(6,2,2,5),(7,0,4,4)]),

    dict(num=9, title="Curfew", root=11, mode="aeo", bpm=62,
         kit="TR-808", beat_style="heartbeat", arp=True, lead="lead", long=False,
         prog_a=[0, 5, 6, 4], prog_b=[3, 5, 4, 4], wobble=1.1,
         hook=[(0,0,2,4),(0,2,2,2),(1,0,3,0),(1,3,1,2),(2,0,2,3),(2,2,2,4),(3,0,4,2),
               (4,0,2,5),(4,2,2,4),(5,0,3,2),(5,3,1,0),(6,0,2,1),(6,2,2,2),(7,0,4,0)],
         hook_b=[(0,0,3,5),(0,3,1,4),(1,0,4,3),(2,0,2,4),(2,2,2,5),(3,0,4,4),
                 (4,0,3,2),(4,3,1,1),(5,0,4,0),(6,0,2,2),(6,2,2,4),(7,0,4,0)]),

    dict(num=10, title="Vertical Hold", root=8, mode="aeo", bpm=66,
         kit=None, beat_style=None, arp=True, lead="lead", long=False,
         prog_a=[0, 3, 5, 4], prog_b=[5, 0, 3, 4], wobble=2.2,
         hook=[(0,0,4,7),(1,0,2,6),(1,2,2,5),(2,0,4,4),(3,0,4,4),
               (4,0,4,7),(5,0,2,8),(5,2,2,9),(6,0,4,8),(7,0,4,7)],
         hook_b=[(0,0,4,5),(1,0,4,4),(2,0,2,5),(2,2,2,6),(3,0,4,4),
                 (4,0,4,2),(5,0,3,4),(5,3,1,2),(6,0,4,0),(7,0,4,0)]),

    dict(num=11, title="School Night", root=2, mode="aeo", bpm=63,
         kit="CR-8000", beat_style="heartbeat", arp=False, lead="bell", long=False,
         prog_a=[0, 5, 3, 4], prog_b=[3, 4, 0, 4], wobble=1.2,
         hook=[(0,0,2,4),(0,2,2,5),(1,0,4,2),(2,0,2,3),(2,2,2,4),(3,0,4,0),
               (4,0,2,4),(4,2,2,7),(5,0,4,5),(6,0,2,4),(6,2,2,2),(7,0,4,0)],
         hook_b=None),

    dict(num=12, title="Sign-Off", root=9, mode="aeo", bpm=56,
         kit=None, beat_style=None, arp=False, lead="lead", long=False,
         prog_a=[0, 3, 5, 4], prog_b=[5, 3, 4, 4], wobble=1.3,
         hook=[(0,0,4,4),(1,0,3,3),(1,3,1,2),(2,0,4,3),(3,0,4,2),
               (4,0,4,4),(5,0,3,5),(5,3,1,4),(6,0,4,2),(7,0,4,0)],
         hook_b=[(0,0,4,5),(1,0,4,4),(2,0,4,2),(3,0,4,0),
                 (4,0,4,3),(5,0,3,2),(5,3,1,3),(6,0,4,2),(7,0,4,0)]),
]


# ---- synthesis ----------------------------------------------------------------

def lowpass(x, cutoff, order=2):
    b, a = butter(order, min(cutoff, SR / 2 - 100) / (SR / 2), btype="low")
    return lfilter(b, a, x)


def adsr(n, a, d, s, r):
    a_n, d_n, r_n = (min(int(v * SR), n) for v in (a, d, r))
    s_n = max(n - a_n - d_n - r_n, 0)
    env = np.concatenate([np.linspace(0, 1, a_n, endpoint=False),
                          np.linspace(1, s, d_n, endpoint=False),
                          np.full(s_n, s), np.linspace(s, 0, r_n)])
    return np.pad(env, (0, max(n - len(env), 0)))[:n].astype(np.float32)


class Synth:
    """All voices share the tape-wow engine: every note's pitch drifts on
    two slow, phase-random LFOs. `wobble` scales the depth per track."""

    def __init__(self, rng, wobble=1.0):
        self.rng = rng
        self.wob = wobble

    def _freq(self, f0, n):
        t = np.arange(n) / SR
        p1, p2 = self.rng.uniform(0, 2 * np.pi, 2)
        drift = (0.0012 * np.sin(2 * np.pi * 0.31 * t + p1)
                 + 0.0007 * np.sin(2 * np.pi * 0.077 * t + p2)) * self.wob
        return f0 * (1.0 + drift)

    def pad(self, midi, dur):
        n = int(dur * SR)
        f = self._freq(440 * 2 ** ((midi - 69) / 12), n)
        ph = 2 * np.pi * np.cumsum(f) / SR
        sig = (sawtooth(ph * 1.0035) + sawtooth(ph * 0.9965)
               + 0.5 * np.sin(ph * 0.5))
        env = adsr(n, dur * 0.3, 0.2, 0.85, dur * 0.35)
        return lowpass(sig * env, 1300).astype(np.float32) / 2.5

    def lead(self, midi, dur, prev_midi=None):
        n = int(dur * SR)
        t = np.arange(n) / SR
        f0 = 440 * 2 ** ((midi - 69) / 12)
        f = self._freq(f0, n)
        if prev_midi is not None:  # portamento from the previous note
            fp = 440 * 2 ** ((prev_midi - 69) / 12)
            glide = int(0.08 * SR)
            f[:glide] *= np.linspace(fp / f0, 1.0, glide)
        vib = 1 + 0.004 * np.sin(2 * np.pi * 5.3 * t) * np.clip((t - 0.35) / 0.4, 0, 1)
        ph = 2 * np.pi * np.cumsum(f * vib) / SR
        sig = 0.65 * sawtooth(ph, width=0.5) + 0.35 * sawtooth(ph)
        env = adsr(n, 0.04, 0.1, 0.85, min(0.5, dur * 0.3))
        return lowpass(sig * env, 2400).astype(np.float32) / 1.6

    def bell(self, midi, dur):
        n = int(dur * SR)
        t = np.arange(n) / SR
        f = self._freq(440 * 2 ** ((midi - 69) / 12), n)
        ph = 2 * np.pi * np.cumsum(f) / SR
        index = 2.2 * np.exp(-t / (dur * 0.35))
        sig = np.sin(ph + index * np.sin(3.53 * ph))
        return (sig * np.exp(-t / (dur * 0.5)) * adsr(n, 0.005, 0.1, 0.8, 0.2)).astype(np.float32) / 1.4

    def arp(self, midi, dur):
        n = int(dur * SR)
        f = self._freq(440 * 2 ** ((midi - 69) / 12), n)
        ph = 2 * np.pi * np.cumsum(f) / SR
        sig = np.sign(np.sin(ph)) * 0.7 + 0.3 * sawtooth(ph)
        env = np.exp(-np.arange(n) / SR * 7).astype(np.float32)
        return lowpass(sig * env, 1900).astype(np.float32) / 1.8

    def bass(self, midi, dur):
        n = int(dur * SR)
        f = self._freq(440 * 2 ** ((midi - 69) / 12), n)
        ph = 2 * np.pi * np.cumsum(f) / SR
        sig = np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.15 * sawtooth(ph, width=0.5)
        env = adsr(n, 0.02, 0.15, 0.8, min(0.4, dur * 0.3))
        return lowpass(sig * env, 500).astype(np.float32) / 1.3


def hiss_bed(n, rng, level=0.006):
    noise = rng.standard_normal(n).astype(np.float32)
    b, a = butter(2, [200 / (SR / 2), 6000 / (SR / 2)], btype="band")
    noise = lfilter(b, a, noise).astype(np.float32)
    t = np.arange(n) / SR
    return noise * level * (1 + 0.25 * np.sin(2 * np.pi * 0.05 * t)).astype(np.float32)


# ---- per-track writer ----------------------------------------------------------

class TrackWriter:
    def __init__(self, spec):
        self.s = spec
        self.beat = 60.0 / spec["bpm"]
        self.bar = self.beat * 4
        self.rng = np.random.default_rng(500 + spec["num"])
        self.synth = Synth(self.rng, spec["wobble"])
        self.kit = None
        if spec["kit"]:
            folder, *files = KITS[spec["kit"]]
            self.kit = {}
            for name, fn in zip(("kick", "snare", "hhc", "hho"), files):
                _, d = wavfile.read(os.path.join(SAMPLES, folder, fn))
                d = d.astype(np.float32) / 32768.0
                if d.ndim == 2:
                    d = d.mean(axis=1)
                self.kit[name] = d / max(np.abs(d).max(), 1e-9)

    def deg(self, degree, base_oct=5):
        iv = MODES[self.s["mode"]]
        return 12 * (base_oct + degree // 7) + self.s["root"] + iv[degree % 7]

    def hum(self, t, sd=0.008):
        return max(t + float(np.clip(self.rng.normal(0, sd), -2.5 * sd, 2.5 * sd)), 0.0)

    def place(self, bus, t, sig, gain=1.0):
        start = int(t * SR)
        end = min(start + len(sig), bus.shape[-1] if bus.ndim == 1 else bus.shape[1])
        if end <= start:
            return
        seg = sig[:end - start] * gain
        if bus.ndim == 1:
            bus[start:end] += seg
        else:
            bus[:, start:end] += seg

    # section renderers --------------------------------------------------------
    def pads_bar(self, bus, bar_t, chord_deg, level):
        for i, d in enumerate((0, 2, 4)):
            sig = self.synth.pad(self.deg(chord_deg + d, base_oct=4), self.bar * 2.1)
            self.place(bus, self.hum(bar_t + i * 0.04, 0.01), sig, 0.3 + 0.06 * level)

    def bass_bar(self, bus, bar_t, chord_deg):
        sig = self.synth.bass(self.deg(chord_deg, base_oct=2), self.bar * 0.95)
        self.place(bus, self.hum(bar_t), sig, 0.8)

    def arp_bar(self, bus, bar_t, chord_deg, level):
        tones = [0, 4, 7, 9] if level >= 2 else [0, 4, 7, 4]
        for k in range(8):
            d = chord_deg + tones[k % 4]
            sig = self.synth.arp(self.deg(d, base_oct=5), self.beat)
            self.place(bus, self.hum(bar_t + k * self.beat / 2, 0.005), sig, 0.32)

    def lead_notes(self, bus, start_bar, phrase, oct_up=False, gain=0.75):
        prev = None
        voice = self.synth.bell if self.s["lead"] == "bell" else self.synth.lead
        for bar_off, beat, dur_b, degree in phrase:
            t0 = self.hum((start_bar + bar_off) * self.bar + beat * self.beat, 0.010)
            midi = self.deg(degree + (7 if oct_up else 0))
            if self.s["lead"] == "bell":
                sig = voice(midi, dur_b * self.beat * 1.6)
            else:
                sig = voice(midi, dur_b * self.beat * 1.05, prev_midi=prev)
            self.place(bus, t0, sig, gain)
            prev = midi

    def drums_bar(self, bus, bar_t, style, level):
        if not self.kit or not style:
            return
        hits = []
        if style == "heartbeat":
            hits = [(0.0, "kick", 0.5), (2.0, "kick", 0.3)]
            if level >= 2:
                hits += [(1.0, "hhc", 0.14), (3.0, "hhc", 0.14)]
        elif style == "linn":
            hits = [(0.0, "kick", 0.5), (2.0, "kick", 0.35), (1.0, "snare", 0.28), (3.0, "snare", 0.3)]
            if level >= 2:
                hits += [(k * 0.5, "hhc", 0.12 if k % 2 else 0.17) for k in range(8)]
        elif style == "pulse":
            hits = [(0.0, "kick", 0.55), (1.0, "kick", 0.4), (2.0, "kick", 0.55), (3.0, "kick", 0.4)]
            if level >= 2:
                hits += [(k * 0.5 + 0.5, "hhc", 0.13) for k in range(0, 8, 2)]
                hits += [(3.5, "hho", 0.12)]
        for beat_off, piece, g in hits:
            self.place(bus, self.hum(bar_t + beat_off * self.beat, 0.004),
                       self.kit[piece], g * (0.8 + 0.1 * level))

    # form ----------------------------------------------------------------------
    def build(self, total_secs, buses):
        s = self.s
        sections = ["intro", "A", "A2", "breath", "B", "A3", "breath", "B2", "A4", "outro"]
        if s["long"]:
            sections = ["intro", "A", "A2", "breath", "B", "A3", "breath",
                        "B2", "A4", "breath", "B3", "A5", "outro"]
        cur = 0
        for sec in sections:
            if sec == "intro":
                for i in range(4):
                    if i % 2 == 0:
                        self.pads_bar(buses["pad"], (cur + i) * self.bar, s["prog_a"][(i // 2) % 4], 0)
                cur += 4
            elif sec == "breath":
                for i in range(2):
                    if i % 2 == 0:
                        self.pads_bar(buses["pad"], (cur + i) * self.bar, s["prog_a"][0], 1)
                cur += 2
            elif sec in ("A", "A2", "A3", "A4", "A5"):
                level = {"A": 1, "A2": 2, "A3": 3, "A4": 3, "A5": 3}[sec]
                for i in range(8):
                    bt = (cur + i) * self.bar
                    if i % 2 == 0:
                        self.pads_bar(buses["pad"], bt, s["prog_a"][(i // 2) % 4], level)
                    self.bass_bar(buses["bass"], bt, s["prog_a"][(i // 2) % 4])
                    if s["arp"] and level >= 2:
                        self.arp_bar(buses["arp"], bt, s["prog_a"][(i // 2) % 4], level)
                    if level >= 2:
                        self.drums_bar(buses["drums"], bt, s["beat_style"], level)
                self.lead_notes(buses["lead"], cur, s["hook"], oct_up=(level == 3))
                if level == 3:  # a bell shadow doubling the fullest statement
                    old = self.s["lead"]; self.s["lead"] = "bell"
                    self.lead_notes(buses["bell"], cur, s["hook"], oct_up=True, gain=0.28)
                    self.s["lead"] = old
                cur += 8
            elif sec in ("B", "B2", "B3"):
                for i in range(8):
                    bt = (cur + i) * self.bar
                    if i % 2 == 0:
                        self.pads_bar(buses["pad"], bt, s["prog_b"][(i // 2) % 4], 2)
                    self.bass_bar(buses["bass"], bt, s["prog_b"][(i // 2) % 4])
                    if s["arp"]:
                        self.arp_bar(buses["arp"], bt, s["prog_b"][(i // 2) % 4], 2)
                    self.drums_bar(buses["drums"], bt, s["beat_style"], 1)
                if s["hook_b"]:
                    self.lead_notes(buses["lead"], cur, s["hook_b"], oct_up=(sec in ("B2", "B3")))
                cur += 8
            elif sec == "outro":
                for i in (0, 2):
                    self.pads_bar(buses["pad"], (cur + i) * self.bar, s["prog_a"][0] if i else s["prog_a"][3], 0)
                first = s["hook"][0]
                self.lead_notes(buses["lead"], cur + 1, [(0, 0.0, 6.0, first[3])], gain=0.5)
                cur += 6
        return cur


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    room = Convolution(ROOM_IR, mix=1.0)
    for spec in TRACKS:
        w = TrackWriter(spec)
        bars_est = 90 if spec["long"] else 70
        total_secs = bars_est * w.bar + 8.0
        n = int(total_secs * SR)
        buses = {k: np.zeros(n, dtype=np.float32) for k in ("pad", "lead", "bell", "arp", "bass", "drums")}
        cur = w.build(total_secs, buses)
        n = int((cur * w.bar + 8.0) * SR)  # trim over-allocation
        buses = {k: v[:n] for k, v in buses.items()}

        pad = Pedalboard([  # the Juno move: chorus makes the pad
            Chorus(rate_hz=0.55, depth=0.3, centre_delay_ms=12.0, mix=0.5),
            Reverb(room_size=0.9, damping=0.4, wet_level=0.35, dry_level=0.65, width=1.0),
        ])(np.stack([buses["pad"], buses["pad"]]), SR)
        lead = Pedalboard([
            Delay(delay_seconds=w.beat * 0.75, feedback=0.35, mix=0.24),
            Reverb(room_size=0.9, damping=0.35, wet_level=0.32, dry_level=0.68, width=1.0),
        ])(np.stack([buses["lead"] + buses["bell"], buses["lead"] + buses["bell"]]), SR)
        arp = Pedalboard([
            Delay(delay_seconds=w.beat * 1.5, feedback=0.25, mix=0.18),
            Reverb(room_size=0.8, damping=0.5, wet_level=0.2, dry_level=0.8),
        ])(np.stack([buses["arp"], buses["arp"]]), SR)
        bass = Pedalboard([Compressor(threshold_db=-20, ratio=3, attack_ms=8, release_ms=150)])(
            np.stack([buses["bass"], buses["bass"]]), SR)
        drums = Pedalboard([
            Compressor(threshold_db=-18, ratio=2.5, attack_ms=5, release_ms=150),
            LowpassFilter(cutoff_frequency_hz=9000),
        ])(np.stack([buses["drums"], buses["drums"]]), SR)
        hiss = np.stack([hiss_bed(n, w.rng), hiss_bed(n, w.rng)])

        # width: pad and arp lean opposite ways
        pad[0] *= 1.06; pad[1] *= 0.94
        arp[0] *= 0.92; arp[1] *= 1.08

        mix = pad * 0.9 + lead * 0.9 + arp * 0.8 + bass * 0.85 + drums * 0.8 + hiss
        rms = lambda a: np.sqrt((a ** 2).mean())
        wet = room((mix * 0.5).astype(np.float32), SR)
        mix = mix + wet * (0.14 * rms(mix) / max(rms(wet), 1e-9))
        mix = Pedalboard([HighShelfFilter(cutoff_frequency_hz=9000, gain_db=-2.5),
                          HighpassFilter(cutoff_frequency_hz=28)])(mix, SR)

        env = np.ones(n, dtype=np.float32)
        fi, fo = int(1.0 * SR), int(6.0 * SR)
        env[:fi] = np.linspace(0, 1, fi)
        env[-fo:] = np.linspace(1, 0, fo)
        mix *= env
        scale = min(0.055 / max(rms(mix), 1e-9), 0.9 / max(np.abs(mix).max(), 1e-9))
        mix *= scale

        fname = f"{spec['num']:02d} {spec['title']}.wav"
        wavfile.write(os.path.join(OUT_DIR, fname), SR, (mix.T * 32767).astype(np.int16))
        print(f"{fname}: {n/SR/60:.1f} min")

    with open(os.path.join(OUT_DIR, "Sign-Off.m3u"), "w") as f:
        for spec in TRACKS:
            f.write(f"{spec['num']:02d} {spec['title']}.wav\n")
    print("Album complete: Sign-Off")


if __name__ == "__main__":
    main()
