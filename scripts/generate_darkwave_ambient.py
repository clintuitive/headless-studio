"""Synthesizes a slow, minimal darkwave/post-punk piece -- the cold,
washed-out synth pads, melodic chorus-pedal bass guitar, and plodding
drum-machine beat of early Cure and Sisters of Mercy -- and renders it to
a WAV file.

Unlike the other generators, the harmony here is deliberately austere:
bare root+fifth dyads, no thirds or 9ths, so the only "color" comes from
the bass guitar's melodic line. The bass and pad are run through a real
chorus effect (a fractionally-interpolated, LFO-modulated delay -- not the
IIR comb() used for reverb, which is too expensive at chorus-scale
millisecond delays modulated continuously) for that shimmering pedal
sound. The drum pattern never builds in complexity -- once it locks in it
just plods, unchanged, the way a drum machine would; the arrangement's
sense of build comes entirely from which layers are present, not from the
beat getting busier. No sidechain pump either -- that's a dance-music
trope this era of production didn't use. Everything is generated with
oscillators + envelopes, no samples.
"""

import numpy as np
from scipy.signal import sawtooth, butter, lfilter
from scipy.io import wavfile

SR = 44100
BPM = 86
BEAT = 60.0 / BPM
BAR = BEAT * 4
SEED = 58

rng = np.random.default_rng(SEED)

# D Phrygian-tinged minor: i - bII - i - v, bare root+fifth dyads (no thirds).
CHORDS = {
    "Dm": {"bass": 38, "pad": [62, 69]},  # D2 bass / D4-A4 pad dyad
    "Eb": {"bass": 39, "pad": [63, 70]},  # Eb2 bass / Eb4-Bb4 pad dyad
    "Am": {"bass": 45, "pad": [69, 76]},  # A2 bass / A4-E5 pad dyad
}
PROG = ["Dm", "Eb", "Dm", "Am"]

# Melodic, walking goth bassline: root-root-fifth-fourth-root-b7-octave-fifth,
# in semitone offsets from the chord's bass root. Transposes to any chord above.
DARK_BASSLINE = [
    (0.0, 0.5, 0), (0.5, 0.5, 0), (1.0, 0.5, 7), (1.5, 0.5, 5),
    (2.0, 0.5, 0), (2.5, 0.5, 10), (3.0, 0.5, 12), (3.5, 0.5, 7),
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
    """Classic pedal chorus: dry signal + one or more copies read from a
    continuously-modulated delay tap, linearly interpolated between samples.
    Pure index-gather, O(voices * n) -- fast at any delay length, unlike an
    IIR comb filter driven at audio-modulation rates."""
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

def pad_voice(freq, dur, cutoff=850):
    t = np.arange(int(dur * SR)) / SR
    osc = (
        np.sin(2 * np.pi * freq * t)
        + 0.4 * sawtooth(2 * np.pi * freq * 1.003 * t)
        + 0.4 * sawtooth(2 * np.pi * freq * 0.997 * t)
    ) / 1.8
    env = adsr(len(t), a=dur * 0.55, d=0.3, s=0.8, r=dur * 0.4)
    return lowpass(osc * env, cutoff)


def shimmer_voice(freq, dur):
    t = np.arange(int(dur * SR)) / SR
    tremolo = 1 + 0.15 * np.sin(2 * np.pi * 0.3 * t)
    osc = np.sin(2 * np.pi * freq * t) * tremolo
    env = adsr(len(t), a=dur * 0.5, d=0.3, s=0.5, r=dur * 0.5)
    return osc * env


def bass_guitar(freq, dur, cutoff=1100):
    t = np.arange(int(dur * SR)) / SR
    osc = 0.6 * sawtooth(2 * np.pi * freq * t) + 0.5 * np.sin(2 * np.pi * freq * t) \
        + 0.15 * np.sin(2 * np.pi * freq * 2 * t)
    pick_n = min(int(0.01 * SR), len(t))
    pick = np.zeros(len(t))
    pick[:pick_n] = rng.standard_normal(pick_n) * np.exp(-np.arange(pick_n) / SR * 350)
    env = adsr(len(t), a=0.004, d=0.18, s=0.55, r=dur * 0.3)
    sig = osc * env + pick * 0.35
    sig = np.tanh(sig * 1.4)  # mild amp-style saturation
    return lowpass(sig, cutoff)


def kick():
    dur = 0.45
    t = np.arange(int(dur * SR)) / SR
    freq = 110 * np.exp(-t * 9) + 42
    phase = 2 * np.pi * np.cumsum(freq) / SR
    return np.sin(phase) * np.exp(-t * 7)


def tom_snare():
    dur = 0.25
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    b, a = butter(2, [200 / (SR / 2), 3000 / (SR / 2)], btype="band")
    noise = lfilter(b, a, noise)
    tone_freq = 220 * np.exp(-t * 10) + 90
    phase = 2 * np.pi * np.cumsum(tone_freq) / SR
    tone = np.sin(phase)
    env = np.exp(-t * 18)
    return (noise * 0.6 + tone * 0.7) * env


def hat():
    dur = 0.04
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    b, a = butter(2, [7000 / (SR / 2), 13000 / (SR / 2)], btype="band")
    noise = lfilter(b, a, noise)
    env = np.exp(-np.arange(n) / SR * 90)
    return noise * env * 0.3


# ---- arrangement ------------------------------------------------------------

def render_bar(pad_l, pad_r, bass_l, bass_r, perc_l, perc_r, bar_t, chord_name, *,
               pad_gain=0.0, bass_mode=None, drum_mode=None, shimmer=False):
    c = CHORDS[chord_name]

    for j, midi in enumerate(c["pad"]):
        gain = pad_gain * (0.8 if j == 0 else 0.6)
        sig = pad_voice(midi_to_freq(midi), BAR * 1.3) * gain
        l, r = stereo(sig, pan=-0.2 + 0.4 * j)
        mix_add(pad_l, pad_r, bar_t, l, r)

    if shimmer:
        sig = shimmer_voice(midi_to_freq(c["pad"][1] + 12), BAR * 1.6) * 0.1
        l, r = stereo(sig, pan=0.0)
        mix_add(pad_l, pad_r, bar_t, l, r)

    if bass_mode == "sparse":
        for beat_i in (0, 2):
            sig = bass_guitar(midi_to_freq(c["bass"]), BEAT * 1.6) * 0.8
            mix_add(bass_l, bass_r, bar_t + beat_i * BEAT, sig, sig)
    elif bass_mode == "full":
        for beat_off, dur_b, offset in DARK_BASSLINE:
            sig = bass_guitar(midi_to_freq(c["bass"] + offset), dur_b * BEAT * 1.6) * 0.8
            mix_add(bass_l, bass_r, bar_t + beat_off * BEAT, sig, sig)

    if drum_mode == "plod":
        for beat_i in (0, 2):
            t0 = bar_t + beat_i * BEAT
            k = kick() * 0.75
            mix_add(perc_l, perc_r, t0, k, k)
        for beat_i in (1, 3):
            t0 = bar_t + beat_i * BEAT
            s = tom_snare() * 0.6
            mix_add(perc_l, perc_r, t0, s, s)
        for step in (1, 3, 5, 7):
            if rng.random() < 0.5:
                h = hat()
                mix_add(perc_l, perc_r, bar_t + step * (BEAT / 2), h, h)


def render_movement(pad_l, pad_r, bass_l, bass_r, perc_l, perc_r, start_bar, n_bars, **kwargs):
    for bar_i in range(n_bars):
        bar_t = (start_bar + bar_i) * BAR
        chord_name = PROG[bar_i % len(PROG)]
        render_bar(pad_l, pad_r, bass_l, bass_r, perc_l, perc_r, bar_t, chord_name, **kwargs)


def main():
    movements = [
        # Intro: pad alone, washing in.
        dict(n_bars=8, pad_gain=0.5, bass_mode=None, drum_mode=None, shimmer=False),
        # Bass enters: sparse root pulses, no drums yet.
        dict(n_bars=8, pad_gain=0.65, bass_mode="sparse", drum_mode=None, shimmer=False),
        # Drums lock in: full walking bassline, plodding beat begins.
        dict(n_bars=16, pad_gain=0.75, bass_mode="full", drum_mode="plod", shimmer=False),
        # Full wash: a high shimmer layer joins, everything sustained.
        dict(n_bars=24, pad_gain=0.9, bass_mode="full", drum_mode="plod", shimmer=True),
        # Breakdown: drums drop, pad and bass continue.
        dict(n_bars=8, pad_gain=0.7, bass_mode="full", drum_mode=None, shimmer=False),
        # Return: full arrangement again, the peak.
        dict(n_bars=24, pad_gain=0.95, bass_mode="full", drum_mode="plod", shimmer=True),
        # Outro: drums and bass drop out, pad alone fades back to silence.
        dict(n_bars=16, pad_gain=0.5, bass_mode=None, drum_mode=None, shimmer=False),
    ]

    total_bars = sum(m["n_bars"] for m in movements)
    total_secs = total_bars * BAR + 8.0
    n_samples = int(total_secs * SR)

    pad_l, pad_r = np.zeros(n_samples), np.zeros(n_samples)
    bass_l, bass_r = np.zeros(n_samples), np.zeros(n_samples)
    perc_l, perc_r = np.zeros(n_samples), np.zeros(n_samples)

    bar_cursor = 0
    for m in movements:
        kwargs = {k: v for k, v in m.items() if k != "n_bars"}
        render_movement(pad_l, pad_r, bass_l, bass_r, perc_l, perc_r, bar_cursor, m["n_bars"], **kwargs)
        bar_cursor += m["n_bars"]

    # Stereo chorus (opposite LFO phase L/R) on the pad and bass guitar.
    pad_l = chorus(pad_l, rate_hz=0.5, depth_ms=4.0, base_ms=15.0, mix=0.4, phase0=0.0)
    pad_r = chorus(pad_r, rate_hz=0.5, depth_ms=4.0, base_ms=15.0, mix=0.4, phase0=np.pi)
    bass_l = chorus(bass_l, rate_hz=0.7, depth_ms=5.0, base_ms=18.0, mix=0.5, phase0=0.0)
    bass_r = chorus(bass_r, rate_hz=0.7, depth_ms=5.0, base_ms=18.0, mix=0.5, phase0=np.pi)

    # Separate reverb sends -- pads washed, bass mostly dry, drums lightly roomy.
    wet_pad_l = schroeder_reverb(pad_l, wet=0.45)
    wet_pad_r = schroeder_reverb(pad_r, wet=0.45)
    wet_bass_l = schroeder_reverb(bass_l, wet=0.15)
    wet_bass_r = schroeder_reverb(bass_r, wet=0.15)
    wet_perc_l = schroeder_reverb(perc_l, wet=0.3)
    wet_perc_r = schroeder_reverb(perc_r, wet=0.3)

    master_l = wet_pad_l + wet_bass_l + wet_perc_l
    master_r = wet_pad_r + wet_bass_r + wet_perc_r

    fade_in = int(3.0 * SR)
    fade_out = int(7.0 * SR)
    env = np.ones(n_samples)
    env[:fade_in] = np.linspace(0, 1, fade_in)
    env[-fade_out:] = np.linspace(1, 0, fade_out)

    out_l = np.tanh(master_l * env * 1.05)
    out_r = np.tanh(master_r * env * 1.05)

    peak = max(np.abs(out_l).max(), np.abs(out_r).max(), 1e-9)
    out_l = out_l / peak * 0.9
    out_r = out_r / peak * 0.9

    stereo_out = np.stack([out_l, out_r], axis=1)
    pcm = (stereo_out * 32767).astype(np.int16)
    wavfile.write("darkwave_ambient.wav", SR, pcm)
    print(f"Wrote darkwave_ambient.wav: {total_secs:.1f}s, {total_bars} bars at {BPM} BPM")


if __name__ == "__main__":
    main()
