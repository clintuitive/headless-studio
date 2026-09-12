# Appendix C — VST3 Preset Anatomy

The byte-level reference behind Chapter 3's `load_nam` — for when you
need to set plugin state that isn't exposed as a parameter, and the
save-a-preset-once workflow isn't enough because you want to swap files
programmatically.

## The `.vstpreset` container

What `plugin.preset_data` hands you is a VST3 preset: a container with a
header, one or more state chunks, and a trailing index.

| offset | size | field |
|---|---|---|
| 0 | 40 | header (magic `VST3`, version, the plugin's class ID) |
| 40 | 8 | offset of the chunk **index** (i64) — everything between 48 and this offset is chunk data |
| 48 | … | chunk data — for a simple plugin, one `Comp` (component state) chunk |
| *index offset* | … | the index: ASCII `List`, a chunk count (i32), then one 20-byte entry per chunk |

Each 20-byte index entry: a 4-byte chunk ID (`Comp` = the plugin's own
serialized state; `Cont` = controller/UI state), then offset (i64) and
size (i64).

**The rule that bites:** if you change the length of a chunk, you must
rebuild the index — every offset and size must match reality, or the
plugin silently ignores the entire preset. No error. Default sound. When
byte surgery "doesn't work," check the bookkeeping before the splice.

## Inside the component chunk

The layout belongs to whatever framework the plugin was built with. The
two you'll actually meet:

### iPlug2 plugins (Neural Amp Modeler and family)

A marker string, then length-prefixed fields, then parameter values:

```text
###PluginName###            ASCII marker
[i32 length][version string]
[i32 length][file path 1]        <- NAM: the .nam model path
[i32 length][file path 2]        <- NAM: the impulse-response path
[parameter doubles...]
```

"Length-prefixed" = a 4-byte count followed by exactly that many bytes of
text. To swap a file: find the marker, skip fields to the one you want,
splice in your path with a corrected length prefix, rebuild the index.
Chapter 3's `load_nam` is the complete worked implementation.

### JUCE plugins (a large fraction of everything else)

JUCE's convention serializes state as an XML document. Search the
component chunk for `<?xml` — if found, the state is readable text, often
self-describing (`<PARAM id="filePath" value="/old/path"/>`), and you can
edit it as a string, re-encode, and rebuild the index. Considerably
friendlier than offsets.

## Cracking an unknown plugin

The universal method, no documentation required:

1. Load the plugin, save `bytes(plugin.preset_data)` to a file.
2. Change *exactly one thing* (via `plugin.show_editor()` — usually the
   file picker) and save again.
3. Diff the two files byte by byte.

The differing region *is* the field you care about, and the bytes
immediately around it reveal the convention — a length prefix that
changed with the path length, an XML attribute, a fixed-width slot. A
third save with a path of a very different length disambiguates the
length-prefix question immediately.

```python
a = open("preset_ac15.bin", "rb").read()
b = open("preset_twin.bin", "rb").read()
for i, (x, y) in enumerate(zip(a, b)):
    if x != y:
        print(f"first difference at byte {i}")
        print(a[max(0, i-24):i+40])
        print(b[max(0, i-24):i+40])
        break
```

## When not to bother

If the file choice never changes at render time, skip all of this: the
save-once workflow (Chapter 3, "the easy way") — configure in the
editor, persist `preset_data` to disk, reload the bytes forever — is
robust, format-agnostic, and survives plugin updates better than offset
arithmetic. Byte surgery is for the for-loop: rendering the same
performance through six amps, which is where this studio's whole argument
lives.
