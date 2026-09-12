"""Modern darkwave / post-punk in the vein of French Police's "Hidalgo" --
real-band version: sampled pick bass through a real bass preamp, clean
electric guitar through a real amp capture, and actual LinnDrum LM-2
one-shots for the machine beat.

Same musical material as generate_modern_darkwave.py (A minor, 118 BPM,
driving eighth-note bass, plodding deterministic machine beat, arpeggio +
lead-hook guitar). Guitar, bass, and pad notes are MIDI events played
through GeneralUser GS via FluidSynth, one bus per instrument so effects
apply separately: the guitars get the signature rig -- chorus pedal into a
Neural Amp Modeler capture of a Vox AC15 Top Boost (full mic'd rig) into
reverb -- the pad gets a slow chorus and a long wash, and the bass is
split into a dry path and a NAM Tech21 dUg bass-preamp path mixed in
parallel, so the grit rides on top of the clean fundamental. The drums
skip synthesis entirely: they're the actual sampled hits of a LinnDrum
LM-2, placed directly on the grid. Still bit-identical every bar --
quantized, fixed gains, no fills -- because the drum machine plodding
along unmoved is the genre.

Two things sell the band-in-a-room illusion: the human parts (bass and
both guitars) get seeded timing/velocity/duration jitter -- hands drift,
the machine doesn't -- and every bus feeds one shared convolution reverb
loaded with a real measured room IR, at per-instrument send levels, so
the players all sound like they're in the same physical space.
"""

import os
import ctypes.util

# Python 3.9's find_library doesn't search Homebrew's /opt/homebrew/lib,
# where libfluidsynth lives -- point pyfluidsynth at it explicitly.
_orig_find_library = ctypes.util.find_library
def _find_library(name):
    found = _orig_find_library(name)
    if not found and name == "fluidsynth":
        path = "/opt/homebrew/lib/libfluidsynth.dylib"
        if os.path.exists(path):
            return path
    return found
ctypes.util.find_library = _find_library

import numpy as np
import fluidsynth
from pedalboard import (Pedalboard, Chorus, Delay, Reverb, Compressor, Gain,
                        HighpassFilter, Mix, Chain, Convolution)
from scipy.io import wavfile

from music_engine import load_nam, render_external_instrument

SR = 44100
BPM = 118
BEAT = 60.0 / BPM
BAR = BEAT * 4
SEED = 7

# Humanization: the hands drift, the machine doesn't. Applied to bass and
# guitar only -- drums and pad stay bit-exact on the grid. Seeded so every
# render of the same script is identical.
rng = np.random.default_rng(SEED)


def human(t, vel, t_sd=0.005, v_sd=6):
    """Jitter a note's start time (seconds) and velocity, clamped to sane
    ranges so an outlier never lands a note early into the previous bar."""
    t = max(t + float(np.clip(rng.normal(0, t_sd), -2.5 * t_sd, 2.5 * t_sd)), 0.0)
    vel = int(np.clip(vel + rng.normal(0, v_sd), 1, 127))
    return t, vel

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SF_PATH = os.path.join(SCRIPT_DIR, "..", "Soundfonts", "GeneralUser-GS.sf2")
OUT_PATH = os.path.join(SCRIPT_DIR, "..", "Tracks", "modern_darkwave_band.wav")

# Neural Amp Modeler VST3 + amp captures. The AC15 capture is a full rig
# (amp + mic'd cab); the Twin capture is head-only and would need a cab IR.
NAM_VST3 = os.path.expanduser("~/Library/Audio/Plug-Ins/VST3/NeuralAmpModeler.vst3")
AMP_AC15 = os.path.join(SCRIPT_DIR, "..", "Amps", "Vox_AC15_TopBoost.nam")
AMP_TWIN = os.path.join(SCRIPT_DIR, "..", "Amps", "Fender_TwinVerb_Clean.nam")
AMP_DUG = os.path.join(SCRIPT_DIR, "..", "Amps", "Tech21_dUg_BassPreamp.nam")
GUITAR_AMP = AMP_AC15

# Shared room: a real measured impulse response (Voxengo free IR pack).
# Every bus feeds this one space at its own send level -- the band-in-a-
# room glue that per-bus algorithmic reverbs can't fake.
ROOM_IR = os.path.join(SCRIPT_DIR, "..", "IRs", "Nice Drum Room.wav")

# MFB-512 one-shots -- stark German analog box. Alternates live alongside
# in Samples/ (LM-2, Drumtraks, TR-808, CR-8000, RZ-1, MR10, SK-1); see
# audition_drum_kits.py to compare voicings.
KIT_DIR = os.path.join(SCRIPT_DIR, "..", "Samples", "MFB-512")
KIT = {
    "kick": ("kick.wav", 0.95),
    "snare": ("snare.wav", 0.8),
    "hhc": ("hhc.wav", 0.4),
    "hho": ("hho.wav", 0.45),
}


CH_ARP = 0
CH_LEAD = 1
CH_BASS = 2
CH_PAD = 3
CH_MUTE = 4
CH_FRET = 5

CLEAN_GUITAR = 27   # GM: Electric Guitar (Clean)
MUTED_GUITAR = 28   # GM: Electric Guitar (Muted) -- palm-mute articulation
FRET_NOISE = 120    # GM: Guitar Fret Noise -- finger-slide squeaks
BASS_PICK = 34      # GM: Electric Bass (Pick)
WARM_PAD = 89       # GM: Pad 2 (Warm)

# A natural minor, i - VI - VII - v. Same voicings as the synth version:
# bass root, mid-neck guitar chord tones, root+fifth pad dyad.
CHORDS = [
    {"name": "Am", "bass": 45, "gtr": [57, 60, 64, 69], "pad": [57, 64]},
    {"name": "F",  "bass": 41, "gtr": [53, 57, 60, 65], "pad": [53, 60]},
    {"name": "G",  "bass": 43, "gtr": [55, 59, 62, 67], "pad": [55, 62]},
    {"name": "Em", "bass": 40, "gtr": [52, 55, 59, 64], "pad": [52, 59]},
]

# Verse bass: relentless staccato eighths on the root, fifth pickup into
# the next bar. Chorus bass: bouncing through octave and b7 -- the hook.
BASS_DRIVE = [(i * 0.5, 0.5, 0) for i in range(7)] + [(3.5, 0.5, 7)]
BASS_HOOK = [
    (0.0, 0.5, 0), (0.5, 0.5, 0), (1.0, 0.5, 12), (1.5, 0.5, 0),
    (2.0, 0.5, 10), (2.5, 0.5, 0), (3.0, 0.5, 7), (3.5, 0.5, 5),
]

# Guitar arpeggio: eighth-note picking across the chord shape.
ARP_PATTERN = [0, 2, 1, 2, 3, 2, 1, 2]

# Lead guitar hook, one 4-bar phrase over Am-F-G-Em: (bar, beat, dur_beats, midi).
LEAD_PHRASE = [
    (0, 0.0, 1.5, 76), (0, 1.5, 0.5, 72), (0, 2.0, 1.0, 74), (0, 3.0, 1.0, 71),
    (1, 0.0, 2.0, 72), (1, 2.0, 1.5, 69), (1, 3.5, 0.5, 72),
    (2, 0.0, 1.0, 74), (2, 1.0, 1.0, 71), (2, 2.0, 2.0, 74),
    (3, 0.0, 3.0, 71), (3, 3.0, 1.0, 67),
]

# Per-bus MIDI event lists: (sample_pos, 'on'/'off', channel, note, velocity).
EVENTS = {"gtr": [], "bass": [], "drums": [], "pad": []}

# Ample Bass P Lite II renders in a separate x86_64 (Rosetta) process --
# the AU is an Intel-only build. Falls back to the FluidSynth bass if the
# helper fails. Bass notes are mirrored here in seconds-based form.
X86_PYTHON = os.path.expanduser("~/.venvs/x86-audio/bin/python")
AMPLE_HELPER = os.path.join(SCRIPT_DIR, "render_ample_bass.py")
AMPLE_NOTES = []


def add_note(bus, t, dur, ch, note, vel):
    EVENTS[bus].append((int(t * SR), "on", ch, note, vel))
    EVENTS[bus].append((int((t + dur) * SR), "off", ch, note, 0))


# ---- arrangement ------------------------------------------------------------

def render_bar(bar_t, chord, *, bass=None, drums=False, arp=False, pad=False):
    step = BEAT / 2

    if bass is not None:
        pattern = BASS_DRIVE if bass == "drive" else BASS_HOOK
        for beat_off, dur_b, offset in pattern:
            vel = 105 if beat_off in (0.0, 2.0) else 96  # accent the downbeats
            t, vel = human(bar_t + beat_off * BEAT, vel, t_sd=0.004)
            dur = dur_b * BEAT * 0.82 * rng.uniform(0.92, 1.08)
            add_note("bass", t, dur, CH_BASS, chord["bass"] + offset, vel)
            AMPLE_NOTES.append({"t": t, "dur": dur, "note": chord["bass"] + offset, "vel": vel})

    if drums:
        for beat_i in (0, 2):
            EVENTS["drums"].append((bar_t + beat_i * BEAT, "kick"))
        for beat_i in (1, 3):
            EVENTS["drums"].append((bar_t + beat_i * BEAT, "snare"))
        for k8 in range(8):
            EVENTS["drums"].append((bar_t + k8 * step, "hho" if k8 == 7 else "hhc"))

    if arp:
        # Verses palm-mute the same pattern ("muted"); choruses ring open.
        muted = arp == "muted"
        ch = CH_MUTE if muted else CH_ARP
        base_dur = step * (0.55 if muted else 1.6)
        for k8, tone_i in enumerate(ARP_PATTERN):
            t, vel = human(bar_t + k8 * step, 86 if muted else 80, t_sd=0.006, v_sd=8)
            add_note("gtr", t, base_dur * rng.uniform(0.9, 1.1), ch,
                     chord["gtr"][tone_i], vel)
        # Occasional fret squeak as the hand shifts into the next bar.
        if rng.random() < 0.28:
            t, vel = human(bar_t + 3.45 * BEAT, 46, t_sd=0.03, v_sd=8)
            add_note("gtr", t, 0.3, CH_FRET, 60, vel)

    if pad:
        for j, note in enumerate(chord["pad"]):
            add_note("pad", bar_t, BAR * 1.05, CH_PAD, note, 58 if j == 0 else 48)


def render_lead(start_bar, n_bars):
    for phrase_start in range(0, n_bars, 4):
        for bar_off, beat, dur_b, note in LEAD_PHRASE:
            if phrase_start + bar_off >= n_bars:
                continue
            t0 = (start_bar + phrase_start + bar_off) * BAR + beat * BEAT
            t0, vel = human(t0, 98, t_sd=0.012, v_sd=8)
            add_note("gtr", t0, dur_b * BEAT * 0.95 * rng.uniform(0.9, 1.1),
                     CH_LEAD, note, vel)


# ---- FluidSynth bus rendering -----------------------------------------------

def render_bus(events, total_secs, setup):
    """One FluidSynth pass over a single bus's sorted event list. `setup`
    configures programs and pan CCs on a fresh synth."""
    n_samples = int(total_secs * SR)
    fs = fluidsynth.Synth(samplerate=float(SR))
    fs.setting("synth.gain", 0.6)
    sfid = fs.sfload(SF_PATH)
    setup(fs, sfid)

    audio = np.zeros(n_samples * 2, dtype=np.float32)
    pos = 0
    for ev in sorted(events, key=lambda e: e[0]):
        sp = min(ev[0], n_samples)
        if sp > pos:
            raw = fs.get_samples(sp - pos)
            end = min(pos * 2 + len(raw), len(audio))
            audio[pos * 2:end] += raw[:end - pos * 2].astype(np.float32) / 32768.0
            pos = sp
        if ev[1] == "on":
            fs.noteon(ev[2], ev[3], ev[4])
        else:
            fs.noteoff(ev[2], ev[3])
    if pos < n_samples:
        raw = fs.get_samples(n_samples - pos)
        end = min(pos * 2 + len(raw), len(audio))
        audio[pos * 2:end] += raw[:end - pos * 2].astype(np.float32) / 32768.0
    fs.delete()
    return np.stack([audio[0::2], audio[1::2]])


def render_ample_bass(total_secs):
    """Render the bass stem through Ample Bass P Lite II in a Rosetta
    subprocess. Returns a (2, n) float array, or None to fall back."""
    return render_external_instrument(
        AMPLE_NOTES,
        total_secs,
        python_path=X86_PYTHON,
        helper_path=AMPLE_HELPER,
        sample_rate=SR,
        architecture="x86_64",
        label="Ample Bass",
    )


def setup_gtr(fs, sfid):
    fs.program_select(CH_ARP, sfid, 0, CLEAN_GUITAR)
    fs.program_select(CH_LEAD, sfid, 0, CLEAN_GUITAR)
    fs.program_select(CH_MUTE, sfid, 0, MUTED_GUITAR)
    fs.program_select(CH_FRET, sfid, 0, FRET_NOISE)
    fs.cc(CH_ARP, 10, 44)    # arp a little left
    fs.cc(CH_LEAD, 10, 84)   # lead a little right
    fs.cc(CH_MUTE, 10, 44)   # muted verses sit where the arp sits
    fs.cc(CH_FRET, 10, 50)


def setup_bass(fs, sfid):
    fs.program_select(CH_BASS, sfid, 0, BASS_PICK)


def setup_pad(fs, sfid):
    fs.program_select(CH_PAD, sfid, 0, WARM_PAD)


def render_drum_bus(events, total_secs):
    """LinnDrum one-shots placed straight onto the grid -- no synthesis.
    Each sample is peak-normalized once, scaled by its kit gain, and every
    hit is the identical waveform: a real drum machine."""
    n_samples = int(total_secs * SR)
    bus = np.zeros((2, n_samples), dtype=np.float32)
    hits = {}
    for name, (fname, gain) in KIT.items():
        _, data = wavfile.read(os.path.join(KIT_DIR, fname))
        data = data.astype(np.float32) / 32768.0
        if data.ndim == 2:
            data = data.mean(axis=1)
        hits[name] = data / max(np.abs(data).max(), 1e-9) * gain
    for t, name in events:
        s = hits[name]
        start = int(t * SR)
        end = min(start + len(s), n_samples)
        if end > start:
            bus[:, start:end] += s[:end - start]
    return bus


# ---- main -------------------------------------------------------------------

def main():
    movements = [
        # The bass hook opens alone, dry and driving.
        dict(n_bars=4, bass="hook"),
        # The machine locks in.
        dict(n_bars=4, bass="drive", drums=True),
        # Verse 1: palm-muted arpeggio guitar enters, chugging.
        dict(n_bars=16, bass="drive", drums=True, arp="muted"),
        # Chorus 1: arp rings open, lead hook, warm pad, bass bounces.
        dict(n_bars=16, bass="hook", drums=True, arp="open", pad=True, lead=True),
        # Verse 2: back to the muted drive, lead drops out.
        dict(n_bars=8, bass="drive", drums=True, arp="muted"),
        # Chorus 2.
        dict(n_bars=16, bass="hook", drums=True, arp="open", pad=True, lead=True),
        # Breakdown: drums and bass cut, the open guitar hangs in the reverb.
        dict(n_bars=8, arp="open", pad=True),
        # Final chorus, full arrangement.
        dict(n_bars=16, bass="hook", drums=True, arp="open", pad=True, lead=True),
        # Outro: back to bass and machine, the way it started.
        dict(n_bars=8, bass="drive", drums=True),
    ]

    total_bars = sum(m["n_bars"] for m in movements)
    total_secs = total_bars * BAR + 6.0

    bar_cursor = 0
    for m in movements:
        for bar_i in range(m["n_bars"]):
            render_bar((bar_cursor + bar_i) * BAR, CHORDS[bar_i % 4],
                       bass=m.get("bass"), drums=m.get("drums", False),
                       arp=m.get("arp", False), pad=m.get("pad", False))
        if m.get("lead"):
            render_lead(bar_cursor, m["n_bars"])
        bar_cursor += m["n_bars"]

    print(f"Rendering {total_bars} bars ({total_secs:.1f}s) in 3 bus passes + drum samples ...")
    gtr = render_bus(EVENTS["gtr"], total_secs, setup_gtr)
    pad = render_bus(EVENTS["pad"], total_secs, setup_pad)
    drums = render_drum_bus(EVENTS["drums"], total_secs)
    bass = render_ample_bass(total_secs)
    if bass is None:
        bass = render_bus(EVENTS["bass"], total_secs, setup_bass)

    print("Applying effects ...")
    # The signature rig, in pedal order: chorus pedal into a real amp
    # capture (NAM), reverb after the amp.
    amp = load_nam(GUITAR_AMP)
    amp.input_db = -3.0   # keep the AC15 just below break-up: clean jangle
    # Dotted-eighth delay after the amp -- the post-punk staple.
    dotted_8th = BEAT * 0.75
    gtr_fx = Pedalboard([
        Chorus(rate_hz=0.8, depth=0.2, centre_delay_ms=12.0, mix=0.5),
        amp,
        Delay(delay_seconds=dotted_8th, feedback=0.28, mix=0.16),
        Reverb(room_size=0.85, damping=0.45, wet_level=0.24, dry_level=0.76, width=1.0),
    ])
    pad_fx = Pedalboard([
        Chorus(rate_hz=0.4, depth=0.3, centre_delay_ms=15.0, mix=0.35),
        Reverb(room_size=0.9, damping=0.5, wet_level=0.4, dry_level=0.6, width=1.0),
    ])
    # Bass split in parallel: clean fundamental + the dUg preamp's grit on
    # top, then compressed together so the eighth-note drive stays tight.
    dug = load_nam(AMP_DUG)
    dug.input_db = -6.0
    bass_fx = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=35),
        Mix([
            Chain([Gain(gain_db=0.0)]),                 # dry path
            Chain([dug, Gain(gain_db=-8.0)]),           # grit path, tucked under
        ]),
        Compressor(threshold_db=-18, ratio=4, attack_ms=4, release_ms=90),
        Gain(gain_db=0.0),
    ])
    # No algorithmic reverb on the drums -- the shared room IR handles space.
    drum_fx = Pedalboard([
        Compressor(threshold_db=-15, ratio=3, attack_ms=2, release_ms=60),
    ])

    gtr = gtr_fx(gtr, SR)
    pad = pad_fx(pad, SR)
    bass = bass_fx(bass, SR)
    drums = drum_fx(drums, SR)

    bass *= 1.0
    drums *= 0.95
    gtr *= 0.85
    pad *= 0.5
    dry = bass + drums + gtr + pad

    # Shared room send: everyone plays into the same real space. Drums
    # loudest (a kit fills a room), bass barely (low end stays tight).
    room_send = (0.7 * drums + 0.55 * gtr + 0.45 * pad + 0.25 * bass).astype(np.float32)
    room = Convolution(ROOM_IR, mix=1.0)(room_send, SR)
    rms = lambda a: np.sqrt((a ** 2).mean())
    room *= 0.22 * rms(dry) / max(rms(room), 1e-9)

    master = dry + room

    n_samples = master.shape[1]
    fade_in = int(0.05 * SR)
    fade_out = int(5.0 * SR)
    env = np.ones(n_samples, dtype=np.float32)
    env[:fade_in] = np.linspace(0, 1, fade_in)
    env[-fade_out:] = np.linspace(1, 0, fade_out)
    master *= env

    peak = max(np.abs(master).max(), 1e-9)
    master = master / peak * 0.9

    wavfile.write(OUT_PATH, SR, (master.T * 32767).astype(np.int16))
    print(f"Wrote {os.path.normpath(OUT_PATH)}: {total_secs:.1f}s, {total_bars} bars at {BPM} BPM")


if __name__ == "__main__":
    main()
