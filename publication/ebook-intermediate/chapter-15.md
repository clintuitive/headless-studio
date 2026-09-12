# Chapter 15 — Delivery, Publication and Reproducible Files

A delivery package connects a finished mix with the files that reach listeners.
It should be possible to identify a recording without relying on a filename
such as `final-final.wav`. Keep its format, duration, source identity and hash
alongside the track list and credits.

## Assemble the release folder

The album renderer writes numbered 24-bit stereo WAV masters at 44.1 kHz,
listening MP3s and session manifests. Keep the artwork and track metadata in
the release folder too. Preserve comparison renders in separate directories
so a later experiment cannot overwrite a selected master.

A manifest records each file's identity. A SHA-256 digest changes if the bytes
change; it does not tell you whether the music sounds better. Use it to compare
a local export with a copied or published file.

```python
from pathlib import Path
import hashlib

path = Path('Tracks/albums/The Quiet Hours/Masters/02 Slow Rain.wav')
digest = hashlib.sha256(path.read_bytes()).hexdigest()
print(path.name, digest)
```

For larger files, compute the digest in chunks instead of holding the complete
file in memory. Record hashes after the final metadata and encoding steps,
since those can also change the file's bytes.

## Check the actual delivery files

Measure the encoded WAV and MP3 rather than inferring their behavior from the
working float mix. Lossy encoding can change peaks. Confirm channel count,
sample rate, duration, finite samples, expected opening and closing tails,
and the presence of every numbered track.

The project's mastering targets are −22 LUFS for core tracks and −23 for
selected quieter pieces, with a −1.2 dBTP ceiling taking priority. These are
choices for the records, not universal requirements for a streaming service.
Chapter 12 explains the gain-only calculation and the float-stem null test.

Listen through complete songs and transitions after the technical checks.
Keep that judgment separate from a report that the files passed measurement.

## Carry the metadata and credits

Keep artist, album title, track titles, order, artwork and source credits in a
readable record. Embedded WAV or MP3 tags do not guarantee that a distributor's
form will populate the same fields. Inspect the submitted information directly.

The Quiet Hours' listening MP3s carry instrument attribution in their comment
metadata. The music page and downloadable credits also identify Salamander
Grand Piano and VSCO Community Edition, their creators, source links, licenses
and preparation changes. Retain that information when copying the recordings.

Treat distributor delivery as a separate action from website publishing.
Consult the destination's current requirements for formats, metadata,
identifiers and replacement recordings. Keep any submission records with the
release package; the website's players are not evidence of store availability.

## Build the publication from one manuscript

The repository's `publication/` directory contains the article Markdown, book
chapters, styles, player code and build scripts. Build the EPUB first, then
build HTML from the same sources:

```bash
python -m pip install -r publication/requirements.txt
python publication/build_epub.py
python publication/build.py
```

The EPUB builder packages the chapters and checks its internal links. The HTML
builder produces the article pages, book reader, complete book page and music
page. A code-only checkout has no album audio: a full website bundle also needs
the separately hosted media under `publication/downloads/`.

The music page has a custom player for each album. Each uses one audio element,
a track list, transport controls and a seek slider. Playback advances through
the track list and stops after the last track. A document-level play handler
pauses other audio, including the standalone sketches. Without JavaScript,
the track links still lead directly to the MP3s.

## Verify a publication before and after deployment

Validate local links, expected chapter order, player track counts and referenced
media before publishing. Generate a file manifest and compare its hashes with
the staged bundle. Keep a private backup and switch the complete directory into
place only after those checks pass.

After deployment, check the public HTML, EPUB, scripts and styles against the
local build. Exercise the player in a browser: select tracks, seek, change
albums and reach the end of a sequence. Check a narrow viewport and keyboard
controls. Version changed asset URLs when caches could otherwise retain an
incompatible stylesheet or script.

The result is a record and a publication that can be inspected at each stage:
score, performance, mix, delivery and the actual files listeners receive.
