"""Synthesizes a French coldwave ("la vague froide") piece in the vein of
early Marquis de Sade, KaS Product and Clair Obscur, and renders it to a
WAV file.

Where generate_darkwave_ambient.py puts the melody in a Peter Hook-style
"lead bass," French coldwave moved that job to cheap, patchable
monosynths (the Korg MS-20 above all) -- the genre's melodic interest
worked almost exclusively through the synthesizer, while the rhythm
section turned militant and mechanical instead of musical. So here the
hook lives in a monophonic MS-20-ish lead voice with real portamento
(built by smoothing a continuous pitch-contour into one phase-accumulated
oscillator, the same cumsum() trick the kick drum uses, rather than
synthesizing each note as an isolated grain). The bass, in turn, gives up
its melodic role and becomes a short, doubled eight-step sequencer pulse
(root-root-root-octave-root-root-root-fifth) -- driving, repetitive,
non-melodic. The drum machine pattern is completely deterministic and
unswung (no probabilistic hi-hats), and it never builds in complexity: it
is simply off, full, or stripped to rim-plus-hat for the "Icy Breakdown,"
where the harmony also drifts from the main i-bVI-bVII progression to a
tighter i-bII half-step wobble -- the coldest, most exposed passage. The
tempo (132 BPM) is well above the other generator's 86 BPM plod, chasing
the "militant rhythm section" character the genre is known for. Production
stays raw and dry on purpose -- a short slapback echo on the lead instead
of thick chorus, light reverb throughout, and an outro where the machines
cut out rather than fade -- closer to the DIY cassette-culture sound of
the genre than its more polished British cousins. Everything is generated
with oscillators + envelopes, no samples.
"""

import numpy as np
from scipy.signal import sawtooth, butter, lfilter
from scipy.io import wavfile

SR = 44100
BPM = 132
BEAT = 60.0 / BPM
BAR = BEAT * 4
SEED = 104

rng = np.random.default_rng(SEED)

# B minor, drifting cold: i - i - bVI - bVII for the main groove, with a
# tighter i - bII half-step wobble (ICE_PROG) for the "Icy Breakdown."
# Bare root+fifth dyads throughout -- no thirds, same austerity as the
# other darkwave generator, just a different drift.
CHORDS = {
    "Bm": {"bass": 47, "pad": [71, 78]},  # B2 bass / B4-F#5 pad dyad (i)
    "G":  {"bass": 43, "pad": [67, 74]},  # G2 bass / G4-D5 pad dyad (bVI)
    "A":  {"bass": 45, "pad": [69, 76]},  # A2 bass / A4-E5 pad dyad (bVII)
    "C":  {"bass": 36, "pad": [60, 67]},  # C2 bass / C4-G4 pad dyad (bII)
}
MAIN_PROG = ["Bm", "Bm", "G", "A"]
ICE_PROG = ["Bm", "C", "Bm", "C"]

# The militant bass pulse: 8 sixteenth-note steps, repeated twice per bar.
# Semitone offsets from the chord root -- root-heavy with an octave jab and
# a fifth, not a tune.
COLD_PULSE = [0, 0, 0, 12, 0, 0, 0, 7]

# Drum machine grid, 16 sixteenth-note steps per bar. Fixed, never random.
KICK_STEPS = [0, 4, 7, 8, 12]
RIM_STEPS = [4, 12]

# The lead synth's hook -- narrow-range, modal, legato within the bar.
LEAD_MOTIF_FULL = [
    (0.0, 1.0, 0), (1.0, 0.5, 7), (1.5, 0.5, 5),
    (2.0, 1.0, 0), (3.0, 0.5, 10), (3.5, 0.5, 7),
]
# The exposed, deadpan version for the intro/outro/breakdown -- mostly space.
LEAD_MOTIF_SPARSE = [(0.0, 1.5, 0), (2.0, 1.0, 7)]


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


def tap_delay(x, delay_s, feedback, n_taps=4, sr=SR):
    """Slapback echo via shifted, attenuated copies -- cheap at the
    beat-scale delay lengths used here, unlike comb()'s IIR recursion."""
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


def schroeder_reverb(x, wet=0.2, sr=SR):
    combs = sum(comb(x, d, fb, sr) for d, fb in
                [(0.0297, 0.78), (0.0371, 0.74), (0.0411, 0.71), (0.0437, 0.68)])
    combs /= 4.0
    for d, g in [(0.005, 0.7), (0.0017, 0.7)]:
        n = max(int(d * sr), 1)
        b = np.zeros(n + 1); b[0] = -g; b[-1] = 1.0
        a = np.zeros(n + 1); a[0] = 1.0; a[-1] = -g
        combs = lfilter(b, a, combs)
    return (1 - wet) * x + wet * combs


def chorus(x, rate_hz=0.5, depth_ms=3.0, base_ms=12.0, mix=0.3, voices=2, phase0=0.0, sr=SR):
    """Dry signal + copies read from a continuously LFO-modulated delay tap,
    linearly interpolated -- a much lighter touch than the chorus in the UK
    generator, since this scene's bass leaned raw and sequenced, not
    pedal-soaked."""
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

def cold_pad_voice(freq, dur, cutoff=1500, detune=0.006):
    t = np.arange(int(dur * SR)) / SR
    osc = (
        0.5 * np.sin(2 * np.pi * freq * t)
        + 0.6 * sawtooth(2 * np.pi * freq * (1 + detune) * t)
        + 0.6 * sawtooth(2 * np.pi * freq * (1 - detune) * t)
    ) / 1.7
    env = adsr(len(t), a=dur * 0.4, d=0.25, s=0.75, r=dur * 0.45)
    return lowpass(osc * env, cutoff)


def pulse_bass_voice(freq, dur, cutoff=900):
    t = np.arange(int(dur * SR)) / SR
    osc = 0.7 * np.sin(2 * np.pi * freq * t) + 0.5 * sawtooth(2 * np.pi * freq * t)
    env = adsr(len(t), a=0.003, d=0.06, s=0.4, r=dur * 0.5)
    sig = np.tanh(osc * env * 1.3)
    return lowpass(sig, cutoff)


def ms20_lead_phrase(motif, chord, bar_dur, transpose=0, glide_s=0.025, cutoff=2600, gain=1.0):
    """A monophonic lead with real portamento: one continuous oscillator for
    the whole bar, its pitch held per-note and glided at transitions, rather
    than a fresh grain per note. Raw saw+square blend, lightly driven --
    thin and trebly like a cheap patchable monosynth, not a lush pad."""
    n = int(bar_dur * SR)
    root = chord["pad"][0] + transpose
    first_freq = midi_to_freq(root + motif[0][2])
    freq_contour = np.full(n, first_freq)
    gate = np.zeros(n)
    prev_freq = first_freq
    glide_n_max = max(int(glide_s * SR), 1)
    for beat_off, dur_b, offset in motif:
        start_idx = int(beat_off * BEAT * SR)
        end_idx = min(start_idx + int(dur_b * BEAT * SR), n)
        if end_idx <= start_idx:
            continue
        f = midi_to_freq(root + offset)
        freq_contour[start_idx:end_idx] = f
        g_n = min(glide_n_max, end_idx - start_idx)
        if g_n > 1:
            freq_contour[start_idx:start_idx + g_n] = np.linspace(prev_freq, f, g_n)
        note_n = end_idx - start_idx
        gate[start_idx:end_idx] = adsr(note_n, a=0.008, d=0.05, s=0.75, r=min(0.04, dur_b * BEAT * 0.3))
        prev_freq = f
    phase = 2 * np.pi * np.cumsum(freq_contour) / SR
    osc = 0.55 * sawtooth(phase) + 0.45 * np.sign(np.sin(phase))
    osc = np.tanh(osc * 1.25)
    return lowpass(osc, cutoff) * gate * gain


def cold_kick():
    dur = 0.22
    t = np.arange(int(dur * SR)) / SR
    freq = 150 * np.exp(-t * 35) + 55
    phase = 2 * np.pi * np.cumsum(freq) / SR
    body = np.sin(phase) * np.exp(-t * 22)
    click_n = min(int(0.003 * SR), len(t))
    click = np.zeros(len(t))
    click[:click_n] = rng.standard_normal(click_n) * np.exp(-np.arange(click_n) / SR * 900)
    return np.tanh((body * 0.9 + click * 0.5) * 1.3)


def rimshot():
    dur = 0.07
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    b, a = butter(2, [1800 / (SR / 2), 5500 / (SR / 2)], btype="band")
    noise = lfilter(b, a, noise)
    tone = np.sin(2 * np.pi * 420 * t) * np.exp(-t * 120)
    env = np.exp(-t * 70)
    return noise * env * 0.5 + tone * 0.6


def cold_hat():
    dur = 0.035
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    b, a = butter(2, [8000 / (SR / 2), 14000 / (SR / 2)], btype="band")
    noise = lfilter(b, a, noise)
    env = np.exp(-np.arange(n) / SR * 140)
    return noise * env * 0.28


# ---- arrangement ------------------------------------------------------------

def render_bar(pad_l, pad_r, bass_l, bass_r, lead_l, lead_r, perc_l, perc_r, bar_t, chord_name, *,
               pad_gain=0.0, bass_mode=None, lead_mode=None, drum_mode=None, lead_octave_double=False):
    c = CHORDS[chord_name]
    step_dur = BEAT / 4

    for j, midi in enumerate(c["pad"]):
        gain = pad_gain * (0.8 if j == 0 else 0.55)
        sig = cold_pad_voice(midi_to_freq(midi), BAR * 1.2) * gain
        l, r = stereo(sig, pan=-0.25 + 0.5 * j)
        mix_add(pad_l, pad_r, bar_t, l, r)

    if bass_mode == "pulse":
        for rep in (0, 1):
            for i, off in enumerate(COLD_PULSE):
                t0 = bar_t + (rep * 8 + i) * step_dur
                sig = pulse_bass_voice(midi_to_freq(c["bass"] + off), step_dur * 1.6) * 0.75
                mix_add(bass_l, bass_r, t0, sig, sig)

    if lead_mode:
        motif = {"full": LEAD_MOTIF_FULL, "sparse": LEAD_MOTIF_SPARSE}[lead_mode]
        sig = ms20_lead_phrase(motif, c, BAR, gain=0.6)
        l, r = stereo(sig, pan=0.05)
        mix_add(lead_l, lead_r, bar_t, l, r)
        if lead_octave_double:
            sig2 = ms20_lead_phrase(motif, c, BAR, transpose=12, cutoff=3200, gain=0.3)
            l2, r2 = stereo(sig2, pan=-0.2)
            mix_add(lead_l, lead_r, bar_t, l2, r2)

    if drum_mode == "full":
        for s in KICK_STEPS:
            k = cold_kick() * 0.8
            mix_add(perc_l, perc_r, bar_t + s * step_dur, k, k)
        for s in RIM_STEPS:
            rs = rimshot() * 0.6
            mix_add(perc_l, perc_r, bar_t + s * step_dur, rs, rs)
        for s in range(16):
            h = cold_hat() * (0.4 if s % 4 == 0 else 0.28)
            mix_add(perc_l, perc_r, bar_t + s * step_dur, h, h)
    elif drum_mode == "minimal":
        for s in RIM_STEPS:
            rs = rimshot() * 0.5
            mix_add(perc_l, perc_r, bar_t + s * step_dur, rs, rs)
        for s in (0, 8):
            h = cold_hat() * 0.22
            mix_add(perc_l, perc_r, bar_t + s * step_dur, h, h)


def render_movement(pad_l, pad_r, bass_l, bass_r, lead_l, lead_r, perc_l, perc_r,
                     start_bar, n_bars, prog, **kwargs):
    for bar_i in range(n_bars):
        bar_t = (start_bar + bar_i) * BAR
        chord_name = prog[bar_i % len(prog)]
        render_bar(pad_l, pad_r, bass_l, bass_r, lead_l, lead_r, perc_l, perc_r,
                   bar_t, chord_name, **kwargs)


def main():
    movements = [
        # Intro: cold pad alone, a sparse exposed lead teaser -- no rhythm section yet.
        dict(n_bars=8, prog=MAIN_PROG, pad_gain=0.55, bass_mode=None,
             lead_mode="sparse", drum_mode=None, lead_octave_double=False),
        # Rhythm Enters: the machine switches on at full pattern immediately -- it doesn't build.
        dict(n_bars=12, prog=MAIN_PROG, pad_gain=0.65, bass_mode="pulse",
             lead_mode="sparse", drum_mode="full", lead_octave_double=False),
        # Full Motif: the lead synth's hook takes over -- the main groove locks in.
        dict(n_bars=20, prog=MAIN_PROG, pad_gain=0.75, bass_mode="pulse",
             lead_mode="full", drum_mode="full", lead_octave_double=False),
        # Icy Breakdown: strip back, drift to the bII half-step wobble -- the coldest moment.
        dict(n_bars=12, prog=ICE_PROG, pad_gain=0.5, bass_mode=None,
             lead_mode="sparse", drum_mode="minimal", lead_octave_double=False),
        # Return: full groove again, lead doubled an octave up -- the only real lift in the piece.
        dict(n_bars=24, prog=MAIN_PROG, pad_gain=0.85, bass_mode="pulse",
             lead_mode="full", drum_mode="full", lead_octave_double=True),
        # Outro: the machines cut out rather than fade -- pad and lead trail off alone.
        dict(n_bars=12, prog=MAIN_PROG, pad_gain=0.55, bass_mode=None,
             lead_mode="sparse", drum_mode=None, lead_octave_double=False),
    ]

    total_bars = sum(m["n_bars"] for m in movements)
    total_secs = total_bars * BAR + 4.0
    n_samples = int(total_secs * SR)

    pad_l, pad_r = np.zeros(n_samples), np.zeros(n_samples)
    bass_l, bass_r = np.zeros(n_samples), np.zeros(n_samples)
    lead_l, lead_r = np.zeros(n_samples), np.zeros(n_samples)
    perc_l, perc_r = np.zeros(n_samples), np.zeros(n_samples)

    bar_cursor = 0
    for m in movements:
        kwargs = {k: v for k, v in m.items() if k not in ("n_bars", "prog")}
        render_movement(pad_l, pad_r, bass_l, bass_r, lead_l, lead_r, perc_l, perc_r,
                         bar_cursor, m["n_bars"], m["prog"], **kwargs)
        bar_cursor += m["n_bars"]

    # Light stereo chorus on the bass pulse only -- raw and sequenced, not pedal-soaked.
    bass_l = chorus(bass_l, rate_hz=0.5, depth_ms=3.0, base_ms=12.0, mix=0.25, phase0=0.0)
    bass_r = chorus(bass_r, rate_hz=0.5, depth_ms=3.0, base_ms=12.0, mix=0.25, phase0=np.pi)

    # Icy slapback echo on the lead instead of thick chorus.
    lead_l = tap_delay(lead_l, BEAT * 0.5, 0.32)
    lead_r = tap_delay(lead_r, BEAT * 0.5 * 1.04, 0.32)

    # Dry, raw mix throughout -- much less reverb than the UK-style generator.
    wet_pad_l = schroeder_reverb(pad_l, wet=0.25)
    wet_pad_r = schroeder_reverb(pad_r, wet=0.25)
    wet_bass_l = schroeder_reverb(bass_l, wet=0.05)
    wet_bass_r = schroeder_reverb(bass_r, wet=0.05)
    wet_lead_l = schroeder_reverb(lead_l, wet=0.15)
    wet_lead_r = schroeder_reverb(lead_r, wet=0.15)
    wet_perc_l = schroeder_reverb(perc_l, wet=0.12)
    wet_perc_r = schroeder_reverb(perc_r, wet=0.12)

    master_l = wet_pad_l + wet_bass_l + wet_lead_l + wet_perc_l
    master_r = wet_pad_r + wet_bass_r + wet_lead_r + wet_perc_r

    fade_in = int(2.5 * SR)
    fade_out = int(2.5 * SR)
    env = np.ones(n_samples)
    env[:fade_in] = np.linspace(0, 1, fade_in)
    env[-fade_out:] = np.linspace(1, 0, fade_out)

    out_l = np.tanh(master_l * env * 1.1)
    out_r = np.tanh(master_r * env * 1.1)

    peak = max(np.abs(out_l).max(), np.abs(out_r).max(), 1e-9)
    out_l = out_l / peak * 0.9
    out_r = out_r / peak * 0.9

    stereo_out = np.stack([out_l, out_r], axis=1)
    pcm = (stereo_out * 32767).astype(np.int16)
    wavfile.write("french_coldwave.wav", SR, pcm)
    print(f"Wrote french_coldwave.wav: {total_secs:.1f}s, {total_bars} bars at {BPM} BPM")


if __name__ == "__main__":
    main()
