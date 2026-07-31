# Hip-hop / R&B guided DJ format

Status: version 1, practical/adaptive. It is derived from—but is not the
same certification claim as—the practicing-DJ rules in
`HIP_HOP_RNB_8_BAR.md`.

**Marked experimental 2026-07-31** (`brain/dj_formats.py`, `status:
"experimental"`) — still shown in the GUI, but visibly labeled "not ready."
Ear tests through this date preferred plain `none` + a free-text mix brief
over this format. Not archived (unlike the strict format above) because
it's still the active development target — see `PROGRESS.md` for the
comparison finding and next steps.

## What remains hard

1. Every incoming song starts on beat 1 of a four-beat bar.
2. Every transition begins on a verified bar downbeat.
3. The plan records whether each transition used an expert 8-bar recipe or
   a guided fallback. Fallbacks are never presented as expert-certified.

## Preferred path

When Song A has a verified 8-bar chorus/hook and Song B has a verified
8-bar intro, use one of the strict format's recipes:

- `chorus_to_intro`
- `acapella_hook_swap`
- `intro_loop_under_entry`

Those transitions are marked `format_compliance=expert_recipe`.

## Guided fallback

When the library lacks enough structural evidence:

- cue Song B at an analyzed bar downbeat;
- anchor Song A at the next detected chorus downbeat when one exists,
  otherwise at the next 32-beat phrase boundary;
- retain the compatibility-selected transition technique so large tempo/key
  gaps do not get forced through an unsafe full sync;
- mark the transition `format_compliance=guided_fallback` and persist the
  reason in the plan.

This fallback follows the universal “everything enters on the 1” advice but
does not claim that an unverified cue is an 8-bar intro or that an inferred
boundary is an 8-bar chorus.

## Relationship to strict mode

Use `hiphop-rnb-8bar` for a small, auditioned, human-certified set. Use
`hiphop-rnb-guided` for ordinary library playlists where musical structure
metadata is incomplete. Never weaken the strict format to make an arbitrary
playlist pass.
