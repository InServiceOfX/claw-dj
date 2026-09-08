# Intent: Ok great! Amend the user story please, also just remind the user that...

<!-- pdd-intent-id: ok-great-amend-the-user-story-please-also-just-r-34e4a77f -->
<!-- pdd-intent-sha256: 34e4a77faa00c290fca5bf9040a7483c20242cc55531eaec3392774fcfc87668 -->

## Record

- Intent ID: `ok-great-amend-the-user-story-please-also-just-r-34e4a77f`
- Kind: `add`
- Supersedes: none
- Approval ID: `ok-great-amend-the-user-story-please-also-just-r-34e4a77f`
- Source kind: `file`
- Source reference: `docs/intents/request__backbeat_matching_from_build.md`
- Request SHA-256: `34e4a77faa00c290fca5bf9040a7483c20242cc55531eaec3392774fcfc87668`
- Project scope: `repository`
- Adoption scenario: `existing_pdd_change`

- Technology: `python, rust`

## Original Request

> Ok great! Amend the user story please, also just remind the user that beat back is what we've been calling "snare" or clap. (because I'll probably keep saying it but we want to start saying backbeat (see i need to get used to it). For the recommendations, can youj go ahead and implement all of this? Go ahead and implement the necessary PYthon and Rust code too (Rust preferred, but if necessary, use Python). (for 2, 3 for analysis of rhytm by section and filtering). Basically implement all those 4 recommendations and we'll give it a try, because we want to get the backbeat matching working from the beginning, especially for those DJ format options, like here: http://127.0.0.1:8787/#mix Club set
> Mix to listen like once the mix is Built that it follows backbeat matching from the beginning

## Must Stay Unchanged

- None stated.

## Examples

- None stated.

## Candidate Product Areas

- The single plan-aware entry to mix composition, callable from both the GUI and the CLI so the two cannot produce different artifacts.
- Pure function over a dict; DOES NOT import build_mix_plan, so it stays cheap to test and free of the 1895-line module.
- THE HARNESS-FACING CONTRACT.
- GET returns PlanMeta plus rev plus staleness with an ETag BUILT FROM THE REV AND THE SLUG, NEVER FROM display_name: display_name is free-...
- Promotes the legacy singletons (playlist_selection.json, playlist.json, mix_plan.json) into plan #1 with origin='migrated' and status='wip'.
