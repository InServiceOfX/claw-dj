<!-- pdd-story-status: implemented-awaiting-listening-acceptance-2026-09-04 -->
<!-- pdd-story-areas: mix_profiles, build_mix_plan, plan_mix_build, run_mix_plan, backbeat, crossfader -->
<!-- pdd-story-prompts: prompts/brain/plan_mix_build_Python.prompt -->
<!-- pdd-story-dev-units: plan_mix_build_Python.prompt -->

# User Story: Blend tracks gradually and seamlessly, not with a sudden fader switch

## Story

As a DJ/listener, I want the crossfader to move at an appropriately slow,
musical pace so one track blends almost or perfectly seamlessly into the next,
with both the beats and backbeats staying together throughout the overlap.
Quick switchovers should be deliberate DJ-performance choices, not the normal
result of asking for a smooth blend.

**Backbeat** means the snare/clap accents, often on counts 2 and 4 in 4/4.
Good alignment and a pleasing fade are separate acceptance requirements;
improving one must not sacrifice the other.

## Acceptance criteria

1. **Gradual by default.** Ordinary smooth blends in Club set, Mix to listen
   and other applicable formats transfer the audible mix progressively,
   without a sudden switch, last-moment rush or abrupt loss of the outgoing
   track. Selecting Club set alone does not authorize quick cuts everywhere.
2. **Use the time the music needs.** Choose the overlap from the actual
   phrases, available intro/outro material, vocals and tempo. The acceptable
   32-beat example below is not a maximum: longer blends are welcome when
   compatible material supports them. A 64-beat blend is an audition candidate,
   not a universal minimum or a reason to run past a verse/end-of-track.
   Respect certified cues, deliberate tempo holds and protected verse landings.
3. **Keep the groove through the whole fade.** Beats and backbeats remain
   aligned while both tracks are audible. Do not bypass alignment checks or
   claim that a known clash is resolved merely because the fade is gradual.
   Preserve the requested fade under the zero-handoff rule below while
   reporting unresolved alignment for review. Bass/EQ/volume
   changes must support the smooth transfer, not introduce an audible lurch.
4. **Do not confuse uncertainty with a musical cut.** An inconclusive
   entrance check is distinct from a confirmed mismatch. Routine uncertainty
   retains the full planned gradual fade, labelled unverified, including
   missing drums, weak local evidence and lost evidence after a verified
   entrance. Never turn those states into an automatic two-beat handoff. If a
   real playback fault or insufficient remaining audio
   prevents the intended blend, identify that exception honestly and choose
   the least disruptive feasible exit; do not label it a successful smooth
   blend. Confirm mismatch from repeated coherent measurements or confident
   incompatible rhythm evidence, not one noisy observation. Even a measured
   mismatch retains the planned fade, honestly labelled, while verification
   continues: **zero automatic evidence-triggered short handoffs per mix**.
   “At most once” is not a budget for the runner to spend; a rare deliberate
   short handoff requires an explicit request. Never extend, reverse or snap
   the fader. Corroborate
   sudden stopped/near-end readings before treating them as an emergency.
5. **Quick cuts are explicit exceptions.** Allow abrupt switchovers for
   intentionally selected DJ cuts, scratches, beat drops or comparable
   performance passages. Preserve those effects when deliberately requested;
   do not impose them on ordinary blends. “DJ tracks” is provisionally
   interpreted this way, not inferred just from “DJ” in an artist/title.
6. **Measure the audible transfer, not just the slider.** Acceptance includes
   the effective crossfader curve, channel levels and EQ: visually slow
   movement alone is not proof of a seamless audible blend. Report planned
   versus executed duration in beats/seconds and why a blend was shortened.
7. **Listen to repeated transitions.** Audition Wall to Wall → On Fire →
   Who Shot Ya as a continuous chain, then representative later transitions.
   The default blends should sound gradual while retaining the perceived
   backbeat improvement. Check intentional cuts separately. Logs and tests
   support, but do not replace, Ernest's listening acceptance.

## Listening examples supplied by Ernest

- **Too abrupt:** Wall to Wall → On Fire, 94 BPM, labelled `smooth_blend`
  and “long crossfade with light EQ,” but executed a two-beat landing after
  “entrance timing could not be verified.” Two beats at that tempo is about
  **1.28 seconds**. Ernest reports the backbeat matching seems fine, but this
  and many other fades are too fast. This is a regression example, not an
  accepted artistic-cut exception.
- **Acceptable, with room to be slower:** On Fire → Who Shot Ya, 95 BPM,
  positions reported verified at +15 ms, 32-beat landing (about **20.21
  seconds**). Ernest heard good backbeat matching and an okay smooth fade;
  he explicitly welcomes taking longer when musically appropriate.
- **Also regressions, not authorized cuts:** Rock the Boat → Just a Friend
  → 2 Bricks; Part 2 & Bump Heads → Barry White → Biggie → Rick Ross →
  Keith Murray; and Benjamins → Put It On Me → Jealous → Superwoman pt.2.
  Weak or unavailable local evidence reduced these to two beats. The policy
  applies to filter-sweep `key_clash_blend` as well as `smooth_blend`.
- **Mid-blend regression:** 2 Bricks → Stunt 101 was initially verified
  (−50 ms), then repeatedly rushed on lost evidence. The old “32-beat landing”
  log concealed the actual shortening. Lost evidence must keep the fade;
  report the executed duration. A 71-second 2 Bricks file cued at 38.38s
  still has a genuine finite-audio limit, which must be handled explicitly.

## Implemented scope and remaining acceptance

Approved implementation: `docs/intents/request__implement_gradual_blend_recovery.md`,
corrected by `docs/intents/request__zero_automatic_short_handoffs.md`.
Build and live execution share gradual fade policy v3. Old two-/eight-beat
fallback metadata cannot override it. Planned 32/64-beat overlaps remain intact under
uncertainty; explicit DJ cuts remain distinct. Entrance verification uses a
short observation window and retains the last cue-preserving timed launch
when inconclusive. Tests measure fader duration, continuity, direction and
telemetry, including stale transport readings and half/double-time families.
An independent agent reviewed the changes and challenged the tests.

No universal longer duration was imposed, and the current artifact and live
Mixxx session were not changed. An already-running CLI must be restarted by
the user to load the corrected Python. Old cached short-handoff previews require
re-preparation before rendering. Synthetic tests and source previews cannot
prove the effective Mixxx crossfader curve or audible seamlessness; criterion
7 remains a live listening gate, not a claimed completed acceptance test.

Source: [Ernest's request and console excerpts](../docs/intents/request__gradual_seamless_crossfader_blends.md).
Related: [backbeat matching](story__when_i_blend_i_match_the_snare_not_just_the_beat.md)
and [listening-oriented DJ blends](story__when_i_mix_for_a_restaurant_bar_or_lounge_i_play_most_of_each_song_with_dj_blends.md).
