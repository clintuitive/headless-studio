"""Sample-based instrument and drum rendering."""

from __future__ import annotations

import json
import os
from collections import defaultdict, deque
from math import gcd
from collections.abc import Iterable

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

from .events import Event


def _pcm_to_float(data: np.ndarray) -> np.ndarray:
    if data.dtype == np.uint8:
        return (data.astype(np.float32) - 128.0) / 128.0
    if np.issubdtype(data.dtype, np.integer):
        scale = float(max(abs(np.iinfo(data.dtype).min), np.iinfo(data.dtype).max))
        return data.astype(np.float32) / scale
    return data.astype(np.float32)


def read_sample(path, sample_rate):
    """Read PCM/float WAV, preserving channels and converting the sample rate."""
    source_rate, data = wavfile.read(path)
    data = _pcm_to_float(data)
    if source_rate != sample_rate:
        divisor = gcd(int(source_rate), int(sample_rate))
        data = resample_poly(data, sample_rate // divisor, source_rate // divisor, axis=0)
    return np.asarray(data, dtype=np.float32)


class ExsSampler:
    """Render an extracted EXS instrument from its zone manifest."""

    def __init__(
        self,
        sample_dir: str,
        *,
        sample_rate: int = 44_100,
        rng: np.random.Generator | None = None,
        pickup: float | None = None,
        deterministic: bool = False,
        groups: Iterable[str] | None = None,
        release: float = 0.09,
        stereo_output: bool = False,
    ):
        self.directory = os.path.abspath(sample_dir)
        self.sample_rate = int(sample_rate)
        self.rng = rng if rng is not None else np.random.default_rng(0)
        self.pickup = pickup
        self.deterministic = deterministic
        self.release = float(release)
        self.stereo_output = stereo_output
        if self.sample_rate <= 0 or self.release < 0:
            raise ValueError("Sample rate must be positive and release nonnegative")
        with open(os.path.join(self.directory, "manifest.json")) as handle:
            self.zones = json.load(handle)
        if groups:
            groups = tuple(groups)
            self.zones = [
                zone
                for zone in self.zones
                if any(group in zone.get("group", "") for group in groups)
            ]
        if not self.zones:
            raise ValueError(f"No matching EXS zones in {self.directory}")
        self._cache: dict[str, np.ndarray] = {}
        self._zone_cache = {}

    def _zone(self, note: int, velocity: int) -> dict:
        key = (note, velocity)
        if key in self._zone_cache:
            velocity_zones = self._zone_cache[key]
            return velocity_zones[0] if self.deterministic else velocity_zones[int(self.rng.integers(len(velocity_zones)))]
        candidates = [
            zone for zone in self.zones if zone["keylo"] <= note <= zone["keyhi"]
        ]
        if not candidates:
            candidates = sorted(
                self.zones, key=lambda zone: abs(zone["root"] - note)
            )[:3]
        velocity_zones = [
            zone
            for zone in candidates
            if zone["vello"] <= velocity <= zone["velhi"]
        ] or candidates
        self._zone_cache[key] = velocity_zones
        if self.deterministic:
            return velocity_zones[0]
        return velocity_zones[int(self.rng.integers(len(velocity_zones)))]

    def _load(self, filename: str) -> np.ndarray:
        if filename not in self._cache:
            data = read_sample(os.path.join(self.directory, filename), self.sample_rate)
            if self.stereo_output:
                data = np.stack([data, data]) if data.ndim == 1 else data.T
            elif data.ndim == 2:
                data = data.mean(axis=1)
            self._cache[filename] = data
        return self._cache[filename]

    def render(
        self,
        events: Iterable[Event],
        total_seconds: float,
        *,
        attack: float = 0.0,
    ) -> np.ndarray:
        n_samples = int(total_seconds * self.sample_rate)
        output = np.zeros((2, n_samples) if self.stereo_output else n_samples, dtype=np.float32)
        # Legacy MIDI tuples use FIFO note-off matching. Optional sixth-field
        # voice IDs make nested overlaps unambiguous for new callers.
        open_notes = defaultdict(deque)
        notes = []
        for event in sorted(events, key=lambda item: (item[0], 0 if item[1] == "off" else 1)):
            position, kind, channel, note, value = event[:5]
            if position < 0:
                raise ValueError("Negative event position")
            key = (channel, note, event[5] if len(event) > 5 else None)
            if kind == "on" and value > 0:
                open_notes[key].append((position, value))
            elif (kind == "off" or kind == "on" and value == 0) and open_notes[key]:
                start, velocity = open_notes[key].popleft()
                notes.append((start, position - start, note, velocity))
        # A missing note-off sustains to the end of this finite render.
        for (_, note, _), voices in open_notes.items():
            for start, velocity in voices:
                notes.append((start, max(0, n_samples - start), note, velocity))
        notes.sort(key=lambda note: note[0])

        for position, duration, note, velocity in notes:
            zone = self._zone(note, velocity)
            data = self._load(zone["file"])
            ratio = 2.0 ** ((note - zone["root"]) / 12.0)
            release_samples = int(self.release * self.sample_rate)
            length = min(int(data.shape[-1] / ratio), duration + release_samples, n_samples - position)
            if length <= 0:
                continue
            # Only interpolate the played region, not the whole source sample.
            source_positions = np.arange(length) * ratio
            low = np.floor(source_positions).astype(int)
            high = np.minimum(low + 1, data.shape[-1] - 1)
            fraction = (source_positions - low).astype(np.float32)
            signal = data[..., low] * (1.0 - fraction) + data[..., high] * fraction

            if length > release_samples and release_samples:
                signal[..., -release_samples:] *= np.linspace(
                    1.0, 0.0, release_samples, dtype=np.float32
                )

            if self.pickup:
                frequency = 440.0 * 2.0 ** ((note - 69) / 12.0)
                delay = max(int(self.pickup * self.sample_rate / frequency), 1)
                if delay < signal.shape[-1]:
                    filtered = signal.copy()
                    filtered[..., delay:] -= signal[..., :-delay]
                    signal = filtered * 0.8

            signal *= 0.45 + 0.55 * velocity / 127.0
            if attack > 0.0:
                attack_samples = min(int(attack * self.sample_rate), signal.shape[-1])
                signal[..., :attack_samples] *= np.sin(
                    np.linspace(0.0, np.pi / 2.0, attack_samples, dtype=np.float32)
                ) ** 2

            end = min(position + signal.shape[-1], n_samples)
            if end > position:
                output[..., position:end] += signal[..., :end - position]
        return output


class DrumSampler:
    """Render velocity-layered drum hits from an extracted EXS manifest."""

    def __init__(
        self,
        sample_dir: str,
        *,
        sample_rate: int = 44_100,
        rng: np.random.Generator | None = None,
        output_gain: float = 1.0,
    ):
        self.directory = os.path.abspath(sample_dir)
        self.sample_rate = int(sample_rate)
        self.rng = rng if rng is not None else np.random.default_rng(0)
        self.output_gain = float(output_gain)
        with open(os.path.join(self.directory, "manifest.json")) as handle:
            zones = json.load(handle)
        self.by_key: dict[int, list[dict]] = defaultdict(list)
        for zone in zones:
            self.by_key[zone["keylo"]].append(zone)
        self._cache: dict[str, np.ndarray] = {}

    def _load(self, filename: str) -> np.ndarray:
        if filename not in self._cache:
            data = read_sample(os.path.join(self.directory, filename), self.sample_rate)
            self._cache[filename] = (
                np.stack([data, data]) if data.ndim == 1 else data.T
            )
        return self._cache[filename]

    def render(self, events: Iterable[Event], total_seconds: float) -> np.ndarray:
        n_samples = int(total_seconds * self.sample_rate)
        output = np.zeros((2, n_samples), dtype=np.float32)
        for event in sorted(events, key=lambda item: item[0]):
            position, kind, _, note, velocity = event[:5]
            if position < 0:
                raise ValueError("Negative event position")
            if kind != "on" or velocity == 0:
                continue
            zones = self.by_key.get(note)
            if not zones:
                continue
            matches = [
                zone
                for zone in zones
                if zone["vello"] <= velocity <= zone["velhi"]
            ]
            if not matches:
                matches = [min(zones, key=lambda zone: abs(zone["vello"] - velocity))]
            zone = matches[int(self.rng.integers(len(matches)))]
            signal = self._load(zone["file"]) * (0.55 + 0.45 * velocity / 127.0)
            end = min(position + signal.shape[1], n_samples)
            if end > position:
                output[:, position:end] += signal[:, :end - position]
        return output * self.output_gain
