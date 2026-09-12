# Chapter 6 — Drum Machines Are Sample Players

Every chapter so far has chased more realism. This one is about the band
member whose realism points the other way. A 1982 drum machine is, in its
entirety, a box that plays short fixed recordings at scheduled times
through volume knobs. That's not a limitation to transcend — it **is the
sound** — and it means your script can be a bit-perfect drum machine, not
an imitation of one, in about forty lines. This chapter builds that
player, adds the two refinements the real boxes had, and then spends its
back half on the decision that actually shapes your record: *which*
machine — answered with a harness that turns the choice into a science
experiment.

## Why the boxes sound like the boxes

When a LinnDrum plays hi-hat sixteenth-notes for three minutes, every
single closed hat is the *identical recording* — same chip, same output
circuit, same level. That relentless sameness is the plodding,
unmoved-machine quality that defines entire genres: the dead-eyed
post-punk beat, the immaculate 80s pop groove. If you synthesize drums,
you approximate that quality. If you "humanize" it, you *destroy* it. The
faithful implementation is the obvious one — place identical recordings
on a grid:

```python
def render_drum_bus(events, total_secs, kit):
    """events: a list of (seconds, piece_name, gain) triples.
    kit: {"kick": loaded_audio, "snare": ..., "hhc": ..., "hho": ...}"""
    n = int(total_secs * SR)
    bus = np.zeros((2, n), dtype=np.float32)     # empty stereo track
    for t, name, gain in events:
        hit = kit[name] * gain
        start = int(t * SR)
        end = min(start + len(hit), n)
        bus[:, start:end] += hit[:end - start]   # add the hit onto the grid
    return bus
```

Loading a kit takes two decisions worth defending:

```python
from music_engine.samplers import read_sample

def load_kit(folder, files, gains):
    kit = {}
    for name, fname in files.items():
        # Handles source rate, signed PCM, unsigned 8-bit and float WAV.
        d = read_sample(os.path.join(folder, fname), SR)
        if d.ndim == 2:              # stereo file?
            d = d.mean(axis=1)       # average to mono
        loudest = max(np.abs(d).max(), 1e-9)
        kit[name] = d / loudest * gains[name]    # normalize, then set level
    return kit
```

**Normalize each hit first** (divide by its own loudest sample), *then*
apply your chosen gain. One-shot collections arrive with wildly
inconsistent recording levels; normalizing means the gains express
*musical* balance and carry between machines. My standing starting point:
kick 0.95, snare 0.8, closed hat 0.4, open hat 0.45. This example averages
stereo hits to mono for deliberate later placement. Preserve stereo when
the source width matters, and check the mono fold-down for cancellation.

## Where the sounds come from

The [smpldsnds/drum-machines](https://github.com/smpldsnds/drum-machines)
repository collects freely shared recordings from dozens of hardware
boxes. The eight in my studio, each in one line:

| Machine | Character |
|---|---|
| LinnDrum LM-2 | *the* 80s pop kit — real drums in memory chips, roomy, confident |
| Sequential Drumtraks | the Linn's new-wave cousin — tighter, brighter |
| Roland TR-808 | electronic circuits, not recordings: the deep boomy kick of hip-hop |
| Roland CR-8000 | the 808's home-organ sibling — thinner, charming |
| Casio RZ-1 | mid-80s low-resolution sampler crunch |
| MFB-512 | stark German box; short punchy kicks that leave room for bass |
| Korg MR10 | scrappy cheapie, all attack |
| Casio SK-1 | the toy sampler — beautiful garbage |

Give each machine a folder with consistent file names, and "which drum
machine" becomes a single config value in your song.

## Patterns as data, and two hardware refinements

A beat, in this system, is just a function that emits `(time, piece,
gain)` triples for one bar:

```python
def linn_beat(bar_t, full):
    """Kick on 1 and 3, snare on 2 and 4, eighth-note hats."""
    B = BEAT                                   # seconds per beat
    hits = [(bar_t,         "kick",  0.50),
            (bar_t + 2 * B, "kick",  0.35),
            (bar_t + 1 * B, "snare", 0.28),
            (bar_t + 3 * B, "snare", 0.30)]
    if full:                                   # hats join in full sections
        for k in range(8):
            level = 0.17 if k % 2 == 0 else 0.12   # accent alternate hats
            hits.append((bar_t + k * B / 2, "hhc", level))
    return hits
```

Notice the *accent structure* riding in the gains — louder downbeat kicks,
alternating hat levels. That's the accent button every real box had, and
gains are exactly how the hardware did dynamics (most machines had two
levels per sound, total).

The second hardware behavior worth copying is the **hi-hat choke**. On a
real box, the open and closed hat shared one output circuit — a closed hit
*silenced* a ringing open hat. Sample playback that skips this sounds
subtly wrong to anyone who's heard the real thing, because open hats smear
across the closed hits that should have cut them off. The fix: when
placing a hat, first cut short any still-ringing hat before it (with a
5-millisecond fade at the cut so it doesn't click). The abruptness that
remains is authentic — it's what the circuit did. (Implementation in the
companion code; it's a dictionary remembering the last hat's position.)

## Choosing: the audition harness

Now the payoff section. Which machine serves *this* song? The wrong way to
decide is auditioning drum sounds in a file browser. A kick heard alone
tells you almost nothing about that kick under a bass line, through your
compressor, in your reverb — drum sounds only mean anything in context.
The 808's long boom is either the glue of the track or mud all over your
bassline, and you cannot tell which from the sample alone.

The right way costs a for-loop:

```python
for machine in ("LM-2", "Drumtraks", "TR-808", "CR-8000",
                "RZ-1", "MFB-512", "MR10", "SK-1"):
    kit = load_kit(machine_folder(machine), FILES[machine], GAINS)
    bus = render_drum_bus(song_beat_events, secs, kit)
    processed = drum_effects(bus, SR)          # the song's real drum chain
    write_wav(f"auditions/{machine}.wav", processed)
```

Render *the actual beat from your actual song*, through the song's
*actual processing*, once per machine. Eight files, seconds of compute,
then a blind back-to-back listen where the machine is the only thing
varying. That's a controlled experiment — the thing a DAW workflow only
ever approximates with a lot of clicking.

I'll repeat the result that converted me. For a darkwave song whose genre
history *demands* the LinnDrum, I ran the harness expecting a coronation.
Under the driving bassline, the Linn's roomy kick fought the low end; the
MFB-512's short thump sat perfectly in the pocket and handed the bass its
space. I shipped the German box. Heard solo I'd have picked the Linn every
time; in context it wasn't close — and by hand, I'd have stopped
auditioning long before machine number six.

## Processing the bus

The drums get the *least* processing of any band member, on purpose:

```python
drum_fx = Pedalboard([
    Compressor(threshold_db=-15, ratio=3, attack_ms=2, release_ms=60),
])
```

A **compressor** evens out volume differences — it turns down the loud
moments, squeezing the track together. (First appearance in the book, so:
`threshold` is the level where it starts working, `ratio` is how hard it
squeezes, `attack`/`release` are how fast it reacts and recovers.) Here
its job is "glue": with a quick-but-not-instant attack, the drum hits keep
their snap while the space between them tightens, and the kit gels the
way one machine through one output jack gels.

No reverb here at all — the drums' sense of *space* comes from the shared
room in Chapter 11, where they'll get the biggest share of it, because
nothing fills a room like a drum kit.

## Practical notes

- **When identical hits are wrong.** This whole chapter inverts the moment
  you want a *drummer* instead of a drum machine — identical hits on an
  acoustic kit trigger the machine-gun effect instantly. That problem was
  already solved last chapter: extract a sampled acoustic kit (GarageBand's
  kits have velocity layers and alternate takes) and let the
  `ExsSampler`'s round-robin do drummer-realism. Two drum philosophies,
  one event format.
- **Swing.** The hardware's swing knob delays every off-beat hit by a
  fixed fraction. In code, it's a transform on the event list — and note
  that it's a *pattern* change, not humanization: swung events repeat
  identically bar after bar, exactly like the hardware.
- **Layering.** A classic production move made trivial here: put the
  808's boomy kick *underneath* the LinnDrum's knock by emitting both
  machines' kicks in one event list, each at its own gain.

The rhythm section is complete. One sound remains that no sample and no
plugin provides — the analog synthesizer voices this book's synth album
is made of. Next chapter, we build sound itself from trigonometry, and
make it wobble like an old tape machine.
