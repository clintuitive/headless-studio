# Chapter 8 — The Song Is a Data Structure

The instrument chapters describe several ways to render a note. This chapter
brings those sounds into an arrangement, starting with
structure. The claim of this chapter is that a song's *arrangement* — who
plays when, what patterns they play, how the sections stack up — is best
written not as code that *does* things but as **data that means things**:
plain lists and dictionaries that a simple loop walks through. The payoff
lands immediately and compounds all book long: data can be diffed,
swept in a loop, and eventually generated — and "double the quiet section
and cut verse two" becomes a two-line edit you can hear ninety seconds
later.

## Three layers, three lifetimes

Arrangement information changes at three different speeds, so we keep it
in three separate structures:

- **Harmony** — what chords the song uses (decided once per song)
- **Patterns** — what a player does within one bar (changes per section)
- **Form** — the order of sections (changes when the song changes shape)

### Harmony: the chord table

```python
CHORDS = [
    {"name": "Am", "bass": 45, "gtr": [57, 60, 64, 69], "pad": [57, 64]},
    {"name": "F",  "bass": 41, "gtr": [53, 57, 60, 65], "pad": [53, 60]},
    {"name": "G",  "bass": 43, "gtr": [55, 59, 62, 67], "pad": [55, 62]},
    {"name": "Em", "bass": 40, "gtr": [52, 55, 59, 64], "pad": [52, 59]},
]
```

(The numbers are MIDI note numbers — piano keys, where 60 is middle C and
each step is one semitone.) Look at what this table encodes beyond "which
chords": **a voicing per instrument**. The guitar's four notes sit
mid-neck, where a guitarist's hand would actually be. The pad gets only
two notes — root and fifth — because a pad playing the chord's third
muddies the guitar playing the same third. The bass gets one note. All
your knowledge about each instrument's register lives *here*, written
once.

The rest of the song asks only `CHORDS[bar_number % 4]` — the `%`
(remainder) makes the four chords cycle forever, bar after bar.

### Patterns: one bar of behavior

```python
# Verse bass: relentless eighth notes on the chord's root note, with a
# little pickup into the next bar.  Each entry is:
#   (position_in_bar_in_beats, length_in_beats, pitch_offset_in_semitones)
BASS_DRIVE = []
for i in range(7):
    BASS_DRIVE.append((i * 0.5, 0.5, 0))     # seven eighth-notes on the root
BASS_DRIVE.append((3.5, 0.5, 7))             # last eighth jumps up a fifth

# Chorus bass: bouncing through the octave — the hook.
BASS_HOOK = [
    (0.0, 0.5, 0), (0.5, 0.5, 0), (1.0, 0.5, 12), (1.5, 0.5, 0),
    (2.0, 0.5, 10), (2.5, 0.5, 0), (3.0, 0.5, 7), (3.5, 0.5, 5),
]
```

The crucial trick is that patterns are **relative**: they say "the chord's
bass note, plus 7 semitones," never "the note A." One pattern therefore
works over all four chords, and the verse writes itself for as many bars
as needed. The guitar's pattern is even simpler — a list of *indexes* into
the chord's guitar voicing (`[0, 2, 1, 2, 3, 2, 1, 2]` — a picking
pattern across the chord shape).

Longer thoughts — the lead melody — add a bar coordinate:
`(bar, beat, length, note)`. At that scale the data *is* the melody,
visible and editable note by note. When the melody's third phrase felt
crowded, the fix was deleting one tuple.

### Form: the movements list

```python
movements = [
    dict(n_bars=4,  bass="hook"),                      # bass opens alone
    dict(n_bars=4,  bass="drive", drums=True),         # the machine locks in
    dict(n_bars=16, bass="drive", drums=True, arp="muted"),   # verse 1
    dict(n_bars=16, bass="hook",  drums=True, arp="open",
         pad=True, lead=True),                         # chorus 1
    dict(n_bars=8,  bass="drive", drums=True, arp="muted"),   # verse 2
    dict(n_bars=16, bass="hook",  drums=True, arp="open",
         pad=True, lead=True),                         # chorus 2
    dict(n_bars=8,  arp="open", pad=True),             # the quiet breakdown
    dict(n_bars=16, bass="hook",  drums=True, arp="open",
         pad=True, lead=True),                         # final chorus
    dict(n_bars=8,  bass="drive", drums=True),         # outro
]
```

Each movement is a **cast list**: which band members play, and in what
mode. The values pull double duty as pattern selectors — `bass="drive"`
versus `bass="hook"`, guitar `"muted"` versus `"open"` — so a section's
character and its lineup live in one dictionary.

Read the list top to bottom and you can *see* the song: the lone bass
intro, the drum machine entering, verse/chorus alternation, the breakdown
where the rhythm section drops out and the guitar hangs in the reverb,
the full final statement, the outro that returns to the opening image.
Arrangement craft — tension, release, symmetry — has become list-shaped,
and that's the chapter's whole point: in a DAW, structure is implicit in a
thousand clip positions; here it's explicit in twenty lines you can read.

## The walker

The code that turns the data into Chapter 2 note events is deliberately
boring:

```python
bar_cursor = 0                             # running position, in bars
for m in movements:
    for bar_i in range(m["n_bars"]):
        bar_time = (bar_cursor + bar_i) * BAR          # seconds
        chord = CHORDS[bar_i % 4]
        write_bar(bar_time, chord,
                  bass=m.get("bass"),           # .get returns None/False
                  drums=m.get("drums", False),  # if the key is absent —
                  arp=m.get("arp", False),      # absent means "sits out"
                  pad=m.get("pad", False))
    if m.get("lead"):
        write_lead(bar_cursor, m["n_bars"])
    bar_cursor += m["n_bars"]
```

`write_bar` dispatches to small per-instrument functions that walk a
pattern and emit notes. Every interesting decision already happened — in
the data. When something's wrong with the song, you debug a list, not a
timeline.

One deliberate subtlety: `bar_cursor` accumulates as it goes, so **no
section knows its absolute position in the song**. That's what makes
structural surgery free: insert a movement, delete one, or duplicate the
breakdown with `movements[6:7] * 2` (Python list-repeat), and everything
downstream re-flows automatically.

## When one song becomes twelve

At album scale, the movements list graduates into a *named template*. The
synth album's writer names its section types and lets each song's spec
pick a sequence:

```python
sections = ["intro", "A", "A2", "breath", "B", "A3",
            "breath", "B2", "A4", "outro"]
```

A shared vocabulary can be useful, but each track needs a reason for its
sequence, length and density. The album scores keep individual forms and
themes. Chapter 13 develops this distinction between reusing an engine and
repeating a song. Treat this template as an example to depart from.

## Practical notes

- **Comments are part of the notation.** `# breakdown: drums and bass
  cut, the guitar hangs in the reverb` — the *why* layer. A change to the
  movements list plus its commit message is a complete record of a
  structural decision, which is Chapter 1's producer's-notebook promise
  coming true.
- **Resist formalizing.** It's tempting to turn movements into a class
  with declared fields and validation. Every song I've written wanted one
  field the previous song didn't have. Dictionaries with `.get()` defaults
  absorb that evolution for free — the walker just ignores keys it doesn't
  know. Let structure emerge from use.
- **Tempo changes?** This book's songs run a fixed tempo (true to the
  genre). If you need a slowdown, the change is contained: `BAR` stops
  being a constant and becomes a lookup from bar number to seconds — and
  all event starts, note ends and duration calculations must use that mapping.

The arrangement specifies the musical positions. Chapter 9 turns them into
performed note boundaries, keeping related gestures together and deciding
which parts should provide a stable rhythmic reference.

---

*Next — Chapter 9: Performance Timing and a Stable Beat.*
