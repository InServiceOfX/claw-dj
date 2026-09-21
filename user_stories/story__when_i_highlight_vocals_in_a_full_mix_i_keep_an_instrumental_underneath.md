<!-- pdd-story-status: specified-2026-09-20; existing Astra offline example audited; general live implementation pending -->
<!-- pdd-story-areas: build_mix_plan, plan_mix_build, mix_directives, playback, mix_preview -->
<!-- pdd-story-prompts: plan_mix_build_Python.prompt -->
<!-- pdd-story-dev-units: plan_mix_build_Python.prompt -->

# User Story: Highlight vocals in a full mix over a continuous instrumental

## Story

As a DJ, I want to highlight a vocal performance from a record that already
contains its own beat, while a compatible instrumental plays underneath on
another deck throughout the chosen body. I want a fuller, consistent backing
and clear words, with one continuous groove and matched backbeats.

The foreground need not be vocals-only. I should not have to find an acapella
or extract stems. The system keeps the foreground classified as a full mix,
then balances its existing backing against the support instrumental.

## Canonical example

Ernest, 2026-09-20: play **WHO SHOT YA — 50 Cent · 24 Shots**, highlighting
50 Cent and Tony Yayo's performances, with **Who_Shot_Ya (Instrumental) —
The_Notorious_BIG · Who_Shot_Ya VLS** on another deck throughout the body.
Strengthen the instrumental while keeping those voices in front.

The 24 Shots recording has a separate mandatory source boundary: **exclude
everything at or after 1:32 (92 seconds)**. Complete its fade before then.
Covering the bad tail with the good instrumental does not satisfy this rule.

## Acceptance criteria

1. **Separate roles and explicit pairing.** The plan identifies the foreground
   recording, supporting recording, approved source regions, and overlap span.
   The support role does not turn either record into a different catalog type.
   The user can choose the bed or accept a compatible proposed bed.
2. **Support throughout the requested body.** Both records play concurrently
   throughout that span, allowing smooth entrance/exit envelopes. A short
   introductory overlap, a bed used only at handoffs, or playing the entire
   instrumental afterward does not fulfill the request.
3. **Backbeat and pattern continuity.** Match tempo, backbeat identity, and
   musical phrase. Check drift across the body and each loop wrap. Equal BPM
   labels, aligned generic beat ticks, or an unchecked sync flag are insufficient.
   “Match the snare” remains an accepted user synonym for backbeat matching.
4. **Clear foreground with complementary backing.** Balance channel levels,
   EQ, and optional verified filters so voices remain intelligible and the bed
   supplies useful weight. Check doubled drums, phase cancellation, and mono
   compatibility. EQ is not represented as perfect vocal isolation. The system
   must not simply sum two complete recordings at full gain.
5. **The same instrumental is appropriate when reinforcing that beat.** Do not
   reject this matching bed because the acapella story sometimes prefers a
   different song. Other musically compatible beds remain possible when the
   intended result is a different arrangement.
6. **Whole musical loops.** If looping is needed, use a verified clean phrase
   with no unwanted voice and a clean wrap. Avoid rolling/slip behavior that
   later jumps to unrelated content. Do not assume every song fits 32 beats.
7. **Deck ownership survives handoffs.** Keep the support deck reserved and
   audible for its full span. Three simultaneous sources require three live
   decks or an explicitly labeled offline render. A two-deck configuration may
   use a brief instrumental bridge, then load the freed foreground deck; it
   must not claim an impossible three-source overlap or load over the live bed.
8. **Source exclusions outrank musical convenience.** Cues, loops, fades, and
   support layers all respect each recording's mandatory excluded regions and
   end. Playback-rate changes do not move a source-time boundary.
9. **Explicit completion and cleanup.** The plan says whether the bed continues
   into the next vocal or fades out. Restore the layer's owned controls; stop
   every owned deck on cancellation/failure so a hidden bed cannot keep playing.
10. **Reviewable and portable.** Preview depicts simultaneous foreground and
    support, with source spans and handoff behavior. Save durable intent in
    notes/prompts, and store generated media and audition evidence outside the
    repo. Numerical measurements do not replace a listening comparison.

## Relationship to existing stories

- [Vocals-only and instrumental-only layering](story__when_i_add_vocals_only_and_instrumental_only_tracks_i_layer_them_i_do_not_play_the_acapella_in_full.md)
  covers genuine dry vocals and their prohibition on accidental solo playback.
  Its classification, exceptions, and accepted Get Up / Outta Control pairing
  stay intact.
- [Same-beat instrumental bridges](story__when_i_mix_the_same_beat_or_sample_lineage_i_use_the_instrumental_as_a_short_bridge.md)
  covers short exposed bridges. Its short-duration preference does not limit
  an instrumental that remains underneath a featured vocal throughout its body.
- [Backbeat matching](story__when_i_blend_i_match_the_snare_not_just_the_beat.md)
  governs rhythmic identity in this longer overlap too.
- [Mandatory source ends](story__mandatory_source_end_survives_every_mix.md)
  applies to every source used in the layer.

## Current evidence and remaining implementation

The Astra offline render already has matching instrumental support throughout
source 0–91.95s of 50 Cent. Independent reconstruction exactly matched its
saved premaster over a 70-second interior window. This demonstrates existing
layer coverage, not listening acceptance or a general live-deck implementation.

The live runner's existing `vocal_over_bed` routine supplies part of the
lifecycle, but explicit full-mix pairing, persistent three-deck ownership,
calibrated foreground/support EQ, backbeat handling in that branch, continuous
drift monitoring, preview, and cleanup still need implementation and tests.
See [research and Mixxx design](../docs/FULL_MIX_INSTRUMENTAL_LAYERING.md).
