"""Synthesizes a modern darkwave / post-punk track in the vein of French
Police's "Hidalgo" -- driving eighth-note bass guitar, a plodding,
never-changing drum-machine beat, and a chorused, reverb-washed guitar --
and renders it to a WAV file.

The guitar is the new element versus the ambient darkwave generator: notes
are plucked with a block-vectorized Karplus-Strong string model (a noise
burst recirculated through an averaging lowpass, one buffer-length block at
a time) rather than raw oscillators, which gives the attack and decay of a
real picked electric. Both guitar buses then go through the LFO-modulated
chorus in opposite L/R phase and a generous reverb send -- the classic
pedal-board sound. The drums are fully deterministic: no random hat drops,
no fills, the same bar looped for the entire song, because a drum machine
plods and that's the point. The arrangement moves the way "Hidalgo" does:
the bass hook opens alone, the machine locks in, and sections build by
adding/removing layers over a bassline that never stops driving.
"""

import os

import numpy as np
from scipy.signal import sawtooth, butter, lfilter
from scipy.io import wavfile

SR = 44100
BPM = 118
BEAT = 60.0 / BPM
BAR = BEAT * 4
SEED = 41

rng = np.random.default_rng(SEED)

# A natural minor, i - VI - VII - v: the melancholic-but-danceable loop
# modern darkwave lives on. Guitar tones are the chord spelled mid-neck.
CHORDS = {
    "Am": {"bass": 45, "gtr": [57, 60, 64, 69], "pad": [57, 64]},
    "F":  {"bass": 41, "gtr": [53, 57, 60, 65], "pad": [53, 60]},
    "G":  {"bass": 43, "gtr": [55, 59, 62, 67], "pad": [55, 62]},
    "Em": {"bass": 40, "gtr": [52, 55, 59, 64], "pad": [52, 59]},
}
PROG = ["Am", "F", "G", "Em"]

# Verse bass: relentless staccato eighths on the root, a fifth pickup into
# the next bar. Semitone offsets from the chord root.
BASS_DRIVE = [(i * 0.5, 0.5, 0) for i in range(7)] + [(3.5, 0.5, 7)]

# Chorus bass: same engine but bouncing through octave and b7 -- the hook.
BASS_HOOK = [
    (0.0, 0.5, 0), (0.5, 0.5, 0), (1.0, 0.5, 12), (1.5, 0.5, 0),
    (2.0, 0.5, 10), (2.5, 0.5, 0), (3.0, 0.5, 7), (3.5, 0.5, 5),
]

# Guitar arpeggio: eighth-note picking across the chord shape, low string
# anchoring the pattern the way a pick-hand ostinato does.
ARP_PATTERN = [0, 2, 1, 2, 3, 2, 1, 2]

# Lead guitar hook, one 4-bar phrase over Am-F-G-Em: (bar, beat, dur_beats, midi).
LEAD_PHRASE = [
    (0, 0.0, 1.5, 76), (0, 1.5, 0.5, 72), (0, 2.0, 1.0, 74), (0, 3.0, 1.0, 71),
    (1, 0.0, 2.0, 72), (1, 2.0, 1.5, 69), (1, 3.5, 0.5, 72),
    (2, 0.0, 1.0, 74), (2, 1.0, 1.0, 71), (2, 2.0, 2.0, 74),
    (3, 0.0, 3.0, 71), (3, 3.0, 1.0, 67),
]


def midi_to_freq(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def adsr(n, a, d, s, r, sr=SR):
    n = max(n, 1)
    a_n, d_n, r_n = int(a * sr), int(d * sr), int(r * sr)
    a_n, d_n, r_n = (min(x, n) for x in (a_n, d_n, r_n))
    s_n = max(n - a_n - d_n - r_n, 0)
    env = np.concatenate([
        np.linspace(0, 1, a_n, endpoint=False),
        np.linspace(1, s, d_n, endpoint=False),
        np.full(s_n, s),
        np.linspace(s, 0, r_n),
    ])
    if len(env) < n:
        env = np.pad(env, (0, n - len(env)))
    return env[:n]


def lowpass(x, cutoff, order=2, sr=SR):
    cutoff = min(max(cutoff, 50), sr / 2 - 100)
    b, a = butter(order, cutoff / (sr / 2), btype="low")
    return lfilter(b, a, x)


def comb(x, delay_s, feedback, sr=SR):
    d = max(int(delay_s * sr), 1)
    a = np.zeros(d + 1)
    a[0] = 1.0
    a[-1] = -feedback
    return lfilter([1.0], a, x)


def schroeder_reverb(x, wet=0.3, sr=SR):
    combs = sum(comb(x, d, fb, sr) for d, fb in
                [(0.0297, 0.78), (0.0371, 0.74), (0.0411, 0.71), (0.0437, 0.68)])
    combs /= 4.0
    for d, g in [(0.005, 0.7), (0.0017, 0.7)]:
        n = max(int(d * sr), 1)
        b = np.zeros(n + 1); b[0] = -g; b[-1] = 1.0
        a = np.zeros(n + 1); a[0] = 1.0; a[-1] = -g
        combs = lfilter(b, a, combs)
    return (1 - wet) * x + wet * combs


def chorus(x, rate_hz=0.6, depth_ms=5.0, base_ms=16.0, mix=0.5, voices=2, phase0=0.0, sr=SR):
    """Classic pedal chorus: dry signal + copies read from a continuously
    LFO-modulated delay tap, linearly interpolated between samples."""
    n = len(x)
    t = np.arange(n) / sr
    out = x * (1 - mix)
    idx = np.arange(n)
    for v in range(voices):
        lfo = np.sin(2 * np.pi * rate_hz * t + phase0 + v * np.pi / voices)
        delay_samples = (base_ms + depth_ms * lfo) * sr / 1000.0
        read_pos = np.clip(idx - delay_samples, 0, n - 1)
        idx0 = np.floor(read_pos).astype(int)
        idx1 = np.clip(idx0 + 1, 0, n - 1)
        frac = read_pos - idx0
        delayed = x[idx0] * (1 - frac) + x[idx1] * frac
        out += delayed * (mix / voices)
    return out


def mix_add(buf_l, buf_r, start_t, sig_l, sig_r):
    start = int(start_t * SR)
    end = min(start + len(sig_l), len(buf_l))
    if end <= start:
        return
    n = end - start
    buf_l[start:end] += sig_l[:n]
    buf_r[start:end] += sig_r[:n]


def stereo(sig, pan=0.0):
    l_gain = np.sqrt(0.5 * (1 - pan))
    r_gain = np.sqrt(0.5 * (1 + pan))
    return sig * l_gain, sig * r_gain


# ---- instrument voices -----------------------------------------------------

def guitar_pluck(freq, dur, damp=0.995, tone=4200):
    """Karplus-Strong plucked string, vectorized one delay-line block at a
    time: seed a period-length noise burst, then each block is the average
    of the previous block and its one-sample rotation, scaled by the string
    damping. Gives a real pick attack and natural exponential decay."""
    period = max(int(SR / freq), 2)
    n = int(dur * SR)
    block = lowpass(rng.standard_normal(period), 7000)
    blocks = []
    total = 0
    while total < n:
        blocks.append(block)
        total += period
        block = damp * 0.5 * (block + np.roll(block, 1))
    sig = np.concatenate(blocks)[:n]
    return lowpass(sig, tone)


def bass_guitar(freq, dur, cutoff=950):
    t = np.arange(int(dur * SR)) / SR
    osc = 0.6 * sawtooth(2 * np.pi * freq * t) + 0.5 * np.sin(2 * np.pi * freq * t) \
        + 0.15 * np.sin(2 * np.pi * freq * 2 * t)
    pick_n = min(int(0.008 * SR), len(t))
    pick = np.zeros(len(t))
    pick[:pick_n] = rng.standard_normal(pick_n) * np.exp(-np.arange(pick_n) / SR * 400)
    env = adsr(len(t), a=0.003, d=0.09, s=0.6, r=0.05)
    sig = osc * env + pick * 0.3
    sig = np.tanh(sig * 1.8)  # driven amp -- the bass carries the track
    return lowpass(sig, cutoff)


def pad_voice(freq, dur, cutoff=750):
    t = np.arange(int(dur * SR)) / SR
    osc = (
        np.sin(2 * np.pi * freq * t)
        + 0.4 * sawtooth(2 * np.pi * freq * 1.004 * t)
        + 0.4 * sawtooth(2 * np.pi * freq * 0.996 * t)
    ) / 1.8
    env = adsr(len(t), a=dur * 0.4, d=0.3, s=0.8, r=dur * 0.35)
    return lowpass(osc * env, cutoff)


def kick():
    # Tight machine kick: fast pitch drop, short tail.
    dur = 0.28
    t = np.arange(int(dur * SR)) / SR
    freq = 105 * np.exp(-t * 14) + 46
    phase = 2 * np.pi * np.cumsum(freq) / SR
    click = np.exp(-t * 900) * 0.4
    return np.sin(phase) * np.exp(-t * 13) + click


def snare():
    # Drum-machine snare: bright gated noise over a short 190 Hz body.
    dur = 0.18
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    b, a = butter(2, [400 / (SR / 2), 7500 / (SR / 2)], btype="band")
    noise = lfilter(b, a, noise)
    tone = np.sin(2 * np.pi * 190 * t)
    return (noise * 0.8 + tone * 0.5) * np.exp(-t * 30)


def hat(open_=False):
    dur = 0.14 if open_ else 0.045
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    b, a = butter(2, [7500 / (SR / 2), 14000 / (SR / 2)], btype="band")
    noise = lfilter(b, a, noise)
    decay = 35 if open_ else 90
    return noise * np.exp(-np.arange(n) / SR * decay) * 0.3


# Pre-render one of each hit so every bar is bit-identical -- mechanical.
KICK, SNARE, HAT_C, HAT_O = kick(), snare(), hat(), hat(open_=True)


# ---- arrangement ------------------------------------------------------------

def render_bar(bus, bar_t, chord_name, *, bass=None, drums=False,
               arp=False, pad_gain=0.0):
    c = CHORDS[chord_name]

    if bass is not None:
        pattern = BASS_DRIVE if bass == "drive" else BASS_HOOK
        for beat_off, dur_b, offset in pattern:
            sig = bass_guitar(midi_to_freq(c["bass"] + offset), dur_b * BEAT * 0.95) * 0.85
            mix_add(bus["bass_l"], bus["bass_r"], bar_t + beat_off * BEAT, sig, sig)

    if drums:
        for beat_i in (0, 2):
            mix_add(bus["perc_l"], bus["perc_r"], bar_t + beat_i * BEAT, KICK * 0.85, KICK * 0.85)
        for beat_i in (1, 3):
            mix_add(bus["perc_l"], bus["perc_r"], bar_t + beat_i * BEAT, SNARE * 0.5, SNARE * 0.5)
        for step in range(8):
            h = HAT_O if step == 7 else HAT_C
            l, r = stereo(h * 0.7, pan=0.15)
            mix_add(bus["perc_l"], bus["perc_r"], bar_t + step * (BEAT / 2), l, r)

    if arp:
        for step, tone_i in enumerate(ARP_PATTERN):
            sig = guitar_pluck(midi_to_freq(c["gtr"][tone_i]), BEAT * 1.4) * 0.4
            l, r = stereo(sig, pan=-0.3)
            mix_add(bus["gtr_l"], bus["gtr_r"], bar_t + step * (BEAT / 2), l, r)

    if pad_gain > 0:
        for j, midi in enumerate(c["pad"]):
            sig = pad_voice(midi_to_freq(midi), BAR * 1.2) * pad_gain * (0.8 if j == 0 else 0.6)
            l, r = stereo(sig, pan=-0.15 + 0.3 * j)
            mix_add(bus["pad_l"], bus["pad_r"], bar_t, l, r)


def render_lead(bus, start_bar, n_bars):
    for phrase_start in range(0, n_bars, 4):
        for bar_off, beat, dur_b, midi in LEAD_PHRASE:
            if phrase_start + bar_off >= n_bars:
                continue
            t0 = (start_bar + phrase_start + bar_off) * BAR + beat * BEAT
            sig = guitar_pluck(midi_to_freq(midi), dur_b * BEAT * 1.5, damp=0.9965) * 0.55
            l, r = stereo(sig, pan=0.25)
            mix_add(bus["gtr_l"], bus["gtr_r"], t0, l, r)


def render_movement(bus, start_bar, n_bars, lead=False, **kwargs):
    for bar_i in range(n_bars):
        bar_t = (start_bar + bar_i) * BAR
        chord_name = PROG[bar_i % len(PROG)]
        render_bar(bus, bar_t, chord_name, **kwargs)
    if lead:
        render_lead(bus, start_bar, n_bars)


def main():
    movements = [
        # The bass hook opens alone, dry and driving.
        dict(n_bars=4, bass="hook"),
        # The machine locks in.
        dict(n_bars=4, bass="drive", drums=True),
        # Verse 1: chorused arpeggio guitar enters.
        dict(n_bars=16, bass="drive", drums=True, arp=True),
        # Chorus 1: lead guitar hook, cold pad underneath, bass bounces.
        dict(n_bars=16, bass="hook", drums=True, arp=True, pad_gain=0.3, lead=True),
        # Verse 2: back to the drive, lead drops out.
        dict(n_bars=8, bass="drive", drums=True, arp=True),
        # Chorus 2.
        dict(n_bars=16, bass="hook", drums=True, arp=True, pad_gain=0.35, lead=True),
        # Breakdown: drums and bass cut, the guitar hangs in the reverb.
        dict(n_bars=8, arp=True, pad_gain=0.4),
        # Final chorus, full arrangement.
        dict(n_bars=16, bass="hook", drums=True, arp=True, pad_gain=0.4, lead=True),
        # Outro: back to bass and machine, the way it started.
        dict(n_bars=8, bass="drive", drums=True),
    ]

    total_bars = sum(m["n_bars"] for m in movements)
    total_secs = total_bars * BAR + 6.0
    n_samples = int(total_secs * SR)

    bus = {name: np.zeros(n_samples) for name in
           ("bass_l", "bass_r", "perc_l", "perc_r", "gtr_l", "gtr_r", "pad_l", "pad_r")}

    bar_cursor = 0
    for m in movements:
        kwargs = {k: v for k, v in m.items() if k != "n_bars"}
        render_movement(bus, bar_cursor, m["n_bars"], **kwargs)
        bar_cursor += m["n_bars"]

    # The signature sound: guitar bus through stereo chorus (opposite LFO
    # phase L/R), then a long reverb send. Pad gets a slower, subtler chorus.
    gtr_l = chorus(bus["gtr_l"], rate_hz=0.8, depth_ms=6.0, base_ms=14.0, mix=0.55, phase0=0.0)
    gtr_r = chorus(bus["gtr_r"], rate_hz=0.8, depth_ms=6.0, base_ms=14.0, mix=0.55, phase0=np.pi)
    pad_l = chorus(bus["pad_l"], rate_hz=0.4, depth_ms=4.0, base_ms=16.0, mix=0.35, phase0=0.0)
    pad_r = chorus(bus["pad_r"], rate_hz=0.4, depth_ms=4.0, base_ms=16.0, mix=0.35, phase0=np.pi)

    wet_gtr_l = schroeder_reverb(gtr_l, wet=0.42)
    wet_gtr_r = schroeder_reverb(gtr_r, wet=0.42)
    wet_pad_l = schroeder_reverb(pad_l, wet=0.5)
    wet_pad_r = schroeder_reverb(pad_r, wet=0.5)
    # Bass nearly dry so the drive stays tight; drums just a touch of room.
    wet_bass_l = schroeder_reverb(bus["bass_l"], wet=0.08)
    wet_bass_r = schroeder_reverb(bus["bass_r"], wet=0.08)
    wet_perc_l = schroeder_reverb(bus["perc_l"], wet=0.15)
    wet_perc_r = schroeder_reverb(bus["perc_r"], wet=0.15)

    master_l = wet_bass_l + wet_perc_l + wet_gtr_l + wet_pad_l
    master_r = wet_bass_r + wet_perc_r + wet_gtr_r + wet_pad_r

    fade_in = int(0.05 * SR)
    fade_out = int(5.0 * SR)
    env = np.ones(n_samples)
    env[:fade_in] = np.linspace(0, 1, fade_in)
    env[-fade_out:] = np.linspace(1, 0, fade_out)

    out_l = np.tanh(master_l * env * 1.1)
    out_r = np.tanh(master_r * env * 1.1)

    peak = max(np.abs(out_l).max(), np.abs(out_r).max(), 1e-9)
    out_l = out_l / peak * 0.9
    out_r = out_r / peak * 0.9

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "Tracks", "modern_darkwave.wav")
    stereo_out = np.stack([out_l, out_r], axis=1)
    pcm = (stereo_out * 32767).astype(np.int16)
    wavfile.write(out_path, SR, pcm)
    print(f"Wrote {os.path.normpath(out_path)}: {total_secs:.1f}s, {total_bars} bars at {BPM} BPM")


if __name__ == "__main__":
    main()
