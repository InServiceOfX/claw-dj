<!-- pdd-story-prompts: prompts/brain/plan_mix_build_Python.prompt, prompts/brain/showcase_moves_Python.prompt, prompts/hands/audition_transition_Python.prompt, prompts/hands/live_kit_Python.prompt -->
<!-- pdd-story-status: accepted-2026-10-17 -->
<!-- pdd-story-intent: docs/intents/intent__no-abrupt-cut-offs-echo-cut-and-brake-exits-only-22291d42.md -->

# User Story: Never end a song with an abrupt cut-off

## Story

As the DJ, I never hear a song cut off sharply. That means no echo-out exit,
hard or on-beat cut, half-time-or-cut, brake, spinback or filter-drop exit.
The only exception is when I deliberately ask for one, very rarely and with a
lot of care: to highlight a drop or for pitch-play work. When two songs won't
blend, claw-dj and its agents re-pair or reorder them so a gentle blend works.
They never cut one song short to escape the pairing.

## Acceptance criteria (observable)

1. **No cut-off by default.** A built plan contains no abrupt exit unless my
   DJ note asks for it with my reason, `abrupt_reason="..."`. That transition
   records the reason (`abrupt_exit.reason`).
2. **The planner never chooses one.** An extreme tempo gap gets a gentle
   tempo-gap blend, not a hard cut. A model's choreography never adds an
   echo-out or filter-drop exit. A noted `exit_style=echo_out` or
   `filter_drop`, or `entry_style=beat_drop`, without my reason is ignored,
   and Build says so.
3. **The runner refuses.** The live runner refuses a plan with an abrupt exit
   that has no recorded reason, before anything plays, and names each
   transition. Auditioning such a transition is refused the same way.
4. **Re-pair, don't cut.** When a pair doesn't blend (tempo gap, syncopation,
   grid drift), the fix is a different pairing or order with a blend of at
   least 16 counts. A cut is never the fix. A ballad meeting a ballad on
   melodic harmony is a good gentle answer.
5. **Unchanged exemptions.** Beat juggling, and same-song handoffs of
   identical material (short 4-beat blends), keep their existing exemptions
   from the gentle-faders story.
6. **Tests guard it.** Tests fail when Build schedules an unrequested abrupt
   exit, when the showcase offers one, or when the runner or audition would
   play one.

## Examples

1. **Sade "Turn My Back" → Justin Bieber "Sorry", 2026-10-17.** That blend
   didn't fit, so an agent replaced it with a 4-beat echo-out. I heard Sade cut
   off sharply: "202 is terrible." The fix is re-pairing. The initial proposed
   neighbors were superseded: Ernest approved **Majid Jordan "Pacifico" →
   "Sorry" → The-Dream "Ghetto"** on 2026-10-22, with "Sorry" starting at
   0:00 and never next to SWV. Follow the current plan's effective DJ notes;
   this dated example is not a universal ordering rule for other mixes.
2. **Maxwell "Whenever Wherever Whatever" → Anita Baker "Caught Up In The
   Rapture".** Approved: "both are ballads and intersect during purely
   melodic harmonies, no percussion to match." A gentle answer where a cut
   might have been tempting.
3. **A deliberate drop.** A DJ note
   `exit_style=filter_drop abrupt_reason="highlight the drop"` still gives a
   filter-drop exit, with the reason on the transition.
4. **Majid Jordan "A Place Like This" → Joe "More & More".** The 2026-10-15
   echo-out repair is rejected. The pair still needs a re-pair.

## Must not

- Do not end a song with an echo-out, cut, brake, spinback or filter drop
  that I didn't ask for.
- Do not use an abrupt exit to escape a pair that won't blend.
- Do not let a model or the planner choose one.
- Do not write `abrupt_reason` on my behalf. Only my own request supplies it.

## Source

Ernest, 2026-10-17, after auditioning an agent's echo-out "fix" for
transition 202 of RnB-cooldown-mix-vol-02:

> 202 is terrible. I hate the sharp cut off of Sade's song. DO NOT DO THAT.
> Does it warrant a user story or do we have a user story that we do not do
> abrupt cut offs like that except very rarely and with a lot of care when we
> want to highlight a drop or do some interesting pitch play work? DO NOT DO
> THAT AGAIN Icannot emphasize. Please.

Then: "go ahead with those user story amends".
