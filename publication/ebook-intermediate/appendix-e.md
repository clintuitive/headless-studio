# Appendix E — Free Resources

Everything this book's records were built with that you can download
today for nothing. URLs current as of publication; the names are stable
enough to search if a link drifts.

## Sound sources

- **GeneralUser GS** — the General MIDI soundfont behind Chapter 2.
  Free, ~30 MB, all 128 programs at consistent levels.
  → schristiancollins.com/generaluser.php
- **FluidR3 GM** — the soundfont Ubuntu ships as the
  `fluid-soundfont-gm` package; a fine alternative.
- **TimGM6mb** — a tiny (6 MB) GM soundfont, handy for tests and CI; it
  ships *inside* the `pretty_midi` pip package, which makes it the most
  reliably downloadable soundfont in existence:
  ```python
  import pretty_midi, os, shutil
  shutil.copy(os.path.join(os.path.dirname(pretty_midi.__file__),
                           "TimGM6mb.sf2"), "TimGM6mb.sf2")
  ```

## Amps and effects

- **Neural Amp Modeler (plugin)** — the free VST3/AU that plays `.nam`
  amp captures. → neuralampmodeler.com
- **Tone Hunt** — the community library of thousands of free `.nam`
  captures; the AC15, Twin, and dUg bass preamp on this book's records
  all came from community captures. → tonehunt.org
- **Voxengo free impulse responses** — the measured rooms behind
  Chapter 11, including the drum room on the darkwave record.
  → voxengo.com (Impulse Modeler / free IR pack)
- **OpenAIR** — academic library of measured spaces (churches,
  concert halls) under permissive licenses; the featured-space IRs.

## Drum machines

- **smpldsnds/drum-machines** — one-shots from dozens of hardware boxes;
  all eight machines in Chapter 6 (LinnDrum LM-2, Drumtraks, TR-808,
  CR-8000, RZ-1, MFB-512, MR10, SK-1) came from here.
  → github.com/smpldsnds/drum-machines

## Python libraries

| library | role in the book |
|---|---|
| `pedalboard` | plugin hosting + built-in effects (Spotify, ch. 3–4, 10–11) |
| `pyfluidsynth` | the FluidSynth binding (ch. 2) |
| `numpy` | audio *is* NumPy arrays, everywhere |
| `scipy` | WAV I/O, filters, `sawtooth` (ch. 5–7) |
| `mido` | MIDI messages for instrument plugins (ch. 3–4) |
| `mutagen` | release metadata tagging (ch. 15) |
| `pretty_midi` | mostly for the soundfont in its pocket (tests) |

## Instruments already on your Mac

- **The GarageBand factory library** — the several-GB sampler content
  Chapter 5 unlocks (Steinway, Mellotron, kits, guitars). Free with
  every Mac; extraction is Chapter 5, format is Appendix B, license
  note in both.
- **Ample Bass P Lite II** — the free deep-sampled P-bass rescued in
  Chapter 4. → amplesound.net (free line)

## The companion code

The complete working pipeline — every loader, the band scripts, the
album engine, the audition harnesses, the stems exporter with its null
test, and reproducible teaching examples — is free
and open on GitHub, MIT-licensed:
**github.com/clintuitive/headless-studio**. Code only: the sound sources
above are downloads, not redistributables, which is why this appendix
exists.

If a link here has rotted: the search terms in bold survive, and the
book's errata page lives at the blog —
**clintjohnson.cloud/headless-studio**.
