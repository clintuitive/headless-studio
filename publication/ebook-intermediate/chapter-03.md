# Chapter 3 — Processing Saved Audio with VST3 Effects

A plugin is a function with an expensive haircut. Audio goes in, audio comes
out. Forty years of audio engineering sit inside the box, and the interface it
presents to us is `process(samples) -> samples` — which is why the box drops so
neatly into a Python studio despite having been built for a mouse.

That shape suggests the order of operations. Render the performance once, save
it, then push it through as many effects as your patience allows without ever
asking the instrument to play again. The instrument's job is finished. The
plugin's job is a separate afternoon.

You don't need plugins to start, and I'd rather you didn't. The self-contained
sketches run on NumPy and SciPy alone:

```bash
python -m pip install -r requirements.txt
python scripts/generate_portable_samples.py --piece open-window --output-dir Tracks/demo
```

That gives you dry buses, processed stems and a float mix — a small complete
record, nothing downloaded. Reach for a plugin when there's a particular sound
you're after: an amp model you already trust, a delay with a character you
can't be bothered to rebuild from first principles.

## Put the plugin after the saved performance

The optional host installs with `python -m pip install pedalboard`. The plugin
itself is your problem. It has to match your operating system *and* your
processor architecture, and this repository ships nobody else's software.
(Chapter 4 is entirely about what to do when that match can't be made.)

Here is the whole idea, running a saved stereo float WAV through an effect.
Substitute a path to something you actually have installed:

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

Two details in there will bite you if you skip past them.

Working in float means you never have to guess what scale the samples were
stored at. A 16-bit integer WAV stores values from −32768 to 32767; a 24-bit one
uses a different range again; float WAVs are simply −1.0 to 1.0 and always have
been. Convert once, at the edges, and let everything in between be float.

And the transpose matters. SciPy hands you an array of frames, each holding its
channels — shape `(frames, 2)`. The host wants channels, each holding its
frames — shape `(2, frames)`. `.T` swaps those two axes, and `.copy()` makes the
result contiguous in memory, which some hosts insist on. Neither operation
touches the sample rate or changes a single number; they only change how the
numbers are arranged. Getting this backwards produces a result so mangled it's
usually obvious, which is the one mercy of the situation.

Print `plugin.parameters` to see what the plugin exposes. Set the values you
care about deliberately, and write them down with the mix. Parameter names and
ranges belong to that specific plugin, so a setting that sounds right on my
amp model means precisely nothing on yours.

## Preserve state and tails

Effects remember. A delay is holding echoes from a second ago. A compressor is
partway through its envelope. An amp model has its own internal weather.

This matters because audio is often processed in blocks rather than all at
once, and if you reset the plugin between blocks you'll get a different result
from processing the whole thing in one go — a delay that restarts, a compressor
that keeps flinching. So when you process in blocks, use the host's
state-preserving mode, and leave enough trailing silence at the end for the
effect to decay into. Then confirm it behaved, with the exact host and plugin
versions you installed, because this is precisely the sort of thing that
changes quietly between releases.

Some plugins also keep settings that never appear as automatable parameters —
a loaded impulse response, a model file, a mode switch buried in the UI. The
reliable move is to configure the plugin through its own interface, save a
preset, and load that. The repository's `music_engine/plugins.py` has a Neural
Amp Modeler helper that understands one specific preset layout: an adapter for
a format I went and learned, not a general-purpose preset editor. If the format
changes, the helper needs re-checking before you trust it with a record.
Appendix C takes that apart byte by byte, for when the save-a-preset workflow
isn't enough.

## Keep the experiment comparable

Change one setting. Keep the dry performance fixed. Match the listening levels
before you decide anything — a louder render sounds more detailed, more
present, generally better, even when the only thing that improved was the gain.
Everyone falls for this. Knowing about it helps less than you'd hope, so
normalize the comparison instead of trusting yourself.

Save the processed bus as a float stem. If several instruments share a
*nonlinear* effect — distortion, saturation, an amp — keep the combined output
as a group stem as well. Separately processed inputs are not guaranteed to sum
back to the same sound, and Chapter 12 shows exactly where and why that promise
breaks.

One practical note: plugin loading in the shared engine is lazy, so the sampler
and synthesis chapters never ask you to configure a host you didn't want. And
if a plugin insists on a runtime the rest of your studio can't live with, you
can push that one rendering step across a process boundary instead, which is
the next chapter.

---

*Next — Chapter 4: An Instrument Across a Process Boundary.*
