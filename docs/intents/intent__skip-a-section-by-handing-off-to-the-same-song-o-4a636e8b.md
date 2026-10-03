# Intent: Skip a section by handing off to the same song on another deck

<!-- pdd-intent-id: skip-a-section-by-handing-off-to-the-same-song-o-4a636e8b -->
<!-- pdd-intent-sha256: 4a636e8b283756063bbea53e78fa3be48ba8be26ebcdb87aa9e41dcb94706034 -->

## Record

- Intent ID: `skip-a-section-by-handing-off-to-the-same-song-o-4a636e8b`
- Kind: `add`
- Supersedes: none
- Approval ID: `skip-a-section-by-handing-off-to-the-same-song-o-4a636e8b`
- Source kind: `inline`
- Source reference: `not applicable`
- Request SHA-256: `4a636e8b283756063bbea53e78fa3be48ba8be26ebcdb87aa9e41dcb94706034`
- Project scope: `repository`
- Adoption scenario: `existing_pdd_change`

- Technology: `not stated`

## Original Request

> this sounds great! (mix_reprise_first_full.py --start-at diddy) great job! is there a way to generalize this, or make this a user story, or amend our current user story to reflect the work you did here? this just sounds great and a lot better than the skip before. (Context, 2026-10-03: skipping Diddy's verse in Mo Money Mo Problems with an instant beat jump was audible, "you can hear the skip"; Ernest suggested instead blending the current deck into another deck playing the same song cued a little before the start of Biggie's verse. It worked once the second copy was lined up at the same point of the repeated chorus, 96 beats on, measured from the vocal, and the handoff happened late in the first chorus so most of it plays, with a 4-beat blend.)

## Must Stay Unchanged

- None stated.

## Examples

- None stated.

## Candidate Product Areas

- The single plan-aware entry to mix composition, callable from both the GUI and the CLI so the two cannot produce different artifacts.
- Serves brain/web/*.js and *.css.
- The riskiest module in the feature: the only one that changes behaviour inside working, ear-tested ordering code.
- POST {track_ids[], base_rev} is a FULL REPLACEMENT, never index arithmetic, because index deltas desync the moment two writers interleave.
- Library-scoped SQLite storage appending two CREATE TABLE IF NOT EXISTS blocks (bunches, bunch_members) to brain/library_index.py's SCHEMA.
