"""Synthesizes a long-form ambient synthwave track that builds slowly, and
renders it to a WAV file.

Unlike the other two generators, this one is built around a single
recurring melodic hook (a short, chord-relative phrase played on a warm
bell/pluck voice with a stereo echo trail) that gets restated through seven
movements: Intro -> Pulse Emerges -> Chill Beat Enters -> Groove Builds ->
Full Bloom -> Release -> Outro. Across that arc the pad filter brightens,
the bassline gains presence, an arpeggio joins, and the drums grow from
nothing to a full (but still chill, never aggressive) groove before pulling
back down to silence -- one slow build rather than a string of drops.
Everything is generated with oscillators + envelopes, no samples.
"""

import numpy as np
from scipy.signal import sawtooth, butter, lfilter
from scipy.io import wavfile

SR = 44100
BPM = 88
BEAT = 60.0 / BPM
BAR = BEAT * 4
SEED = 21

rng = np.random.default_rng(SEED)

# E minor: i - VI - III - VII for the main loop (the classic retrowave move,
# transposed), with a iv - i - VI - VII lift for the "Full Bloom" movement.
CHORDS = {
    "Em": {"bass": 40, "pad": [64, 67, 71], "color": 78, "third": 3},  # E2 / E4-G4-B4, +F#5(9th)
    "C":  {"bass": 36, "pad": [60, 64, 67], "color": 74, "third": 4},  # C2 / C4-E4-G4, +D5(9th)
    "G":  {"bass": 43, "pad": [67, 71, 74], "color": 81, "third": 4},  # G2 / G4-B4-D5, +A5(9th)
    "D":  {"bass": 38, "pad": [62, 66, 69], "color": 76, "third": 4},  # D2 / D4-F#4-A4, +E5(9th)
    "Am": {"bass": 45, "pad": [69, 72, 76], "color": 83, "third": 3},  # A2 / A4-C5-E5, +B5(9th)
}
MAIN_PROG = ["Em", "C", "G", "D"]
PEAK_PROG = ["Am", "Em", "C", "D"]

# The hook: a one-bar, chord-relative phrase (5 - 8 - 3 - 5 - 1) that repeats
# every bar, transposed to whatever chord is underneath it.
HOOK = [
    (0.0, 0.75, "fifth"), (1.0, 0.75, "octave"), (2.0, 0.5, "third"),
    (2.75, 0.5, "fifth"), (3.5, 0.5, "root"),
]


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


def tap_delay(x, delay_s, feedback, n_taps=8, sr=SR):
    """Echo via shifted, attenuated copies -- O(n_taps * n), unlike comb()'s
    O(n * delay_samples) IIR recursion, which is only cheap for the short
    (sub-50ms) delays schroeder_reverb uses. For an audible, beat-scale
    echo (hundreds of ms) comb() would take ages; this stays fast."""
    d = max(int(delay_s * sr), 1)
    out = x.copy()
    tap = x
    gain = feedback
    for _ in range(n_taps):
        shifted = np.zeros_like(x)
        if d < len(x):
            shifted[d:] = tap[:-d]
        tap = shifted
        out += tap * gain
        gain *= feedback
    return out


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
    l_gain = np.sqrt(0.5 * (1 - pan))
    r_gain = np.sqrt(0.5 * (1 + pan))
    return sig * l_gain, sig * r_gain


# ---- instrument voices -----------------------------------------------------

def pad_voice(freq, dur, cutoff=900, detune=0.004):
    t = np.arange(int(dur * SR)) / SR
    osc = (
        np.sin(2 * np.pi * freq * t)
        + 0.5 * sawtooth(2 * np.pi * freq * (1 + detune) * t)
        + 0.5 * sawtooth(2 * np.pi * freq * (1 - detune) * t)
    ) / 2.0
    env = adsr(len(t), a=dur * 0.5, d=0.2, s=0.85, r=dur * 0.35)
    return lowpass(osc * env, cutoff)


def bass_voice(freq, dur):
    t = np.arange(int(dur * SR)) / SR
    osc = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * freq * 2 * t)
    pulse = 1 - 0.16 * (0.5 + 0.5 * np.sin(2 * np.pi * (2 / BEAT) * t))
    env = adsr(len(t), a=0.2, d=0.25, s=0.9, r=dur * 0.3)
    return osc * env * pulse


def arp_voice(freq, dur, cutoff=2200):
    t = np.arange(int(dur * SR)) / SR
    osc = sawtooth(2 * np.pi * freq * t, width=0.5)  # triangle-ish
    env = adsr(len(t), a=0.01, d=0.05, s=0.3, r=dur * 0.6)
    return lowpass(osc * env, cutoff)


def hook_voice(freq, dur, cutoff=2400):
    t = np.arange(int(dur * SR)) / SR
    osc = 0.55 * np.sin(2 * np.pi * freq * t) + 0.45 * sawtooth(2 * np.pi * freq * 1.002 * t)
    env = adsr(len(t), a=0.015, d=0.12, s=0.55, r=dur * 0.55)
    return lowpass(osc * env, cutoff)


def lead_voice(freq, dur, cutoff=1900):
    t = np.arange(int(dur * SR)) / SR
    osc = 0.6 * np.sin(2 * np.pi * freq * t) + 0.4 * sawtooth(2 * np.pi * freq * 1.003 * t)
    env = adsr(len(t), a=dur * 0.3, d=0.2, s=0.7, r=dur * 0.5)
    return lowpass(osc * env, cutoff)


def kick():
    dur = 0.3
    t = np.arange(int(dur * SR)) / SR
    freq = 150 * np.exp(-t * 20) + 45
    phase = 2 * np.pi * np.cumsum(freq) / SR
    osc = np.sin(phase)
    env = np.exp(-t * 16)
    return osc * env


def clap():
    dur = 0.15
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    b, a = butter(2, [1500 / (SR / 2), 4000 / (SR / 2)], btype="band")
    noise = lfilter(b, a, noise)
    t = np.arange(n) / SR
    env = np.exp(-t * 35) + 0.6 * np.exp(-np.maximum(t - 0.012, 0) * 60)
    return noise * env


def shaker():
    dur = 0.08
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    b, a = butter(2, [6000 / (SR / 2), 12000 / (SR / 2)], btype="band")
    noise = lfilter(b, a, noise)
    env = np.exp(-np.arange(n) / SR * 60)
    return noise * env


def hihat(open_=False):
    dur = 0.18 if open_ else 0.05
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    b, a = butter(2, [9000 / (SR / 2), 16000 / (SR / 2)], btype="band")
    noise = lfilter(b, a, noise)
    env = np.exp(-np.arange(n) / SR * (18 if open_ else 70))
    return noise * env * 0.5


# ---- arrangement ------------------------------------------------------------

def render_hook(hook_l, hook_r, bar_t, chord, gain, pan=0.0):
    for beat_off, dur_b, token in HOOK:
        sig = hook_voice(tone_freq(chord, token), dur_b * BEAT * 1.6) * gain
        l, r = stereo(sig, pan=pan)
        mix_add(hook_l, hook_r, bar_t + beat_off * BEAT, l, r)


def render_bar(tonal_l, tonal_r, hook_l, hook_r, perc_l, perc_r, kick_times, bar_t, chord_name, *,
               pad_gain=1.0, cutoff=900, bass_gain=0.0, arp=False,
               hook_gain=0.6, hook_pan=0.0, lead=False, perc_mode=None):
    c = CHORDS[chord_name]

    for j, midi in enumerate([*c["pad"], c["color"]]):
        gain = pad_gain * (0.85 if j < 3 else 0.3)
        sig = pad_voice(midi_to_freq(midi), BAR * 1.4, cutoff=cutoff) * gain
        l, r = stereo(sig, pan=-0.3 + 0.2 * j)
        mix_add(tonal_l, tonal_r, bar_t, l, r)

    if bass_gain > 0:
        sig = bass_voice(midi_to_freq(c["bass"]), BAR * 1.05) * bass_gain
        mix_add(tonal_l, tonal_r, bar_t, sig, sig)

    if arp:
        notes = [c["pad"][0], c["pad"][0] + c["third"], c["pad"][0] + 7, c["pad"][0] + 12]
        step = BEAT / 2
        for k in range(8):
            note = notes[k % len(notes)]
            sig = arp_voice(midi_to_freq(note), step * 1.8) * 0.35
            pan = 0.45 if k % 2 == 0 else -0.45
            l, r = stereo(sig, pan=pan)
            mix_add(tonal_l, tonal_r, bar_t + k * step, l, r)

    if hook_gain > 0:
        render_hook(hook_l, hook_r, bar_t, c, hook_gain, pan=hook_pan)

    if lead:
        note = c["pad"][1] + 12
        sig = lead_voice(midi_to_freq(note), BAR * 1.5) * 0.3
        l, r = stereo(sig, pan=-0.15)
        mix_add(tonal_l, tonal_r, bar_t + BEAT * 2, l, r)

    if perc_mode == "soft":
        for beat_i in (0, 2):
            t0 = bar_t + beat_i * BEAT
            k = kick() * 0.4
            mix_add(perc_l, perc_r, t0, k, k)
            kick_times.append(t0)
        for k4 in range(4):
            sh = shaker() * 0.12
            mix_add(perc_l, perc_r, bar_t + k4 * BEAT, sh, sh)
    elif perc_mode == "groove":
        for beat_i in range(4):
            t0 = bar_t + beat_i * BEAT
            k = kick() * 0.5
            mix_add(perc_l, perc_r, t0, k, k)
            kick_times.append(t0)
        for beat_i in (1, 3):
            cl = clap() * 0.3
            mix_add(perc_l, perc_r, bar_t + beat_i * BEAT, cl, cl)
        for k8 in range(8):
            sh = shaker() * 0.16
            mix_add(perc_l, perc_r, bar_t + k8 * (BEAT / 2), sh, sh)
    elif perc_mode == "full":
        for beat_i in range(4):
            t0 = bar_t + beat_i * BEAT
            k = kick() * 0.58
            mix_add(perc_l, perc_r, t0, k, k)
            kick_times.append(t0)
        for beat_i in (1, 3):
            cl = clap() * 0.38
            mix_add(perc_l, perc_r, bar_t + beat_i * BEAT, cl, cl)
        for step in range(16):
            if step % 2 == 0 or rng.random() < 0.6:
                h = hihat(open_=(step == 15)) * 0.22
                mix_add(perc_l, perc_r, bar_t + step * (BEAT / 4), h, h)
        for k8 in range(8):
            sh = shaker() * 0.14
            mix_add(perc_l, perc_r, bar_t + k8 * (BEAT / 2), sh, sh)


def render_movement(tonal_l, tonal_r, hook_l, hook_r, perc_l, perc_r, kick_times, start_bar, n_bars, prog, **kwargs):
    cutoff = kwargs.pop("cutoff", 900)
    cutoff_end = kwargs.pop("cutoff_end", None)
    for bar_i in range(n_bars):
        bar_t = (start_bar + bar_i) * BAR
        chord_name = prog[bar_i % len(prog)]
        if cutoff_end is not None and n_bars > 1:
            c_cut = cutoff + (cutoff_end - cutoff) * bar_i / (n_bars - 1)
        else:
            c_cut = cutoff
        render_bar(tonal_l, tonal_r, hook_l, hook_r, perc_l, perc_r, kick_times, bar_t, chord_name,
                   cutoff=c_cut, **kwargs)


def main():
    movements = [
        # Intro: just the pad and a soft, sparse hook -- the theme on its own.
        dict(n_bars=8, prog=MAIN_PROG, pad_gain=0.45, cutoff=600, cutoff_end=650,
             bass_gain=0.0, arp=False, hook_gain=0.35, hook_pan=0.0, lead=False, perc_mode=None),
        # Pulse Emerges: the bassline's eighth-note pulse is the first rhythm, no drums yet.
        dict(n_bars=8, prog=MAIN_PROG, pad_gain=0.55, cutoff=650, cutoff_end=750,
             bass_gain=0.35, arp=False, hook_gain=0.4, hook_pan=0.05, lead=False, perc_mode=None),
        # Chill Beat Enters: sparse soft kick + shaker, the first real beat.
        dict(n_bars=12, prog=MAIN_PROG, pad_gain=0.65, cutoff=750, cutoff_end=900,
             bass_gain=0.55, arp=False, hook_gain=0.5, hook_pan=-0.05, lead=False, perc_mode="soft"),
        # Groove Builds: full kick pattern + clap + arpeggio joins underneath the hook.
        dict(n_bars=16, prog=MAIN_PROG, pad_gain=0.8, cutoff=900, cutoff_end=1150,
             bass_gain=0.75, arp=True, hook_gain=0.6, hook_pan=0.1, lead=False, perc_mode="groove"),
        # Full Bloom: the peak -- lifted chords, lead answers the hook, fullest (still chill) groove.
        dict(n_bars=24, prog=PEAK_PROG, pad_gain=1.0, cutoff=1150, cutoff_end=1500,
             bass_gain=0.95, arp=True, hook_gain=0.75, hook_pan=0.0, lead=True, perc_mode="full"),
        # Release: pull back from the peak, mirroring Groove Builds.
        dict(n_bars=16, prog=MAIN_PROG, pad_gain=0.8, cutoff=1500, cutoff_end=1100,
             bass_gain=0.6, arp=True, hook_gain=0.55, hook_pan=-0.1, lead=False, perc_mode="groove"),
        # Outro: drums and bass drop out, hook and pad fade back to where it began.
        dict(n_bars=24, prog=MAIN_PROG, pad_gain=0.5, cutoff=1100, cutoff_end=600,
             bass_gain=0.0, arp=False, hook_gain=0.3, hook_pan=0.0, lead=False, perc_mode=None),
    ]

    total_bars = sum(m["n_bars"] for m in movements)
    total_secs = total_bars * BAR + 6.0
    n_samples = int(total_secs * SR)

    tonal_l, tonal_r = np.zeros(n_samples), np.zeros(n_samples)
    hook_l, hook_r = np.zeros(n_samples), np.zeros(n_samples)
    perc_l, perc_r = np.zeros(n_samples), np.zeros(n_samples)
    kick_times = []

    bar_cursor = 0
    for m in movements:
        kwargs = {k: v for k, v in m.items() if k not in ("n_bars", "prog")}
        render_movement(tonal_l, tonal_r, hook_l, hook_r, perc_l, perc_r, kick_times,
                         bar_cursor, m["n_bars"], m["prog"], **kwargs)
        bar_cursor += m["n_bars"]

    # Stereo echo trail on the hook bus (slightly different L/R delay for width).
    hook_l = tap_delay(hook_l, BEAT * 0.75, 0.4)
    hook_r = tap_delay(hook_r, BEAT * 0.75 * 1.05, 0.4)
    tonal_l += hook_l
    tonal_r += hook_r

    # Sidechain "pump": only bites where kicks actually exist (Groove/Full/Release).
    duck = np.ones(n_samples)
    depth = 0.3
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

    wet_l = schroeder_reverb(master_l, wet=0.3)
    wet_r = schroeder_reverb(master_r, wet=0.3)

    fade_in = int(3.0 * SR)
    fade_out = int(6.0 * SR)
    env = np.ones(n_samples)
    env[:fade_in] = np.linspace(0, 1, fade_in)
    env[-fade_out:] = np.linspace(1, 0, fade_out)

    out_l = np.tanh(wet_l * env * 1.1)
    out_r = np.tanh(wet_r * env * 1.1)

    peak = max(np.abs(out_l).max(), np.abs(out_r).max(), 1e-9)
    out_l = out_l / peak * 0.92
    out_r = out_r / peak * 0.92

    stereo_out = np.stack([out_l, out_r], axis=1)
    pcm = (stereo_out * 32767).astype(np.int16)
    wavfile.write("synthwave_slowbuild.wav", SR, pcm)
    print(f"Wrote synthwave_slowbuild.wav: {total_secs:.1f}s, {total_bars} bars at {BPM} BPM")


if __name__ == "__main__":
    main()
