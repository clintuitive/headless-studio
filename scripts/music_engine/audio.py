"""Small, dependency-light audio and mix helpers."""

from __future__ import annotations

import numpy as np


def rms(audio: np.ndarray) -> float:
    """Return full-buffer RMS as a Python float."""
    return float(np.sqrt(np.mean(np.asarray(audio, dtype=np.float64) ** 2)))


def stereo(signal: np.ndarray, pan: float = 0.0) -> np.ndarray:
    """Pan a mono signal into stereo using equal-power gains.

    ``pan`` is clamped to ``[-1, 1]``: -1 is left, 0 is center, 1 is right.
    """
    pan = float(np.clip(pan, -1.0, 1.0))
    left = np.sqrt(0.5 * (1.0 - pan))
    right = np.sqrt(0.5 * (1.0 + pan))
    signal = np.asarray(signal)
    return np.stack([signal * left, signal * right])


def normalize_peak(audio: np.ndarray, target: float = 0.9) -> np.ndarray:
    """Scale a buffer to a target absolute peak without changing shape."""
    peak = max(float(np.max(np.abs(audio))), 1e-9)
    return audio / peak * float(target)


def match_rms(
    audio: np.ndarray,
    target: float,
    *,
    peak_ceiling: float | None = 0.9,
) -> np.ndarray:
    """Match RMS while optionally respecting an absolute peak ceiling."""
    scale = float(target) / max(rms(audio), 1e-9)
    if peak_ceiling is not None:
        peak_scale = float(peak_ceiling) / max(float(np.max(np.abs(audio))), 1e-9)
        scale = min(scale, peak_scale)
    return audio * scale


def apply_fades(
    audio: np.ndarray,
    sample_rate: int,
    *,
    fade_in: float = 0.0,
    fade_out: float = 0.0,
) -> np.ndarray:
    """Return a copy with linear fades applied along the last axis."""
    out = np.array(audio, copy=True)
    n = out.shape[-1]
    env = np.ones(n, dtype=np.float32)
    n_in = min(max(int(fade_in * sample_rate), 0), n)
    n_out = min(max(int(fade_out * sample_rate), 0), n)
    if n_in:
        env[:n_in] = np.linspace(0.0, 1.0, n_in, dtype=np.float32)
    if n_out:
        env[-n_out:] *= np.linspace(1.0, 0.0, n_out, dtype=np.float32)
    out *= env
    return out
