# Intent: Vocals-only and instrumental-only stems are layered

<!-- pdd-intent-id: this-should-probably-be-a-user-story-because-we--f05faa07 -->
<!-- pdd-intent-sha256: f05faa07574321425e3fa999d58e009699332e213b216a3f0a7c032711d16817 -->

## Record

- Intent ID: `this-should-probably-be-a-user-story-because-we--f05faa07`
- Kind: `add` (story drafted; `entry_style=vocal_over_bed` implemented 2026-08-19)
- Source: inline chat 2026-08-19 after listening to 50centgunitera
- Request SHA-256: `f05faa07574321425e3fa999d58e009699332e213b216a3f0a7c032711d16817`
- Planner note: keyword match suggested api_plan_duplicate / arrange.js /
  bunch_store. Those are the wrong product areas. This is identification
  + mix order + overlapping ride (catalog / mix_order_brief /
  build_mix_plan / plan_mix_build).

## Original Request

> This should probably be a user story because we want this to be
> enforced: The user should be able to choose vocals only and instrument
> only tracks which are accurately identified as such. The vocals only
> tracks are meant to be mixed at the same time, matching beat with an
> instrumental only track. In no way should a vocal only track be placed
> in full, unless we are showcasing a certain part of it as an acapella
> break, we usually want to either blend it into another song with an
> interesting beat or instrumental break, or play the vocal only track
> over another interesting instrumental only track, not necessary the
> same track that it came from (because we could just play the original
> song anyway). I just heard the Lloyd Banks tracks and how you mixed it
> even with the vocal only, it's pretty good, since Lloyd Banks is a
> good rapper even just with acapella. But that's more of an exception
> than the norm

## Meaning (awaiting approval)

- User-chosen vocals-only and instrumental-only stems, identified
  accurately.
- Default: layer the vocal on a beat-matched instrumental bed (or a
  short break in another full song).
- Do not sequence an acapella as a full solo slot.
- Matching same-song instrumental is allowed, not preferred.
- Lloyd Banks dry acapella holding attention was tried and sounded bad;
  that exception is revoked. Canonical accepted layer: Get Up (Acapella)
  over Outta Control Instrumental, bed stays live.

## Story

`user_stories/story__when_i_add_vocals_only_and_instrumental_only_tracks_i_layer_them_i_do_not_play_the_acapella_in_full.md`
