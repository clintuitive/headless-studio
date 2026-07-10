"""Kraftwerk meets Joy Division -- Berlin School sequencer track.

A hypnotic, mechanical sawtooth sequence over cold organ-like pads,
Peter Hook-style high melodic bass, syncopated chord stabs, and a
precise kick+snare drum machine. F minor, 100 BPM.
Pure oscillators, no samples.
"""

import numpy as np
from scipy.signal import sawtooth, butter, lfilter
from scipy.io import wavfile

SR = 44100
BPM = 100
BEAT = 60.0 / BPM
BAR = BEAT * 4
SEED = 42

rng = np.random.default_rng(SEED)

# F minor: i - bVI - bIII - bVII (Fm - Db - Ab - Eb)
CHORDS = [
    {"bass": 41, "pad": [53, 56, 60], "seq": [53, 60, 56, 65, 60, 56, 53, 63], "stab": [65, 60]},  # Fm
    {"bass": 37, "pad": [49, 53, 56], "seq": [49, 56, 53, 61, 56, 53, 49, 60], "stab": [61, 56]},  # Db
    {"bass": 44, "pad": [56, 60, 63], "seq": [56, 63, 60, 68, 63, 60, 56, 65], "stab": [68, 63]},  # Ab
    {"bass": 39, "pad": [51, 55, 58], "seq": [51, 58, 55, 63, 58, 55, 51, 58], "stab": [63, 58]},  # Eb
]

# 4-bar melodic bass hook (beat_offset, duration_beats, midi) -- Peter Hook style
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
    cutoff = min(max(float(cutoff), 50.0), sr / 2.0 - 100.0)
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


def mix_add(buf_l, buf_r, start_t, sig_l, sig_r):
    start = int(start_t * SR)
    end = min(start + len(sig_l), len(buf_l))
    if end <= start:
        return
    n = end - start
    buf_l[start:end] += sig_l[:n]
    buf_r[start:end] += sig_r[:n]


def stereo(sig, pan=0.0):
    return sig * np.sqrt(0.5 * (1 - pan)), sig * np.sqrt(0.5 * (1 + pan))


def kraft_seq(freq, dur):
    """Clean, mechanical sawtooth sequence note -- Kraftwerk style."""
    t = np.arange(int(dur * SR)) / SR
    osc = sawtooth(2 * np.pi * freq * t)
    env = adsr(len(t), a=0.004, d=0.07, s=0.65, r=dur * 0.25)
    return lowpass(osc * env, 1900) * 0.6


def kraft_pad(freq, dur):
    """Cold organ-like pad: sine harmonics, slow attack -- Computer Love."""
    t = np.arange(int(dur * SR)) / SR
    osc = (
        np.sin(2 * np.pi * freq * t)
        + 0.3 * np.sin(2 * np.pi * freq * 2 * t)
        + 0.1 * np.sin(2 * np.pi * freq * 3 * t)
    )
    env = adsr(len(t), a=dur * 0.55, d=0.5, s=0.8, r=dur * 0.4)
    return lowpass(osc * env, 750) * 0.5


def hook_bass(freq, dur):
    """Bright, picked melodic bass -- Peter Hook high-register style."""
    t = np.arange(int(dur * SR)) / SR
    osc = 0.7 * sawtooth(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * freq * t)
    pick_n = min(int(0.008 * SR), len(t))
    pick = np.zeros(len(t))
    pick[:pick_n] = rng.standard_normal(pick_n) * np.exp(-np.arange(pick_n) / SR * 500)
    env = adsr(len(t), a=0.003, d=0.1, s=0.65, r=dur * 0.3)
    sig = np.tanh((osc * env + pick * 0.2) * 1.2)
    return lowpass(sig, 2500) * 0.7


def stab_voice(freqs):
    """Short punchy synth stab on off-beats -- Trans-Europe Express style."""
    dur = 0.09
    t = np.arange(int(dur * SR)) / SR
    osc = sum(sawtooth(2 * np.pi * f * t) for f in freqs) / len(freqs)
    env = adsr(len(t), a=0.002, d=0.04, s=0.1, r=0.03)
    return lowpass(osc * env, 2600) * 0.65


def mech_kick():
    dur = 0.35
    t = np.arange(int(dur * SR)) / SR
    freq = 130 * np.exp(-t * 20) + 48
    phase = 2 * np.pi * np.cumsum(freq) / SR
    return np.sin(phase) * np.exp(-t * 8)


def mech_snare():
    dur = 0.22
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    b, a = butter(2, [400 / (SR / 2), 5000 / (SR / 2)], btype="band")
    noise = lfilter(b, a, noise)
    t = np.arange(n) / SR
    env = np.exp(-t * 22)
    return noise * env * 0.8


def render_bar(seq_l, seq_r, pad_l, pad_r, perc_l, perc_r,
               bar_t, chord_idx, *, seq=False, pad=False, drums=None,
               stabs=False, pad_gain=1.0):
    chord = CHORDS[chord_idx % 4]
    step = BEAT / 2

    if seq:
        for k, midi in enumerate(chord["seq"]):
            sig = kraft_seq(midi_to_freq(midi), step * 1.5)
            l, r = stereo(sig, 0.0)
            mix_add(seq_l, seq_r, bar_t + k * step, l, r)

    if pad:
        for j, midi in enumerate(chord["pad"]):
            gain = pad_gain * (0.85 if j == 0 else 0.65)
            sig = kraft_pad(midi_to_freq(midi), BAR * 1.3) * gain
            l, r = stereo(sig, pan=-0.3 + 0.3 * j)
            mix_add(pad_l, pad_r, bar_t, l, r)

    if stabs:
        stab_freqs = [midi_to_freq(m) for m in chord["stab"]]
        for beat_off in (1.5, 3.5):
            sig = stab_voice(stab_freqs)
            l, r = stereo(sig, 0.0)
            mix_add(seq_l, seq_r, bar_t + beat_off * BEAT, l, r)

    if drums == "full":
        for beat_i in (0, 2):
            k = mech_kick() * 0.82
            mix_add(perc_l, perc_r, bar_t + beat_i * BEAT, k, k)
        for beat_i in (1, 3):
            s = mech_snare() * 0.72
            mix_add(perc_l, perc_r, bar_t + beat_i * BEAT, s, s)


def render_bass(bass_l, bass_r, section_start_t, n_bars):
    for loop_i in range(n_bars // 4):
        loop_t = section_start_t + loop_i * BAR * 4
        for beat_off, dur_b, midi in BASS_HOOK:
            t0 = loop_t + beat_off * BEAT
            dur = dur_b * BEAT + 0.05
            sig = hook_bass(midi_to_freq(midi), dur)
            mix_add(bass_l, bass_r, t0, sig, sig)


def main():
    movements = [
        dict(n_bars=8,  seq=True, bass=False, pad=False, drums=None,   stabs=False),
        dict(n_bars=8,  seq=True, bass=True,  pad=False, drums=None,   stabs=False),
        dict(n_bars=8,  seq=True, bass=True,  pad=False, drums="full", stabs=False),
        dict(n_bars=8,  seq=True, bass=True,  pad=True,  drums="full", stabs=False, pad_gain=0.6),
        dict(n_bars=16, seq=True, bass=True,  pad=True,  drums="full", stabs=True,  pad_gain=0.8),
        dict(n_bars=16, seq=True, bass=True,  pad=True,  drums="full", stabs=True),
        dict(n_bars=8,  seq=True, bass=False, pad=True,  drums=None,   stabs=False, pad_gain=0.7),
        dict(n_bars=16, seq=True, bass=True,  pad=True,  drums="full", stabs=True),
        dict(n_bars=8,  seq=True, bass=False, pad=False, drums=None,   stabs=False),
    ]

    total_bars = sum(m["n_bars"] for m in movements)
    total_secs = total_bars * BAR + 5.0
    n_samples = int(total_secs * SR)

    seq_l, seq_r = np.zeros(n_samples), np.zeros(n_samples)
    pad_l, pad_r = np.zeros(n_samples), np.zeros(n_samples)
    perc_l, perc_r = np.zeros(n_samples), np.zeros(n_samples)
    bass_l, bass_r = np.zeros(n_samples), np.zeros(n_samples)

    bar_cursor = 0
    for m in movements:
        pad_gain = m.get("pad_gain", 1.0)
        for bar_i in range(m["n_bars"]):
            render_bar(
                seq_l, seq_r, pad_l, pad_r, perc_l, perc_r,
                bar_cursor * BAR + bar_i * BAR, bar_i % 4,
                seq=m["seq"], pad=m["pad"], drums=m["drums"],
                stabs=m["stabs"], pad_gain=pad_gain,
            )
        if m["bass"]:
            render_bass(bass_l, bass_r, bar_cursor * BAR, m["n_bars"])
        bar_cursor += m["n_bars"]

    # Separate reverb sends -- sequence and stabs tight, pads cold and spacious
    wet_seq_l = schroeder_reverb(seq_l, wet=0.14)
    wet_seq_r = schroeder_reverb(seq_r, wet=0.14)
    wet_pad_l = schroeder_reverb(pad_l, wet=0.38)
    wet_pad_r = schroeder_reverb(pad_r, wet=0.38)
    wet_perc_l = schroeder_reverb(perc_l, wet=0.18)
    wet_perc_r = schroeder_reverb(perc_r, wet=0.18)
    wet_bass_l = schroeder_reverb(bass_l, wet=0.22)
    wet_bass_r = schroeder_reverb(bass_r, wet=0.22)

    master_l = wet_seq_l + wet_pad_l + wet_perc_l + wet_bass_l
    master_r = wet_seq_r + wet_pad_r + wet_perc_r + wet_bass_r

    fade_in = int(2.0 * SR)
    fade_out = int(5.0 * SR)
    env = np.ones(n_samples)
    env[:fade_in] = np.linspace(0, 1, fade_in)
    env[-fade_out:] = np.linspace(1, 0, fade_out)

    out_l = np.tanh(master_l * env * 1.08)
    out_r = np.tanh(master_r * env * 1.08)
    peak = max(np.abs(out_l).max(), np.abs(out_r).max(), 1e-9)
    out_l = out_l / peak * 0.91
    out_r = out_r / peak * 0.91

    stereo_out = np.stack([out_l, out_r], axis=1)
    pcm = (stereo_out * 32767).astype(np.int16)
    wavfile.write("berlin_sequence.wav", SR, pcm)
    print(f"Wrote berlin_sequence.wav: {total_secs:.1f}s, {total_bars} bars at {BPM} BPM")


if __name__ == "__main__":
    main()
