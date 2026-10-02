<!-- pdd-story-prompts: prompts/brain/plan_mix_build_Python.prompt -->
<!-- pdd-story-status: accepted-2026-10-02 -->
<!-- pdd-story-intent: docs/intents/intent__live-mini-experiments-on-a-section-of-a-mix-48d34784.md -->

# User Story: Live mini-experiments on a section of a mix

## Story

As a DJ working with any AI agent harness (Claude Code, Codex, Grok Build,
Hermes Agent, or another), I can try out a small piece of a mix **live in
Mixxx** without listening to or rebuilding the whole mix, so I find out
quickly whether an idea is good.

A piece can be:

- a transition between two songs,
- a cued section of a song looped over and over, or
- a new blend or layer on 2, 3 or more decks.

## Acceptance criteria (observable)

1. **Small and live.** The agent sets the experiment up from the mix plan's
   original sources and plays only that piece in Mixxx. I don't sit through
   the rest of the mix.
2. **Iterate cheaply.** Between rounds we change one or two things (for
   example shift one deck by a beat to fix the backbeat, change pitch or EQ,
   move an entry point) and play it again without starting over.
3. **The full mix is untouched.** The plan, its notes and its built artifact
   do not change while I experiment, and do not change when I drop an
   experiment.
4. **Keep what works.** When I like an experiment, its decisions are carried
   into the full mix with all the songs, as an explicit step.
5. **No rendered audio.** Experiments play the original files live through
   Mixxx controls. No WAV or other rendered audio file is made to audition an
   idea.
6. **Failure is a result.** Trying, judging and dropping an idea is cheap, and
   a dropped idea leaves nothing behind in the full mix.

## Must not

- Do not render audio to audition an experiment.
- Do not rebuild, replay or modify the full mix to test one piece of it.
- Do not fold an experiment into the full mix without the DJ saying so.

## Example

The Diana Ross *I'm Coming Out* over Ariana Grande plus the Mo Money
instrumental audition (2026-10-01) played three decks live for about a
minute. The first run showed the backbeat one count off. The next run fixed
it with a one-beat Ariana shift, and the idea was then dropped because it
still did not sound good. The full mix was never touched. The same one-beat
correction was later carried into the full mix's Ariana-over-instrumental
layer, which is criterion 4 in action.

## Source

Ernest, 2026-10-01, after that audition:

> I'd encourage these one off auditions in the future for things we want to
> experiment with. Because now we found out if an idea is good or not! ...
> while working with a LLM whether in claude code, codex, grok build, hermes
> agent, etc., we want to be able to "test" and "experiment" on smaller
> sections of a mix, whether it's a transition, or cueing a part of a song to
> repeat and loop over and over, or to create a new blend and new sound,
> whether 2 or 3 or more decks, without having for the user to listen and sit
> through entire mix and reconstructing entire mix. Our claw-dj "harness"
> should allow for this "mini" experimentation, work and iterative with the
> LLM or AI agent, AI harness on smaller parts of the mix which if successful
> will be incorporated into the larger mix with all the songs.

Earlier the same day:

> let's not rely on ffmpeg at all; we want to mix live. no rendered WAV. use
> mixxx or tools, functions using mixxx and mix live.
