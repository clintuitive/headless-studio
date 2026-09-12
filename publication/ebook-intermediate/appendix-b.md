# Appendix B — The EXS Format Reference

The reverse-engineered layout of Apple's EXS24 sampler instrument format
(`.exs` files), as used by Chapter 5's parser and extractor. This is, to
my knowledge, the only written reference for these offsets; it was
recovered by differential hex-dumping and validated against the entire
GarageBand factory library.

## File structure

An `.exs` file is a flat sequence of chunks. No file header — the first
chunk starts at byte 0. All integers are little-endian.

### Chunk header (84 bytes)

| offset | size | field |
|---|---|---|
| 0 | 4 | flags. Chunk **kind** is in the low nibble of byte 3 (`data[pos+3] & 0x0F`); high bits flag name presence |
| 4 | 4 | payload size in bytes (u32) — the header's 84 bytes not included |
| 8 | 4 | chunk id (u32) |
| 12 | 4 | padding |
| 16 | 4 | magic: ASCII `TBOS` |
| 20 | 64 | chunk name: ASCII, NUL-terminated, zero-padded |

The next chunk begins at `pos + 84 + size`. **Parse defensively:** some
factory files carry padding between chunks; if the magic isn't at the
expected position, advance one byte at a time until `TBOS` reappears.

### Chunk kinds

| kind | meaning |
|---|---|
| `0x01` | zone — one playable region |
| `0x02` | group — articulation/bank name (zones reference by index, in file order) |
| `0x03` | sample — audio file reference (indexed in file order) |

### Zone payload (kind `0x01`, ≥ 96 bytes)

| payload offset | size | field |
|---|---|---|
| 1 | 1 | root note (MIDI number — the pitch the sample was recorded at) |
| 6 | 1 | key range low |
| 7 | 1 | key range high |
| 9 | 1 | velocity range low |
| 10 | 1 | velocity range high |
| 12 | 4 | sample start, **in sample frames**, into the referenced audio file (u32) |
| 16 | 4 | sample end, in frames (u32) |
| 88 | 4 | group index (u32) |
| 92 | 4 | sample index (u32) |

The frame-exact start/end offsets are the treasure: they let an extractor
cut individual hits out of consolidated `.caf` containers with no
transient detection and no guesswork.

Zones can also carry sustain-loop metadata (not used by this book's
decay-and-release playback model) — relevant if you extend the sampler to
looped synth-style patches.

## Field-tested wrinkles

**Name truncation.** The 64-byte name field truncates long sample
filenames to the pattern `prefix#HASH.ext`. When the literal name isn't
found on disk, fuzzy-match the prefix:
`find <sample root> -name "prefix*.ext"` — unique in practice across the
factory library.

**Locating the audio.** Search in this order: (1) the instrument's own
directory; (2) the mirrored path with `Sampler Instruments` replaced by
`EXS Factory Samples` (Logic's layout); (3) a filesystem search of the
factory-samples root.

**Where the files live.**

```text
/Library/Application Support/GarageBand/Instrument Library/Sampler/
├── Sampler Instruments/       .exs files
└── Sampler Files/             audio (often *_consolidated.caf)

/Library/Application Support/Logic/
├── Sampler Instruments/
└── EXS Factory Samples/
```

## The extraction manifest

Chapter 5's extractor writes each zone's metadata plus its extracted
filename to `manifest.json` — that file, not the WAV names, is the
interface every downstream consumer (the `ExsSampler`) reads:

```json
{"name": "Kick soft", "root": 36, "keylo": 36, "keyhi": 36,
 "vello": 1, "velhi": 79, "start": 0, "end": 44100,
 "group": "hits", "file": "note036_v001-079_000.wav"}
```

## Legal reminder

Apple's current [GarageBand license, sections 2G and 2I](https://www.apple.com/legal/sla/docs/GarageBand.pdf)
permits certain original soundtrack uses, but also restricts standalone
extraction, use outside the software's intended context, redistribution and
reverse engineering, subject to the exceptions in those terms and applicable
law. Permission to distribute a finished composition is not blanket permission
to extract factory samples for another renderer. This format walkthrough does
not establish that permission. Use the parser with files you created or have
explicit permission to parse and extract; no Apple software or sample content
is included in this repository.
