# Chapter 3 — Processing Saved Audio with VST3 Effects

A plugin host takes audio in, processes it, and returns audio. That makes it a
useful stage in a Python studio: save an instrument's performance once, then
compare effects without asking the instrument to play again.

The basic studio does not require plugins. Start with the self-contained
sketches in [the repository](https://github.com/clintuitive/headless-studio):

```bash
python -m pip install -r requirements.txt
python scripts/generate_portable_samples.py --piece open-window --output-dir Tracks/demo
```

That gives you dry buses, processed stems and a float mix. Add a plugin when
there is a particular sound you want from it, such as an amp model or a delay.

## Put the plugin after the saved performance

Install the optional Python host with `python -m pip install pedalboard` and
install a plugin compatible with your operating system and processor. Plugins
are separate software; the repository does not distribute them.

This example processes an existing stereo float WAV through an effect. Replace
the plugin path with your own installed effect:

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

A float WAV avoids guessing the scale of integer samples. The transpose is
just as important: SciPy reads frames by channels, while this host expects
channels by frames. Neither operation changes the sample rate.

Inspect `plugin.parameters` to discover the controls the host exposes. Set
values deliberately and record them with the mix. Parameter names and ranges
belong to the installed plugin, so an example for one effect is not a universal
preset for every VST3.

## Preserve state and tails

An effect may remember what happened in earlier buffers. A delay stores echoes;
a compressor follows its envelope; an amp model can have internal state.
Resetting the effect at every chunk changes the result. When processing in
blocks, use the host's state-preserving mode and include enough trailing silence
for the effect to decay. Verify that behavior with the exact host and plugin
versions you install.

A plugin can also keep settings outside its automatable parameters. Prefer
loading a preset saved through the plugin's supported interface. The repository's
`music_engine/plugins.py` includes a Neural Amp Modeler helper for its specific
preset layout; that is an adapter for a known format, not a general preset
editor. A format change needs its own validation before use.

## Keep the experiment comparable

Change one effect setting while keeping the dry performance fixed. Match
listening levels before choosing between versions. A louder render can seem
more detailed even when the actual improvement is just gain.

Save the processed bus as a float stem. If several instruments share a nonlinear
effect, keep its combined output as a group stem: the separately processed
inputs are not guaranteed to sum to the same result. The [mix and stem
article](https://clintjohnson.cloud/headless-studio/stems-null-test.html) explains that boundary.

Plugin loading is lazy in the shared engine. Readers can use the sampler and
synthesis examples without configuring an optional host. If a plugin requires
a different runtime, move that one rendering step across a [process
boundary](https://clintjohnson.cloud/headless-studio/incompatible-plugins-out-of-process.html).
