# Chapter 14 — AI Collaboration and a Clear Production Record

Two questions get tangled together constantly, so let's untangle them before
anything else. *How was the waveform produced?* and *who made the decisions?*
are different questions with different answers. A deterministic Python script
can render a melody that a person wrote by hand, or one that arrived with AI
assistance, and the audio file looks identical either way. The rendering method
describes the machinery. It says nothing at all about authorship.

So here's the record for this project, stated plainly. The Headless Studio uses
synthesis and sample playback. Its albums involved AI assistance in code,
composition, arrangement and production, with me — Clint Johnson — providing
the concepts, the direction and the listening decisions. No external
generative-audio service was used, and there are no generated vocals on these
recordings.

That paragraph took a while to get right, and getting it right matters more
than any of the technique in this chapter.

## Record concrete contributions

A useful production record names things: the concept, the writing, the
performance sources, the mix decisions. What it avoids is compressing all of
that into a single vague label, in either direction — "made with AI" and "made
by a human" are both close to content-free when a record involved a dozen
different kinds of work.

Write down which ideas were accepted and where they show up in the score or the
processing. Sign-Off's separation of steady drum attacks from unstable pitched
material, for instance, is a direction with a visible implementation: the drums
bypass the timing warp, in a specific function, on a specific line. The Quiet
Hours uses phrase-level piano timing and selective string support. Those are
choices you can discuss, hear, disagree with and edit — which is exactly what a
vague label prevents.

Keep whatever working notes help the project. But a published tutorial should
teach the resulting technique, not depend on a transcript of how anyone arrived
at it. Nobody needs the conversation; they need the routing decision.

## Inspect generated work at the right level

Reviewing generated work well is a skill, and it mostly comes down to choosing
the altitude.

A generated score is easy to evaluate when motifs and forms are explicit — the
data structures of Chapter 8 are a review surface as much as an authoring
surface. An audio function is easy to evaluate when its input and output units
are stated. Review at those levels, before asking a complete album render to
surface every mistake for you. It will surface some of them, forty minutes at a
time.

Tests catch wrong sample rates, unsigned PCM offsets, mismatched note-offs,
clipping, truncated output. Listening catches a melody that goes nowhere and a
room return that swallows the lead. Neither one substitutes for the other, and
a project that only does the first will pass every check while making music
nobody wants to hear twice.

When you compare alternatives, hold the performed sources fixed and match the
listening levels — the same discipline as every other comparison in this book.
Then write feedback that points at a stage: a drum attack feels late, a chord
release cuts short, a string entrance covers the melody. Each of those names
something that can be changed and re-evaluated. "It doesn't feel right" names
nothing.

## Keep code and source permissions separate

An open-source renderer does not relicense the samples or plugins it loads. It
can't; those permissions were never its to grant. Keep third-party assets
outside the public repository, hold on to their source, licence and preparation
records locally, and carry the required credits into published audio metadata
and onto the listening page.

The portable sketches and the six-zone sampler demo exist partly for this
reason: a reader can start with sounds generated entirely by the code, with no
licence to read and nothing to obtain. The album instruments then add
separately obtained sources with their own notices. Those are explicit
dependencies you go and satisfy — not hidden contents of a repository clone,
and not a surprise for anyone who forks the project.

## Answer the destination's questions accurately

Distributors and publishers ask about this now, and the questions change.
Use your actual production record when you fill the forms in. Read what's being
asked this time rather than what was asked last year, and distinguish
contributions to music, lyrics, vocals and production, since a form frequently
wants them separated. Then keep what you submitted with the delivery package,
so it can be checked later against what you said elsewhere.

A clear account of the work makes both the record and its teaching material
easier to trust. It also stops an explanation of the renderer from quietly
turning into a broader claim about authorship — which is an easy thing to do by
accident, and a hard thing to walk back.

---

*Next — Chapter 15: Delivery, Publication and Reproducible Files.*
