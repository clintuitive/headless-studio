"""Export the user's 8 favorite album tracks as editable multi-track MIDI
+ a reference sheet, for fleshing out in GarageBand.

Each .mid holds one MTrk per part (Chords / Bass / Melody / Arp) at the
track's real tempo and meter, so GarageBand imports one software-
instrument track per part. The A section (8 bars) is written first; if
the track had a contrasting B phrase, it follows (bars 9-16). Notes are
reconstructed from each track's scale-degree spec -- the exact hooks and
progressions the user heard, now as notes they can edit and reassign.

No external deps (pure SMF byte writer). Output:
  Tracks/Favorites for GarageBand/NN Title.mid  +  README.md
"""

import os
import struct

SR_TPQ = 480  # ticks per quarter note

MODES = {"ion": [0, 2, 4, 5, 7, 9, 11], "dor": [0, 2, 3, 5, 7, 9, 10],
         "aeo": [0, 2, 3, 5, 7, 8, 10]}
PCNAME = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
MODEWORD = {"ion": "major", "dor": "dorian", "aeo": "minor"}

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "Tracks", "Favorites for GarageBand")

# The eight favorites, in the order the user named them. Each carries the
# exact spec fields from the album scripts. chord_bars: how long one chord
# lasts (Quiet Hours changes every bar, Sign-Off every two). bass_oct and
# arp: per-album voicing. kit/notes: for the reference sheet.
FAVORITES = [
    dict(n=1, title="Sodium Lights", album="Sign-Off", root=2, mode="dor", bpm=82,
         meter=4, chord_bars=2, bass_oct=2, arp=True, kit="LinnDrum LM-2",
         prog_a=[0, 3, 5, 4], prog_b=[5, 3, 0, 4],
         hook=[(0,0,1,7),(0,1,0.5,6),(0,1.5,0.5,5),(0,2,2,4),(1,0,1,5),(1,1,0.5,4),(1,1.5,0.5,2),(1,2,2,4),
               (2,0,1,7),(2,1,0.5,6),(2,1.5,0.5,5),(2,2,2,6),(3,0,4,4),
               (4,0,1,7),(4,1,0.5,8),(4,1.5,0.5,7),(4,2,2,6),(5,0,1,5),(5,1,0.5,4),(5,1.5,0.5,5),(5,2,2,6),
               (6,0,2,7),(6,2,2,5),(7,0,4,4)],
         hook_b=[(0,0,3,9),(0,3,1,8),(1,0,4,7),(2,0,3,8),(2,3,1,7),(3,0,4,6),
                 (4,0,3,7),(4,3,1,5),(5,0,4,4),(6,0,2,5),(6,2,2,6),(7,0,4,7)]),

    dict(n=2, title="Drive Home, 1983", album="Sign-Off", root=1, mode="aeo", bpm=88,
         meter=4, chord_bars=2, bass_oct=2, arp=True, kit="TR-808",
         prog_a=[0, 6, 5, 4], prog_b=[3, 6, 0, 4],
         hook=[(0,0,2,4),(0,2,1,4),(0,3,1,5),(1,0,2,4),(1,2,2,2),(2,0,2,4),(2,2,1,4),(2,3,1,5),(3,0,4,6),
               (4,0,2,7),(4,2,1,7),(4,3,1,8),(5,0,2,7),(5,2,2,5),(6,0,2,4),(6,2,1,5),(6,3,1,4),(7,0,4,2)],
         hook_b=[(0,0,3,9),(0,3,1,8),(1,0,3,7),(1,3,1,8),(2,0,4,9),(3,0,4,7),
                 (4,0,3,5),(4,3,1,4),(5,0,3,2),(5,3,1,4),(6,0,4,5),(7,0,4,4)]),

    dict(n=3, title="Slow Rain", album="The Quiet Hours", root=9, mode="aeo", bpm=60,
         meter=4, chord_bars=1, bass_oct=3, arp=False, kit=None, strings="Cello",
         prog_a=[0, 5, 2, 6], prog_b=[3, 2, 5, 4],
         hook=[(0,0,0.5,7),(0,0.5,0.5,6),(0,1,1,5),(0,2,2,4),(1,0,0.5,5),(1,0.5,0.5,4),(1,1,1,2),(1,2,2,0),
               (2,0,0.5,4),(2,0.5,0.5,2),(2,1,1,1),(2,2,2,2),(3,0,4,2),
               (4,0,0.5,7),(4,0.5,0.5,6),(4,1,1,5),(4,2,2,4),(5,0,0.5,5),(5,0.5,0.5,4),(5,1,1,2),(5,2,2,4),
               (6,0,0.5,4),(6,0.5,0.5,5),(6,1,1,6),(6,2,2,4),(7,0,4,7)],
         hook_b=[(0,0,3,5),(0,3,1,4),(1,0,3,4),(1,3,1,2),(2,0,2,4),(2,2,2,5),(3,0,4,6),
                 (4,0,3,5),(4,3,1,4),(5,0,3,2),(5,3,1,1),(6,0,2,2),(6,2,2,1),(7,0,4,0)]),

    dict(n=4, title="Northbound", album="The Quiet Hours", root=2, mode="ion", bpm=78,
         meter=4, chord_bars=1, bass_oct=3, arp=False, kit=None, strings="String Section",
         prog_a=[0, 4, 3, 4], prog_b=[5, 4, 3, 4],
         hook=[(0,0,0.5,4),(0,0.5,0.5,5),(0,1,1,6),(0,2,2,7),(1,0,0.5,6),(1,0.5,0.5,5),(1,1,1,6),(1,2,2,4),
               (2,0,0.5,5),(2,0.5,0.5,6),(2,1,1,7),(2,2,2,8),(3,0,4,6),
               (4,0,0.5,4),(4,0.5,0.5,5),(4,1,1,6),(4,2,2,7),(5,0,0.5,8),(5,0.5,0.5,7),(5,1,1,8),(5,2,2,9),
               (6,0,2,8),(6,2,2,6),(7,0,4,7)],
         hook_b=[(0,0,3,9),(0,3,1,8),(1,0,3,7),(1,3,1,8),(2,0,2,9),(2,2,2,10),(3,0,4,8),
                 (4,0,3,7),(4,3,1,6),(5,0,3,5),(5,3,1,6),(6,0,2,7),(6,2,2,5),(7,0,4,4)]),

    dict(n=5, title="Paper Boats", album="The Quiet Hours", root=2, mode="dor", bpm=63,
         meter=3, chord_bars=1, bass_oct=3, arp=False, kit=None, strings="3 Violins",
         prog_a=[0, 3, 0, 4], prog_b=[5, 3, 6, 4],
         hook=[(0,0,1,4),(0,1,2,5),(1,0,1,4),(1,1,2,2),(2,0,1,4),(2,1,1,5),(2,2,1,6),(3,0,3,4),
               (4,0,1,7),(4,1,2,8),(5,0,1,7),(5,1,2,5),(6,0,1,4),(6,1,1,2),(6,2,1,1),(7,0,3,0)],
         hook_b=[(0,0,2,9),(0,2,1,8),(1,0,3,7),(2,0,2,8),(2,2,1,7),(3,0,3,6),
                 (4,0,2,5),(4,2,1,4),(5,0,3,4),(6,0,1,2),(6,1,1,3),(6,2,1,4),(7,0,3,4)]),

    dict(n=6, title="The Small Hours", album="The Quiet Hours", root=4, mode="aeo", bpm=55,
         meter=4, chord_bars=1, bass_oct=3, arp=False, kit=None, strings="Cello",
         prog_a=[0, 5, 0, 4], prog_b=[3, 5, 1, 4],
         hook=[(0,0,4,4),(1,0,3,2),(1,3,1,0),(2,0,4,2),(3,0,3,1),(3,3,1,2),
               (4,0,4,4),(5,0,3,5),(5,3,1,4),(6,0,4,2),(7,0,4,0)],
         hook_b=[(0,0,4,5),(1,0,3,4),(1,3,1,5),(2,0,4,6),(3,0,4,4),
                 (4,0,4,3),(5,0,3,2),(5,3,1,3),(6,0,4,4),(7,0,4,2)]),

    dict(n=7, title="First Light", album="The Quiet Hours", root=0, mode="ion", bpm=66,
         meter=4, chord_bars=1, bass_oct=3, arp=False, kit=None, strings=None,
         prog_a=[0, 4, 5, 3], prog_b=[3, 4, 0, 4],
         hook=[(0,0,2,0),(0,2,2,1),(1,0,2,2),(1,2,2,4),(2,0,3,4),(2,3,1,3),(3,0,4,4),
               (4,0,2,7),(4,2,2,8),(5,0,2,9),(5,2,2,11),(6,0,3,10),(6,3,1,9),(7,0,4,7)],
         hook_b=[(0,0,2,5),(0,2,1,4),(0,3,1,3),(1,0,3,4),(1,3,1,2),(2,0,2,2),(2,2,2,4),(3,0,4,4),
                 (4,0,2,5),(4,2,1,6),(4,3,1,5),(5,0,3,6),(5,3,1,4),(6,0,2,7),(6,2,2,8),(7,0,4,7)]),

    dict(n=8, title="Static Bloom", album="Sign-Off", root=7, mode="aeo", bpm=58,
         meter=4, chord_bars=2, bass_oct=2, arp=False, kit=None,
         prog_a=[0, 3, 5, 4], prog_b=[5, 3, 0, 0],
         hook=[(0,0,4,4),(1,0,4,2),(2,0,4,3),(3,0,4,0),
               (4,0,4,4),(5,0,4,7),(6,0,4,5),(7,0,4,4)],
         hook_b=None),
]


def deg(root, mode, degree, base_oct=5):
    iv = MODES[mode]
    return 12 * (base_oct + degree // 7) + root + iv[degree % 7]


def chord_name(root, mode, cd):
    iv = MODES[mode]
    pc = (root + iv[cd % 7]) % 12
    third = (deg(root, mode, cd + 2, 0) - deg(root, mode, cd, 0)) % 12
    fifth = (deg(root, mode, cd + 4, 0) - deg(root, mode, cd, 0)) % 12
    suffix = {(4, 7): "", (3, 7): "m", (3, 6): "dim", (4, 8): "aug"}.get(
        (third, fifth), "m" if third == 3 else "")
    return PCNAME[pc] + suffix


# ---- minimal Standard MIDI File writer ---------------------------------------

def _vlq(n):
    out = bytearray([n & 0x7F])
    n >>= 7
    while n:
        out.insert(0, (n & 0x7F) | 0x80)
        n >>= 7
    return bytes(out)


def _track(events, name, tempo=None, timesig=None):
    """events: list of (tick, midi, dur_tick, vel, channel)."""
    msgs = []  # (tick, order, bytes)
    if name is not None:
        nb = name.encode()
        msgs.append((0, -3, b"\xff\x03" + _vlq(len(nb)) + nb))
    if tempo is not None:
        mpqn = 60_000_000 // tempo
        msgs.append((0, -2, b"\xff\x51\x03" + struct.pack(">I", mpqn)[1:]))
    if timesig is not None:
        num, den_pow = timesig  # den_pow: 2 -> quarter, so 3/4 = (3,2)
        msgs.append((0, -1, bytes([0xFF, 0x58, 0x04, num, den_pow, 24, 8])))
    for tick, midi, dur, vel, ch in events:
        msgs.append((tick, 1, bytes([0x90 | ch, midi, vel])))          # note on
        msgs.append((tick + dur, 0, bytes([0x80 | ch, midi, 0])))       # note off
    msgs.sort(key=lambda m: (m[0], m[1]))
    data = bytearray()
    last = 0
    for tick, _, b in msgs:
        data += _vlq(tick - last) + b
        last = tick
    data += b"\x00\xff\x2f\x00"
    return b"MTrk" + struct.pack(">I", len(data)) + bytes(data)


def write_midi(path, tracks_events, bpm, timesig):
    header = b"MThd" + struct.pack(">IHHH", 6, 1, len(tracks_events), SR_TPQ)
    chunks = b""
    for i, (name, events) in enumerate(tracks_events):
        chunks += _track(events, name,
                         tempo=bpm if i == 0 else None,
                         timesig=timesig if i == 0 else None)
    with open(path, "wb") as f:
        f.write(header + chunks)


# ---- reconstruct parts --------------------------------------------------------

def build_track(spec):
    root, mode, meter = spec["root"], spec["mode"], spec["meter"]
    tpb = SR_TPQ  # one beat = one quarter note
    chords, bass, lead, arp = [], [], [], []

    def phrase(prog, hook, bar_off):
        n_slots = 8 // spec["chord_bars"]
        for s in range(n_slots):
            cd = prog[s % 4]
            start_bar = bar_off + s * spec["chord_bars"]
            t = int(start_bar * meter * tpb)
            dur = int(spec["chord_bars"] * meter * tpb)
            for k in (0, 2, 4):  # triad, held
                chords.append((t, deg(root, mode, cd + k, 4), dur, 64, 0))
            bass.append((t, deg(root, mode, cd, spec["bass_oct"]), dur, 80, 1))
            if spec["arp"]:
                tones = [0, 4, 7, 9]
                for b in range(spec["chord_bars"]):
                    for k in range(2 * meter):  # eighth notes
                        at = int((start_bar + b) * meter * tpb + k * tpb / 2)
                        d = cd + tones[k % 4]
                        arp.append((at, deg(root, mode, d, 5), int(tpb * 0.45), 66, 3))
        for (bar, beat, dur_b, degree) in hook:
            t = int((bar_off + bar) * meter * tpb + beat * tpb)
            lead.append((t, deg(root, mode, degree, 5), int(dur_b * tpb * 0.98), 96, 2))

    phrase(spec["prog_a"], spec["hook"], 0)
    if spec["hook_b"]:
        phrase(spec["prog_b"], spec["hook_b"], 8)

    tracks = [("Chords", chords), ("Bass", bass), ("Melody", lead)]
    if spec["arp"]:
        tracks.append(("Arp", arp))
    return tracks


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    lines = ["# Favorites — GarageBand starter kits\n",
             "Each `.mid` opens as separate tracks (Chords / Bass / Melody / Arp). "
             "Set your GarageBand project to the BPM and time signature below, then "
             "build. Chords are spelled for the **A** section (the main phrase) and "
             "**B** (the contrasting phrase, bars 9–16 in the file).\n"]
    for spec in FAVORITES:
        tracks = build_track(spec)
        ts = (spec["meter"], 2)  # x/4
        path = os.path.join(OUT_DIR, f"{spec['n']:02d} {spec['title']}.mid")
        write_midi(path, tracks, spec["bpm"], ts)

        key = f"{PCNAME[spec['root']]} {MODEWORD[spec['mode']]}"
        n_slots = 8 // spec["chord_bars"]
        chA = [chord_name(spec["root"], spec["mode"], spec["prog_a"][s % 4])
               for s in range(4 if spec["chord_bars"] == 2 else 4)]
        chB = [chord_name(spec["root"], spec["mode"], spec["prog_b"][s % 4])
               for s in range(4)]
        each = "2 bars each" if spec["chord_bars"] == 2 else "1 bar each, looped twice"
        extra = f", {spec['kit']} drums" if spec.get("kit") else \
                (f", {spec['strings']} strings" if spec.get("strings") else ", piano/synth only")
        lines.append(f"## {spec['n']:02d} · {spec['title']}  ({spec['album']})")
        lines.append(f"- **{spec['bpm']} BPM · {spec['meter']}/4 · {key}**{extra}")
        lines.append(f"- **A progression** ({each}): {' – '.join(chA)}")
        if spec["hook_b"]:
            lines.append(f"- **B progression**: {' – '.join(chB)}")
        parts = "Chords, Bass, Melody" + (", Arp" if spec["arp"] else "")
        lines.append(f"- Tracks in the file: {parts}\n")
        print(f"wrote {os.path.basename(path)}")

    with open(os.path.join(OUT_DIR, "README.md"), "w") as f:
        f.write("\n".join(lines))
    print(f"\nWrote {len(FAVORITES)} MIDI files + README to {os.path.normpath(OUT_DIR)}")


if __name__ == "__main__":
    main()
