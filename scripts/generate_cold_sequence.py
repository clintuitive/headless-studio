"""Gary Numan / early Depeche Mode cold synthwave.

Driving TB-303-style mid-range sequence over Juno-60 chorus pads,
TR-808 drums, and a square-wave lead melody with subtle vibrato.
E minor, 116 BPM. Pure oscillators, no samples.
"""

import numpy as np
from scipy.signal import sawtooth, butter, lfilter
from scipy.io import wavfile

SR = 44100
BPM = 116
BEAT = 60.0 / BPM
BAR = BEAT * 4
SEED = 13

rng = np.random.default_rng(SEED)

# E minor: i - iv - VI - III (Em - Am - C - G)
CHORDS = [
    {"bass": 40, "pad": [52, 55, 59], "seq": [52, 59, 55, 64, 59, 55, 62, 59]},  # Em
    {"bass": 45, "pad": [57, 60, 64], "seq": [57, 64, 60, 69, 64, 60, 67, 64]},  # Am
    {"bass": 36, "pad": [48, 52, 55], "seq": [48, 55, 52, 60, 55, 52, 59, 55]},  # C
    {"bass": 43, "pad": [55, 59, 62], "seq": [55, 62, 59, 67, 62, 59, 57, 62]},  # G
]

# 4-bar melodic hook (beat_offset, duration_beats, midi)
MELODY_HOOK = [
    (0.0,  1.5, 83), (1.5, 0.5, 81), (2.0, 2.0, 79),
    (4.0,  2.0, 76), (6.0, 1.0, 74), (7.0, 1.0, 76),
    (8.0,  1.0, 83), (9.0, 0.5, 81), (9.5, 0.5, 83), (10.0, 2.0, 79),
    (12.0, 3.5, 71), (15.5, 0.5, 74),
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


def chorus(x, rate_hz=0.5, depth_ms=4.0, base_ms=15.0, mix=0.45, phase0=0.0, sr=SR):
    n = len(x)
    t = np.arange(n) / sr
    lfo = np.sin(2 * np.pi * rate_hz * t + phase0)
    delay_samples = (base_ms + depth_ms * lfo) * sr / 1000.0
    idx = np.arange(n)
    read_pos = np.clip(idx - delay_samples, 0, n - 1)
    idx0 = np.floor(read_pos).astype(int)
    idx1 = np.clip(idx0 + 1, 0, n - 1)
    frac = read_pos - idx0
    delayed = x[idx0] * (1 - frac) + x[idx1] * frac
    return x * (1 - mix) + delayed * mix


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


def seq_voice(freq, dur):
    """TB-303-style: bright filter attack that decays to dark sustain."""
    t = np.arange(int(dur * SR)) / SR
    n = len(t)
    osc = sawtooth(2 * np.pi * freq * t)
    env = adsr(n, a=0.004, d=0.08, s=0.5, r=dur * 0.3)
    bright = lowpass(osc * env, 2600)
    dark = lowpass(osc * env, 550)
    filt_env = np.exp(-np.arange(n) / SR * 22)
    return bright * filt_env + dark * (1 - filt_env)


def juno_pad(freq, dur):
    """Juno-60-style: two detuned saws + sub sine, long attack."""
    t = np.arange(int(dur * SR)) / SR
    osc = (
        sawtooth(2 * np.pi * freq * t)
        + sawtooth(2 * np.pi * freq * 1.007 * t)
        + 0.4 * np.sin(2 * np.pi * freq * 0.5 * t)
    ) / 2.4
    env = adsr(len(t), a=dur * 0.45, d=0.3, s=0.75, r=dur * 0.5)
    return lowpass(osc * env, 1100)


def bass_voice(freq, dur):
    t = np.arange(int(dur * SR)) / SR
    osc = np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(2 * np.pi * freq * 2 * t)
    env = adsr(len(t), a=0.006, d=0.15, s=0.7, r=dur * 0.3)
    return lowpass(osc * env, 320)


def lead_voice(freq, dur):
    """Square-wave lead with slight vibrato -- Gary Numan style."""
    t = np.arange(int(dur * SR)) / SR
    n = len(t)
    vib_env = np.clip((t - 0.12) * 4.0, 0, 1)
    vibrato = 1 + 0.003 * np.sin(2 * np.pi * 4.8 * t) * vib_env
    phase = np.cumsum(2 * np.pi * freq * vibrato / SR)
    osc = np.sign(np.sin(phase))
    env = adsr(n, a=0.015, d=0.12, s=0.72, r=dur * 0.45)
    return lowpass(osc * env, 2200) * 0.55


def kick_808():
    dur = 0.55
    t = np.arange(int(dur * SR)) / SR
    freq = 155 * np.exp(-t * 22) + 46
    phase = 2 * np.pi * np.cumsum(freq) / SR
    click_n = int(0.003 * SR)
    click = np.zeros(len(t))
    click[:click_n] = 0.4 * np.exp(-np.arange(click_n) / SR * 600)
    return np.sin(phase) * np.exp(-t * 5.5) + click


def clap_808():
    dur = 0.18
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    b, a = butter(2, [900 / (SR / 2), 7000 / (SR / 2)], btype="band")
    noise = lfilter(b, a, noise)
    t = np.arange(n) / SR
    env = np.exp(-t * 38) + 0.55 * np.exp(-np.maximum(t - 0.009, 0) * 28)
    return noise * env * 0.85


def hihat(open_hat=False):
    dur = 0.1 if open_hat else 0.038
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    b, a = butter(2, [7500 / (SR / 2), 13500 / (SR / 2)], btype="band")
    noise = lfilter(b, a, noise)
    decay = 30 if open_hat else 100
    return noise * np.exp(-np.arange(n) / SR * decay) * (0.45 if open_hat else 0.28)


def render_bar(seq_l, seq_r, pad_l, pad_r, perc_l, perc_r,
               bar_t, chord_idx, *, seq=False, pad=False, bass=False,
               drums=None, seq_gain=1.0, pad_gain=1.0):
    chord = CHORDS[chord_idx % 4]
    step = BEAT / 2

    if seq:
        for k, midi in enumerate(chord["seq"]):
            sig = seq_voice(midi_to_freq(midi), step * 1.6) * seq_gain * 0.7
            l, r = stereo(sig, 0.0)
            mix_add(seq_l, seq_r, bar_t + k * step, l, r)

    if pad:
        for j, midi in enumerate(chord["pad"]):
            gain = pad_gain * (0.8 if j < 2 else 0.5)
            sig = juno_pad(midi_to_freq(midi), BAR * 1.35) * gain
            l, r = stereo(sig, pan=-0.35 + 0.35 * j)
            mix_add(pad_l, pad_r, bar_t, l, r)

    if bass:
        sig = bass_voice(midi_to_freq(chord["bass"]), BAR * 1.05) * 0.85
        mix_add(pad_l, pad_r, bar_t, sig, sig)

    if drums == "full":
        for beat_i in range(4):
            k = kick_808() * 0.72
            mix_add(perc_l, perc_r, bar_t + beat_i * BEAT, k, k)
        for beat_i in (1, 3):
            c = clap_808() * 0.55
            mix_add(perc_l, perc_r, bar_t + beat_i * BEAT, c, c)
        for k8 in range(8):
            is_open = (k8 == 6)
            h = hihat(is_open)
            mix_add(perc_l, perc_r, bar_t + k8 * step, h, h)
    elif drums == "sparse":
        for beat_i in (0, 2):
            k = kick_808() * 0.65
            mix_add(perc_l, perc_r, bar_t + beat_i * BEAT, k, k)
        if rng.random() < 0.7:
            c = clap_808() * 0.45
            mix_add(perc_l, perc_r, bar_t + 2 * BEAT, c, c)


def render_melody(lead_l, lead_r, section_start_t, n_bars):
    for loop_i in range(n_bars // 4):
        loop_t = section_start_t + loop_i * BAR * 4
        for beat_off, dur_b, midi in MELODY_HOOK:
            t0 = loop_t + beat_off * BEAT
            dur = dur_b * BEAT + 0.1
            sig = lead_voice(midi_to_freq(midi), dur) * 0.65
            l, r = stereo(sig, pan=0.15)
            mix_add(lead_l, lead_r, t0, l, r)


def main():
    sections = [
        dict(n_bars=8,  seq=True, pad=False, bass=False, drums=None,     melody=False, seq_gain=0.7),
        dict(n_bars=8,  seq=True, pad=True,  bass=False, drums=None,     melody=False, pad_gain=0.45),
        dict(n_bars=8,  seq=True, pad=True,  bass=True,  drums="sparse", melody=False, pad_gain=0.7),
        dict(n_bars=16, seq=True, pad=True,  bass=True,  drums="full",   melody=False),
        dict(n_bars=16, seq=True, pad=True,  bass=True,  drums="full",   melody=True),
        dict(n_bars=8,  seq=True, pad=True,  bass=False, drums=None,     melody=False, pad_gain=0.75),
        dict(n_bars=8,  seq=True, pad=True,  bass=True,  drums="sparse", melody=False),
        dict(n_bars=24, seq=True, pad=True,  bass=True,  drums="full",   melody=True),
        dict(n_bars=8,  seq=True, pad=True,  bass=False, drums=None,     melody=False, pad_gain=0.5),
        dict(n_bars=8,  seq=True, pad=False, bass=False, drums=None,     melody=False, seq_gain=0.4),
    ]

    total_bars = sum(s["n_bars"] for s in sections)
    total_secs = total_bars * BAR + 5.0
    n_samples = int(total_secs * SR)

    seq_l, seq_r = np.zeros(n_samples), np.zeros(n_samples)
    pad_l, pad_r = np.zeros(n_samples), np.zeros(n_samples)
    perc_l, perc_r = np.zeros(n_samples), np.zeros(n_samples)
    lead_l, lead_r = np.zeros(n_samples), np.zeros(n_samples)

    bar_cursor = 0
    for s in sections:
        seq_gain = s.get("seq_gain", 1.0)
        pad_gain = s.get("pad_gain", 1.0)
        for bar_i in range(s["n_bars"]):
            render_bar(
                seq_l, seq_r, pad_l, pad_r, perc_l, perc_r,
                bar_cursor * BAR + bar_i * BAR, bar_i % 4,
                seq=s["seq"], pad=s["pad"], bass=s["bass"],
                drums=s["drums"], seq_gain=seq_gain, pad_gain=pad_gain,
            )
        if s.get("melody"):
            render_melody(lead_l, lead_r, bar_cursor * BAR, s["n_bars"])
        bar_cursor += s["n_bars"]

    # Stereo chorus on pads (opposite LFO phase L/R for width)
    pad_l = chorus(pad_l, rate_hz=0.45, depth_ms=3.5, base_ms=14.0, mix=0.4, phase0=0.0)
    pad_r = chorus(pad_r, rate_hz=0.45, depth_ms=3.5, base_ms=14.0, mix=0.4, phase0=np.pi)

    wet_seq_l = schroeder_reverb(seq_l, wet=0.18)
    wet_seq_r = schroeder_reverb(seq_r, wet=0.18)
    wet_pad_l = schroeder_reverb(pad_l, wet=0.30)
    wet_pad_r = schroeder_reverb(pad_r, wet=0.30)
    wet_perc_l = schroeder_reverb(perc_l, wet=0.20)
    wet_perc_r = schroeder_reverb(perc_r, wet=0.20)
    wet_lead_l = schroeder_reverb(lead_l, wet=0.28)
    wet_lead_r = schroeder_reverb(lead_r, wet=0.28)

    master_l = wet_seq_l + wet_pad_l + wet_perc_l + wet_lead_l
    master_r = wet_seq_r + wet_pad_r + wet_perc_r + wet_lead_r

    fade_in = int(2.0 * SR)
    fade_out = int(5.0 * SR)
    env = np.ones(n_samples)
    env[:fade_in] = np.linspace(0, 1, fade_in)
    env[-fade_out:] = np.linspace(1, 0, fade_out)

    out_l = np.tanh(master_l * env * 1.05)
    out_r = np.tanh(master_r * env * 1.05)
    peak = max(np.abs(out_l).max(), np.abs(out_r).max(), 1e-9)
    out_l = out_l / peak * 0.91
    out_r = out_r / peak * 0.91

    stereo_out = np.stack([out_l, out_r], axis=1)
    pcm = (stereo_out * 32767).astype(np.int16)
    wavfile.write("cold_sequence.wav", SR, pcm)
    print(f"Wrote cold_sequence.wav: {total_secs:.1f}s, {total_bars} bars at {BPM} BPM")


if __name__ == "__main__":
    main()
