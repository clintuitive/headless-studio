"""Renders the modern-darkwave drum groove once per available drum machine
kit, so different voicings can be auditioned side by side.

Same beat as generate_modern_darkwave_band.py -- kick on 1 and 3, snare on
2 and 4, straight eighth hats with an open hat on the last offbeat, 118
BPM, dead quantized -- and the same processing (glue compression plus the
shared room IR send), so a preview sounds exactly like that kit would in
the actual track. Output: one 8-bar WAV per kit in Tracks/Kit Auditions/.
"""

import os

import numpy as np
from pedalboard import Pedalboard, Compressor, Convolution
from scipy.io import wavfile

SR = 44100
BPM = 118
BEAT = 60.0 / BPM
BAR = BEAT * 4
N_BARS = 8

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLES_DIR = os.path.join(SCRIPT_DIR, "..", "Samples")
ROOM_IR = os.path.join(SCRIPT_DIR, "..", "IRs", "Nice Drum Room.wav")
OUT_DIR = os.path.join(SCRIPT_DIR, "..", "Tracks", "Kit Auditions")

# kit folder -> filenames for kick, snare, closed hat, open hat
KITS = {
    "LM-2":      ("kick.wav", "snare-m.wav", "hhclosed.wav", "hhopen.wav"),
    "Drumtraks": ("DT_Kick.wav", "DT_Snare.wav", "DT_Closedhat.wav", "DT_Openhat.wav"),
    "TR-808":    ("kick.wav", "snare.wav", "hhc.wav", "hho.wav"),
    "CR-8000":   ("kick.wav", "snare.wav", "hhc.wav", "hho.wav"),
    "RZ-1":      ("kick.wav", "snare.wav", "hhc.wav", "hho.wav"),
    "MFB-512":   ("kick.wav", "snare.wav", "hhc.wav", "hho.wav"),
    "MR10":      ("kick.wav", "snare.wav", "hhc.wav", "hho.wav"),
    "SK-1":      ("kick.wav", "snare.wav", "hhc.wav", "hho.wav"),
}
GAINS = {"kick": 0.95, "snare": 0.8, "hhc": 0.4, "hho": 0.45}


def load_hit(kit, fname, gain):
    _, data = wavfile.read(os.path.join(SAMPLES_DIR, kit, fname))
    data = data.astype(np.float32) / 32768.0
    if data.ndim == 2:
        data = data.mean(axis=1)
    return data / max(np.abs(data).max(), 1e-9) * gain


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    total_secs = N_BARS * BAR + 1.5
    n_samples = int(total_secs * SR)
    fx = Pedalboard([Compressor(threshold_db=-15, ratio=3, attack_ms=2, release_ms=60)])
    room = Convolution(ROOM_IR, mix=1.0)

    for kit, (kick_f, snare_f, hhc_f, hho_f) in KITS.items():
        hits = {n: load_hit(kit, f, GAINS[n]) for n, f in
                zip(("kick", "snare", "hhc", "hho"), (kick_f, snare_f, hhc_f, hho_f))}
        bus = np.zeros((2, n_samples), dtype=np.float32)
        for bar in range(N_BARS):
            bar_t = bar * BAR
            events = ([(bar_t + b * BEAT, "kick") for b in (0, 2)]
                      + [(bar_t + b * BEAT, "snare") for b in (1, 3)]
                      + [(bar_t + k * BEAT / 2, "hho" if k == 7 else "hhc") for k in range(8)])
            for t, name in events:
                s = hits[name]
                start = int(t * SR)
                end = min(start + len(s), n_samples)
                bus[:, start:end] += s[:end - start]

        dry = fx(bus, SR)
        wet = room((dry * 0.7).astype(np.float32), SR)
        rms = lambda a: np.sqrt((a ** 2).mean())
        out = dry + wet * (0.22 * rms(dry) / max(rms(wet), 1e-9))
        peak = max(np.abs(out).max(), 1e-9)
        out = out / peak * 0.9
        path = os.path.join(OUT_DIR, f"{kit}.wav")
        wavfile.write(path, SR, (out.T * 32767).astype(np.int16))
        print(f"wrote {kit}.wav")


if __name__ == "__main__":
    main()
