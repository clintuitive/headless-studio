"""Shared rendering tools for the music-generation scripts.

The song files should describe music: tempo, harmony, parts, movements,
and per-track production choices.  This package owns the reusable studio
infrastructure underneath those decisions.
"""

from .audio import (
    apply_fades,
    match_rms,
    normalize_peak,
    rms,
    stereo,
)
from .events import EventTimeline, cc_curve
from .humanize import Humanizer
from .plugins import load_nam
from .renderers import render_external_instrument
from .samplers import DrumSampler, ExsSampler, ZoneSampler

__all__ = [
    "apply_fades",
    "cc_curve",
    "DrumSampler",
    "EventTimeline",
    "ExsSampler",
    "ZoneSampler",
    "Humanizer",
    "load_nam",
    "match_rms",
    "normalize_peak",
    "render_external_instrument",
    "rms",
    "stereo",
]
