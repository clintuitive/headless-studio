---
title: "How I Test Audio Tutorials on Operating Systems I Don't Own"
date: 2026-07-05
slug: ci-for-audio-tutorials
description: "A historical walkthrough of the audio tutorial test harness, with updated scope for the rebuilt studio."
---

**September 2026 scope update:** this article describes the original tutorial
harness. The rebuilt studio's current workflow tests the core engine and a
self-contained synthesis example. It does not prove that every older plugin
rig, install command or private sample library works on every platform.
Check the repository's workflow results for the specific revision you use.

The original motivation still applies: an author's installed machine can
hide missing dependencies. The walkthrough below shows how the earlier
harness approached that problem.

## "Works on my machine" is worse for tutorials than for products

When a product has an environment bug, the user files an issue. When a
*tutorial* has one, the reader assumes they made a mistake, burns an
afternoon, and quietly concludes you didn't test it. They're right. And a
tutorial author's machine is the worst possible test environment: years of
half-remembered installs mean the tutorial *can't fail* locally — every
dependency it forgets to mention is already present.

The fix is the same one software teams use: continuous integration on clean
machines. GitHub Actions gives you fresh Ubuntu, Windows, and macOS runners
free of charge. The whole harness is one workflow file and three test
scripts.

## The matrix

```yaml
jobs:
  test:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    runs-on: ${{ matrix.os }}
    defaults:
      run:
        shell: bash          # one script language on all three OSes

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install FluidSynth (Linux)
        if: runner.os == 'Linux'
        run: sudo apt-get update && sudo apt-get install -y fluidsynth libfluidsynth-dev fluid-soundfont-gm

      - name: Install FluidSynth (macOS)
        if: runner.os == 'macOS'
        run: brew install fluid-synth

      - name: Install FluidSynth (Windows)
        if: runner.os == 'Windows'
        run: choco install fluidsynth -y

      - name: Install Python packages from the articles
        run: pip install pedalboard pyfluidsynth numpy scipy

      - name: "Article: headless VST3 hosting"
        run: python tests/test_pedalboard_host.py

      - name: "Article: FluidSynth sample-accurate render"
        run: python tests/test_fluidsynth_render.py

      - name: Upload rendered audio
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: renders-${{ matrix.os }}
          path: "*.wav"
```

Two details do a lot of work here. `fail-fast: false` means a Windows failure
doesn't cancel the Linux and macOS runs — you want the *full* picture per
push. And `shell: bash` on every step means one scripting dialect everywhere
(GitHub's Windows runners ship a real bash).

The install steps aren't incidental — they're **the article's install
instructions, executed literally**. If `choco install fluidsynth` stops
working, the job goes red and the article is wrong. That's the contract.

## Tests that distinguish "broken" from "couldn't check"

Each test script exercises one article's code and prints a verdict per claim:
`PASS`, `FAIL`, or `SKIP`. The distinction between the last two matters more
than anything else in the harness. `FAIL` means the article lies — a claim
executed and produced the wrong result, and the job exits nonzero. `SKIP`
means the claim couldn't be exercised (a third-party plugin isn't installed,
a download was unavailable) — reported loudly, but not red.

```python
sf2 = find_soundfont()
if sf2 is None:
    print(f"SKIP fluidsynth-render on {sys.platform}: no soundfont found")
    return
...
if peak < 0.01:
    print(f"FAIL fluidsynth-render on {sys.platform}: rendered silence")
    sys.exit(1)
print(f"PASS fluidsynth-render on {sys.platform}: peak {peak:.3f}")
```

Without the three-way verdict, you end up either ignoring red jobs
("that's just the plugin thing") — at which point the harness is dead — or
quietly weakening tests until they can't fail. Audio adds one more wrinkle:
**silence is a passing exit code.** A render pipeline can complete
successfully and produce zeros. Every audio test needs a peak or RMS
assertion; "it ran" proves nothing.

## What it caught on day one

**Bug 1: the test's own soundfont download was fake.** The harness fetched a
GM soundfont from a raw GitHub URL that had, at some point, become a Git LFS
pointer — a few hundred bytes of text where a 6 MB binary should be.
FluidSynth said `Not a RIFF file` and rendered silence on two of three OSes.
The fix was twofold: source the soundfont from inside the `pretty_midi` pip
package (pip is a far more reliable CDN than a raw URL), and validate magic
bytes before use — four lines that turn a mystery into a message:

```python
with open(sf2_path, "rb") as f:
    if f.read(4) != b"RIFF":
        print(f"NOTE: {sf2_path} is not a valid SoundFont — ignoring it")
```

**Bug 2: my Windows advice was plausible and wrong.** After CI proved the
chocolatey FluidSynth install works, I added a helpful note: if the import
can't find the DLL, call `os.add_dll_directory()`. Sounds right. It isn't
sufficient — `ctypes.util.find_library` on Windows searches `PATH` and
ignores `add_dll_directory` entirely. I only learned this by reading
pyfluidsynth's loader source, which contains the workaround *and a comment
explaining the bug*, and which also revealed the choco path is special-cased
upstream so the note was barely needed at all.

That second one is the deeper lesson: **CI catches what's broken, but it
can't catch what's accidentally right.** My test set both `PATH` *and*
`add_dll_directory`, so the green check couldn't tell me which line mattered.
The residual failure mode of tested tutorials is advice that passes for the
wrong reason — and the only fix for that is reading the source of the thing
you're advising about.

## The artifact worth the whole setup

The workflow's last step uploads every rendered WAV. Which means each push
produces the same bassline, rendered by FluidSynth, on Ubuntu, Windows, and
macOS — three files, byte-different, musically identical. Download them and
listen: that's the cross-platform claim as audio instead of a badge.

The harness is ~150 lines total and generalizes to any technical blog whose
code touches the OS: paths, package managers, dynamic libraries, audio
drivers. If your posts include install commands you haven't run on a clean
machine this month, they're aspirations, not instructions.

The whole thing is public and MIT-licensed —
[github.com/clintuitive/headless-studio-tests](https://github.com/clintuitive/headless-studio-tests).
Fork it, point it at your own posts, and let three clean machines tell you the
truth.
