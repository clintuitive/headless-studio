"""Bridges to external or architecture-specific instrument renderers."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from collections.abc import Sequence

import numpy as np
from .samplers import read_sample


def render_external_instrument(
    notes: Sequence[dict],
    total_seconds: float,
    *,
    python_path: str,
    helper_path: str,
    sample_rate: int = 44_100,
    architecture: str | None = None,
    label: str = "External instrument",
) -> np.ndarray | None:
    """Render a JSON note list through a helper process.

    Returns stereo float32 audio, padded or trimmed to the requested duration.
    Missing executables or an empty note list return ``None`` so a caller can
    fall back to another instrument. Helper failures are reported and also
    return ``None``.
    """
    if not notes or not os.path.exists(os.path.expanduser(python_path)):
        return None
    python_path = os.path.expanduser(python_path)
    helper_path = os.path.abspath(helper_path)
    with tempfile.TemporaryDirectory() as directory:
        events_path = os.path.join(directory, "events.json")
        stem_path = os.path.join(directory, "stem.wav")
        with open(events_path, "w") as handle:
            json.dump({"duration": total_seconds, "notes": list(notes)}, handle)
        command = [python_path, helper_path, events_path, stem_path]
        if architecture:
            command = ["arch", f"-{architecture}", *command]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"{label} helper failed:\n{result.stderr.strip()}")
            return None
        if result.stdout.strip():
            print(result.stdout.strip())
        audio = read_sample(stem_path, sample_rate)

    if audio.ndim == 1:
        audio = np.stack([audio, audio], axis=1)
    audio = audio.T
    n_samples = int(total_seconds * sample_rate)
    if audio.shape[1] < n_samples:
        audio = np.pad(audio, ((0, 0), (0, n_samples - audio.shape[1])))
    return audio[:, :n_samples]
