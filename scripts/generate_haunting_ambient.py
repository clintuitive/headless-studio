"""Synthesizes a haunting, nostalgic ambient piece in the vein of Amos
Roddy's Minecraft "Chase the Skies" tracks ("Lilypad", "Fireflies") and
their C418/Lena Raine lineage, and renders it to a WAV file.

This generator works completely differently from the other scripts here.
There is no drum machine, no shared bar grid, and no movement-by-movement
build -- those pieces are about a beat locking in and a song-form arc;
this one is about a handful of layers that never quite line up. The slow
chord pad cycles through a four-chord progression on a 6-bar clock; the
piano melody loops on an independent 5-bar phrase. Six and five
share no common factor below 30 bars, so the melody keeps landing on a
different beat of a different chord each time through -- the same trick
Brian Eno used with mismatched tape-loop lengths on "Music for Airports"
to keep a piece from ever quite repeating itself. The chords themselves
lean on maj9/sus2/m9/maj7(#11) colour (lush, open, never resolving to a
plain triad) rather than the bare root+fifth dyads the darkwave/coldwave
generators use -- warmth instead of austerity. The lead voice is additive
synthesis modeling a piano: near-harmonic partials stretched slightly
sharper than true integer ratios (the same string-stiffness inharmonicity
-- the Railsback curve -- that gives a real piano its character, just far
subtler than a bell's wide intervals), plus a filtered hammer-strike
transient, sitting behind only a slight reverb send for a close, intimate
mic'd-piano feel. Every repetition of its phrase still gets fresh timing
jitter and gain variation, so it never feels quantized. A sparse,
randomly-triggered high "shimmer" layer -- the same piano voice played
high and drenched in much more reverb, for distant contrast -- wanders in
and out on its own. The final mix runs through a slow, irregular
LFO-modulated micro-delay ("wow and flutter") to emulate an unstable tape
transport, plus a gentle final lowpass for warmth -- the lo-fi-nostalgia
techniques that, along with reverb, do most of the emotional work here.
Everything is generated with oscillators + envelopes, no samples.
"""

import numpy as np
from scipy.signal import sawtooth, butter, lfilter
from scipy.io import wavfile

SR = 44100
BPM = 60
BEAT = 60.0 / BPM
BAR = BEAT * 4
SEED = 77

rng = np.random.default_rng(SEED)

TOTAL_BARS = 50
TAIL_SECS = 10.0

# Lush extended/coloured chords -- maj9, sus2, m9, maj7#11 -- the opposite
# philosophy from the bare dyads in the darkwave/coldwave generators.
CHORDS = {
    "C":  {"pad": [60, 64, 67, 71, 74]},  # Cmaj9: C4 E4 G4 B4 D5
    "G":  {"pad": [67, 69, 74, 79]},      # Gsus2 (no 3rd): G4 A4 D5 G5
    "Am": {"pad": [57, 60, 64, 67, 71]},  # Am9: A3 C4 E4 G4 B4
    "F":  {"pad": [65, 69, 71, 72, 76]},  # Fmaj7#11: F4 A4 B4 C5 E5
}
PAD_CYCLE = ["C", "G", "Am", "F"]
PAD_CHORD_BARS = 6  # 24-bar full pad cycle

# The piano melody: a sparse, wandering little tune in C major pentatonic,
# stored as (beat_offset, notated_dur_beats, semitones-from-PIANO_ROOT).
# Phrase length is 5 bars -- deliberately not a divisor of the 6-bar chord
# span, so melody and harmony drift against each other.
PIANO_ROOT = 72  # C5
PIANO_SCALE = [0, 2, 4, 7, 9]  # C D E G A
PIANO_PHRASE_BARS = 5
PIANO_PHRASE = [
    (0.0, 1.5, 0), (2.5, 1.0, 4), (5.0, 2.0, 7), (8.5, 1.0, 4),
    (10.0, 1.5, 2), (13.0, 2.5, 9), (16.5, 1.0, 0), (18.0, 1.5, -3),
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


def wow_flutter(x, rate_hz=0.15, depth_ms=2.0, base_ms=3.0, phase0=0.0, sr=SR):
    """Tape-transport pitch wobble: a slow main LFO plus a faster, weaker
    one (irregular, not a clean single sine) modulating a fractional-delay
    read tap -- the same resampling trick a chorus effect uses, just an
    order of magnitude slower and applied to the whole mix in series, not
    blended in parallel, since real tape wobble affects everything on it."""
    n = len(x)
    t = np.arange(n) / sr
    lfo = np.sin(2 * np.pi * rate_hz * t + phase0) + 0.4 * np.sin(2 * np.pi * rate_hz * 2.7 * t + phase0 * 1.3 + 0.8)
    delay_samples = (base_ms + depth_ms * lfo) * sr / 1000.0
    idx = np.arange(n)
    read_pos = np.clip(idx - delay_samples, 0, n - 1)
    idx0 = np.floor(read_pos).astype(int)
    idx1 = np.clip(idx0 + 1, 0, n - 1)
    frac = read_pos - idx0
    return x[idx0] * (1 - frac) + x[idx1] * frac


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

def choir_pad_voice(freq, dur, cutoff=2000, detune=0.005):
    t = np.arange(int(dur * SR)) / SR
    osc = (
        np.sin(2 * np.pi * freq * t)
        + np.sin(2 * np.pi * freq * (1 + detune) * t)
        + np.sin(2 * np.pi * freq * (1 - detune) * t)
        + 0.3 * sawtooth(2 * np.pi * freq * t, width=0.5)
    ) / 3.3
    env = adsr(len(t), a=dur * 0.45, d=0.25, s=0.85, r=dur * 0.5)
    return lowpass(osc * env, cutoff)


def piano_voice(freq, dur):
    """Additive piano: near-harmonic partials stretched slightly sharper
    than true integer ratios -- the same string-stiffness inharmonicity
    real piano strings have (the Railsback curve), just subtle, not a
    bell's wide intervals -- each decaying at its own rate (highs damp
    fastest), plus a filtered hammer-strike transient."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    partials = []
    for k in range(1, 7):
        ratio = k * (1 + 0.0004 * k * k)  # stretched harmonic
        amp = 1.0 / k ** 1.1
        decay = 0.45 + 0.32 * (k - 1)
        partials.append((ratio, amp, decay))
    sig = np.zeros(n)
    for ratio, amp, decay in partials:
        sig += amp * np.sin(2 * np.pi * freq * ratio * t) * np.exp(-t * decay)
    sig /= sum(a for _, a, _ in partials)
    hammer_n = min(int(0.012 * SR), n)
    hammer = np.zeros(n)
    noise = rng.standard_normal(hammer_n)
    b, a = butter(2, [800 / (SR / 2), 3500 / (SR / 2)], btype="band")
    hammer[:hammer_n] = lfilter(b, a, noise) * np.exp(-np.arange(hammer_n) / SR * 500)
    sig += hammer * 0.2
    fade_n = min(int(0.003 * SR), n)
    sig[:fade_n] *= np.linspace(0, 1, fade_n)
    return sig


# ---- arrangement ------------------------------------------------------------

def render_pad_layer(pad_l, pad_r, total_bars):
    bar_i = 0
    while bar_i < total_bars:
        chord_name = PAD_CYCLE[(bar_i // PAD_CHORD_BARS) % len(PAD_CYCLE)]
        notes = CHORDS[chord_name]["pad"]
        span = PAD_CHORD_BARS * BAR
        t0 = bar_i * BAR
        n_notes = len(notes)
        for j, midi in enumerate(notes):
            gain = 0.42 * (1.0 if j == 0 else 0.65)
            sig = choir_pad_voice(midi_to_freq(midi), span * 1.25) * gain
            pan = -0.35 + 0.7 * (j / max(n_notes - 1, 1))
            l, r = stereo(sig, pan)
            mix_add(pad_l, pad_r, t0, l, r)
        bar_i += PAD_CHORD_BARS


def render_piano_layer(piano_l, piano_r, total_secs):
    phrase_secs = PIANO_PHRASE_BARS * 4 * BEAT
    t = 0.0
    while t < total_secs:
        for beat_off, dur_b, semis in PIANO_PHRASE:
            onset = t + beat_off * BEAT + rng.normal(0, 0.035)
            if onset < 0 or onset >= total_secs:
                continue
            octave_bump = 12 if rng.random() < 0.10 else (-12 if rng.random() < 0.05 else 0)
            freq = midi_to_freq(PIANO_ROOT + semis + octave_bump)
            ring_dur = 1.8 + dur_b * 0.8
            sig = piano_voice(freq, ring_dur) * rng.uniform(0.4, 0.55)
            l, r = stereo(sig, rng.uniform(-0.3, 0.3))
            mix_add(piano_l, piano_r, onset, l, r)
        t += phrase_secs


def render_shimmer_layer(sh_l, sh_r, total_bars):
    for bar_i in range(total_bars):
        if rng.random() < 0.2:
            onset = bar_i * BAR + rng.uniform(0.3, BAR - 0.5)
            semis = int(rng.choice(PIANO_SCALE)) + 12
            sig = piano_voice(midi_to_freq(PIANO_ROOT + semis), 2.6) * rng.uniform(0.12, 0.22)
            l, r = stereo(sig, rng.uniform(-0.6, 0.6))
            mix_add(sh_l, sh_r, onset, l, r)


def main():
    total_secs = TOTAL_BARS * BAR + TAIL_SECS
    n_samples = int(total_secs * SR)

    pad_l, pad_r = np.zeros(n_samples), np.zeros(n_samples)
    piano_l, piano_r = np.zeros(n_samples), np.zeros(n_samples)
    sh_l, sh_r = np.zeros(n_samples), np.zeros(n_samples)

    render_pad_layer(pad_l, pad_r, TOTAL_BARS)
    render_piano_layer(piano_l, piano_r, TOTAL_BARS * BAR)
    render_shimmer_layer(sh_l, sh_r, TOTAL_BARS)

    wet_pad_l = schroeder_reverb(pad_l, wet=0.5)
    wet_pad_r = schroeder_reverb(pad_r, wet=0.5)
    # Slight reverb on the piano itself -- close and intimate; the shimmer
    # layer (the same voice, played high) stays drenched for distant contrast.
    wet_piano_l = schroeder_reverb(piano_l, wet=0.18)
    wet_piano_r = schroeder_reverb(piano_r, wet=0.18)
    wet_sh_l = schroeder_reverb(sh_l, wet=0.65)
    wet_sh_r = schroeder_reverb(sh_r, wet=0.65)

    master_l = wet_pad_l + wet_piano_l + wet_sh_l
    master_r = wet_pad_r + wet_piano_r + wet_sh_r

    master_l = wow_flutter(master_l, rate_hz=0.13, depth_ms=1.8, base_ms=3.0, phase0=0.0)
    master_r = wow_flutter(master_r, rate_hz=0.13, depth_ms=1.8, base_ms=3.0, phase0=0.6)

    fade_in = int(7.0 * SR)
    fade_out = int(11.0 * SR)
    env = np.ones(n_samples)
    env[:fade_in] = np.linspace(0, 1, fade_in)
    env[-fade_out:] = np.linspace(1, 0, fade_out)

    out_l = np.tanh(master_l * env * 1.05)
    out_r = np.tanh(master_r * env * 1.05)

    # Gentle warm lowpass -- softens the digital edge, classic lo-fi-nostalgia move.
    out_l = lowpass(out_l, 9000)
    out_r = lowpass(out_r, 9000)

    peak = max(np.abs(out_l).max(), np.abs(out_r).max(), 1e-9)
    out_l = out_l / peak * 0.85
    out_r = out_r / peak * 0.85

    stereo_out = np.stack([out_l, out_r], axis=1)
    pcm = (stereo_out * 32767).astype(np.int16)
    wavfile.write("haunting_ambient.wav", SR, pcm)
    print(f"Wrote haunting_ambient.wav: {total_secs:.1f}s, {TOTAL_BARS} bars at {BPM} BPM")


if __name__ == "__main__":
    main()
