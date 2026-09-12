---
title: Test the Studio on a Clean Machine
date: 2026-07-05
slug: ci-for-audio-tutorials
description: What the repository CI checks, what it leaves to local renders, and how to avoid mistaking a passing job for musical quality.---

An audio script can finish successfully and write silence. It can also work on
its author's machine because an unmentioned plugin or sample library happens
to be installed. A useful test setup addresses both problems without claiming
to test instruments it does not have.

The repository runs its core checks on Linux, macOS and Windows with Python
3.11 and 3.12. The workflow is `.github/workflows/core.yml`; consult the workflow
files in the checkout for the authoritative configuration.

## Test the portable path first

The core job installs `requirements.txt`, runs the engine tests, and renders
Open Window. Its commands are:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s scripts/tests -v
python scripts/generate_portable_samples.py --piece open-window --output-dir Tracks/ci
```

The test command needs `PYTHONPATH` set to `scripts`; the workflow sets that
as an environment variable. This avoids pretending the repository is an
installed package. The portable render uses no external instruments, so a
failure cannot be excused as a missing private library.

Tests cover concrete contracts in the engine: sample conversion and rates,
event pairing, stereo behavior and score constraints. The portable render
also checks finite output, its peak bound and reconstruction from float stems.
Those checks tell us whether the basic path still works across the matrix.
They do not certify every plugin, SoundFont or album asset.

## Keep external-asset checks explicit

Before an album render, run the asset preflight:

```bash
python scripts/check_album_assets.py --album quiet-hours --asset-root /path/to/studio-assets
```

It checks required paths and tools. It does not listen to the samples or decide
whether their licenses permit a release. Source identities and permission
records are separate inputs to the project.

For a render that uses those assets, verify hashes, duration, output format,
finite values and tail behavior. Measure true peak after MP3 encoding as well
as in the PCM master. Keep failures visible: a skipped optional plugin test is
not evidence that the plugin works.

## Keep the public repository small enough to inspect

A second workflow checks the committed file inventory and runs a pinned,
checksum-verified Gitleaks binary over Git history. Source code and publication
files belong in the public repository. Credentials, installed plugins, sample
libraries and private release records do not.

The inventory permits the site's custom player JavaScript as source code; it
does not bundle a third-party audio player. The site uses browser audio playback
and direct links to separately hosted recordings.

A scanner reduces accidental exposure. It cannot prove ownership of a sample
or identify every possible secret. Review what a change adds, especially when
moving work from a local studio directory into the public checkout.

## A passing render still needs a listener

A null test can identify a missing stem. It cannot identify a dull melody.
A loudness meter can identify a gain mismatch. It cannot decide whether a
string part distracts from the piano.

Use clean-machine checks to establish a dependable starting point, then use
matched listening comparisons to choose musical changes. Keep the distinction
in the test report: what ran, what passed, what required an external setup,
and what still needs a human decision.
