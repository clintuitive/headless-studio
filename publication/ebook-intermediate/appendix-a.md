# Appendix A — Setup, Per Operating System

For the current minimal quickstart, create a virtual environment and run
`pip install -r requirements.txt`, then
`python scripts/generate_portable_samples.py --piece afterimage` from the
repository root. Optional older rigs use `requirements-plugins.txt` plus
separately installed native plugins and assets. The setup recipes below are
not a claim that all proprietary instruments run on all platforms.

Every install command in the book, collected in one place. Everything in
this appendix runs in the book's continuous-integration harness on clean
Ubuntu, Windows, and macOS machines — these are tested instructions, not
remembered ones.

## The Python packages (all platforms)

```bash
pip install pedalboard pyfluidsynth numpy scipy mido
# optional extras used in later chapters:
pip install mutagen        # metadata tagging (Chapter 15)
```

Python 3.9 or newer. All five core packages install from pre-built wheels
on all three OSes — no compilers needed.

## FluidSynth (Chapter 2)

**macOS**

```bash
brew install fluid-synth
```

If `import fluidsynth` then fails with "Couldn't find the FluidSynth
library," add the loader shim *before* the import (from the Sign-Off
album script, where it ships in production):

```python
import ctypes.util, os

_orig_find_library = ctypes.util.find_library
def _find_library(name):
    found = _orig_find_library(name)
    if not found and name == "fluidsynth":
        path = "/opt/homebrew/lib/libfluidsynth.dylib"
        if os.path.exists(path):
            return path
    return found
ctypes.util.find_library = _find_library
```

**Linux (Debian/Ubuntu)**

```bash
sudo apt-get install fluidsynth libfluidsynth-dev fluid-soundfont-gm
```

The third package installs a General MIDI soundfont at
`/usr/share/sounds/sf2/FluidR3_GM.sf2` — usable immediately.

**Windows**

```powershell
choco install fluidsynth
```

Verified on clean machines: the chocolatey install works with no further
configuration (pyfluidsynth special-cases its install directory,
`C:\tools\fluidsynth\bin`). If you installed FluidSynth anywhere *else*,
register the directory both ways before importing — `find_library` only
searches `PATH`, while the DLL's own dependencies resolve via
`add_dll_directory`:

```python
import os
os.add_dll_directory(r"C:\path\to\fluidsynth\bin")
os.environ["PATH"] = r"C:\path\to\fluidsynth\bin;" + os.environ["PATH"]
```

## Plugin folders (Chapter 3)

`load_plugin` needs a path; installers put plugins here:

| Platform | System-wide | Per-user |
|---|---|---|
| macOS VST3 | `/Library/Audio/Plug-Ins/VST3` | `~/Library/Audio/Plug-Ins/VST3` |
| macOS Audio Unit | `/Library/Audio/Plug-Ins/Components` | `~/Library/Audio/Plug-Ins/Components` |
| Windows VST3 | `C:\Program Files\Common Files\VST3` | — |
| Linux VST3 | `/usr/lib/vst3` | `~/.vst3` |

## The Intel-Python rescue environment (Chapter 4, macOS only)

For Intel-only plugins on Apple Silicon:

```bash
arch -x86_64 /usr/bin/python3 -m venv ~/.venvs/x86-audio
arch -x86_64 ~/.venvs/x86-audio/bin/pip install pedalboard mido numpy scipy
```

Invoke helpers with `subprocess.run(["arch", "-x86_64",
"~/.venvs/x86-audio/bin/python", "helper.py", ...])`.

## Windows plugins on Linux (Chapter 4)

```bash
# Arch: yay -S yabridge yabridgectl wine-staging
# (see the yabridge README for apt/dnf equivalents)
yabridgectl add "$HOME/.wine/drive_c/Program Files/Common Files/VST3"
yabridgectl sync        # bridged plugins appear in ~/.vst3
```

## 32-bit plugins on Windows (Chapter 4)

Install a 32-bit Python from python.org alongside your 64-bit one, then
run the same helper script under it:

```python
subprocess.run([r"C:\Python311-32\python.exe", "render_helper.py",
                "notes.json", "out.wav"])
```

## Format conversion tools (Chapters 5–6)

- **macOS:** `afconvert` is built in.
  `afconvert -f WAVE -d LEI16@44100 in.caf out.wav`
- **Windows/Linux:** `ffmpeg -i in.caf out.wav` (install via
  choco/apt/brew).

## Sanity check

After setup, this five-liner proves the two load-bearing pieces work:

```python
import numpy as np, fluidsynth                     # (shim first on macOS)
from pedalboard import Pedalboard, Chorus
noise = np.random.default_rng(0).uniform(-0.3, 0.3, (2, 44100)).astype("float32")
out = Pedalboard([Chorus()])(noise, 44100)
print("pedalboard OK:", out.shape, "— fluidsynth OK:", fluidsynth.Synth() is not None)
```
