"""Seeded performance variation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Humanizer:
    """Apply reproducible timing and velocity drift.

    A caller may provide its existing ``numpy.random.Generator`` to preserve
    a song's exact random stream during migration.
    """

    rng: np.random.Generator
    timing_sd: float = 0.006
    velocity_sd: float = 8.0
    clamp_sd: float = 2.5

    @classmethod
    def seeded(
        cls,
        seed: int,
        *,
        timing_sd: float = 0.006,
        velocity_sd: float = 8.0,
    ) -> "Humanizer":
        return cls(np.random.default_rng(seed), timing_sd, velocity_sd)

    def __call__(
        self,
        time_seconds: float,
        velocity: float,
        *,
        timing_sd: float | None = None,
        velocity_sd: float | None = None,
    ) -> tuple[float, int]:
        timing_sd = self.timing_sd if timing_sd is None else timing_sd
        velocity_sd = self.velocity_sd if velocity_sd is None else velocity_sd
        offset = np.clip(
            self.rng.normal(0.0, timing_sd),
            -self.clamp_sd * timing_sd,
            self.clamp_sd * timing_sd,
        )
        time_seconds = max(float(time_seconds + offset), 0.0)
        velocity = int(np.clip(velocity + self.rng.normal(0.0, velocity_sd), 1, 127))
        return time_seconds, velocity
