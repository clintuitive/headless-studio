# Chapter 15 — Delivery, Publication and Reproducible Files

Somewhere on your drive is a file called `final-final.wav`, and you no longer
know what's in it. Everyone has one. This chapter is about making sure it isn't
the one you release.

A delivery package connects a finished mix to the files that actually reach
listeners, in a way that survives you forgetting everything. Format, duration,
source identity, hash — kept alongside the track list and the credits, so the
question "which version is this?" always has an answer that doesn't depend on
memory or filenames.

## Assemble the release folder

The album renderer writes numbered 24-bit stereo WAV masters at 44.1 kHz,
listening MP3s and session manifests. Keep the artwork and track metadata in
the release folder too — they're part of the release, and they go missing
first. And keep comparison renders in separate directories, so a later
experiment can't quietly overwrite the master you chose.

A manifest records each file's identity. A SHA-256 digest changes if a single
byte changes, which makes it perfect for answering "is this the file I
exported?" and useless for answering "does this sound better?" Use it for the
first question only.

```python
from pathlib import Path
import hashlib

path = Path('Tracks/albums/The Quiet Hours/Masters/02 Slow Rain.wav')
digest = hashlib.sha256(path.read_bytes()).hexdigest()
print(path.name, digest)
```

For larger files, read in chunks rather than holding the whole thing in memory
— a full album of 24-bit masters will make a laptop regret this loop. And
compute the hashes *after* the final metadata and encoding steps, because
writing a tag changes the bytes and therefore the digest, which is a
five-minute confusion you only need to have once.

## Check the actual delivery files

Measure the encoded WAV and MP3 themselves. Do not infer their behaviour from
the working float mix, however confident you feel about it — lossy encoding
moves peaks, as Chapter 12 explained, and the file people download is the only
file that matters.

Confirm channel count, sample rate, duration, finite samples, the expected
opening and closing tails, and the presence of every numbered track. That last
one sounds trivial until an album ships with two copies of track 7.

The project's mastering targets are −22 LUFS for core tracks and −23 for
selected quieter pieces, with a −1.2 dBTP ceiling taking priority. Those are
choices for these records, not universal streaming requirements. Chapter 12 has
the gain-only calculation and the float-stem null test behind them.

Then listen through complete songs and transitions, after the technical checks
have passed. Keep that judgment separate in your own head from the report
saying every file measured correctly. They are different kinds of true.

## Carry the metadata and credits

Keep artist, album title, track titles, order, artwork and source credits in a
record you can actually read. Embedded WAV or MP3 tags are worth setting, but
they don't guarantee a distributor's form will pick up the same fields —
inspect what you submitted rather than assuming it inherited anything.

The Quiet Hours' listening MP3s carry instrument attribution in their comment
metadata. The music page and the downloadable credits file identify Salamander
Grand Piano and VSCO Community Edition, their creators, source links, licences
and the preparation changes I made. That information travels with the
recordings; when you copy the files somewhere, copy it too.

Treat distributor delivery as a separate action from publishing the website.
Consult the destination's current requirements for formats, metadata,
identifiers and replacement recordings, and keep any submission records with
the release package. A player on your own site is evidence of nothing about
store availability.

## Build the publication from one manuscript

The repository's `publication/` directory holds the article Markdown, the book
chapters, the styles, the player code and the build scripts. Build the EPUB
first, then the HTML from the same sources:

```bash
python -m pip install -r publication/requirements.txt
python publication/build_epub.py
python publication/build.py
```

The EPUB builder packages the chapters and checks its internal links. The HTML
builder produces the article pages, the book reader, the single-page complete
book and the music page. A code-only checkout has no album audio, so a full
website bundle also needs the separately hosted media under
`publication/downloads/`.

The music page carries a custom player for each album: one audio element, a
track list, transport controls, a seek slider. Playback advances through the
list and stops after the last track, and a document-level play handler pauses
any other audio — including the standalone sketches — so two albums can never
play over each other. Without JavaScript the track links still lead straight to
the MP3s, which is the behaviour I'd want as a visitor.

## Verify a publication before and after deployment

Before publishing, validate the local links, the chapter order, the player
track counts and the referenced media. Generate a file manifest and compare its
hashes against the staged bundle. Keep a private backup, and switch the
complete directory into place only once those checks pass — never over a live
music page with a build that's missing its recordings.

Afterwards, check the public HTML, EPUB, scripts and styles against your local
build. Then exercise the player in an actual browser: select tracks, seek,
switch albums, reach the end of a sequence. Try a narrow viewport and the
keyboard controls. And version any changed asset URLs, or a returning visitor's
cache will happily serve them last month's stylesheet with this month's markup.

That's the whole pipeline. Score, performance, mix, delivery, publication —
every stage inspectable, every file identifiable, and the only irreproducible
part of it the one that should be: deciding what sounds good.

---

*Next — the appendices: setup, the manifest reference, VST3 preset anatomy, GM
program numbers, and where to read further.*
