# Intent: Instrumental / no-vocal tracks are not bound by verse boundaries

<!-- pdd-intent-kind: add -->

## Record

- Kind: `add` (story drafted; `has_vocal_verses` implemented 2026-08-28)
- Source: inline chat 2026-08-28 after verse-boundary enforcement

## Original Request

> For a song that is all instrumental or has no vocals (maybe this
> should be a user story?), there are no verses or "verse boundaries"
> so the "restrictions" don't apply to that track.

## Meaning

- Verse start/stop rules apply only when someone is rapping or singing.
- Instrumental-only (and other no-vocal) tracks may be cut on any phrase.
- Do not treat inherited vocal lyrics on an instrumental as verses.

## Story

`user_stories/story__when_a_track_has_no_vocals_verse_boundaries_do_not_apply.md`
