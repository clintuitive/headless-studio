"""Synthesizes a loopable orchestral march in the style of Akira Ifukube's
Showa-era Toho kaiju film scores (Godzilla 1954, Rodan 1956), and renders
it to a WAV file for use as a game soundtrack loop.

Ifukube's kaiju march rests on five recognisable elements, all reproduced here
with oscillators and envelopes -- no samples.

  Taiko bass drum — a deep sine-sweep voice (160 Hz pitch-dropping to 45 Hz)
  with a long, resonant body. The pattern: heavy downbeats on 1 and 3, medium
  hits on 2 and 4, plus a pushed 8th-note just before beats 3 and 1-of-next-bar
  ("BOOM-bm-BOOM, BOOM-bm-BOOM"), giving the music its characteristic
  lumbering, relentless forward motion.

  Military side drum — bandpassed noise plus a low tone-tap on beats 2 and 4,
  dry and close, no reverb. The martial punctuation Ifukube borrowed from
  Western military march writing.

  Crash cymbal — on section downbeats (bars 0, 8, 16, 24) only, with a long
  2-second decay. Toho percussion sections did not play cymbals on every bar.

  Tuba / low brass ostinato — square+sawtooth voice filtered dark (~500 Hz),
  pedaling root on beats 1-3, a chromatic lower-neighbor approach note just
  before beat 3, and a power-fifth leap on beat 4. Sets the harmonic floor
  while the choir does the colour work.

  Open brass choir — three-voice open voicings (root / fifth / octave) per
  chord, not triads. Ifukube's orchestration avoided the "filled-in" third
  in his monster cues; the hollow open interval gives the brass its massive,
  cavernous character. Each voice gets slow vibrato (5.5 Hz) fading in after
  the initial attack, as a live player would.

  String tremolo — three detuned sawtooth oscillators per chord tone,
  amplitude-modulated at 7 Hz. Heavy hall reverb. The pulsing-danger texture
  Ifukube placed under every monster-approach scene.

  Brass lead (horn) — monophonic, brighter than the choir, playing an 8-bar
  monster-march theme: dotted rhythms (the characteristic Ifukube long-short
  push), a fifth leap in bar 1, chromatic semitone descents in bars 2 and 5,
  and a falling cadential figure in bars 4 and 8 that lands on the root D just
  in time for the seamless loop restart.

Harmonic plan: D Aeolian (D natural minor). 32 bars at 120 BPM = 64 seconds.
Progression: A section (Dm × 4, Gm Gm A A) × 2 with a B section
(Dm Dm Bb A / Gm A Dm Dm) and a Climax (Dm Dm Gm A / Dm Bb A Dm).
The loop ends on Dm, matching bar 1 -- clean loop point, no crossfade needed.
"""

import numpy as np
from scipy.signal import sawtooth, butter, lfilter
from scipy.io import wavfile

SR = 44100
BPM = 120
BEAT = 60.0 / BPM   # 0.5 s per beat
BAR  = BEAT * 4     # 2.0 s per bar
STEP = BEAT / 4     # 16th note = 0.125 s

SEED = 1956         # year Rodan was released
rng = np.random.default_rng(SEED)

LOOP_BARS = 32
TOTAL_SECS = LOOP_BARS * BAR   # 64.0 s -- seamless loop, no tail

# Open brass voicings: root / fifth / octave (no third -- Ifukube's hollow sound).
# "bass" = tuba MIDI note, "choir" = brass choir MIDI notes.
CHORDS = {
    "Dm": {"bass": 38, "choir": [62, 69, 74]},   # D2  /  D4 A4 D5
    "Gm": {"bass": 43, "choir": [67, 74, 79]},   # G2  /  G4 D5 G5
    "Bb": {"bass": 46, "choir": [70, 74, 77]},   # Bb2 /  Bb4 D5 F5
    "A":  {"bass": 45, "choir": [69, 73, 76]},   # A2  /  A4 C#5 E5  (V -- major)
}

PROG = [
    # A section (bars 0-7)
    "Dm","Dm","Dm","Dm",  "Gm","Gm","A","A",
    # B section (bars 8-15)
    "Dm","Dm","Bb","A",   "Gm","A","Dm","Dm",
    # A reprise (bars 16-23)
    "Dm","Dm","Dm","Dm",  "Gm","Gm","A","A",
    # Climax (bars 24-31) -- ends on Dm, loops back to bar 0
    "Dm","Dm","Gm","A",   "Dm","Bb","A","Dm",
]
assert len(PROG) == LOOP_BARS

MELODY_ROOT = 62   # D4

# 8-bar brass monster theme.  (phrase_bar, beat_offset, duration_beats, semis_from_D4)
# Ifukube hallmarks: dotted long-short push, fifth leap, chromatic semitone descents.
MELODY = [
    # Bar 0: D(dotted-q) F(8th) G(q) G(q)
    (0, 0.0, 1.5,  0), (0, 1.5, 0.5, 3), (0, 2.0, 1.0, 5), (0, 3.0, 1.0, 5),
    # Bar 1: F(half) E(q) Eb(q)  -- chromatic descent
    (1, 0.0, 2.0,  3), (1, 2.0, 1.0, 2), (1, 3.0, 1.0, 1),
    # Bar 2: D(dotted-q) C#(8th) D(half)
    (2, 0.0, 1.5,  0), (2, 1.5, 0.5, -1), (2, 2.0, 2.0, 0),
    # Bar 3: A G F D -- falling fifth cadence
    (3, 0.0, 1.0,  7), (3, 1.0, 1.0, 5), (3, 2.0, 1.0, 3), (3, 3.0, 1.0, 0),
    # Bar 4: G(dotted-q) Bb(8th) C(q) C(q)  -- over Gm, a fourth higher
    (4, 0.0, 1.5,  5), (4, 1.5, 0.5, 8), (4, 2.0, 1.0, 10), (4, 3.0, 1.0, 10),
    # Bar 5: Bb(half) A(q) Ab(q)  -- chromatic fall
    (5, 0.0, 2.0,  8), (5, 2.0, 1.0, 7), (5, 3.0, 1.0, 6),
    # Bar 6: A(dotted-q) F#(8th) A(half)  -- over A major, major third colour
    (6, 0.0, 1.5,  7), (6, 1.5, 0.5, 4), (6, 2.0, 2.0, 7),
    # Bar 7: B A G D  -- falling resolve, lands on root D ready to loop
    (7, 0.0, 1.0,  9), (7, 1.0, 1.0, 7), (7, 2.0, 1.0, 5), (7, 3.0, 1.0, 0),
]

# Percussion patterns (16 16th-note steps per bar).
# TAIKO: (step, gain) -- heavy downbeats + pushed 8th before beats 3 and 1.
TAIKO  = [(0, 1.0), (4, 0.65), (6, 0.42), (8, 1.0), (12, 0.65), (14, 0.42)]
SNARE  = [4, 12]           # military: beats 2 and 4 only
CRASH_BARS = {0, 8, 16, 24}   # section downbeats

# Tuba ostinato: (step, semitones_from_chord_bass) within each bar.
# Root pedal on 1-3, chromatic lower-neighbor pickup before 3, fifth on 4.
TUBA = [(0, 0), (4, 0), (7, -1), (8, 0), (12, 7)]


# ── utilities ────────────────────────────────────────────────────────────────

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


def bandpass(x, lo, hi, order=2, sr=SR):
    lo, hi = max(lo, 20), min(hi, sr / 2 - 100)
    b, a = butter(order, [lo / (sr / 2), hi / (sr / 2)], btype="band")
    return lfilter(b, a, x)


def comb(x, delay_s, feedback, sr=SR):
    d = max(int(delay_s * sr), 1)
    a = np.zeros(d + 1); a[0] = 1.0; a[-1] = -feedback
    return lfilter([1.0], a, x)


def hall_reverb(x, wet=0.45, sr=SR):
    """Schroeder reverb tuned for a large concert hall (~1.5 s RT60)."""
    combs = sum(comb(x, d, fb) for d, fb in
                [(0.0437, 0.82), (0.0411, 0.79), (0.0371, 0.77), (0.0297, 0.74)])
    combs /= 4.0
    for d, g in [(0.005, 0.7), (0.0017, 0.7)]:
        n = max(int(d * sr), 1)
        b = np.zeros(n + 1); b[0] = -g; b[-1] = 1.0
        a = np.zeros(n + 1); a[0] = 1.0; a[-1] = -g
        combs = lfilter(b, a, combs)
    return (1 - wet) * x + wet * combs


def mix_add(buf_l, buf_r, t0, sig_l, sig_r):
    s = int(t0 * SR)
    e = min(s + len(sig_l), len(buf_l))
    if e <= s:
        return
    n = e - s
    buf_l[s:e] += sig_l[:n]
    buf_r[s:e] += sig_r[:n]


def stereo(sig, pan=0.0):
    return sig * np.sqrt(0.5 * (1 - pan)), sig * np.sqrt(0.5 * (1 + pan))


# ── instrument voices ────────────────────────────────────────────────────────

def taiko_hit(gain=1.0):
    """Deep orchestral bass drum: long sine sweep 160 Hz → 45 Hz."""
    dur = 0.75
    n = int(dur * SR)
    t = np.arange(n) / SR
    freq = 160 * np.exp(-t * 7) + 45
    phase = 2 * np.pi * np.cumsum(freq) / SR
    body = np.sin(phase) * np.exp(-t * 5)
    thump_n = int(0.012 * SR)
    click = np.zeros(n)
    click[:thump_n] = rng.standard_normal(thump_n) * np.exp(-np.arange(thump_n) / SR * 400)
    click = lowpass(click, 180)
    return np.tanh((body * 0.9 + click * 0.3) * 1.4) * gain


def snare_hit():
    """Military side drum: noise burst + 210 Hz tone, short and dry."""
    dur = 0.18
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = bandpass(rng.standard_normal(n), 1500, 7000)
    tone = np.sin(2 * np.pi * 210 * t) * 0.3
    env = np.exp(-t * 42)
    return (noise + tone) * env * 0.5


def crash_cymbal():
    """Orchestral crash: broadband noise with a 2-second decay."""
    dur = 2.5
    n = int(dur * SR)
    noise = bandpass(rng.standard_normal(n), 2500, 14000)
    env = np.exp(-np.arange(n) / SR * 2.2)
    return noise * env * 0.45


def tuba_note(freq, dur):
    """Low brass: dark square+sawtooth filtered to ~500 Hz."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    phase = 2 * np.pi * freq * t
    osc = 0.6 * np.sign(np.sin(phase)) + 0.4 * sawtooth(phase)
    env = adsr(n, a=0.025, d=0.09, s=0.72, r=dur * 0.3)
    return lowpass(np.tanh(osc * env * 1.2), 520)


def brass_chord_voice(freq, dur):
    """Open brass choir note: sawtooth+square, vibrato fading in after attack."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    vib_env = np.clip((t - 0.15) / 0.3, 0, 1)
    pitch_lfo = 1.0 + 0.0045 * np.sin(2 * np.pi * 5.5 * t) * vib_env
    phase = 2 * np.pi * np.cumsum(freq * pitch_lfo) / SR
    osc = 0.6 * sawtooth(phase) + 0.4 * np.sign(np.sin(phase))
    env = adsr(n, a=0.07, d=0.18, s=0.78, r=dur * 0.35)
    return lowpass(np.tanh(osc * env * 1.1), 1700)


def brass_lead_note(freq, dur):
    """Solo horn: brighter than choir, slight attack transient, vibrato on sustain."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    vib_env = np.clip((t - 0.1) / 0.25, 0, 1)
    pitch_lfo = 1.0 + 0.005 * np.sin(2 * np.pi * 5.8 * t) * vib_env
    phase = 2 * np.pi * np.cumsum(freq * pitch_lfo) / SR
    osc = 0.65 * sawtooth(phase) + 0.35 * np.sign(np.sin(phase))
    # Brief noise transient -- the "edge" of a brass attack
    trans_n = int(0.018 * SR)
    trans = np.zeros(n)
    trans[:trans_n] = (rng.standard_normal(trans_n)
                       * np.linspace(0.35, 0, trans_n))
    trans = lowpass(trans, 3200)
    env = adsr(n, a=0.045, d=0.12, s=0.82, r=min(dur * 0.35, 0.45))
    return lowpass(np.tanh((osc + trans) * env * 1.05), 2400)


def string_tremolo_chord(freqs, dur, tremolo_hz=7.0, detune=0.003):
    """Tremolo strings: three detuned sawteeth per tone, fast AM at 7 Hz."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    tremolo = 0.5 + 0.5 * np.sin(2 * np.pi * tremolo_hz * t)
    sig = np.zeros(n)
    for f in freqs:
        for df in (1.0, 1 + detune, 1 - detune):
            sig += sawtooth(2 * np.pi * f * df * t) / (3 * len(freqs))
    env = adsr(n, a=0.55, d=0.3, s=0.68, r=dur * 0.45)
    return lowpass(sig, 2900) * env * tremolo


# ── arrangement ──────────────────────────────────────────────────────────────

N_SAMPLES = int(TOTAL_SECS * SR)


def new_bus():
    return np.zeros(N_SAMPLES), np.zeros(N_SAMPLES)


def render_percussion(perc_l, perc_r):
    for bar_i in range(LOOP_BARS):
        t_bar = bar_i * BAR
        for step, gain in TAIKO:
            sig = taiko_hit(gain)
            mix_add(perc_l, perc_r, t_bar + step * STEP, sig, sig)
        for step in SNARE:
            sig = snare_hit()
            mix_add(perc_l, perc_r, t_bar + step * STEP, sig, sig)
        if bar_i in CRASH_BARS:
            sig = crash_cymbal()
            # Slight stereo spread on crash
            l, r = stereo(sig, 0.15)
            mix_add(perc_l, perc_r, t_bar, l, r)


def render_tuba(tuba_l, tuba_r):
    note_dur = BEAT * 1.1   # slightly longer than a quarter note for legato
    for bar_i in range(LOOP_BARS):
        chord = CHORDS[PROG[bar_i]]
        t_bar = bar_i * BAR
        for step, semis in TUBA:
            freq = midi_to_freq(chord["bass"] + semis)
            sig = tuba_note(freq, note_dur) * 0.82
            mix_add(tuba_l, tuba_r, t_bar + step * STEP, sig, sig)


def render_choir(choir_l, choir_r):
    for bar_i in range(LOOP_BARS):
        chord = CHORDS[PROG[bar_i]]
        t_bar = bar_i * BAR
        for j, midi in enumerate(chord["choir"]):
            gain = 0.52 * (1.0 if j == 0 else 0.72)
            sig = brass_chord_voice(midi_to_freq(midi), BAR * 1.35) * gain
            pan = -0.38 + 0.38 * j   # root center-left, fifth right, octave further right
            l, r = stereo(sig, pan)
            mix_add(choir_l, choir_r, t_bar, l, r)


def render_strings(str_l, str_r):
    for bar_i in range(LOOP_BARS):
        chord = CHORDS[PROG[bar_i]]
        t_bar = bar_i * BAR
        # Strings one octave below the choir voicing
        freqs = [midi_to_freq(m - 12) for m in chord["choir"]]
        sig = string_tremolo_chord(freqs, BAR * 1.35) * 0.52
        l, r = stereo(sig, 0.0)
        mix_add(str_l, str_r, t_bar, l, r)


def render_lead(lead_l, lead_r):
    phrase_bars = 8
    for cycle in range(LOOP_BARS // phrase_bars):
        cycle_bar = cycle * phrase_bars
        for phrase_bar, beat_off, dur_b, semis in MELODY:
            global_bar = cycle_bar + phrase_bar
            if global_bar >= LOOP_BARS:
                continue
            t0 = global_bar * BAR + beat_off * BEAT
            dur = dur_b * BEAT + 0.06   # slight legato overlap
            sig = brass_lead_note(midi_to_freq(MELODY_ROOT + semis), dur) * 0.72
            # Lead sits just right of center, like a first horn in a Toho session
            l, r = stereo(sig, 0.12)
            mix_add(lead_l, lead_r, t0, l, r)


def main():
    perc_l,  perc_r  = new_bus()
    tuba_l,  tuba_r  = new_bus()
    choir_l, choir_r = new_bus()
    str_l,   str_r   = new_bus()
    lead_l,  lead_r  = new_bus()

    render_percussion(perc_l, perc_r)
    render_tuba(tuba_l, tuba_r)
    render_choir(choir_l, choir_r)
    render_strings(str_l, str_r)
    render_lead(lead_l, lead_r)

    # Reverb: hall on strings and choir; room on percussion; tuba nearly dry.
    wet_choir_l = hall_reverb(choir_l, wet=0.48)
    wet_choir_r = hall_reverb(choir_r, wet=0.48)
    wet_lead_l  = hall_reverb(lead_l,  wet=0.32)
    wet_lead_r  = hall_reverb(lead_r,  wet=0.32)
    wet_str_l   = hall_reverb(str_l,   wet=0.62)
    wet_str_r   = hall_reverb(str_r,   wet=0.62)
    wet_perc_l  = hall_reverb(perc_l,  wet=0.28)
    wet_perc_r  = hall_reverb(perc_r,  wet=0.28)
    wet_tuba_l  = hall_reverb(tuba_l,  wet=0.14)
    wet_tuba_r  = hall_reverb(tuba_r,  wet=0.14)

    master_l = wet_choir_l + wet_lead_l + wet_str_l + wet_perc_l + wet_tuba_l
    master_r = wet_choir_r + wet_lead_r + wet_str_r + wet_perc_r + wet_tuba_r

    master_l = np.tanh(master_l * 1.15)
    master_r = np.tanh(master_r * 1.15)

    peak = max(np.abs(master_l).max(), np.abs(master_r).max(), 1e-9)
    master_l = master_l / peak * 0.88
    master_r = master_r / peak * 0.88

    stereo_out = np.stack([master_l, master_r], axis=1)
    pcm = (stereo_out * 32767).astype(np.int16)
    wavfile.write("rodan_march.wav", SR, pcm)
    print(f"Wrote rodan_march.wav: {TOTAL_SECS:.1f}s, {LOOP_BARS} bars at {BPM} BPM (seamless loop)")


if __name__ == "__main__":
    main()
