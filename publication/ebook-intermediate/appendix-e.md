# Appendix E — Sources and Further Reading

The repository is the runnable companion to this book:
[clintuitive/headless-studio](https://github.com/clintuitive/headless-studio).
Its MIT licence covers the code and documentation only — it has nothing to say
about separately installed software or anybody else's recordings.

## Start without external instruments

Everything here runs from a clean checkout with NumPy and SciPy:

- `scripts/generate_portable_samples.py` builds Afterimage, Open Window and
  Night Transit from synthesized tones and noise.
- `scripts/generate_sampler_demo.py` builds six sample zones, a JSON manifest,
  provenance information and a short performance of it.
- `scripts/tests/` and `.github/workflows/core.yml` define the core checks —
  worth reading if you want to know what the project actually guarantees.

## Album sources

- [Salamander Grand Piano](https://github.com/sfzinstruments/SalamanderGrandPiano):
  recordings by Alexander Holm, mapping by kinwie, retuning by Markus Fiedler,
  under [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/).
- [VSCO Community Edition](https://github.com/sgossner/VSCO-2-CE): recordings
  by Sam Gossner/Versilian Studios and Simon Dalzell/Ivy Audio, sample cutting
  by Elan Hickler/Soundemote, under CC0.
- `scripts/prepare_open_instruments.py` pins the source revisions and defines
  every preparation step; `THIRD_PARTY.md` records the credits and the scope of
  each dependency.

## Optional audio tools

- [FluidSynth](https://www.fluidsynth.org/) and
  [pyfluidsynth](https://github.com/nwhitehead/pyfluidsynth) give you the
  SoundFont path from Chapter 2. The native library, the binding and the
  SoundFont itself are three separate things to obtain.
- [Pedalboard](https://github.com/spotify/pedalboard) is the plugin host from
  Chapter 3. Its documentation covers supported formats and runtime behaviour;
  each plugin's own documentation covers its requirements.
- [FFmpeg](https://ffmpeg.org/documentation.html) handles the encoding and
  loudness measurement used in the delivery stage.
- [NumPy](https://numpy.org/doc/) and [SciPy](https://docs.scipy.org/doc/scipy/)
  document the arrays, filters, resampling and convolution that hold the whole
  studio together. If you read only one set of docs from this list, read these.

## Publication and listening

The [Headless Studio site](https://clintjohnson.cloud/headless-studio/) hosts
the articles, the HTML book, the EPUB and the album players. The recordings on
the site are kept separate from the public code checkout, so a clone gets you
the studio rather than the records. If you share performances built on the
credited sources, carry their attribution along with them.
