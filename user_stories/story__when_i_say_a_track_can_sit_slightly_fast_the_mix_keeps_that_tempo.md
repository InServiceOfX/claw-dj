<!-- pdd-story-status: drafted-2026-08-28 -->
<!-- pdd-story-areas: mix_directives, build_mix_plan, run_mix_plan -->
<!-- pdd-story-prompts: plan_mix_build_Python.prompt -->
<!-- pdd-story-dev-units: plan_mix_build_Python.prompt -->

# User Story: A track can be kept slightly faster than native if the ear says it still sounds like the record

## Story

As a DJ, I can tell the agent that a specific song **can sit slightly
faster** than its analyzed BPM — and **stay there**. The mix plan must
honor that note: beat-match into the faster neighbor, then **do not**
glide the rate back down to the original tempo.

This is not a global "speed everything up" rule. Most records sound like a
fast-forwarded chipmunk if you leave them 8–12% fast. Only when I (or a
locked note) say this song can take the lift does the plan keep the blend
tempo.

## Acceptance criteria (observable)

1. **Notes are the source.** A human or agent dj_note can record that a
   track may play above native BPM and must not be settled back. The
   token is `keep_blend_tempo`. An explicit `play_bpm=<n>` still wins if
   both are present.
2. **The plan aligns.** Incoming syncs to the outgoing deck (or to a
   stated `play_bpm`). After the transition, Mixxx does **not** print
   "rate settled to native" and does **not** ramp back to the analyzed
   BPM for that track.
3. **Chipmunk is in scope.** The note is only legal when that record
   still sounds like itself at the lift — typically a rap/vocal that
   already has energy, not a sung hook that would squeak. The agent must
   not apply `keep_blend_tempo` to every tempo gap.
4. **Example (50centgunitera).** N.W.A. *Straight Outta Compton* (~103)
   into G-Unit *Straight Outta Southside* (native ~92). Southside can
   stay at Compton's tempo for the interpolation handoff. Pinning
   `play_bpm=92.22` (native hold) was the wrong default for this pair.

## Must not

- Do not keep blend tempo on a track that would sound chipmunked.
- Do not invent `keep_blend_tempo` from a BPM gap alone.
- Do not settle back "a little" (`settle_bpm`) when the note says keep
  the blend tempo — that is a different, partial-lift tool.

## Source

Ernest, 2026-08-28, after hearing Southside drop back to 92 under Compton:

> The user can prompt such that the AI agent would record 'notes' about
> how to play a song, which include whether a track can be played
> slightly faster than the default BPM, tempo, and doesn't have to be
> brought back gradually to its original BPM tempo and the mix plan
> should align strongly to these suggestions. For now it includes
> whether a track can be played and kept at a slightly higher tempo,
> BPM, without then sounding like a fastforwarded chipmunk.
>
> Straight Outta Southside needs to blend with the tempo of Straight
> Outta Compton better, slightly make it faster and keep it that same
> tempo. It's fine for this song.
