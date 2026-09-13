---
title: Test the Studio on a Clean Machine
date: 2026-07-05
slug: ci-for-audio-tutorials
description: What the repository CI checks, what it leaves to local renders, and how to avoid mistaking a passing job for musical quality.
---

An audio script can succeed brilliantly and write four minutes of silence. It
can also work perfectly on your machine because of a plugin you installed in
2023 and forgot to mention. Both failures are quiet, and both are embarrassing
in public. So the repository's tests exist to catch them — while being honest
that they can't test instruments the test machine doesn't have.

The core checks run on Linux, macOS and Windows, against Python 3.11 and 3.12.
The workflow is `.github/workflows/core.yml`; that file in the checkout is the
authority, not this paragraph.

## Test the portable path first

The core job installs `requirements.txt`, runs the engine tests, and renders
Open Window:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s scripts/tests -v
python scripts/generate_portable_samples.py --piece open-window --output-dir Tracks/ci
```

The test command needs `PYTHONPATH` pointing at `scripts`, which the workflow
sets as an environment variable rather than pretending the repository is an
installed package. The portable render uses no external instruments at all, and
that's the point: when it fails, nobody gets to blame a missing private
library.

The tests cover concrete contracts inside the engine — sample conversion and
rates, event pairing, stereo behaviour, score constraints. The portable render
adds checks for finite output, a peak bound, and reconstruction from the float
stems. Together they tell you the basic path still works across the matrix.
They certify nothing about any plugin, SoundFont or album asset, and shouldn't
be read as if they do.

## Keep external-asset checks explicit

Before an album render, run the asset preflight:

```bash
python scripts/check_album_assets.py --album quiet-hours --asset-root /path/to/studio-assets
```

It confirms the required paths and tools exist. It does not listen to the
samples, and it has no opinion on whether their licenses permit a release —
source identity and permission are things you bring to the project, not things
a script can infer.

For a render that uses those assets, verify hashes, duration, output format,
finite values and tail behaviour. Measure true peak after MP3 encoding as well
as in the PCM master. And keep the failures visible: a skipped optional plugin
test is not evidence that the plugin works, however green the summary looks.

## Keep the public repository small enough to inspect

A second workflow checks the committed file inventory and runs a pinned,
checksum-verified Gitleaks binary over the Git history. Source code and
publication files belong in the public repository. Credentials, installed
plugins, sample libraries and private release records emphatically do not.

The inventory allows the site's own player JavaScript as source code — it isn't
a bundled third-party audio player. The site uses ordinary browser audio
playback and direct links to separately hosted recordings.

A scanner reduces accidental exposure. It cannot prove you own a sample, and it
will not catch every possible secret. Read what a change adds, especially when
you're moving work out of a local studio directory into the public checkout,
which is precisely when the interesting mistakes happen.

## A passing render still needs a listener

A null test will find a missing stem. It will never find a dull melody. A
loudness meter will find a gain mismatch and remain serenely untroubled by a
string part that's been fighting the piano for two minutes.

Use the clean-machine checks to establish a starting point you can rely on,
then use matched listening comparisons to make the musical decisions. Keep the
difference visible in the report: what ran, what passed, what needed an
external setup, and what is still waiting on a human being with headphones on.
