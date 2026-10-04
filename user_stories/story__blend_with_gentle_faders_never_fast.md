<!-- pdd-story-prompts: prompts/hands/live_kit_Python.prompt, prompts/brain/plan_mix_build_Python.prompt -->
<!-- pdd-story-status: accepted-2026-10-03 -->
<!-- pdd-story-intent: docs/intents/intent__blend-with-gentle-faders-no-agent-moves-them-fas-b18167b2.md -->

# User Story: Blend with gentle faders, and no agent can move them fast

## Story

Every blend into a different song moves the faders gently: a steady ramp
over at least 16 counts, fading in as well as out. claw-dj **enforces** this
in code, so no AI agent or harness can move a fader fast by accident. That
covers one-shot mix builds, hand-written live scripts, and any model.

A rule that only lives in instructions was not enough. Agents kept slamming
the channel faders over 4-8 counts, often on an S-curve that is steepest in
the middle.

## Acceptance criteria (observable)

1. **Gentle ramp.** In a blend into a different song, each channel fader
   (and the crossfader) moves on a steady, linear ramp over at least 16
   counts. A fader never sweeps faster than full travel per 16 counts. A
   half sweep may take 8. An S-curve is measured at its steepest point.
2. **In and out.** The rule covers the incoming fader rising as well as the
   outgoing fader falling.
3. **Explicit exemptions only.** Only these may move faster, and only when
   marked in the code or plan:
   - beat juggling;
   - deliberate on-beat cuts;
   - platter, echo and filter exits;
   - same-song handoffs of identical material (short 4-beat blends were
     approved there).

   An exemption is never the default, and its reason is written next to it.
4. **Builder floor.** The plan builder never schedules a blend shorter than
   16 counts. That holds even when a "quick" or "short" brief or a per-pair
   override asks for less. Quick briefs shorten rides and cuts, not blends.
5. **Runner refuses.** The live runner refuses a plan with a too-short blend
   before anything plays, naming each offending transition.
6. **Toolkit refuses.** The live toolkit refuses a too-fast channel-fader
   move before writing anything to Mixxx. Its shared moves (riff crossover,
   fade out) stay gentle even when their EQ part is short.
7. **Tests guard it.** Tests fail when the builder, runner or toolkit would
   produce a fast fader move.

## Examples

1. **Mo Money → Ariana, 2026-10-03.** The 8-beat blend raised her fader in
   4 counts and dropped the album's in 4, on an S-curve. Ernest: "TOO FAST".
   Now each fader ramps linearly over 16 counts, overlapping, with the bass
   swapped halfway.
2. **Chorus bass layers under Ariana.** The instrumental's bass eases in and
   out over 16 counts, not 8.
3. **A "quick" mix brief.** It used to scale 16-beat blends to 12. Now they
   stay at 16, and only the rides get shorter.
4. **Exempt and kept.** The Diddy-verse and trumpet-solo skips are same-song
   handoffs with 4-beat blends, and keep them. So does the approved unison
   entry of Mo Money over her reprise (same riff), marked with its reason.

## Must not

- Do not move a fader in a blend into a different song faster than full
  travel per 16 counts.
- Do not lower the minimum or add an exemption to get a script running.
  Lengthen the move instead.
- Do not leave the rule only in instructions. The code must refuse.

## Source

Ernest, 2026-10-03, watching Mixxx during the Mo Money → Ariana blend:

> you're blending the channel faders moving them in which should be a gentle
> blend TOO FAST. I've noticed this when asking for any one shot build the
> mix. You and any other AI agent, AI harness has to STOP doing that. Stop
> moving it that fast. blend it in gently. is this a rule or a user story
> already? Is it just not being enforced at all?

Earlier the same day: "you and other AI agents with claw-dj do blend out, or
move that vertical knob down TOO FAST."
