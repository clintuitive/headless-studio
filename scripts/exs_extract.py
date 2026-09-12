"""Minimal EXS24 instrument parser/extractor for the Logic/GarageBand
factory library.

Use only with files you created or are authorized to parse and extract.
Format support does not grant permission to extract licensed factory content.
See THIRD_PARTY.md for the licensing boundary.

An .exs file is a sequence of chunks: 84-byte header (u32 flags -- kind in
the high byte -- u32 data size, u32 id, u32 pad, 'TBOS' magic, 64-byte
name) followed by `size` bytes of data. Zone chunks (kind 0x01 in the
flags high byte, 0x41 with the name-present bit) carry root note, key
range, velocity range, and exact sample-frame start/end offsets into the
referenced audio file; sample chunks (kind 0x03) carry the audio file
names. Together they let us cut individual, correctly-labeled hits
straight out of the '_consolidated.caf' containers -- no guesswork.

Usage:
  python3 exs_extract.py "<file.exs>"              # print the zone table
  python3 exs_extract.py "<file.exs>" <out_dir>    # extract hits as WAVs
Extracted files: note<NN>_v<lo>-<hi>_<i>.wav (+ manifest.json).
"""

import json
import os
import struct
import subprocess
import sys
import tempfile

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly


def parse_exs(path):
    data = open(path, "rb").read()
    zones, samples, groups = [], [], []
    pos = 0
    while pos + 84 <= len(data):
        # Logic has shipped both TBOS and the older JBOS EXS container
        # variants. Their chunk layout is the same for the fields used here.
        if data[pos + 16:pos + 20] not in (b"TBOS", b"JBOS"):
            pos += 1  # resync (some files have padding)
            continue
        kind = data[pos + 3] & 0x0F  # high bits flag name presence
        magic = data[pos + 16:pos + 20]
        size = struct.unpack_from("<I", data, pos + 4)[0]
        if magic == b"JBOS":
            # Legacy files set bit 15 as a chunk flag rather than including
            # it in the payload byte count.
            size &= 0x7FFF
        name = data[pos + 20:pos + 84].split(b"\x00")[0].decode("ascii", "replace")
        z = data[pos + 84:pos + 84 + size]
        if kind == 0x01 and size >= 96:  # zone
            zones.append({
                "name": name,
                "root": z[1],
                "keylo": z[6], "keyhi": z[7],
                "vello": z[9], "velhi": z[10],
                "start": struct.unpack_from("<I", z, 12)[0],
                "end": struct.unpack_from("<I", z, 16)[0],
                "group_idx": struct.unpack_from("<I", z, 88)[0],
                "sample_idx": struct.unpack_from("<I", z, 92)[0],
            })
        elif kind == 0x02:  # group (articulation) name
            groups.append(name)
        elif kind == 0x03:  # sample file reference
            samples.append({"name": name, "index": len(samples)})
        pos += 84 + size
    for zn in zones:
        zn["group"] = groups[zn["group_idx"]] if zn["group_idx"] < len(groups) else ""
    return zones, samples


def find_audio(sample_name, exs_path):
    """Locate the referenced audio file near the .exs or in the factory
    sample tree (mirrors the Sampler Instruments <-> EXS Factory layout)."""
    inst_dir = os.path.dirname(exs_path)
    candidates = [os.path.join(inst_dir, sample_name)]
    mirror = inst_dir.replace("/Sampler Instruments/", "/EXS Factory Samples/")
    candidates.append(os.path.join(mirror, sample_name))
    roots = [
        "/Library/Application Support/Logic/EXS Factory Samples",
        "/Library/Application Support/Logic/Sampler Files",
        "/Library/Application Support/GarageBand/Instrument Library/Sampler/Sampler Files",
    ]
    for root in roots:
        if not os.path.isdir(root):
            continue
        hit = subprocess.run(["find", root, "-name", sample_name, "-print", "-quit"],
                             capture_output=True, text=True).stdout.strip()
        if hit:
            candidates.append(hit)
    if "#" in sample_name:
        # EXS 64-byte name field truncates long names as 'prefix#HASH.ext';
        # fuzzy-match the prefix against the real (untruncated) file.
        prefix = sample_name.split("#")[0]
        ext = os.path.splitext(sample_name)[1]
        for root in roots:
            if not os.path.isdir(root):
                continue
            hit = subprocess.run(["find", root, "-name", f"{prefix}*{ext}", "-print", "-quit"],
                                 capture_output=True, text=True).stdout.strip()
            if hit:
                candidates.append(hit)
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def main():
    exs_path = sys.argv[1]
    zones, samples = parse_exs(exs_path)
    print(f"{len(zones)} zones, {len(samples)} sample files")
    for s in samples:
        print(f"  sample[{s['index']}]: {s['name']}")
    if len(sys.argv) < 3:
        for z in zones[:40]:
            print(f"  key {z['keylo']:3d}-{z['keyhi']:3d} vel {z['vello']:3d}-{z['velhi']:3d} "
                  f"smp{z['sample_idx']} frames {z['start']}-{z['end']} ({z['name']})")
        if len(zones) > 40:
            print(f"  ... and {len(zones) - 40} more")
        return

    out_dir = sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    audio_cache = {}
    manifest = []
    with tempfile.TemporaryDirectory() as td:
        for i, z in enumerate(zones):
            s = samples[z["sample_idx"]]
            if s["name"] not in audio_cache:
                src = find_audio(s["name"], exs_path)
                if src is None:
                    print(f"  MISSING: {s['name']}")
                    audio_cache[s["name"]] = None
                    continue
                wav = os.path.join(td, f"src{z['sample_idx']}.wav")
                converted = subprocess.run(
                    ["afconvert", "-f", "WAVE", "-d", "LEI16@44100", src, wav],
                    capture_output=True,
                )
                if converted.returncode != 0:
                    # Some newer GarageBand CAFs contain AAC/ALAC at 22.05 kHz
                    # that current afconvert builds refuse to transcode.
                    # Decode at the native rate so EXS frame offsets remain
                    # valid; individual zones are resampled after slicing.
                    subprocess.run(
                        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                         "-i", src, "-c:a", "pcm_s16le", wav],
                        check=True,
                    )
                sr, x = wavfile.read(wav)
                audio_cache[s["name"]] = (sr, x)
            entry = audio_cache[s["name"]]
            if entry is None:
                continue
            sr, x = entry
            seg = x[z["start"]:z["end"]]
            if len(seg) < 32:
                continue
            if sr != 44100:
                from math import gcd
                divisor = gcd(sr, 44100)
                if np.issubdtype(seg.dtype, np.integer):
                    scale = float(max(abs(np.iinfo(seg.dtype).min),
                                      np.iinfo(seg.dtype).max))
                    seg = seg.astype(np.float32) / scale
                seg = resample_poly(seg, 44100 // divisor, sr // divisor)
                sr = 44100
            fname = f"note{z['keylo']:03d}_v{z['vello']:03d}-{z['velhi']:03d}_{i:03d}.wav"
            wavfile.write(os.path.join(out_dir, fname), sr, seg)
            manifest.append({**{k: int(v) if isinstance(v, (int, np.integer)) else v
                                for k, v in z.items()}, "file": fname})
    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    print(f"extracted {len(manifest)} hits to {out_dir}")


if __name__ == "__main__":
    main()
