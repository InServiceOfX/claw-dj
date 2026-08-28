<!-- pdd-story-status: drafted-2026-08-28 -->
<!-- pdd-story-areas: verse, stems, build_mix_plan -->
<!-- pdd-story-prompts: plan_mix_build_Python.prompt -->
<!-- pdd-story-dev-units: plan_mix_build_Python.prompt -->

# User Story: Instrumental / no-vocal tracks are not bound by verse boundaries

## Story

As a DJ, when a track is **all instrumental** or otherwise has **no
vocals**, there is no artist verse to respect. The mix may enter or
leave that track on any phrase that sounds good.

Verse-boundary rules (`respect_verse_entry` / `respect_verse_exit`) exist
for a rapper or singer whose verse is in progress. They must **not**
rewrite cues or stretch rides on:

- instrumental-only versions (`(Instrumental)`, ` - Instrumental`, etc.)
- other no-vocal beds (looped instrumental sections used as a bed)

Those stems often inherit the *vocal* track's synced lyrics (On Fire
Instrumental carrying Banks's LRC). Treating that as a verse map is a
false restriction.

A vocals-only acapella **does** have verses; that is a different object.

## Acceptance criteria (observable)

1. `classify_stem` already identifies instrumental-only tracks.
2. `has_vocal_verses` is false for those titles/paths.
3. Automatic `phrase_body` on an instrumental is **not** rewritten by
   verse_guard, even if lyric segments exist.
4. Automatic rides on an instrumental are **not** extended to a "verse
   end."
5. `audit_mix_plan` does not report instrumental tracks as verse cuts.
6. Full mixes and acapellas still get verse rules.

## Must not

- Do not skip verse rules on a full mix just because a stretch is
  instrumental.
- Do not skip verse rules on an acapella.
- Do not invent a new stem class; reuse vocals_only / instrumental_only /
  full_mix.

## Source

Ernest, 2026-08-28, after verse-boundary enforcement:

> For a song that is all instrumental or has no vocals (maybe this
> should be a user story?), there are no verses or "verse boundaries"
> so the "restrictions" don't apply to that track.
