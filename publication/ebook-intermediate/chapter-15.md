# Chapter 15 — Delivery, Replacement Releases, and Publishing the Work

Delivery begins with an identified recording. A filename alone is not enough:
`02 Slow Rain.wav` can refer to several performances and mixes. Keep the audio
hash, render manifest and source snapshot with the delivery folder so that
“the version we uploaded” has one unambiguous meaning.

## Prepare a reviewable package

The rebuilt albums use stereo 44.1 kHz, 24-bit PCM WAV masters. Each album
folder also contains the original cover artwork, a numbered track list,
listening MP3s, a complete album preview, and a release manifest. The original
metadata is preserved separately as a historical reference; its old audio
measurements do not describe the replacement recordings.

Before uploading, verify the actual exported files. Check format and duration,
measure loudness and true peak, reject nonfinite or silent audio, and make sure
every track and the complete preview reaches the intended ending. The package
builder checks preview duration against the sum of the masters. This catches
an incomplete concatenation even if an encoder exits without an obvious error.

Keep technical verification separate from listening approval. A hash proves
identity. A null test checks reconstruction. Neither proves that a fade feels
right or that the album has enough contrast.

## New recordings are not minor file corrections

DistroKid offers an Audio Swap feature for eligible changes, but its policy
excludes new recordings, remixes, restructured tracks and new production.
These rebuilt albums fall outside that scope. Buying access to the feature
would not change their eligibility.

The replacement workflow therefore uses new releases with the same album
and track titles and original artwork. Treat rewritten or newly recorded
tracks as new recordings when assigning identifiers; do not reuse an old ISRC
merely to suggest continuity. Check the distributor's current rules at the
point of delivery.

Reference: [DistroKid — Audio Swap](https://support.distrokid.com/hc/en-us/articles/39612177702163-Audio-Swap-Replace-Your-Audio-Without-Losing-Anything).

## Match metadata deliberately

Review the artist association, spelling, track order, genre, language, artwork,
credits, instrumental status, AI disclosure and destination stores. Embedded
WAV tags do not automatically populate every distributor field. Inspect the
upload form itself.

For these albums, the original account records list Clintuitive and 21 stores.
The replacement submissions follow that selection and retain the original titles
and artwork. Optional paid extras are separate choices; a new upload form's
defaults are not evidence that an extra was used on the original release.

Both replacements were submitted successfully on September 12, 2026, using
the verified masters and no paid extras. DistroKid is processing them for
streaming services. The original editions no longer appear in its release
list; their store takedowns have been requested. Neither a submission
confirmation nor an empty distributor list proves a store has finished
processing the change.

A later website listening revision of The Quiet Hours uses Salamander Grand
Piano and VSCO Community Edition strings. That revision is separate from the
submitted files; distributor updates will be handled separately.
The [music page](https://clintjohnson.cloud/headless-studio/music.html) identifies the current listening edition and
provides its instrument credits.

## Retire the old editions in a controlled sequence

The intended result is one current edition of each album, without confusing
old duplicates. Where the distributor permits it, submit the replacement
before retiring the old edition. In this case, DistroKid rejected same-title
submissions until the originals were deleted. The finished masters and
metadata were prepared first, then the original takedowns were confirmed.
Fresh upload forms cleared the stale duplicate warnings in the earlier tabs,
and both replacements were accepted. This order can create a temporary gap
in store availability. Distribution and removal are separate processes; do
not claim an old edition is gone from a store just because a request was sent.

Keep a small status record with original release IDs, new release IDs when
assigned, submission state, takedown state and verified store links. Publishing
new previews on your own site does not mean the replacements are already on
Spotify. Label those two states clearly for listeners.

## Publish the code, book and listening page together

The public repository contains the renderer and the maintained intermediate
manuscript. Exclude private samples, account configuration, credentials and
multi-gigabyte sessions. Provide a short example that runs with the minimal
dependencies, then document the additional assets required by the albums.

Build the website and EPUB from the same Markdown chapters. Validate links,
chapter order and the EPUB package, then inspect the rendered pages. Building
should write a local artifact; deploying should be an explicit separate step.
A backup of the previous site makes a publishing mistake recoverable.

The listening page can offer the new recordings directly while distributor
publication is pending. Update the streaming links only when the new store
pages are verified. Clear version labels save a listener from comparing an
old stream with a new production description and wondering why they disagree.

A headless studio is most useful when it leaves an understandable trail:
a score you can revise, a performance you can reuse, a mix you can reconstruct,
and a delivery package whose identity you can prove.
