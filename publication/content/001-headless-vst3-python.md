---
title: Driving VST3 Effects from Python
date: 2026-07-02
slug: headless-vst3-python
description: An optional plugin stage for a studio built around saved performances and reproducible mixes.
---

A plugin is a function with an expensive haircut. Audio goes in, audio comes
out. Nothing about that shape requires a window, a mouse or a timeline — which
is exactly why it drops so neatly into a Python studio. Render the performance
once, save it, then push it through as many effects as your patience allows
without ever asking the instrument to play again.

You don't need plugins to start. The self-contained sketches in
[the repository](https://github.com/clintuitive/headless-studio) run on NumPy
and SciPy alone:

```bash
python -m pip install -r requirements.txt
python scripts/generate_portable_samples.py --piece open-window --output-dir Tracks/demo
```

That gives you dry buses, processed stems and a float mix — a small complete
record, nothing downloaded. Reach for a plugin when there's a particular sound
you're after: an amp model you already trust, a delay with a character you
can't be bothered to rebuild from scratch.

## Put the plugin after the saved performance

The optional host installs with `python -m pip install pedalboard`. The plugin
itself is your problem: it has to match your operating system and processor,
and the repository doesn't ship anyone else's software.

Here's the whole idea, running an existing stereo float WAV through an effect.
Swap in the path to something you actually have installed:

```python
import numpy as np
from scipy.io import wavfile
from pedalboard import load_plugin

rate, frames = wavfile.read('Tracks/demo/open-window/dry/melody.wav')
assert frames.dtype == np.float32 and frames.ndim == 2
channels = frames.T.copy()                 # host layout: channels × frames
plugin = load_plugin('/path/to/effect.vst3')
processed = plugin(channels, rate)
assert np.isfinite(processed).all()
wavfile.write('Tracks/effected-melody.wav', rate, processed.T)
```

Two details in there will bite you if you skip them. Working in float means
you never have to guess what scale the integer samples were stored at. And the
transpose matters: SciPy hands you frames by channels, while the host wants
channels by frames. Neither operation touches the sample rate.

Print `plugin.parameters` to see what the plugin exposes. Set the values you
care about deliberately and write them down with the mix — parameter names and
ranges belong to that specific plugin, so my settings for one effect mean
nothing for yours.

## Preserve state and tails

Effects remember. A delay is holding echoes, a compressor is mid-envelope, an
amp model has its own internal weather. Reset the plugin between chunks and you
get a different result than you'd get processing the whole thing at once. So
when you process in blocks, use the host's state-preserving mode, and leave
enough trailing silence for the effect to finish decaying into. Then check that
it behaved, with the exact host and plugin versions you installed.

Some plugins also keep settings that never appear as automatable parameters.
The reliable move is to save a preset through the plugin's own interface and
load that. The repository's `music_engine/plugins.py` has a Neural Amp Modeler
helper that understands one specific preset layout — an adapter for a format I
went and learned, not a general-purpose preset editor. If the format changes,
that helper needs re-checking before you trust it.

## Keep the experiment comparable

Change one setting. Keep the dry performance fixed. Match the listening levels
before you decide anything, because a louder render sounds more detailed even
when the only thing that improved was the gain, and you will fall for it.

Save the processed bus as a float stem. If several instruments share a
nonlinear effect, keep the combined output as a group stem too: separately
processed inputs are not guaranteed to sum back to the same sound. The [mix and
stem article](/stems-null-test.html) works through where that boundary sits.

Plugin loading in the shared engine is lazy, so the sampler and synthesis
examples never ask you to configure a host you don't want. And if a plugin
insists on a runtime the rest of your studio can't live with, push that one
rendering step across a [process
boundary](/incompatible-plugins-out-of-process.html) and carry on.
