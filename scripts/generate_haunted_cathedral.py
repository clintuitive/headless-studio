"""The Cure 'Faith' era / early 4AD haunted cathedral sound.

Washed-out sine ensemble pads, triangle-wave arpeggios, sparse glockenspiel
hits, a string-like lead melody with slow vibrato, and a minimal drum machine
(kick on 1, snare on 3) with heavy reverb. B minor, 72 BPM.
Pure oscillators, no samples.
"""

import numpy as np
from scipy.signal import sawtooth, butter, lfilter
from scipy.io import wavfile

SR = 44100
BPM = 72
BEAT = 60.0 / BPM
BAR = BEAT * 4
SEED = 33

rng = np.random.default_rng(SEED)

# B minor: i - VI - iv - VII (Bm - G - Em - A)
CHORDS = {
    "Bm": {"bass": 47, "pad": [59, 62, 66], "arp": [59, 62, 66, 71, 66, 62, 59, 62], "glock": 83},
    "G":  {"bass": 43, "pad": [55, 59, 62], "arp": [55, 59, 62, 67, 62, 59, 55, 59], "glock": 79},
    "Em": {"bass": 40, "pad": [52, 55, 59], "arp": [52, 55, 59, 64, 59, 55, 52, 55], "glock": 76},
    "A":  {"bass": 45, "pad": [57, 61, 64], "arp": [57, 61, 64, 69, 64, 61, 57, 61], "glock": 78},
}
PROG = ["Bm", "G", "Em", "A"]

# 4-bar haunting lead melody (beat_offset, duration_beats, midi)
LEAD_MELODY = [
    (0.0,  2.5, 78), (2.5, 0.5, 76), (3.0, 1.0, 74),
    (4.0,  2.0, 71), (6.0, 1.5, 73), (7.5, 0.5, 71),
    (8.0,  2.0, 76), (10.0, 1.0, 74), (11.0, 1.0, 73),
    (12.0, 3.5, 66), (15.5, 0.5, 71),
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


def cure_pad(freq, dur):
    """Detuned sine ensemble -- washed-out, very slow attack."""
    t = np.arange(int(dur * SR)) / SR
    osc = (
        np.sin(2 * np.pi * freq * t)
        + 0.6 * np.sin(2 * np.pi * freq * 1.005 * t)
        + 0.6 * np.sin(2 * np.pi * freq * 0.995 * t)
        + 0.2 * np.sin(2 * np.pi * freq * 2.003 * t)
    ) / 2.4
    env = adsr(len(t), a=dur * 0.6, d=0.5, s=0.65, r=dur * 0.55)
    return lowpass(osc * env, 700)


def arp_voice(freq, dur):
    """Triangle-wave arp note -- gentle, ethereal."""
    t = np.arange(int(dur * SR)) / SR
    osc = sawtooth(2 * np.pi * freq * t, width=0.5)
    env = adsr(len(t), a=0.01, d=0.12, s=0.3, r=dur * 0.7)
    return lowpass(osc * env, 1800) * 0.45


def glockenspiel_voice(freq):
    """Bell with non-harmonic partials -- sparse, high, haunting."""
    dur = 0.8
    t = np.arange(int(dur * SR)) / SR
    osc = (
        np.sin(2 * np.pi * freq * t)
        + 0.5 * np.sin(2 * np.pi * freq * 2.756 * t)
        + 0.2 * np.sin(2 * np.pi * freq * 5.4 * t)
    )
    return osc * np.exp(-t * 5.5) * 0.35


def string_lead(freq, dur):
    """Slow-attack string-like voice with vibrato -- The Cure lead sound."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    vib_env = np.clip((t - 0.2) * 3.0, 0, 1)
    vib = 1 + 0.004 * np.sin(2 * np.pi * 4.5 * t) * vib_env
    phase = 2 * np.pi * np.cumsum(freq * vib) / SR
    osc = (
        np.sin(phase)
        + 0.5 * np.sin(2 * np.pi * freq * 1.004 * t)
        + 0.5 * np.sin(2 * np.pi * freq * 0.996 * t)
    ) / 2.0
    env = adsr(n, a=dur * 0.35, d=0.4, s=0.7, r=dur * 0.5)
    return lowpass(osc * env, 1500)


def cure_kick():
    dur = 0.4
    t = np.arange(int(dur * SR)) / SR
    freq = 100 * np.exp(-t * 10) + 50
    phase = 2 * np.pi * np.cumsum(freq) / SR
    return np.sin(phase) * np.exp(-t * 7)


def cure_snare():
    dur = 0.3
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    b, a = butter(2, [200 / (SR / 2), 4000 / (SR / 2)], btype="band")
    noise = lfilter(b, a, noise)
    t = np.arange(n) / SR
    tone = 0.4 * np.sin(2 * np.pi * 180 * t) * np.exp(-t * 15)
    return (noise * 0.7 + tone) * np.exp(-t * 14) * 0.7


def cure_hihat():
    dur = 0.06
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    b, a = butter(2, [6000 / (SR / 2), 12000 / (SR / 2)], btype="band")
    noise = lfilter(b, a, noise)
    return noise * np.exp(-np.arange(n) / SR * 70) * 0.2


def render_movement(pad_l, pad_r, arp_l, arp_r, perc_l, perc_r,
                    start_bar, n_bars, *, pad_gain=1.0, arp=False,
                    drums=None, glock=False):
    step = BEAT / 2
    for bar_i in range(n_bars):
        bar_t = (start_bar + bar_i) * BAR
        chord_name = PROG[bar_i % len(PROG)]
        c = CHORDS[chord_name]

        for j, midi in enumerate(c["pad"]):
            gain = pad_gain * (0.75 if j == 0 else 0.55)
            sig = cure_pad(midi_to_freq(midi), BAR * 1.4) * gain
            l, r = stereo(sig, pan=-0.3 + 0.3 * j)
            mix_add(pad_l, pad_r, bar_t, l, r)

        if arp:
            for k, midi in enumerate(c["arp"]):
                sig = arp_voice(midi_to_freq(midi), step * 2.2)
                pan = -0.35 if k % 2 == 0 else 0.35
                l, r = stereo(sig, pan=pan)
                mix_add(arp_l, arp_r, bar_t + k * step, l, r)

        if glock and bar_i % 2 == 0:
            sig = glockenspiel_voice(midi_to_freq(c["glock"]))
            l, r = stereo(sig, pan=0.5)
            mix_add(arp_l, arp_r, bar_t + 2 * BEAT, l, r)

        if drums == "sparse":
            k = cure_kick() * 0.75
            mix_add(perc_l, perc_r, bar_t, k, k)
            s = cure_snare() * 0.65
            mix_add(perc_l, perc_r, bar_t + 2 * BEAT, s, s)
        elif drums == "full":
            for beat_i in (0, 2):
                k = cure_kick() * 0.8
                mix_add(perc_l, perc_r, bar_t + beat_i * BEAT, k, k)
            s = cure_snare() * 0.68
            mix_add(perc_l, perc_r, bar_t + 2 * BEAT, s, s)
            for beat_i in (1, 3):
                h = cure_hihat()
                mix_add(perc_l, perc_r, bar_t + beat_i * BEAT, h, h)


def render_lead(lead_l, lead_r, section_start_t, n_bars):
    for loop_i in range(n_bars // 4):
        loop_t = section_start_t + loop_i * BAR * 4
        for beat_off, dur_b, midi in LEAD_MELODY:
            t0 = loop_t + beat_off * BEAT
            dur = dur_b * BEAT + 0.15
            sig = string_lead(midi_to_freq(midi), dur) * 0.6
            l, r = stereo(sig, pan=0.1)
            mix_add(lead_l, lead_r, t0, l, r)


def main():
    movements = [
        dict(n_bars=8,  pad_gain=0.4,  arp=False, drums=None,     glock=False, lead=False),
        dict(n_bars=8,  pad_gain=0.65, arp=True,  drums=None,     glock=False, lead=False),
        dict(n_bars=8,  pad_gain=0.75, arp=True,  drums="sparse", glock=True,  lead=False),
        dict(n_bars=16, pad_gain=0.85, arp=True,  drums="sparse", glock=True,  lead=True),
        dict(n_bars=8,  pad_gain=0.6,  arp=True,  drums=None,     glock=True,  lead=False),
        dict(n_bars=24, pad_gain=0.9,  arp=True,  drums="full",   glock=True,  lead=True),
        dict(n_bars=8,  pad_gain=0.65, arp=True,  drums=None,     glock=False, lead=False),
        dict(n_bars=16, pad_gain=0.4,  arp=False, drums=None,     glock=False, lead=False),
    ]

    total_bars = sum(m["n_bars"] for m in movements)
    total_secs = total_bars * BAR + 8.0
    n_samples = int(total_secs * SR)

    pad_l, pad_r = np.zeros(n_samples), np.zeros(n_samples)
    arp_l, arp_r = np.zeros(n_samples), np.zeros(n_samples)
    perc_l, perc_r = np.zeros(n_samples), np.zeros(n_samples)
    lead_l, lead_r = np.zeros(n_samples), np.zeros(n_samples)

    bar_cursor = 0
    for m in movements:
        render_movement(
            pad_l, pad_r, arp_l, arp_r, perc_l, perc_r,
            bar_cursor, m["n_bars"],
            pad_gain=m["pad_gain"], arp=m["arp"],
            drums=m["drums"], glock=m["glock"],
        )
        if m.get("lead"):
            render_lead(lead_l, lead_r, bar_cursor * BAR, m["n_bars"])
        bar_cursor += m["n_bars"]

    # Separate reverb sends -- pads and arps very wet, drums medium, lead light
    wet_pad_l = schroeder_reverb(pad_l, wet=0.52)
    wet_pad_r = schroeder_reverb(pad_r, wet=0.52)
    wet_arp_l = schroeder_reverb(arp_l, wet=0.48)
    wet_arp_r = schroeder_reverb(arp_r, wet=0.48)
    wet_perc_l = schroeder_reverb(perc_l, wet=0.40)
    wet_perc_r = schroeder_reverb(perc_r, wet=0.40)
    wet_lead_l = schroeder_reverb(lead_l, wet=0.35)
    wet_lead_r = schroeder_reverb(lead_r, wet=0.35)

    master_l = wet_pad_l + wet_arp_l + wet_perc_l + wet_lead_l
    master_r = wet_pad_r + wet_arp_r + wet_perc_r + wet_lead_r

    fade_in = int(3.0 * SR)
    fade_out = int(7.0 * SR)
    env = np.ones(n_samples)
    env[:fade_in] = np.linspace(0, 1, fade_in)
    env[-fade_out:] = np.linspace(1, 0, fade_out)

    out_l = np.tanh(master_l * env * 1.05)
    out_r = np.tanh(master_r * env * 1.05)
    peak = max(np.abs(out_l).max(), np.abs(out_r).max(), 1e-9)
    out_l = out_l / peak * 0.90
    out_r = out_r / peak * 0.90

    stereo_out = np.stack([out_l, out_r], axis=1)
    pcm = (stereo_out * 32767).astype(np.int16)
    wavfile.write("haunted_cathedral.wav", SR, pcm)
    print(f"Wrote haunted_cathedral.wav: {total_secs:.1f}s, {total_bars} bars at {BPM} BPM")


if __name__ == "__main__":
    main()
