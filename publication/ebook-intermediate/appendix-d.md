# Appendix D — General MIDI Program Numbers

The 128 instruments every GM soundfont provides, in the standard sixteen
families. Programs are numbered 0–127 here, matching
`fs.program_select(channel, sfid, bank, program)` — some references list
them 1–128; if your soundfont seems off by one instrument, that's why.

This is a reference for the optional FluidSynth path in Chapter 2. Neither
album uses General MIDI: Sign-Off's pitched sources are synthesized and The
Quiet Hours plays prepared Salamander and VSCO samples. But a SoundFont is the
fastest way to get a whole band making noise on a machine with nothing
installed, and it's an excellent sketchpad.

**Bolded** entries are a serviceable starting band — the handful I'd reach
for first when roughing out an arrangement this way.

| # | Piano | # | Chromatic Percussion |
|---|---|---|---|
| 0 | Acoustic Grand Piano | 8 | Celesta |
| 1 | Bright Acoustic Piano | 9 | Glockenspiel |
| 2 | Electric Grand Piano | 10 | Music Box |
| 3 | Honky-tonk Piano | 11 | Vibraphone |
| 4 | Electric Piano 1 | 12 | Marimba |
| 5 | Electric Piano 2 | 13 | Xylophone |
| 6 | Harpsichord | 14 | Tubular Bells |
| 7 | Clavinet | 15 | Dulcimer |

| # | Organ | # | Guitar |
|---|---|---|---|
| 16 | Drawbar Organ | 24 | Acoustic Guitar (nylon) |
| 17 | Percussive Organ | 25 | Acoustic Guitar (steel) |
| 18 | Rock Organ | 26 | Electric Guitar (jazz) |
| 19 | Church Organ | **27** | **Electric Guitar (clean)** |
| 20 | Reed Organ | **28** | **Electric Guitar (muted)** |
| 21 | Accordion | 29 | Overdriven Guitar |
| 22 | Harmonica | 30 | Distortion Guitar |
| 23 | Tango Accordion | 31 | Guitar Harmonics |

| # | Bass | # | Strings |
|---|---|---|---|
| 32 | Acoustic Bass | 40 | Violin |
| 33 | Electric Bass (finger) | 41 | Viola |
| **34** | **Electric Bass (pick)** | 42 | Cello |
| 35 | Fretless Bass | 43 | Contrabass |
| 36 | Slap Bass 1 | 44 | Tremolo Strings |
| 37 | Slap Bass 2 | 45 | Pizzicato Strings |
| 38 | Synth Bass 1 | 46 | Orchestral Harp |
| 39 | Synth Bass 2 | 47 | Timpani |

| # | Ensemble | # | Brass |
|---|---|---|---|
| **48** | **String Ensemble 1** | 56 | Trumpet |
| 49 | String Ensemble 2 | 57 | Trombone |
| 50 | Synth Strings 1 | 58 | Tuba |
| 51 | Synth Strings 2 | 59 | Muted Trumpet |
| 52 | Choir Aahs | 60 | French Horn |
| 53 | Voice Oohs | 61 | Brass Section |
| 54 | Synth Choir | 62 | Synth Brass 1 |
| 55 | Orchestra Hit | 63 | Synth Brass 2 |

| # | Reed | # | Pipe |
|---|---|---|---|
| 64 | Soprano Sax | 72 | Piccolo |
| 65 | Alto Sax | 73 | Flute |
| 66 | Tenor Sax | 74 | Recorder |
| 67 | Baritone Sax | 75 | Pan Flute |
| 68 | Oboe | 76 | Blown Bottle |
| 69 | English Horn | 77 | Shakuhachi |
| 70 | Bassoon | 78 | Whistle |
| 71 | Clarinet | 79 | Ocarina |

| # | Synth Lead | # | Synth Pad |
|---|---|---|---|
| 80 | Lead 1 (square) | 88 | Pad 1 (new age) |
| 81 | Lead 2 (sawtooth) | **89** | **Pad 2 (warm)** |
| 82 | Lead 3 (calliope) | 90 | Pad 3 (polysynth) |
| 83 | Lead 4 (chiff) | 91 | Pad 4 (choir) |
| 84 | Lead 5 (charang) | 92 | Pad 5 (bowed) |
| 85 | Lead 6 (voice) | 93 | Pad 6 (metallic) |
| 86 | Lead 7 (fifths) | 94 | Pad 7 (halo) |
| 87 | Lead 8 (bass+lead) | 95 | Pad 8 (sweep) |

| # | Synth Effects | # | Ethnic |
|---|---|---|---|
| 96 | FX 1 (rain) | 104 | Sitar |
| 97 | FX 2 (soundtrack) | 105 | Banjo |
| 98 | FX 3 (crystal) | 106 | Shamisen |
| 99 | FX 4 (atmosphere) | 107 | Koto |
| 100 | FX 5 (brightness) | 108 | Kalimba |
| 101 | FX 6 (goblins) | 109 | Bag pipe |
| 102 | FX 7 (echoes) | 110 | Fiddle |
| 103 | FX 8 (sci-fi) | 111 | Shanai |

| # | Percussive | # | Sound Effects |
|---|---|---|---|
| 112 | Tinkle Bell | **120** | **Guitar Fret Noise** |
| 113 | Agogo | 121 | Breath Noise |
| 114 | Steel Drums | 122 | Seashore |
| 115 | Woodblock | 123 | Bird Tweet |
| 116 | Taiko Drum | 124 | Telephone Ring |
| 117 | Melodic Tom | 125 | Helicopter |
| 118 | Synth Drum | 126 | Applause |
| 119 | Reverse Cymbal | 127 | Gunshot |

Program 120, *Guitar Fret Noise*, was the joke instrument of the sound-card
era and is quietly one of the most useful things in the list. Sprinkle a few
fret squeaks between chord changes, quiet and slightly early, and a stiff
guitar part starts sounding like hands on strings — the same idea as
Chapter 9's performance stage, applied to a sound rather than a schedule.
Programs 121–127 reward the same re-examination: *Breath Noise* is a
wind-player's byproduct waiting for exactly that trick.

**The percussion exception.** MIDI channel 10 (index 9) is traditionally
percussion: *note numbers* select drums (35/36 kicks, 38/40 snares, 42/44/46
hats…) rather than pitches, and the program number selects a *kit*. This
book's records skip GM drums entirely in favour of Chapter 6's real drum
machine samples — but the channel-10 convention explains why a melody
accidentally assigned there plays as drum hits, a rite of passage worth
having named.

**Reality check.** GM defines the *names*; your soundfont defines the
*sounds*. A well-regarded free set like GeneralUser GS holds up well across
the instruments above, but quality across the full 128 varies enormously
within any single soundfont, and two soundfonts can disagree completely about
what program 89 ought to sound like. Audition before you trust one — a
for-loop over candidate programs rendering the same phrase is Chapter 6's kit
audition, transposed, and it costs you about a minute.
