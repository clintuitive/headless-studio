"""The compact event format shared by the generators."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

import numpy as np

Event = tuple[int, str, int, int, int]


class EventTimeline:
    """Named buses of sample-position MIDI-like events.

    Events intentionally remain plain tuples for compatibility with the
    existing generators and external render helpers.
    """

    def __init__(self, sample_rate: int = 44_100, buses: Iterable[str] = ()):
        self.sample_rate = int(sample_rate)
        self.buses: dict[str, list[Event]] = defaultdict(list)
        for bus in buses:
            self.buses[bus] = []

    def note(
        self,
        bus: str,
        time_seconds: float,
        duration_seconds: float,
        note: int,
        velocity: int,
        *,
        channel: int = 0,
    ) -> None:
        start = int(time_seconds * self.sample_rate)
        end = int((time_seconds + duration_seconds) * self.sample_rate)
        self.buses[bus].append((start, "on", channel, int(note), int(velocity)))
        self.buses[bus].append((end, "off", channel, int(note), 0))

    def cc(
        self,
        bus: str,
        time_seconds: float,
        number: int,
        value: int,
        *,
        channel: int = 0,
    ) -> None:
        value = int(np.clip(value, 0, 127))
        self.buses[bus].append(
            (int(time_seconds * self.sample_rate), "cc", channel, int(number), value)
        )

    def __getitem__(self, bus: str) -> list[Event]:
        return self.buses[bus]


def cc_curve(
    events: Iterable[Event],
    total_seconds: float,
    *,
    sample_rate: int = 44_100,
    controller: int = 11,
    initial_value: int = 110,
) -> np.ndarray:
    """Interpolate a sample-accurate controller envelope."""
    n = int(total_seconds * sample_rate)
    times = [0]
    values = [initial_value / 127.0]
    for event in sorted(events, key=lambda item: item[0]):
        if event[1] == "cc" and event[3] == controller:
            times.append(event[0])
            values.append(event[4] / 127.0)
    return np.interp(np.arange(n), times, values).astype(np.float32)
