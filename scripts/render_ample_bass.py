"""Rosetta-side helper: renders a bass stem through Ample Bass P Lite II.

The ABPL2 Audio Unit is a 2016 Intel-only build, so it can't load inside
the arm64 render process. This script runs under an x86_64 Python
(~/.venvs/x86-audio, invoked via `arch -x86_64`) and does one job: read a
JSON note list, play it through the AU, write a WAV stem.

Two quirks matter. The plugin streams samples from disk, so it renders
silence until the streamer has spun up: warm-up renders with reset=False
keep the same processor instance alive until audio appears. And every
call must pass reset=False -- with the default reset=True pedalboard
rebuilds the processor per call and the streamer never catches up.

Usage: python render_ample_bass.py <events.json> <out.wav>
JSON: {"duration": secs, "notes": [{"t": secs, "dur": secs, "note": midi, "vel": 1-127}]}
"""

import json
import os
import sys

import numpy as np
from mido import Message
from pedalboard import load_plugin
from scipy.io import wavfile

SR = 44100
AU_PATH = os.path.expanduser("~/Library/Audio/Plug-Ins/Components/ABPL2.component")


def main():
    events_path, out_path = sys.argv[1], sys.argv[2]
    with open(events_path) as f:
        spec = json.load(f)

    plugin = load_plugin(AU_PATH)

    warmup = [Message("note_on", note=45, velocity=100, time=0.1),
              Message("note_off", note=45, time=0.6)]
    for attempt in range(8):
        test = plugin(warmup, duration=1.0, sample_rate=SR, buffer_size=8192, reset=False)
        if float(np.abs(test).max()) > 0.001:
            break
    else:
        sys.exit("Ample Bass produced no audio after warm-up attempts")

    msgs = []
    for n in spec["notes"]:
        msgs.append(Message("note_on", note=n["note"], velocity=n["vel"], time=n["t"]))
        msgs.append(Message("note_off", note=n["note"], time=n["t"] + n["dur"]))
    msgs.sort(key=lambda m: m.time)

    audio = plugin(msgs, duration=spec["duration"], sample_rate=SR,
                   buffer_size=8192, reset=False)
    peak = float(np.abs(audio).max())
    if peak < 0.001:
        sys.exit("Ample Bass rendered silence")
    wavfile.write(out_path, SR, (np.clip(audio.T, -1, 1) * 32767).astype(np.int16))
    print(f"ample bass stem: {spec['duration']:.1f}s, peak {peak:.3f}, {len(spec['notes'])} notes")


if __name__ == "__main__":
    main()
