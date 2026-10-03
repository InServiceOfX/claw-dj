<!-- pdd-story-prompts: prompts/brain/plan_mix_build_Python.prompt -->
<!-- pdd-story-status: accepted-2026-10-03 -->
<!-- pdd-story-intent: docs/intents/intent__loop-one-bar-live-then-blend-or-drop-into-the-ne-4cbf3ed6.md -->

# User Story: Loop one bar live, then blend or drop into the next song

## Story

As a DJ, I can have claw-dj loop a **single bar** (or a short section) of
the playing record **live in Mixxx** as an effect, let it repeat a few
times, then go **straight into another song**: a blend, or a drop on the
next downbeat.

## Acceptance criteria (observable)

1. **A bar, on the bar.** The loop starts and ends on that record's bar
   lines (its own downbeats, which may not be grid beat 0 of the file).
2. **A few passes, not a drone.** Usually 2–3 passes, about 4 at most so
   it does not get annoying. This is a taste default, not a hard limit:
   a human note can ask for more.
3. **Straight into the next song.** After the last pass, the next song
   comes in immediately, as a blend or a drop on the next downbeat, with
   the backbeat lined up. No dead air, no stray partial bar.
4. **Tunable when the wrap sounds off.** Live-drummed records do not keep
   a perfect grid, so the loop's start and end can be nudged by fractions
   of a beat until the wrap back to count 1 sounds right.
5. **Live only.** The loop runs on the original file in Mixxx. No rendered
   audio.
6. **Remembered per song.** DJ notes can record which bar loops well on a
   given song and how many passes worked, so later mixes can reuse it.

## Example

Diana Ross, *I'm Coming Out*: one bar of the section *Mo Money Mo
Problems* samples (2:55.10–2:57.30, grid beats 318–322 at 109.25 BPM),
3 passes. Ernest, 2026-10-03: "this is fire." The 8-bar loop of the same
section sounded slightly off at the wrap, which is why criterion 4
exists.

## Source

Ernest, 2026-10-03, after the live experiment
(`experiment_ross_sample_loop.py --bars 1 --repeats 3`):

> As a DJ effect to then be able to take this loop repeat 2 or 3 at most 4
> times (no hard upper limit but don't want to be annoying) and then mix or
> blend into another song or deck live would be fire. ... the human DJ would
> like claw-dj to loop a single bar live, and then immediately blend into
> another song or drop at the right time.
