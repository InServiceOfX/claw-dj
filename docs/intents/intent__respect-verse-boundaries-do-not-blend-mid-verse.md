# Intent: Respect verse start and stop; do not blend mid-verse

<!-- pdd-intent-id: respect-verse-boundaries-do-not-blend-mid-verse -->
<!-- pdd-intent-kind: add -->

## Record

- Kind: `add` (story drafted; `brain.verse` / `clawdj verse cue` implemented 2026-08-28)
- Source: inline chat 2026-08-28 after listening to 50centgunitera On Fire
- Planner note: this is cue + ride policy (build_mix_plan / lyric_timeline),
  not a new Mixxx gesture.

## Original Request

> I notice that you, upon an initial mix, tend to blend while someone's
> verse has already started, when we really want to respect the start
> and stop of an artist's verse, whether singing or rapping. If you
> agree it should be a user story, let's make it so and then create the
> subsequent, derived code/Rust function or Python function.
>
> same with On Fire. start much earlier, even the beginning, from 0:00
> is iconic so it's ok to start from the beginning to blend.

## Meaning

- Do not cue a track after a verse has already started.
- Do not fade out while a verse is still going.
- Starting from 0:00 is legal and preferred when the intro is iconic.
- An opening chorus is not a verse landing (Best Friend “If I was your
  best friend” is the hook; the verse is “First we get the talkin”).
- Encode this as a user story plus a Rust/Python function the planner
  uses on automatic cues (human `trust_cue_seconds` still wins).

## Story

`user_stories/story__when_i_mix_i_respect_the_start_and_stop_of_a_verse.md`
