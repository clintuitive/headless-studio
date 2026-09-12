"""THE WEATHER BETWEEN STATIONS — twelve original post-punk instrumentals.

GarageBand Picked Rock Bass and Vintage Strat, MFB-512 drums, a Fender Twin
NAM capture, chorus/reverb guitar, and an always-present analog synth wash.
Each track has its own tempo, progression, form, rhythm language, and hook.
"""

import gc
import os
import re

import numpy as np
from pedalboard import (
    Chorus, Compressor, Delay, Gain, HighpassFilter, LowpassFilter,
    Pedalboard, Reverb,
)
from scipy.io import wavfile
from scipy.signal import sawtooth

from music_engine import (
    EventTimeline, ExsSampler, Humanizer, apply_fades, load_nam,
    normalize_peak, stereo,
)

SR = 44_100
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SAMPLES = os.path.join(ROOT, "Samples")
KIT_DIR = os.path.join(SAMPLES, "MFB-512")
TWIN = os.path.join(ROOT, "Amps", "Fender_TwinVerb_Clean.nam")
OUT_DIR = os.path.join(ROOT, "Tracks", "The Weather Between Stations")

MODES = {
    "aeolian": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
}

# Durations range from about 3:18 to 5:40. Progressions intentionally range
# from five to eight bars so the record does not feel built from four-chord
# loops despite its consistent instrumental palette.
TRACKS = [
    dict(title="Ashen Receiver", bpm=100, bars=80, tonic=40, mode="aeolian",
         prog=[0, 5, 2, 6, 3, 5], prog_b=[3, 6, 5, 4, 0, 6],
         bass="melodic", drums="drive", guitar="chime", lead="guitar",
         motif=[4, 6, 5, 2, 4, 1], chorus=.72, depth=.15, pad=.42, intro=8),
    dict(title="Rooms Without Clocks", bpm=78, bars=72, tonic=38, mode="aeolian",
         prog=[0, 5, 2, 6, 3, 5, 4, 4], prog_b=[3, 5, 0, 6, 5, 3, 4, 4],
         bass="sparse", drums="half", guitar="aligned", lead="synth",
         motif=[4, 3, 2, 4, 6, 4, 3, 2], chorus=.52, depth=.18, pad=.55, intro=8),
    dict(title="Red Exit Sign", bpm=116, bars=96, tonic=37, mode="dorian",
         prog=[0, 3, 6, 4, 0], prog_b=[5, 3, 0, 4, 6],
         bass="drive", drums="urgent", guitar="eighths", lead="guitar",
         motif=[7, 6, 4, 5, 2], chorus=.86, depth=.13, pad=.31, intro=8),
    dict(title="The Glass Stairwell", bpm=70, bars=72, tonic=43, mode="phrygian",
         prog=[0, 1, 5, 3, 6, 1, 4], prog_b=[3, 1, 0, 5, 6, 4, 1],
         bass="sparse", drums="half", guitar="sparse", lead="guitar",
         motif=[4, 3, 1, 2, 6, 5, 1], chorus=.44, depth=.20, pad=.62, intro=8),
    dict(title="Unsent Letters", bpm=92, bars=88, tonic=45, mode="aeolian",
         prog=[0, 6, 5, 3, 2, 4], prog_b=[5, 3, 6, 0, 4, 2],
         bass="pulse", drums="plod", guitar="chime", lead="synth",
         motif=[4, 5, 7, 6, 4, 2], chorus=.64, depth=.16, pad=.46, intro=8),
    dict(title="Low Clouds Over Water", bpm=62, bars=72, tonic=36, mode="dorian",
         prog=[0, 3, 5, 2, 6, 4], prog_b=[5, 3, 0, 2, 4, 6],
         bass="sparse", drums="ambient", guitar="swells", lead="synth",
         motif=[2, 4, 5, 3, 7, 4], chorus=.30, depth=.23, pad=.72, intro=16),
    dict(title="Last Train Signal", bpm=108, bars=104, tonic=42, mode="aeolian",
         prog=[0, 5, 6, 4, 3], prog_b=[3, 6, 0, 5, 4],
         bass="drive", drums="urgent", guitar="eighths", lead="guitar",
         motif=[4, 7, 6, 5, 2], chorus=.91, depth=.12, pad=.30, intro=8),
    dict(title="A Shape in the Hall", bpm=68, bars=80, tonic=41, mode="phrygian",
         prog=[0, 1, 3, 6, 5, 1, 4, 0], prog_b=[5, 6, 1, 0, 3, 1, 4, 4],
         bass="pulse", drums="half", guitar="sparse", lead="none",
         motif=[4, 3, 1, 5, 6, 3, 2, 1], chorus=.38, depth=.21, pad=.68, intro=12),
    dict(title="Fluorescent Weather", bpm=96, bars=96, tonic=39, mode="dorian",
         prog=[0, 3, 5, 4, 6, 3], prog_b=[5, 6, 0, 4, 3, 5],
         bass="melodic", drums="drive", guitar="aligned", lead="synth",
         motif=[7, 5, 4, 6, 2, 4], chorus=.74, depth=.14, pad=.39, intro=8),
    dict(title="Sleep Mode", bpm=58, bars=80, tonic=40, mode="aeolian",
         prog=[0, 5, 3, 6, 2, 4], prog_b=[3, 5, 0, 6, 4, 2],
         bass="sparse", drums="ambient", guitar="swells", lead="none",
         motif=[4, 2, 5, 3, 1, 4], chorus=.24, depth=.25, pad=.78, intro=16),
    dict(title="Blacktop Static", bpm=112, bars=112, tonic=35, mode="dorian",
         prog=[0, 6, 3, 4, 5], prog_b=[5, 3, 0, 6, 4],
         bass="drive", drums="urgent", guitar="eighths", lead="guitar",
         motif=[7, 6, 5, 4, 2], chorus=.96, depth=.11, pad=.28, intro=8),
    dict(title="Before the Streetlights Die", bpm=72, bars=88, tonic=38, mode="aeolian",
         prog=[0, 5, 2, 6, 3, 5, 4, 4], prog_b=[3, 6, 5, 0, 2, 4, 5, 4],
         bass="sparse", drums="plod", guitar="chime", lead="synth",
         motif=[4, 6, 5, 2, 7, 5, 4, 2], chorus=.48, depth=.19, pad=.66, intro=12),
]


def scale_pitch(tonic, mode, degree):
    scale = MODES[mode]
    octave, index = divmod(degree, 7)
    return tonic + scale[index] + octave * 12


def chord_for(spec, degree):
    root = scale_pitch(spec["tonic"], spec["mode"], degree)
    tones = [scale_pitch(spec["tonic"], spec["mode"], degree + step)
             for step in (0, 2, 4)]
    # Bass around E2; guitar/pad in a compact middle register.
    guitar = []
    for pitch in [tones[0] + 12, tones[1] + 12, tones[2] + 12, tones[0] + 24]:
        while pitch < 50:
            pitch += 12
        while pitch > 69:
            pitch -= 12
        guitar.append(pitch)
    pad = []
    for pitch in [tones[0] + 12, tones[1] + 12, tones[2] + 12]:
        while pitch < 45:
            pitch += 12
        while pitch > 65:
            pitch -= 12
        pad.append(pitch)
    return root, guitar, pad


class TrackRenderer:
    def __init__(self, spec, index):
        self.s = spec
        self.index = index
        self.bpm = spec["bpm"]
        self.beat = 60 / self.bpm
        self.bar = self.beat * 4
        self.rng = np.random.default_rng(500 + index)
        self.human = Humanizer.seeded(500 + index, timing_sd=.0045, velocity_sd=4)
        self.events = EventTimeline(
            SR, ("bass", "guitar", "lead_guitar", "lead_synth", "pad", "drums")
        )

    def note(self, bus, time, duration, pitch, velocity, loose=False):
        if loose:
            time, velocity = self.human(time, velocity)
            duration *= float(self.rng.uniform(.97, 1.03))
        self.events.note(bus, time, duration, pitch, velocity)

    def bass_bar(self, bar, root, active=True):
        if not active:
            return
        styles = {
            "sparse": [(0, 1.45, 0), (2, .78, 7), (3.25, .55, 0)],
            "pulse": [(0, .72, 0), (1, .55, 0), (2, .72, 7), (3, .58, 0)],
            "drive": [(i * .5, .39, 12 if i == 2 else 7 if i in (5, 7) else 0)
                      for i in range(8)],
            "melodic": [(0, .55, 0), (.75, .45, 7), (1.4, .55, 12),
                        (2.1, .5, 10), (2.8, .45, 7), (3.4, .45, 0)],
        }
        for beat, duration, interval in styles[self.s["bass"]]:
            self.note("bass", bar * self.bar + beat * self.beat,
                      duration * self.beat, root + interval,
                      100 if beat == 0 else 89, True)

    def guitar_bar(self, bar, chord, density=1.0):
        style = self.s["guitar"]
        if style == "swells":
            for beat, tone in ((0, 0), (2, 2)):
                self.note("guitar", bar * self.bar + beat * self.beat,
                          2.2 * self.beat, chord[tone], 61, True)
            return
        patterns = {
            "sparse": ([0, 2, 3.25], [0, 1, 3]),
            "aligned": ([0, 1, 2, 3.25], [0, 2, 1, 3]),
            "chime": ([0, .75, 1.5, 2.5, 3.25], [0, 2, 1, 3, 2]),
            "eighths": ([i * .5 for i in range(8)], [0, 2, 1, 2, 3, 2, 1, 2]),
        }
        beats, order = patterns[style]
        if density < .75:
            beats, order = beats[::2], order[::2]
        for beat, tone in zip(beats, order):
            self.note("guitar", bar * self.bar + beat * self.beat,
                      self.beat * (.95 if style == "sparse" else .48),
                      chord[tone], 68 if density < .75 else 73, True)

    def lead_bar(self, bar, chord_degree, motif_degree, bus):
        lead_root = scale_pitch(self.s["tonic"] + 24, self.s["mode"], motif_degree)
        chord_root = scale_pitch(self.s["tonic"] + 24, self.s["mode"], chord_degree)
        # Pull the motif toward the current chord if it drifts too far.
        while lead_root - chord_root > 9:
            lead_root -= 12
        while chord_root - lead_root > 7:
            lead_root += 12
        if bus == "lead_guitar":
            rhythm = [(0, 1.15, lead_root), (2, .75, lead_root + 2),
                      (3.25, .55, chord_root + 7)]
            velocity = 76
        else:
            rhythm = [(0, 1.6, lead_root), (2, 1.35, chord_root + 7)]
            velocity = 65
        for beat, duration, pitch in rhythm:
            self.note(bus, bar * self.bar + beat * self.beat,
                      duration * self.beat, pitch, velocity, bus == "lead_guitar")

    def pad_bar(self, bar, pad):
        for i, pitch in enumerate(pad):
            self.note("pad", bar * self.bar, self.bar * 1.12,
                      pitch, 47 - i * 3)

    def drum_hit(self, time, pitch, velocity):
        self.events.note("drums", time, .04, pitch, velocity)

    def drums_bar(self, bar, restrained=False, fill=False):
        style = self.s["drums"]
        t = bar * self.bar
        if style == "ambient":
            self.drum_hit(t, 36, 91)
            self.drum_hit(t + 2 * self.beat, 38, 79)
            for step in (0, 2, 4, 6):
                self.drum_hit(t + step * self.beat / 2, 42, 39)
        elif style == "half":
            for beat, pitch, velocity in ((0, 36, 112), (1.5, 36, 87),
                                           (2, 38, 109), (3.25, 36, 95)):
                self.drum_hit(t + beat * self.beat, pitch, velocity)
            for step in range(0, 8, 2 if restrained else 1):
                self.drum_hit(t + step * self.beat / 2, 46 if step == 7 else 42,
                              58 if step % 2 == 0 else 44)
        else:
            kicks = (0, 2) if style in ("plod", "drive") else (0, 1.5, 2.5)
            snares = (1, 3)
            for beat in kicks:
                self.drum_hit(t + beat * self.beat, 36, 108)
            for beat in snares:
                self.drum_hit(t + beat * self.beat, 38, 104)
            for step in range(0, 8, 2 if restrained else 1):
                self.drum_hit(t + step * self.beat / 2, 46 if step == 7 else 42,
                              61 if step % 2 == 0 else 47)
        if fill:
            for step, velocity in zip((12, 13, 14, 15), (67, 77, 91, 108)):
                self.drum_hit(t + step * self.beat / 4, 38, velocity)

    def arrange(self):
        bars = self.s["bars"]
        intro = self.s["intro"]
        outro = 8
        middle = bars - intro - outro
        a = min(16, middle // 3)
        b = min(16, middle // 3)
        breath = 8
        return_bars = middle - a - b - breath
        sections = [
            (intro, False, False, False, "a"),
            (a, True, True, False, "a"),
            (b, True, True, True, "b"),
            (breath, False, True, False, "b"),
            (return_bars, True, True, True, "a"),
            (outro, self.s["drums"] != "ambient", False, False, "a"),
        ]
        bar = 0
        for section_index, (length, drums, guitar, lead, progression_name) in enumerate(sections):
            progression = self.s["prog_b"] if progression_name == "b" else self.s["prog"]
            for local in range(length):
                degree = progression[local % len(progression)]
                root, chord, pad = chord_for(self.s, degree)
                self.pad_bar(bar, pad)
                # Intro is pad only on slow/ambient pieces; driving pieces
                # introduce bass halfway through the intro.
                bass_active = section_index != 0 or (
                    self.s["drums"] in ("drive", "urgent") and local >= length // 2)
                self.bass_bar(bar, root, bass_active)
                if drums:
                    self.drums_bar(bar, restrained=section_index in (1, 5),
                                   fill=local == length - 1 and section_index in (1, 2, 4))
                if guitar:
                    self.guitar_bar(bar, chord, .65 if section_index == 3 else 1.0)
                if lead and self.s["lead"] != "none" and local % 2 == 1:
                    motif = self.s["motif"][local % len(self.s["motif"])]
                    bus = "lead_guitar" if self.s["lead"] == "guitar" else "lead_synth"
                    self.lead_bar(bar, degree, motif, bus)
                bar += 1
        # One-bar tonic resolution after the written form.
        root, _, pad = chord_for(self.s, 0)
        self.pad_bar(bar, pad)
        self.note("bass", bar * self.bar, self.bar * .8, root, 91, True)
        return bar + 1

    def render_sampler(self, directory, bus, total_seconds, groups, **kwargs):
        sampler = ExsSampler(
            os.path.join(SAMPLES, directory), sample_rate=SR,
            rng=np.random.default_rng(900 + self.index), groups=groups, **kwargs
        )
        return sampler.render(self.events[bus], total_seconds)

    def render_drums(self, total_seconds):
        files = {
            36: ("kick.wav", .92), 38: ("snare.wav", .74),
            42: ("hhc.wav", .24), 46: ("hho.wav", .27),
        }
        n = int(total_seconds * SR)
        output = np.zeros((2, n), dtype=np.float32)
        cache = {}
        for pitch, (filename, gain) in files.items():
            _, audio = wavfile.read(os.path.join(KIT_DIR, filename))
            audio = audio.astype(np.float32) / 32768
            if audio.ndim == 2:
                audio = audio.mean(axis=1)
            cache[pitch] = audio / max(np.abs(audio).max(), 1e-9) * gain
        for position, kind, _, pitch, velocity in self.events["drums"]:
            if kind != "on":
                continue
            sample = cache[pitch] * (.55 + .45 * velocity / 127)
            end = min(position + len(sample), n)
            output[:, position:end] += sample[:end - position]
        return output

    def synth_bus(self, bus, total_seconds, pad=False):
        n = int(total_seconds * SR)
        output = np.zeros((2, n), dtype=np.float32)
        active, notes = {}, []
        for event in sorted(self.events[bus], key=lambda item: item[0]):
            position, kind, channel, pitch, velocity = event
            key = (channel, pitch)
            if kind == "on":
                active[key] = (position, velocity)
            elif kind == "off" and key in active:
                start, note_velocity = active.pop(key)
                notes.append((start, position - start, pitch, note_velocity))
        for note_index, (start, duration, pitch, velocity) in enumerate(notes):
            tail = 1.35 if pad else .55
            length = min(duration + int(tail * SR), n - start)
            if length <= 0:
                continue
            time = np.arange(length, dtype=np.float32) / SR
            frequency = 440 * 2 ** ((pitch - 69) / 12)
            if pad:
                phase = self.rng.uniform(0, 2 * np.pi)
                drift_l = 1 + .0013 * np.sin(2 * np.pi * .052 * time + phase)
                drift_r = 1 + .0013 * np.sin(2 * np.pi * .061 * time + phase + 1.4)
                ph_l = 2 * np.pi * np.cumsum(frequency * drift_l) / SR
                ph_r = 2 * np.pi * np.cumsum(frequency * drift_r) / SR
                left = (.46 * sawtooth(ph_l * .994) + .46 * sawtooth(ph_l * 1.006)
                        + .24 * np.sin(ph_l / 2))
                right = (.46 * sawtooth(ph_r * .992) + .46 * sawtooth(ph_r * 1.008)
                         + .24 * np.sin(ph_r / 2))
                attack, release, level = 1.0, 1.45, .062
            else:
                left = .68 * np.sin(2 * np.pi * frequency * time) + .32 * sawtooth(
                    2 * np.pi * frequency * .997 * time, width=.5)
                right = .68 * np.sin(2 * np.pi * frequency * time) + .32 * sawtooth(
                    2 * np.pi * frequency * 1.003 * time, width=.5)
                attack, release, level = .12, .48, .15
            a = min(int(attack * SR), length)
            r = min(int(release * SR), length)
            envelope = np.ones(length, dtype=np.float32)
            envelope[:a] = np.sin(np.linspace(0, np.pi / 2, a)) ** 2
            envelope[-r:] *= np.cos(np.linspace(0, np.pi / 2, r)) ** 2
            gain = level * (.58 + .42 * velocity / 127)
            end = start + length
            output[0, start:end] += left * envelope * gain
            output[1, start:end] += right * envelope * gain
        return np.tanh(output).astype(np.float32) if pad else output

    def render(self, number):
        total_bars = self.arrange()
        total_seconds = total_bars * self.bar + 6
        print(f"[{number:02d}/12] {self.s['title']} — {total_seconds / 60:.2f} min")

        bass = stereo(self.render_sampler(
            "PickedRockBass", "bass", total_seconds,
            ["Group #3", "Group #4", "Group #5", "Group #6", "Group #7"],
            release=.08,
        ))
        guitar = stereo(self.render_sampler(
            "VintageStrat", "guitar", total_seconds, ["Main"],
            pickup=.20, release=.18,
        ), -.18)
        lead_guitar = stereo(self.render_sampler(
            "VintageStrat", "lead_guitar", total_seconds, ["Main"],
            pickup=.20, release=.18,
        ), .23)
        drums = self.render_drums(total_seconds)
        pad = self.synth_bus("pad", total_seconds, pad=True)
        synth_lead = self.synth_bus("lead_synth", total_seconds)

        amp = load_nam(TWIN)
        amp.input_db = -9
        guitar = Pedalboard([
            HighpassFilter(cutoff_frequency_hz=110),
            LowpassFilter(cutoff_frequency_hz=6200),
            Chorus(rate_hz=self.s["chorus"], depth=self.s["depth"],
                   centre_delay_ms=13, mix=.45),
            amp,
            Delay(delay_seconds=self.beat * .75, feedback=.24, mix=.15),
            Reverb(room_size=.91, damping=.49, wet_level=.37, dry_level=.72, width=1),
        ])(guitar, SR)
        lead_amp = load_nam(TWIN)
        lead_amp.input_db = -8
        lead_guitar = Pedalboard([
            Chorus(rate_hz=self.s["chorus"] * 1.18, depth=self.s["depth"] * .9,
                   centre_delay_ms=11, mix=.40),
            lead_amp,
            Delay(delay_seconds=self.beat, feedback=.29, mix=.18),
            Reverb(room_size=.93, damping=.45, wet_level=.41, dry_level=.69, width=1),
        ])(lead_guitar, SR)
        pad = Pedalboard([
            HighpassFilter(cutoff_frequency_hz=120),
            LowpassFilter(cutoff_frequency_hz=2750),
            Chorus(rate_hz=.17, depth=.27, centre_delay_ms=19, mix=.41),
            Reverb(room_size=.97, damping=.46, wet_level=.57, dry_level=.54, width=1),
        ])(pad, SR)
        synth_lead = Pedalboard([
            HighpassFilter(cutoff_frequency_hz=230),
            LowpassFilter(cutoff_frequency_hz=4400),
            Chorus(rate_hz=.31, depth=.16, centre_delay_ms=14, mix=.34),
            Delay(delay_seconds=self.beat * .75, feedback=.23, mix=.15),
            Reverb(room_size=.91, damping=.50, wet_level=.39, dry_level=.68, width=1),
        ])(synth_lead, SR)
        bass = Pedalboard([
            HighpassFilter(cutoff_frequency_hz=32),
            LowpassFilter(cutoff_frequency_hz=5800),
            Compressor(threshold_db=-18, ratio=4, attack_ms=9, release_ms=115),
            Gain(gain_db=-2.1 if self.s["bass"] == "sparse" else -1.3),
        ])(bass, SR)
        drums = Pedalboard([
            LowpassFilter(cutoff_frequency_hz=8600),
            Compressor(threshold_db=-16, ratio=3.1, attack_ms=5, release_ms=90),
        ])(drums, SR)

        bass_level = {"sparse": .59, "pulse": .68, "drive": .77, "melodic": .72}[self.s["bass"]]
        drum_level = .58 if self.s["drums"] == "ambient" else .76
        mix = (bass * bass_level + drums * drum_level + guitar * .65
               + lead_guitar * .47 + synth_lead * .29 + pad * self.s["pad"])
        mix = normalize_peak(apply_fades(mix, SR, fade_in=.15, fade_out=5.5), .88)

        safe_title = re.sub(r'[/:*?"<>|]', "", self.s["title"])
        path = os.path.join(OUT_DIR, f"{number:02d} {safe_title}.wav")
        wavfile.write(path, SR, (mix.T * 32767).astype(np.int16))
        return path, total_seconds


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    results = []
    for number, spec in enumerate(TRACKS, 1):
        renderer = TrackRenderer(spec, number)
        results.append(renderer.render(number))
        del renderer
        gc.collect()

    tracklist_path = os.path.join(OUT_DIR, "TRACKLIST.txt")
    with open(tracklist_path, "w") as handle:
        handle.write("THE WEATHER BETWEEN STATIONS\n\n")
        for number, ((path, seconds), spec) in enumerate(zip(results, TRACKS), 1):
            minutes, remainder = divmod(round(seconds), 60)
            handle.write(f"{number:02d}. {spec['title']}  {minutes}:{remainder:02d}\n")
    print(f"\nAlbum complete: {OUT_DIR}")


if __name__ == "__main__":
    main()
