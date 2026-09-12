"""The quiet companion to postrock_hammock, v2: the user's ambient demo
RECREATED as a played clean-guitar bed instead of sampled from the
recording -- so every part shares one clock and the seams disappear.

The demo analysis (chromagram, 2s hops) shows a white-note wash dwelling
~4-7s per chord: at 68 BPM that is two bars per change, on the F-C-Dm-Am
turn. Two independently-humanized Strat takes (neck-pickup comb, Twin +
cab, dotted-delay whisper, modulated plate) pick that progression in
broken chords, sparse and low in the intro, fuller through the middle,
dissolving again at the end -- the same build-and-release arc as the
original recording, but grid-true.

Everything else stays four-elements simple: Steinway theme, heartbeat
percussion (Brooklyn at whisper velocities), long Ample bass notes.
"""

import os

import numpy as np
from scipy.io import wavfile

import generate_postrock_hammock as hk
from generate_postrock_hammock import PIANO_THEME, CHORDS, PROGS, SAMPLES
from music_engine import DrumSampler, ExsSampler, normalize_peak, stereo
from pedalboard import (Pedalboard, Chorus, Delay, Reverb, Compressor, Gain,
                        HighpassFilter, LowpassFilter, PeakFilter,
                        LowShelfFilter, Convolution)

SR = 44100
BPM = 68
BEAT = 60.0 / BPM
BAR = BEAT * 4
SEED = 11

rng = np.random.default_rng(SEED)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(SCRIPT_DIR, "..", "Tracks", "ambient_song.wav")
ROOM_IR = os.path.join(SCRIPT_DIR, "..", "IRs", "Highly Damped Large Room.wav")

KICK, STICK, T_FLR, RIDE, HH_PEDAL = 36, 37, 43, 51, 44

EVENTS = {"piano": [], "drums": [], "gbedL": [], "gbedR": []}
brooklyn = DrumSampler(hk.BROOKLYN_DIR, sample_rate=SR, rng=rng, output_gain=1.3)


def human(t, vel, t_sd=0.010, v_sd=5):
    t = max(t + float(np.clip(rng.normal(0, t_sd), -2.5 * t_sd, 2.5 * t_sd)), 0.0)
    vel = int(np.clip(vel + rng.normal(0, v_sd), 1, 127))
    return t, vel


def add_note(bus, t, dur, note, vel, ch=0):
    EVENTS[bus].append((int(t * SR), "on", ch, note, vel))
    EVENTS[bus].append((int((t + dur) * SR), "off", ch, note, 0))


# ---- the recreated demo: clean-guitar bed ------------------------------------

def gbed_bar(bar_t, chord, mode, vel_base, bus):
    """One take of the bed. 'sparse': a slow-rolled chord ringing the full
    bar. 'picked': broken chords in ringing eighths, the accent wandering
    the way idle fingers do (fixed pattern, so both takes agree)."""
    tones = chord["arp"]
    if mode == "sparse":
        for i, note in enumerate(tones[:4]):
            t, v = human(bar_t + 0.05 + i * 0.09, vel_base - 6, t_sd=0.010, v_sd=4)
            add_note(bus, t, BAR * 1.05, note, v)
    else:
        pattern = [0, 2, 4, 3, 1, 3, 4, 2]
        step = BEAT / 2
        for k, ti in enumerate(pattern):
            t, v = human(bar_t + k * step, vel_base, t_sd=0.008, v_sd=4)
            add_note(bus, t, step * 2.4, tones[ti], v)


# ---- the band ------------------------------------------------------------------

def piano_theme(start_bar, n_bars):
    for cyc in range(0, n_bars, 8):
        for bar_off, beat, dur_b, note in PIANO_THEME:
            if cyc + bar_off >= n_bars:
                continue
            t0 = (start_bar + cyc + bar_off) * BAR + beat * BEAT
            t0, vel = human(t0, 58, t_sd=0.012, v_sd=4)
            add_note("piano", t0, dur_b * BEAT * 1.05, note, vel)
        for ch_i in range(4):
            if cyc + ch_i * 2 >= n_bars:
                continue
            chord = CHORDS[PROGS["calm"][ch_i]]
            t0 = (start_bar + cyc + ch_i * 2) * BAR
            t, v = human(t0, 46, t_sd=0.014, v_sd=3)
            add_note("piano", t, BAR * 1.9, chord["bass"] + 24, v)


def piano_sparse(bar_t, chord):
    for i, note in enumerate(chord["pad"]):
        t, v = human(bar_t + i * 0.07, 48, t_sd=0.012, v_sd=3)
        add_note("piano", t, BAR * 1.9, note, v)


def piano_chime(bar_t, chord):
    t, vel = human(bar_t + 2 * BEAT, 50, t_sd=0.015, v_sd=4)
    add_note("piano", t, BAR * 1.5, chord["pad"][2] + 12, vel)


def perc_bar(bar_t, phrase_bar):
    t, v = human(bar_t, 60, t_sd=0.012)
    add_note("drums", t, 0.08, KICK, v, ch=9)
    t, v = human(bar_t + 2 * BEAT, 54, t_sd=0.012)
    add_note("drums", t, 0.08, STICK, v, ch=9)
    for b in (1.0, 3.0):
        t, v = human(bar_t + b * BEAT, 34, t_sd=0.014, v_sd=4)
        add_note("drums", t, 0.08, HH_PEDAL, v, ch=9)
    if phrase_bar % 2 == 1:
        t, v = human(bar_t + 1.5 * BEAT, 36, t_sd=0.014, v_sd=4)
        add_note("drums", t, 0.08, RIDE, v, ch=9)
    if phrase_bar % 8 == 7:
        for b, vel in ((3.0, 44), (3.5, 50)):
            t, v = human(bar_t + b * BEAT, vel, t_sd=0.012)
            add_note("drums", t, 0.08, T_FLR, v, ch=9)


def bass_chord(bar_t, chord, phrase_bar):
    t, vel = human(bar_t, 76, t_sd=0.010, v_sd=3)
    hk.AMPLE_NOTES.append({"t": t, "dur": BAR * 1.85, "note": chord["bass"], "vel": vel})
    if phrase_bar % 4 == 2 and rng.random() < 0.5:
        t, vel = human(bar_t + BAR + 3 * BEAT, 68, t_sd=0.012, v_sd=3)
        hk.AMPLE_NOTES.append({"t": t, "dur": BEAT * 0.9, "note": chord["bass"] + 7, "vel": vel})


# ---- arrangement --------------------------------------------------------------

def main():
    movements = [
        # The recreated demo alone: rolled chords surfacing from silence.
        dict(n_bars=8, gbed="sparse", gvel=50, glev=0.8),
        # The picking pattern wakes; piano finds the theme inside it.
        dict(n_bars=16, gbed="picked", gvel=54, glev=0.72, piano="theme"),
        # Bass settles under.
        dict(n_bars=16, gbed="picked", gvel=58, glev=0.68, piano="theme", bass=True),
        # The heartbeat joins.
        dict(n_bars=16, gbed="picked", gvel=60, glev=0.65, piano="theme", bass=True, perc=True),
        # Fullest it gets: a high chime rides above the theme.
        dict(n_bars=16, gbed="picked", gvel=64, glev=0.7, piano="theme", bass=True, perc=True, chime=True),
        # Release: back to rolled chords, heartbeat rests.
        dict(n_bars=8, gbed="sparse", gvel=52, glev=0.85, piano="sparse", bass=True),
        # The guitar alone again, dissolving into the plate.
        dict(n_bars=10, gbed="sparse", gvel=46, glev=0.9),
    ]

    total_bars = sum(m["n_bars"] for m in movements)
    total_secs = total_bars * BAR + 8.0
    print(f"{total_bars} bars, {total_secs/60:.1f} minutes")

    glev_bp = [(0, 0.8)]
    bar_cursor = 0
    for m in movements:
        glev_bp.append((bar_cursor + 2, m["glev"]))
        glev_bp.append((bar_cursor + m["n_bars"] - 1, m["glev"]))
        for bar_i in range(m["n_bars"]):
            bar_t = (bar_cursor + bar_i) * BAR
            chord = CHORDS[PROGS["calm"][(bar_i // 2) % 4]]
            for bus in ("gbedL", "gbedR"):  # two independent takes
                gbed_bar(bar_t, chord, m["gbed"], m["gvel"], bus)
            if m.get("piano") == "sparse" and bar_i % 2 == 0:
                piano_sparse(bar_t, chord)
            if m.get("chime") and bar_i % 2 == 0:
                piano_chime(bar_t, chord)
            if m.get("perc"):
                perc_bar(bar_t, bar_i)
            if m.get("bass") and bar_i % 2 == 0:
                bass_chord(bar_t, chord, bar_i)
        if m.get("piano") == "theme":
            piano_theme(bar_cursor, m["n_bars"])
        bar_cursor += m["n_bars"]

    print("Rendering ...")
    neck = dict(pickup=0.27, deterministic=True)
    strat_l = ExsSampler(os.path.join(SAMPLES, "VintageStrat"), rng=rng, **neck)
    strat_r = ExsSampler(os.path.join(SAMPLES, "VintageStrat"), rng=rng, **neck)
    gbed = (stereo(strat_l.render(EVENTS["gbedL"], total_secs), pan=-0.4)
            + stereo(strat_r.render(EVENTS["gbedR"], total_secs), pan=0.4))
    gbed = normalize_peak(gbed, 0.4)
    piano_smp = ExsSampler(os.path.join(SAMPLES, "SteinwayPiano"), rng=rng)
    piano = stereo(piano_smp.render(EVENTS["piano"], total_secs), pan=-0.08)
    piano = normalize_peak(piano, 0.5)
    drums = brooklyn.render(EVENTS["drums"], total_secs)
    bass = hk.render_ample_bass(total_secs)
    if bass is None:
        raise SystemExit("Ample bass helper failed")

    print("Applying effects ...")
    # The recreated demo's dream chain: neck Strat -> spotless Twin + cab
    # -> whisper of dotted delay -> modulated plate, generously wet.
    twin = hk.load_nam(os.path.join(hk.AMPS, "Fender_TwinVerb_Clean.nam"))
    twin.input_db = -4.0
    twin.output_db = 20.0
    gbed = Pedalboard([
        PeakFilter(cutoff_frequency_hz=1000, gain_db=-4.0, q=1.1),
        LowShelfFilter(cutoff_frequency_hz=220, gain_db=2.0),
        LowpassFilter(cutoff_frequency_hz=5000),
        twin,
        Convolution(hk.CAB_IR, mix=1.0),
        Gain(gain_db=16.0),
        Delay(delay_seconds=BEAT * 0.75, feedback=0.25, mix=0.1),
    ])(gbed, SR)
    plate = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=150),
        Reverb(room_size=0.9, damping=0.2, wet_level=1.0, dry_level=0.0, width=1.0),
        Chorus(rate_hz=0.5, depth=0.25, centre_delay_ms=9.0, mix=0.7),
    ])(gbed, SR)
    gbed = gbed * 0.7 + plate * 0.45

    # Section-level breathing, same role the demo's gain automation had.
    glev_bp = sorted(glev_bp)
    t = np.arange(gbed.shape[1], dtype=np.float64) / SR
    times = np.array([bp[0] * BAR for bp in glev_bp])
    gains = np.array([bp[1] for bp in glev_bp])
    gbed *= np.interp(t, times, gains).astype(np.float32)

    piano = Pedalboard([
        LowpassFilter(cutoff_frequency_hz=9000),
        Reverb(room_size=0.88, damping=0.5, wet_level=0.3, dry_level=0.7, width=1.0),
    ])(piano, SR)
    bass = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=30),
        Compressor(threshold_db=-20, ratio=3, attack_ms=10, release_ms=180),
    ])(bass, SR)
    drums = Pedalboard([
        Compressor(threshold_db=-18, ratio=2.5, attack_ms=6, release_ms=200),
        LowpassFilter(cutoff_frequency_hz=9500),
    ])(drums, SR)

    gbed *= 1.0
    piano *= 0.85
    bass *= 0.9
    drums *= 0.7
    dry = gbed + piano + bass + drums

    rms = lambda a: np.sqrt((a ** 2).mean())
    room_send = (0.7 * drums + 0.5 * piano + 0.3 * gbed + 0.15 * bass).astype(np.float32)
    room = Convolution(ROOM_IR, mix=1.0)(room_send, SR)
    room *= 0.18 * rms(dry) / max(rms(room), 1e-9)

    master = dry + room
    n = master.shape[1]
    env = np.ones(n, dtype=np.float32)
    fade_in, fade_out = int(1.5 * SR), int(7.0 * SR)
    env[:fade_in] = np.linspace(0, 1, fade_in)
    env[-fade_out:] = np.linspace(1, 0, fade_out)
    master *= env
    master = master / max(np.abs(master).max(), 1e-9) * 0.9
    wavfile.write(OUT_PATH, SR, (master.T * 32767).astype(np.int16))
    print(f"Wrote {os.path.normpath(OUT_PATH)}: {total_secs/60:.1f} min, {total_bars} bars at {BPM} BPM")


if __name__ == "__main__":
    main()
