# Appendix E — Sources and Further Reading

The repository is the runnable companion to this book:
[clintuitive/headless-studio](https://github.com/clintuitive/headless-studio).
Its code license does not replace the licenses of separately installed
software or source recordings.

## Start without external instruments

- `scripts/generate_portable_samples.py` creates Afterimage, Open Window and
  Night Transit from synthesized tones and noise.
- `scripts/generate_sampler_demo.py` creates six sample zones, a JSON manifest,
  provenance information and a short performance.
- `scripts/tests/` and `.github/workflows/core.yml` define the core checks.

## Album sources

- [Salamander Grand Piano](https://github.com/sfzinstruments/SalamanderGrandPiano):
  recordings by Alexander Holm, mapping by kinwie and retuning by Markus
  Fiedler, under [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/).
- [VSCO Community Edition](https://github.com/sgossner/VSCO-2-CE): recordings by
  Sam Gossner/Versilian Studios and Simon Dalzell/Ivy Audio, sample cutting by
  Elan Hickler/Soundemote, under CC0.
- `scripts/prepare_open_instruments.py` defines the selected source revisions
  and preparation steps; `THIRD_PARTY.md` records credits and dependency scope.

## Optional audio tools

- [FluidSynth](https://www.fluidsynth.org/) and
  [pyfluidsynth](https://github.com/nwhitehead/pyfluidsynth) provide a SoundFont
  rendering path. The native library, binding and SoundFont are separate inputs.
- [Pedalboard](https://github.com/spotify/pedalboard) supplies the optional
  plugin host. Consult its documentation for supported formats and runtime
  behavior, and each plugin's documentation for its own requirements.
- [FFmpeg](https://ffmpeg.org/documentation.html) provides encoding and audio
  measurement tools used by the delivery stage.
- [NumPy](https://numpy.org/doc/) and [SciPy](https://docs.scipy.org/doc/scipy/)
  document the arrays, filters, resampling and convolution used throughout.

## Publication and listening

The [Headless Studio site](https://clintjohnson.cloud/headless-studio/) hosts
the articles, HTML book, EPUB and album players. The website recordings are
separate from the public code checkout. Preserve instrument attribution when
sharing performances that use the credited sources.
