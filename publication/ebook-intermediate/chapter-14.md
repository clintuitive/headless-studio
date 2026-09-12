# Chapter 14 — AI Collaboration and an Honest Production Record

Python rendering and AI involvement describe different parts of a process.
A deterministic script can play a melody written with AI assistance. Calling
that recording “not AI” merely because its final waveform came from NumPy
would leave out part of its authorship history.

For the rebuilt albums, the sound engine uses synthesis and sample playback.
No external generative-audio service or generated vocal was used. AI assistance
did contribute code, new composition, arrangement and production decisions.
Clint supplied the album concepts, critique and selected audition directions.
The production record should say both things plainly.

## Separate the kinds of contribution

A useful project note answers four different questions:

- Who supplied the concept and musical direction?
- How were notes, forms and arrangements written?
- How was the audio performed or synthesized?
- How were editing, effects and delivery carried out?

Slow Rain illustrates why one label is insufficient. Its original composition
was retained, while the new performance and mix followed a selected audition.
Most other tracks were reimagined. The same renderer can handle both cases,
but their histories differ.

Keep prompts and decisions where they help explain a revision. More useful
than a claim that “AI made the album” is a concrete record: Broadcast's damage
was preferred; its drum timing was distracting; drums were separated from the
warp; heavily damaged tracks were balanced with gentler, more ambient pieces.
That is an actionable account of collaboration.

## Disclosure follows the destination's questions

Read a distributor's current wording rather than answering from a personal
definition of AI music. DistroKid's AI credits guidance includes AI-composed
music and arrangements, not just directly generated audio. Its current upload
form distinguishes music, vocals and lyrics, and says AI used only for mixing
or mastering does not count for that question.

The rebuilt release drafts disclose AI involvement in the music. They do not
claim generated vocals. This is a description of the work and the current
form, not a rule guaranteed to remain unchanged for every distributor.

Reference: [DistroKid — What Are AI Credits?](https://support.distrokid.com/hc/en-us/articles/50784235803411-What-Are-AI-Credits).

## Keep source permissions distinct from code licensing

Publishing a renderer under an open-source license does not grant permission
to redistribute every sample or plugin it can load. Keep factory libraries,
third-party drum samples and licensed instrument files outside the public
repository. Document what a reader needs to obtain independently and retain
the applicable license information with the local assets.

The self-contained teaching sketches provide a useful alternative: readers
can render a complete example with synthesized tones and noise before
configuring any external library. They demonstrate the pipeline without
pretending that a clean clone includes the album's sampled instruments.

## Use AI where its output can be inspected

A generated score is easier to revise when its motifs and form are explicit.
A generated DSP function is easier to trust when a test checks the failure it
might introduce: wrong sample rate, unsigned PCM offset, mismatched note-offs,
clipping, or incomplete output. Neither a confident explanation nor a passing
render proves musical quality.

Listen to the result, compare it with the intent, and keep the production
history accurate. That makes both the record and its teaching material easier
to understand and improve.
