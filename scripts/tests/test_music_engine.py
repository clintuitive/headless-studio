import json
import os
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from scipy.io import wavfile

from music_engine import (
    DrumSampler,
    EventTimeline,
    ExsSampler,
    Humanizer,
    apply_fades,
    cc_curve,
    match_rms,
    normalize_peak,
    stereo,
)
from music_engine.plugins import load_nam


class AudioTests(unittest.TestCase):
    def test_equal_power_stereo_pan(self):
        signal = np.ones(16, dtype=np.float32)
        centered = stereo(signal)
        self.assertEqual(centered.shape, (2, 16))
        self.assertAlmostEqual(float(centered[0, 0]), 2 ** -0.5, places=6)
        self.assertAlmostEqual(float(centered[1, 0]), 2 ** -0.5, places=6)
        left = stereo(signal, -1)
        self.assertTrue(np.allclose(left[1], 0))

    def test_normalization_matching_and_fades(self):
        signal = np.linspace(-0.2, 0.2, 1000, dtype=np.float32)
        self.assertAlmostEqual(float(np.abs(normalize_peak(signal, 0.8)).max()), 0.8)
        matched = match_rms(signal, 0.05, peak_ceiling=None)
        self.assertAlmostEqual(float(np.sqrt(np.mean(matched ** 2))), 0.05, places=5)
        faded = apply_fades(np.ones(1000), 1000, fade_in=0.1, fade_out=0.2)
        self.assertEqual(float(faded[0]), 0.0)
        self.assertEqual(float(faded[-1]), 0.0)
        self.assertEqual(float(faded[500]), 1.0)


class EventAndHumanizationTests(unittest.TestCase):
    def test_event_timeline_and_controller_curve(self):
        timeline = EventTimeline(sample_rate=100, buses=["lead"])
        timeline.note("lead", 0.25, 0.5, 60, 90)
        timeline.cc("lead", 0.0, 11, 0)
        timeline.cc("lead", 1.0, 11, 127)
        self.assertEqual(timeline["lead"][0], (25, "on", 0, 60, 90))
        curve = cc_curve(
            timeline["lead"], 1.1, sample_rate=100, initial_value=0
        )
        self.assertAlmostEqual(float(curve[50]), 0.5, places=2)
        self.assertAlmostEqual(float(curve[100]), 1.0, places=6)

    def test_humanizer_is_seeded_and_bounded(self):
        first = Humanizer.seeded(7)
        second = Humanizer.seeded(7)
        values_a = [first(1.0, 64) for _ in range(8)]
        values_b = [second(1.0, 64) for _ in range(8)]
        self.assertEqual(values_a, values_b)
        for time_seconds, velocity in values_a:
            self.assertGreaterEqual(time_seconds, 0)
            self.assertTrue(1 <= velocity <= 127)


class SamplerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.sample_rate = 1000
        mono = np.linspace(0, 0.8, 100, dtype=np.float32)
        wavfile.write(
            os.path.join(self.temp.name, "note.wav"),
            self.sample_rate,
            (mono * 32767).astype(np.int16),
        )
        stereo_hit = np.stack([mono, mono * 0.5], axis=1)
        wavfile.write(
            os.path.join(self.temp.name, "drum.wav"),
            self.sample_rate,
            (stereo_hit * 32767).astype(np.int16),
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_exs_sampler_renders_note_and_attack(self):
        manifest = [{
            "file": "note.wav",
            "root": 60,
            "keylo": 60,
            "keyhi": 60,
            "vello": 1,
            "velhi": 127,
            "group": "Clean",
        }]
        with open(os.path.join(self.temp.name, "manifest.json"), "w") as handle:
            json.dump(manifest, handle)
        sampler = ExsSampler(
            self.temp.name,
            sample_rate=self.sample_rate,
            deterministic=True,
            groups=["Clean"],
        )
        events = [(0, "on", 0, 60, 100), (80, "off", 0, 60, 0)]
        plain = sampler.render(events, 0.2)
        soft = sampler.render(events, 0.2, attack=0.02)
        self.assertGreater(float(np.abs(plain).max()), 0.1)
        self.assertLess(abs(float(soft[1])), abs(float(plain[1])))

    def test_drum_sampler_selects_velocity_layer(self):
        manifest = [{
            "file": "drum.wav",
            "root": 36,
            "keylo": 36,
            "keyhi": 36,
            "vello": 1,
            "velhi": 127,
            "group": "Kick",
        }]
        with open(os.path.join(self.temp.name, "manifest.json"), "w") as handle:
            json.dump(manifest, handle)
        sampler = DrumSampler(
            self.temp.name,
            sample_rate=self.sample_rate,
            rng=np.random.default_rng(1),
        )
        output = sampler.render([(10, "on", 9, 36, 100)], 0.2)
        self.assertEqual(output.shape, (2, 200))
        self.assertGreater(float(np.abs(output[:, 10:]).max()), 0.1)
        self.assertLess(float(np.abs(output[:, :10]).max()), 1e-9)


class NamStateTests(unittest.TestCase):
    class FakePlugin:
        def __init__(self):
            marker = b"###NeuralAmpModeler###"
            component = (
                marker
                + len(b"1.0").to_bytes(4, "little", signed=True)
                + b"1.0"
                + (0).to_bytes(4, "little", signed=True)
            )
            component = component.ljust(96, b"\0")
            list_offset = 48 + len(component)
            header = b"VST3" + b"\0" * 36 + list_offset.to_bytes(
                8, "little", signed=True
            )
            tail = (
                b"List"
                + (1).to_bytes(4, "little", signed=True)
                + b"Comp"
                + (48).to_bytes(8, "little", signed=True)
                + len(component).to_bytes(8, "little", signed=True)
            )
            self.preset_data = header + component + tail

    def test_nam_model_path_is_injected(self):
        plugin = self.FakePlugin()
        with patch("music_engine.plugins.load_plugin", return_value=plugin):
            result = load_nam("/tmp/example.nam", "/tmp/NAM.vst3")
        self.assertIs(result, plugin)
        self.assertIn(os.path.abspath("/tmp/example.nam").encode(), bytes(plugin.preset_data))


if __name__ == "__main__":
    unittest.main()
