"""Synthesizes an upbeat, pop-structured synthwave track and renders it to a WAV file.

Distinct from generate_ambient_synthwave.py: a real verse/chorus/bridge song
form in G major, built around a repeating plucked synth riff (the "hook"),
a sung-style sustained lead melody in the choruses, punchy quarter-note pop
bass, four-on-the-floor kick/snare/clap/hihat, filter-sweep risers between
movements, and the same sidechain "pump" technique as the ambient track.
Everything is synthesized with oscillators + envelopes, no samples.
"""

import numpy as np
from scipy.signal import sawtooth, butter, lfilter
from scipy.io import wavfile

SR = 44100
BPM = 122
BEAT = 60.0 / BPM
BAR = BEAT * 4
SEED = 13

rng = np.random.default_rng(SEED)

# G major: I-V-vi-IV (chorus) / vi-IV-I-V (verse) -- the two classic pop axes.
CHORDS = {
    "G":  {"bass": 43, "pad": [67, 71, 74], "color": 81, "third": 4},  # G2 / G4-B4-D5, +A5(9th)
    "D":  {"bass": 38, "pad": [62, 66, 69], "color": 76, "third": 4},  # D2 / D4-F#4-A4, +E5(9th)
    "Em": {"bass": 40, "pad": [64, 67, 71], "color": 78, "third": 3},  # E2 / E4-G4-B4, +F#5(9th)
    "C":  {"bass": 36, "pad": [60, 64, 67], "color": 74, "third": 4},  # C2 / C4-E4-G4, +D5(9th)
}
VERSE_PROG = ["Em", "C", "G", "D"]
CHORUS_PROG = ["G", "D", "Em", "C"]
PRECHORUS_PROG = ["C", "C", "D", "D"]
BRIDGE_PROG = ["Em", "C"]
BUILD_PROG = ["C", "D"]

# Riff hook: root-fifth-octave-fifth stabs with a passing third, repeats each bar.
RIFF_FULL = [
    (0.0, 0.5, "root"), (0.5, 0.5, "fifth"), (1.0, 0.5, "octave"), (1.5, 0.5, "fifth"),
    (2.0, 0.5, "root"), (2.5, 0.25, "third"), (2.75, 0.25, "fifth"),
    (3.0, 0.5, "octave"), (3.5, 0.5, "fifth"),
]
RIFF_SPARSE = [(0.0, 0.75, "root"), (2.0, 0.75, "fifth")]
HOOK_MELODY = [(0.0, 2.0, "octave"), (2.0, 2.0, "fifth")]


def midi_to_freq(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def tone_freq(chord, token):
    root = chord["pad"][0]
    offset = {"root": 0, "third": chord["third"], "fifth": 7, "octave": 12}[token]
    return midi_to_freq(root + offset)


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


def schroeder_reverb(x, wet=0.25, sr=SR):
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
    l_gain = np.sqrt(0.5 * (1 - pan))
    r_gain = np.sqrt(0.5 * (1 + pan))
    return sig * l_gain, sig * r_gain


# ---- instrument voices -----------------------------------------------------

def pad_voice(freq, dur, cutoff=1700, detune=0.004):
    t = np.arange(int(dur * SR)) / SR
    osc = (
        np.sin(2 * np.pi * freq * t)
        + 0.5 * sawtooth(2 * np.pi * freq * (1 + detune) * t)
        + 0.5 * sawtooth(2 * np.pi * freq * (1 - detune) * t)
    ) / 2.0
    env = adsr(len(t), a=dur * 0.4, d=0.2, s=0.85, r=dur * 0.35)
    return lowpass(osc * env, cutoff)


def pad_stab(freq, dur, cutoff=2200):
    t = np.arange(int(dur * SR)) / SR
    osc = 0.5 * np.sin(2 * np.pi * freq * t) + 0.5 * sawtooth(2 * np.pi * freq * t)
    env = adsr(len(t), a=0.004, d=0.18, s=0.08, r=dur * 0.3)
    return lowpass(osc * env, cutoff)


def bass_hit(freq, dur):
    t = np.arange(int(dur * SR)) / SR
    osc = np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(2 * np.pi * freq * 2 * t)
    env = adsr(len(t), a=0.003, d=0.09, s=0.25, r=dur * 0.4)
    return osc * env


def pluck_voice(freq, dur, cutoff=3000):
    t = np.arange(int(dur * SR)) / SR
    osc = sawtooth(2 * np.pi * freq * t)
    env = adsr(len(t), a=0.002, d=0.1, s=0.05, r=dur * 0.3)
    return lowpass(osc * env, cutoff)


def lead_voice(freq, dur):
    t = np.arange(int(dur * SR)) / SR
    osc = 0.6 * np.sin(2 * np.pi * freq * t) + 0.4 * sawtooth(2 * np.pi * freq * 1.003 * t)
    env = adsr(len(t), a=dur * 0.25, d=0.2, s=0.75, r=dur * 0.45)
    return lowpass(osc * env, 2000)


def kick():
    dur = 0.3
    t = np.arange(int(dur * SR)) / SR
    freq = 150 * np.exp(-t * 20) + 45
    phase = 2 * np.pi * np.cumsum(freq) / SR
    return np.sin(phase) * np.exp(-t * 16)


def snare():
    dur = 0.2
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    b, a = butter(2, [1000 / (SR / 2), 7000 / (SR / 2)], btype="band")
    noise = lfilter(b, a, noise)
    tone = np.sin(2 * np.pi * 180 * t) * np.exp(-t * 40)
    return noise * np.exp(-t * 22) * 0.8 + tone * 0.5


def clap():
    dur = 0.15
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    b, a = butter(2, [1500 / (SR / 2), 4000 / (SR / 2)], btype="band")
    noise = lfilter(b, a, noise)
    env = np.exp(-t * 35) + 0.6 * np.exp(-np.maximum(t - 0.012, 0) * 60)
    return noise * env


def hihat(open_=False):
    dur = 0.18 if open_ else 0.05
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    b, a = butter(2, [9000 / (SR / 2), 16000 / (SR / 2)], btype="band")
    noise = lfilter(b, a, noise)
    env = np.exp(-np.arange(n) / SR * (18 if open_ else 70))
    return noise * env * 0.5


def riser(dur, intensity=1.0):
    n = max(int(dur * SR), 1)
    noise = rng.standard_normal(n)
    chunks = 10
    chunk_len = max(n // chunks, 1)
    out = np.zeros(n)
    for i in range(chunks):
        start = i * chunk_len
        end = n if i == chunks - 1 else min(start + chunk_len, n)
        if start >= end:
            continue
        cutoff = min(300 + (i / (chunks - 1)) * 7000, SR / 2 - 200)
        b, a = butter(2, cutoff / (SR / 2), btype="high")
        out[start:end] = lfilter(b, a, noise[start:end])
    env = (np.arange(n) / n) ** 1.3
    return out * env * 0.6 * intensity


# ---- arrangement ------------------------------------------------------------

def render_bar(tonal_l, tonal_r, perc_l, perc_r, kick_times, bar_t, chord_name, *,
               pad_mode="sustain", pad_gain=1.0, cutoff=1700, bass=True,
               riff_mode=None, hook=False, drum_mode=None):
    c = CHORDS[chord_name]

    if pad_mode == "sustain":
        for j, midi in enumerate([*c["pad"], c["color"]]):
            gain = pad_gain * (0.85 if j < 3 else 0.35)
            sig = pad_voice(midi_to_freq(midi), BAR * 1.3, cutoff=cutoff) * gain
            l, r = stereo(sig, pan=-0.3 + 0.2 * j)
            mix_add(tonal_l, tonal_r, bar_t, l, r)
    elif pad_mode == "stab":
        for beat_i in (0, 2):
            for j, midi in enumerate(c["pad"]):
                sig = pad_stab(midi_to_freq(midi), BEAT * 1.3, cutoff=cutoff) * pad_gain * 0.7
                l, r = stereo(sig, pan=-0.25 + 0.25 * j)
                mix_add(tonal_l, tonal_r, bar_t + beat_i * BEAT, l, r)

    if bass:
        for beat_i in range(4):
            sig = bass_hit(midi_to_freq(c["bass"]), BEAT * 0.9) * 0.95
            mix_add(tonal_l, tonal_r, bar_t + beat_i * BEAT, sig, sig)

    if riff_mode:
        motif = RIFF_FULL if riff_mode == "full" else RIFF_SPARSE
        for beat_off, dur_b, token in motif:
            sig = pluck_voice(tone_freq(c, token), dur_b * BEAT * 1.3) * 0.45
            pan = 0.4 if (beat_off * 2) % 2 == 0 else -0.4
            l, r = stereo(sig, pan=pan)
            mix_add(tonal_l, tonal_r, bar_t + beat_off * BEAT, l, r)

    if hook:
        for beat_off, dur_b, token in HOOK_MELODY:
            sig = lead_voice(tone_freq(c, token), dur_b * BEAT * 1.1) * 0.4
            l, r = stereo(sig, pan=0.05)
            mix_add(tonal_l, tonal_r, bar_t + beat_off * BEAT, l, r)

    if drum_mode in ("light", "full"):
        for beat_i in range(4):
            t0 = bar_t + beat_i * BEAT
            k = kick() * 0.55
            mix_add(perc_l, perc_r, t0, k, k)
            kick_times.append(t0)

        if drum_mode == "full":
            for beat_i in (1, 3):
                t0 = bar_t + beat_i * BEAT
                s = snare() * 0.5
                mix_add(perc_l, perc_r, t0, s, s)
                cl = clap() * 0.35
                mix_add(perc_l, perc_r, t0, cl, cl)
            for step in range(16):
                if step % 2 == 0 or rng.random() < 0.7:
                    open_ = step == 15
                    h = hihat(open_=open_) * (0.3 if open_ else 0.35)
                    mix_add(perc_l, perc_r, bar_t + step * (BEAT / 4), h, h)
        else:
            for step in range(8):
                h = hihat() * 0.2
                mix_add(perc_l, perc_r, bar_t + step * (BEAT / 2), h, h)
            cl = clap() * 0.25
            mix_add(perc_l, perc_r, bar_t + 2 * BEAT, cl, cl)


def render_movement(tonal_l, tonal_r, perc_l, perc_r, kick_times, start_bar, n_bars, prog, *,
                     pad_mode="sustain", pad_gain=1.0, bass=True, riff_mode=None, hook=False,
                     drum_mode=None, cutoff=1700, cutoff_end=None, riser_bars=0, riser_intensity=1.0):
    for bar_i in range(n_bars):
        bar_t = (start_bar + bar_i) * BAR
        chord_name = prog[bar_i % len(prog)]
        if cutoff_end is not None and n_bars > 1:
            c_cut = cutoff + (cutoff_end - cutoff) * bar_i / (n_bars - 1)
        else:
            c_cut = cutoff
        render_bar(tonal_l, tonal_r, perc_l, perc_r, kick_times, bar_t, chord_name,
                   pad_mode=pad_mode, pad_gain=pad_gain, cutoff=c_cut, bass=bass,
                   riff_mode=riff_mode, hook=hook, drum_mode=drum_mode)
    if riser_bars > 0:
        dur = riser_bars * BAR
        start_t = (start_bar + n_bars) * BAR - dur
        sig = riser(dur, riser_intensity)
        mix_add(perc_l, perc_r, start_t, sig, sig)


def main():
    movements = [
        dict(n_bars=8, prog=CHORUS_PROG, pad_mode="sustain", pad_gain=0.5, bass=False,
             riff_mode="full", cutoff=1500),
        dict(n_bars=18, prog=VERSE_PROG, pad_mode="sustain", pad_gain=0.75, bass=True,
             riff_mode="sparse", drum_mode="light", cutoff=1500),
        dict(n_bars=4, prog=PRECHORUS_PROG, pad_mode="sustain", pad_gain=0.85, bass=True,
             riff_mode="sparse", drum_mode="light", cutoff=1700, riser_bars=1, riser_intensity=0.7),
        dict(n_bars=18, prog=CHORUS_PROG, pad_mode="stab", pad_gain=1.0, bass=True,
             riff_mode="full", hook=True, drum_mode="full", cutoff=2000),
        dict(n_bars=18, prog=VERSE_PROG, pad_mode="sustain", pad_gain=0.8, bass=True,
             riff_mode="sparse", drum_mode="light", cutoff=1500),
        dict(n_bars=4, prog=PRECHORUS_PROG, pad_mode="sustain", pad_gain=0.85, bass=True,
             riff_mode="sparse", drum_mode="light", cutoff=1700, riser_bars=1, riser_intensity=0.8),
        dict(n_bars=18, prog=CHORUS_PROG, pad_mode="stab", pad_gain=1.0, bass=True,
             riff_mode="full", hook=True, drum_mode="full", cutoff=2000),
        dict(n_bars=12, prog=BRIDGE_PROG, pad_mode="sustain", pad_gain=0.6, bass=False,
             cutoff=900),
        dict(n_bars=10, prog=BUILD_PROG, pad_mode="sustain", pad_gain=0.85, bass=True,
             riff_mode="sparse", drum_mode="light", cutoff=900, cutoff_end=1900,
             riser_bars=2, riser_intensity=1.1),
        dict(n_bars=32, prog=CHORUS_PROG, pad_mode="stab", pad_gain=1.15, bass=True,
             riff_mode="full", hook=True, drum_mode="full", cutoff=2200),
        dict(n_bars=8, prog=CHORUS_PROG, pad_mode="sustain", pad_gain=0.45, bass=False,
             riff_mode="full", cutoff=1300),
    ]

    total_bars = sum(m["n_bars"] for m in movements)
    total_secs = total_bars * BAR + 4.0
    n_samples = int(total_secs * SR)

    tonal_l, tonal_r = np.zeros(n_samples), np.zeros(n_samples)
    perc_l, perc_r = np.zeros(n_samples), np.zeros(n_samples)
    kick_times = []

    bar_cursor = 0
    for m in movements:
        kwargs = {k: v for k, v in m.items() if k != "n_bars"}
        render_movement(tonal_l, tonal_r, perc_l, perc_r, kick_times, bar_cursor, m["n_bars"], **kwargs)
        bar_cursor += m["n_bars"]

    duck = np.ones(n_samples)
    depth = 0.35
    recovery_rate = 5.0 / (0.8 * BEAT)
    window_len = int(0.9 * BEAT * SR)
    rel = np.arange(window_len) / SR
    dip_shape = 1 - depth * np.exp(-rel * recovery_rate)
    for t0 in kick_times:
        s_idx = int(t0 * SR)
        e_idx = min(s_idx + window_len, n_samples)
        seg_len = e_idx - s_idx
        if seg_len > 0:
            duck[s_idx:e_idx] = np.minimum(duck[s_idx:e_idx], dip_shape[:seg_len])
    tonal_l *= duck
    tonal_r *= duck

    master_l = tonal_l + perc_l
    master_r = tonal_r + perc_r

    wet_l = schroeder_reverb(master_l, wet=0.22)
    wet_r = schroeder_reverb(master_r, wet=0.22)

    fade_in = int(1.0 * SR)
    fade_out = int(4.0 * SR)
    env = np.ones(n_samples)
    env[:fade_in] = np.linspace(0, 1, fade_in)
    env[-fade_out:] = np.linspace(1, 0, fade_out)

    out_l = np.tanh(wet_l * env * 1.15)
    out_r = np.tanh(wet_r * env * 1.15)

    peak = max(np.abs(out_l).max(), np.abs(out_r).max(), 1e-9)
    out_l = out_l / peak * 0.92
    out_r = out_r / peak * 0.92

    stereo_out = np.stack([out_l, out_r], axis=1)
    pcm = (stereo_out * 32767).astype(np.int16)
    wavfile.write("synthwave_pop.wav", SR, pcm)
    print(f"Wrote synthwave_pop.wav: {total_secs:.1f}s, {total_bars} bars at {BPM} BPM")


if __name__ == "__main__":
    main()
