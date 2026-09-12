"""Render matched Ashen Windows excerpts through GarageBand instruments."""

import os

import numpy as np
from pedalboard import Chorus, Compressor, HighpassFilter, LowpassFilter, Pedalboard, Reverb
from scipy.io import wavfile

from music_engine import EventTimeline, ExsSampler, load_nam, normalize_peak, stereo

SR = 44_100
BPM = 104
BEAT = 60 / BPM
BAR = BEAT * 4
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SAMPLES = os.path.join(ROOT, "Samples")
OUT = os.path.join(ROOT, "Tracks", "Ashen_Windows_Instrument_Auditions")
TWIN = os.path.join(ROOT, "Amps", "Fender_TwinVerb_Clean.nam")

CHORDS = [
    (40, [52, 59, 64, 66]), (36, [52, 55, 59, 64]),
    (43, [50, 55, 59, 62]), (42, [50, 54, 57, 62]),
    (45, [52, 57, 60, 64]), (47, [54, 59, 62, 66]),
]


def events():
    bass = EventTimeline(SR, ("part",))
    guitar = EventTimeline(SR, ("part",))
    order = [0, 2, 1, 3, 2, 1, 2, 3]
    pattern = [(0, 0), (.5, 0), (1, 7), (1.5, 0),
               (2, 12), (2.5, 7), (3, 0), (3.5, 5)]
    for bar, (root, chord) in enumerate(CHORDS):
        for beat, interval in pattern:
            bass.note("part", bar * BAR + beat * BEAT, BEAT * .41,
                      root + interval, 102 if beat in (0, 2) else 92)
        for step, index in enumerate(order):
            guitar.note("part", bar * BAR + step * BEAT / 2, BEAT * .42,
                        chord[index], 73)
    return bass["part"], guitar["part"]


def process_bass(audio):
    return Pedalboard([
        HighpassFilter(cutoff_frequency_hz=34),
        LowpassFilter(cutoff_frequency_hz=6200),
        Compressor(threshold_db=-18, ratio=4, attack_ms=8, release_ms=105),
    ])(stereo(audio), SR)


def process_guitar(audio):
    amp = load_nam(TWIN)
    amp.input_db = -8
    return Pedalboard([
        HighpassFilter(cutoff_frequency_hz=115),
        LowpassFilter(cutoff_frequency_hz=6500),
        Chorus(rate_hz=.72, depth=.15, centre_delay_ms=10.5, mix=.43),
        amp,
        Reverb(room_size=.78, damping=.54, wet_level=.25, dry_level=.75, width=1),
    ])(stereo(audio), SR)


def main():
    os.makedirs(OUT, exist_ok=True)
    bass_events, guitar_events = events()
    duration = len(CHORDS) * BAR + 2
    basses = [
        ("picked_rock_bass", "PickedRockBass",
         ["Group #3", "Group #4", "Group #5", "Group #6", "Group #7"]),
        ("p_bass", "PBass", ["Standard"]),
        ("palm_muted_bass", "PalmMutedBass",
         ["Group #5", "Group #6", "Group #7"]),
    ]
    guitars = [
        ("vintage_strat_main", "VintageStrat", ["Main"]),
        ("warm_electric_main", "WarmElectric", ["Main"]),
    ]
    for index, (label, directory, groups) in enumerate(basses):
        sampler = ExsSampler(os.path.join(SAMPLES, directory), sample_rate=SR,
                             rng=np.random.default_rng(100 + index),
                             groups=groups, release=.07)
        audio = normalize_peak(process_bass(sampler.render(bass_events, duration)), .82)
        wavfile.write(os.path.join(OUT, f"{label}.wav"), SR,
                      (audio.T * 32767).astype(np.int16))
    for index, (label, directory, groups) in enumerate(guitars):
        sampler = ExsSampler(os.path.join(SAMPLES, directory), sample_rate=SR,
                             rng=np.random.default_rng(200 + index),
                             groups=groups, pickup=.20, release=.16)
        audio = normalize_peak(process_guitar(sampler.render(guitar_events, duration)), .82)
        wavfile.write(os.path.join(OUT, f"{label}.wav"), SR,
                      (audio.T * 32767).astype(np.int16))
    print(f"Wrote 5 matched auditions to {OUT}")


if __name__ == "__main__":
    main()
