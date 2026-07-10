"""Cold, haunting ambient synthwave with post-rock dynamics.

Synth palette only (oscillators + envelopes, no samples), but arranged like a post-rock track:
quiet pad intros, tension builds with rising sweeps, hard drops with impact hits, stripped-back
breakdowns, and a final hard comeback. Heavy percussion (4-on-floor kick + sub, snare, 16th hats,
open hats, toms, crashes), deep sub-bass, glacial 5-voice pads, minimal lead.

Progression: i7 – VImaj7 – iv7 – v7 (Am7–Fmaj7–Dm7–Em7) — unresolved, cold.
"""

import numpy as np
from scipy.signal import sawtooth, butter, lfilter
from scipy.io import wavfile

SR = 44100
BPM = 92
BEAT = 60.0 / BPM
BAR = BEAT * 4
SEED = 7

rng = np.random.default_rng(SEED)

# i7 – VImaj7 – iv7 – v7 in A natural minor: haunting, cold, never resolves
CHORDS = [
    {"bass": 45, "pad": [69, 72, 76, 79], "color": 71},  # Am7   A2 / A4-C5-E5-G5, +B4(9th)
    {"bass": 41, "pad": [65, 69, 72, 76], "color": 67},  # Fmaj7 F2 / F4-A4-C5-E5, +G4(9th)
    {"bass": 38, "pad": [62, 65, 69, 72], "color": 64},  # Dm7   D2 / D4-F4-A4-C5, +E4(9th)
    {"bass": 40, "pad": [64, 67, 71, 74], "color": 66},  # Em7   E2 / E4-G4-B4-D5, +F#4(9th)
]
ARP_NOTES = [
    [69, 72, 76, 79],
    [65, 69, 72, 76],
    [62, 65, 69, 72],
    [64, 67, 71, 74],
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
    b, a = butter(order, cutoff / (sr / 2), btype="low")
    return lfilter(b, a, x)


def bandpass(x, lo, hi, order=2, sr=SR):
    b, a = butter(order, [lo / (sr / 2), hi / (sr / 2)], btype="band")
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


# ----------------------------------------------------------------------------- tonal voices

def pad_voice(freq, dur, detune=0.006):
    t = np.arange(int(dur * SR)) / SR
    osc = (
        np.sin(2 * np.pi * freq * t) * 0.45
        + sawtooth(2 * np.pi * freq * (1 + detune) * t) * 0.32
        + sawtooth(2 * np.pi * freq * (1 - detune) * t) * 0.32
        + sawtooth(2 * np.pi * freq * (1 + detune * 2.5) * t) * 0.18
        + sawtooth(2 * np.pi * freq * (1 - detune * 2.5) * t) * 0.18
    ) / 1.45
    shimmer = np.sin(2 * np.pi * freq * 2 * t) * 0.07
    env = adsr(len(t), a=dur * 0.70, d=0.35, s=0.88, r=dur * 0.55)
    return lowpass((osc + shimmer) * env, 1100)


def bass_voice(freq, dur):
    t = np.arange(int(dur * SR)) / SR
    sub = np.sin(2 * np.pi * freq * t)
    body = (np.sin(2 * np.pi * freq * t)
            + 0.50 * np.sin(2 * np.pi * freq * 2 * t)
            + 0.20 * np.sin(2 * np.pi * freq * 3 * t))
    body = lowpass(body, 900)
    pulse = 1 - 0.10 * (0.5 + 0.5 * np.sin(2 * np.pi * (1 / BEAT) * t))
    env = adsr(len(t), a=0.06, d=0.35, s=0.82, r=dur * 0.50)
    return (sub * 0.68 + body * 0.52) * env * pulse


def arp_voice(freq, dur):
    t = np.arange(int(dur * SR)) / SR
    osc = sawtooth(2 * np.pi * freq * t, width=0.5)
    env = adsr(len(t), a=0.02, d=0.08, s=0.22, r=dur * 0.72)
    return lowpass(osc * env, 1600)


def lead_voice(freq, dur):
    t = np.arange(int(dur * SR)) / SR
    # No vibrato — a steady, cold tone (vibrato on a high sustained note reads as a siren)
    osc = (0.55 * np.sin(2 * np.pi * freq * t)
           + 0.45 * sawtooth(2 * np.pi * freq * 1.003 * t))
    env = adsr(len(t), a=dur * 0.45, d=0.28, s=0.55, r=dur * 0.68)
    return lowpass(osc * env, 1400)


# ----------------------------------------------------------------------------- percussion

def kick():
    dur = 0.65
    t = np.arange(int(dur * SR)) / SR
    freq = 110 * np.exp(-t * 25) + 42
    phase = 2 * np.pi * np.cumsum(freq) / SR
    body = np.sin(phase) * np.exp(-t * 10) * 0.70
    sub = np.sin(2 * np.pi * 48 * t) * np.exp(-t * 5) * 0.45
    click = np.sin(2 * np.pi * 800 * t) * np.exp(-t * 100) * 0.14
    return body + sub + click


def snare():
    dur = 0.26
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = bandpass(rng.standard_normal(n), 700, 8000)
    tone = np.sin(2 * np.pi * 185 * t) * np.exp(-t * 40)
    env_n = np.exp(-t * 22)
    return noise * env_n * 0.60 + tone * 0.40


def hihat_closed():
    dur = 0.065
    n = int(dur * SR)
    noise = bandpass(rng.standard_normal(n), 9000, 20000)
    env = np.exp(-np.arange(n) / n * 10)
    return noise * env


def hihat_open():
    dur = 0.30
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = bandpass(rng.standard_normal(n), 7000, 18000)
    return noise * np.exp(-t * 8)


def tom(freq):
    dur = 0.28
    t = np.arange(int(dur * SR)) / SR
    f = freq * np.exp(-t * 7) + freq * 0.55
    phase = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(phase) * np.exp(-t * 11) * 0.9


def crash():
    dur = 1.1
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = bandpass(rng.standard_normal(n), 4000, 18000)
    return noise * np.exp(-t * 3.0)


# ----------------------------------------------------------------------------- transition FX

def riser(dur):
    """Filtered-noise wash that opens up and crescendos — tension before a drop (no siren sweep)."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    # Broadband noise wash that swells in — a "whoosh", not a pitched siren
    wash = bandpass(rng.standard_normal(n), 400, 9000) * 0.5
    cresc = (t / dur) ** 2.2  # exponential swell
    return wash * cresc


def impact():
    """Downbeat slam for a drop: sub boom + crash burst."""
    dur = 1.5
    t = np.arange(int(dur * SR)) / SR
    freq = 95 * np.exp(-t * 9) + 38
    phase = 2 * np.pi * np.cumsum(freq) / SR
    boom = np.sin(phase) * np.exp(-t * 2.4) * 0.85
    burst = bandpass(rng.standard_normal(len(t)), 3000, 16000) * np.exp(-t * 4.5) * 0.5
    return boom + burst


def stereo(sig, pan=0.0):
    l_gain = np.sqrt(0.5 * (1 - pan))
    r_gain = np.sqrt(0.5 * (1 + pan))
    return sig * l_gain, sig * r_gain


# ----------------------------------------------------------------------------- arrangement

def render_section(tonal_l, tonal_r, perc_l, perc_r, kick_times, start_bar, n_bars, *,
                    pad=True, bass=True, arp=True, arp_div=2, perc_mode=None,
                    lead=False, pad_gain=1.0, tonal_gain=1.0, perc_gain=1.0,
                    do_riser=False, do_impact=False, do_fill=False, crash_bars=False):
    last_bar = n_bars - 1
    for bar_i in range(n_bars):
        bar_t = (start_bar + bar_i) * BAR
        chord = CHORDS[bar_i % 4]
        arp_set = ARP_NOTES[bar_i % 4]

        if pad:
            for j, midi in enumerate([*chord["pad"], chord["color"]]):
                freq = midi_to_freq(midi)
                gain = pad_gain * tonal_gain * (0.85 if j < 4 else 0.35)
                sig = pad_voice(freq, BAR * 1.4) * gain
                l, r = stereo(sig, pan=(-0.32 + 0.16 * j))
                mix_add(tonal_l, tonal_r, bar_t, l, r)

        if bass:
            sig = bass_voice(midi_to_freq(chord["bass"]), BAR * 1.05) * 0.85 * tonal_gain
            mix_add(tonal_l, tonal_r, bar_t, sig, sig)

        if arp:
            step = BEAT / arp_div
            n_steps = 4 * arp_div
            for k in range(n_steps):
                note = arp_set[k % len(arp_set)]
                sig = arp_voice(midi_to_freq(note), step * 1.8) * 0.35 * tonal_gain
                pan = 0.22 if k % 2 == 0 else -0.22
                l, r = stereo(sig, pan=pan)
                mix_add(tonal_l, tonal_r, bar_t + k * step, l, r)

        # ----- percussion modes
        if perc_mode == "full":
            for beat_i in range(4):
                t0 = bar_t + beat_i * BEAT
                k = kick() * 0.60 * perc_gain
                mix_add(perc_l, perc_r, t0, k, k)
                kick_times.append(t0)
            for beat_i in (1, 3):
                sn = snare() * 0.46 * perc_gain
                l, r = stereo(sn, float(rng.uniform(-0.12, 0.12)))
                mix_add(perc_l, perc_r, bar_t + beat_i * BEAT, l, r)
            for k16 in range(16):
                vel = (0.24 if k16 % 4 == 0 else 0.12 + 0.09 * float(rng.random())) * perc_gain
                hh = hihat_closed() * vel
                l, r = stereo(hh, 0.18 * ((-1) ** k16))
                mix_add(perc_l, perc_r, bar_t + k16 * (BEAT / 4), l, r)
            if bar_i % 2 == 1:
                oh = hihat_open() * 0.34 * perc_gain
                l, r = stereo(oh, 0.40)
                mix_add(perc_l, perc_r, bar_t + 1.5 * BEAT, l, r)

        elif perc_mode == "hard":
            # The comeback: busier kick, ghost snares, open hats on every offbeat, crashes
            for beat_i in range(4):
                t0 = bar_t + beat_i * BEAT
                k = kick() * 0.68 * perc_gain
                mix_add(perc_l, perc_r, t0, k, k)
                kick_times.append(t0)
            # syncopated extra kick on the "and" of 3
            t_synco = bar_t + 2.5 * BEAT
            k = kick() * 0.50 * perc_gain
            mix_add(perc_l, perc_r, t_synco, k, k)
            kick_times.append(t_synco)
            for beat_i in (1, 3):
                sn = snare() * 0.56 * perc_gain
                l, r = stereo(sn, float(rng.uniform(-0.1, 0.1)))
                mix_add(perc_l, perc_r, bar_t + beat_i * BEAT, l, r)
            # ghost snares
            for gt in (0.75, 2.75):
                sn = snare() * 0.14 * perc_gain
                mix_add(perc_l, perc_r, bar_t + gt * BEAT, sn, sn)
            for k16 in range(16):
                vel = (0.30 if k16 % 4 == 0 else 0.16 + 0.10 * float(rng.random())) * perc_gain
                hh = hihat_closed() * vel
                l, r = stereo(hh, 0.20 * ((-1) ** k16))
                mix_add(perc_l, perc_r, bar_t + k16 * (BEAT / 4), l, r)
            for off in range(4):
                oh = hihat_open() * 0.26 * perc_gain
                l, r = stereo(oh, 0.35 * ((-1) ** off))
                mix_add(perc_l, perc_r, bar_t + (off + 0.5) * BEAT, l, r)
            if bar_i % 4 == 0:
                cr = crash() * 0.42 * perc_gain
                l, r = stereo(cr, -0.25)
                mix_add(perc_l, perc_r, bar_t, l, r)

        elif perc_mode == "half":
            # Half-time breakdown groove: spacious, heavy backbeat
            t0 = bar_t
            k = kick() * 0.62 * perc_gain
            mix_add(perc_l, perc_r, t0, k, k)
            kick_times.append(t0)
            sn = snare() * 0.44 * perc_gain
            mix_add(perc_l, perc_r, bar_t + 2 * BEAT, sn, sn)
            for k8 in range(8):
                if k8 % 2 == 0 or float(rng.random()) < 0.4:
                    hh = hihat_closed() * 0.10 * perc_gain
                    mix_add(perc_l, perc_r, bar_t + k8 * (BEAT / 2), hh, hh)

        elif perc_mode == "build":
            density = min(2 + bar_i * 2, 16)
            idxs = (range(16) if density >= 16
                    else sorted(rng.choice(16, size=density, replace=False)))
            for k16 in idxs:
                hh = hihat_closed() * (0.08 + 0.07 * float(rng.random())) * perc_gain
                mix_add(perc_l, perc_r, bar_t + k16 * (BEAT / 4), hh, hh)
            if bar_i >= n_bars // 2:
                t0 = bar_t
                k = kick() * 0.50 * perc_gain
                mix_add(perc_l, perc_r, t0, k, k)
                kick_times.append(t0)

        # ----- transition FX
        if do_impact and bar_i == 0:
            imp = impact() * 0.6 * perc_gain
            mix_add(perc_l, perc_r, bar_t, imp, imp)
        if crash_bars and bar_i % 4 == 0:
            cr = crash() * 0.32 * perc_gain
            l, r = stereo(cr, 0.2)
            mix_add(perc_l, perc_r, bar_t, l, r)
        if do_riser and bar_i == max(last_bar - 1, 0):
            rs = riser(BAR * 2) * perc_gain
            l, r = stereo(rs, 0.0)
            mix_add(perc_l, perc_r, bar_t, l, r)
        if do_fill and bar_i == last_bar:
            # descending tom roll across beats 3 & 4 into the next section
            fill_freqs = np.linspace(200, 80, 8)
            for i, ff in enumerate(fill_freqs):
                tm = tom(ff) * 0.6 * perc_gain
                l, r = stereo(tm, -0.4 + 0.8 * (i / 7))
                mix_add(perc_l, perc_r, bar_t + 2 * BEAT + i * (BEAT / 4), l, r)

        # ----- minimal lead: one sparse note every 4 bars (kept out of the siren register)
        if lead and bar_i % 4 == 0:
            note = chord["pad"][2]  # in-register, no octave jump
            sig = lead_voice(midi_to_freq(note), BAR * 1.6) * 0.24 * tonal_gain
            l, r = stereo(sig, pan=0.22)
            mix_add(tonal_l, tonal_r, bar_t + BEAT * 0.5, l, r)


def main():
    # Post-rock arc: intro → build → DROP → breakdown → build → DROP → quiet breakdown
    #                → big build → HARD COMEBACK → outro
    sections = [
        # 1. Cold intro — pads creeping in, nothing else
        dict(n_bars=8,  pad=True, bass=False, arp=False, perc_mode=None,
             pad_gain=0.45, tonal_gain=0.55),
        # 2. Build A — bass/arp enter, hats build, riser + fill into the drop
        dict(n_bars=8,  pad=True, bass=True,  arp=True,  perc_mode="build",
             tonal_gain=0.8, perc_gain=0.8, do_riser=True, do_fill=True),
        # 3. DROP A — full groove, impact hit, crashes
        dict(n_bars=16, pad=True, bass=True,  arp=True,  perc_mode="full", lead=True,
             do_impact=True, crash_bars=True, tonal_gain=1.0, perc_gain=1.0),
        # 4. Breakdown 1 — strip to half-time, haunting, low energy
        dict(n_bars=8,  pad=True, bass=True,  arp=False, perc_mode="half",
             pad_gain=0.7, tonal_gain=0.7, perc_gain=0.7),
        # 5. Build B — rebuild with arp, riser + fill
        dict(n_bars=8,  pad=True, bass=True,  arp=True,  perc_mode="build",
             tonal_gain=0.9, perc_gain=0.9, do_riser=True, do_fill=True),
        # 6. DROP B — full groove again, heavier
        dict(n_bars=16, pad=True, bass=True,  arp=True,  arp_div=2, perc_mode="full", lead=True,
             do_impact=True, crash_bars=True, tonal_gain=1.05, perc_gain=1.05),
        # 7. Quiet breakdown — near silence, just cold pads + sparse arp + one lead
        dict(n_bars=10, pad=True, bass=False, arp=True,  perc_mode=None, lead=True,
             pad_gain=0.5, tonal_gain=0.45),
        # 8. BIG build — long tension swell, double-time arp, riser + fill
        dict(n_bars=8,  pad=True, bass=True,  arp=True,  arp_div=4, perc_mode="build",
             tonal_gain=1.0, perc_gain=1.0, do_riser=True, do_fill=True),
        # 9. HARD COMEBACK — everything, busiest drums, impact, crashes, peak energy
        dict(n_bars=24, pad=True, bass=True,  arp=True,  arp_div=4, perc_mode="hard", lead=True,
             do_impact=True, tonal_gain=1.15, perc_gain=1.15, pad_gain=1.1),
        # 10. Outro — let it decay, pads dissolving into reverb
        dict(n_bars=12, pad=True, bass=False, arp=False, perc_mode=None,
             pad_gain=0.4, tonal_gain=0.4),
    ]
    total_bars = sum(s["n_bars"] for s in sections)
    total_secs = total_bars * BAR + 5.0
    n_samples = int(total_secs * SR)

    tonal_l, tonal_r = np.zeros(n_samples), np.zeros(n_samples)
    perc_l, perc_r = np.zeros(n_samples), np.zeros(n_samples)
    kick_times = []

    bar_cursor = 0
    for s in sections:
        kwargs = {k: v for k, v in s.items() if k != "n_bars"}
        render_section(tonal_l, tonal_r, perc_l, perc_r, kick_times, bar_cursor, s["n_bars"], **kwargs)
        bar_cursor += s["n_bars"]

    # Sidechain pump: duck tonal layers after each kick
    duck = np.ones(n_samples)
    depth = 0.42
    recovery_rate = 6.0 / (0.8 * BEAT)
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

    wet_l = schroeder_reverb(master_l, wet=0.32)
    wet_r = schroeder_reverb(master_r, wet=0.32)

    fade_in = int(2.0 * SR)
    fade_out = int(6.0 * SR)
    env = np.ones(n_samples)
    env[:fade_in] = np.linspace(0, 1, fade_in)
    env[-fade_out:] = np.linspace(1, 0, fade_out)

    out_l = np.tanh(wet_l * env * 0.85)
    out_r = np.tanh(wet_r * env * 0.85)

    peak = max(np.abs(out_l).max(), np.abs(out_r).max(), 1e-9)
    out_l = out_l / peak * 0.92
    out_r = out_r / peak * 0.92

    stereo_out = np.stack([out_l, out_r], axis=1)
    pcm = (stereo_out * 32767).astype(np.int16)
    wavfile.write("ambient_synthwave.wav", SR, pcm)
    print(f"Wrote ambient_synthwave.wav: {total_secs:.1f}s, {total_bars} bars at {BPM} BPM")


if __name__ == "__main__":
    main()
