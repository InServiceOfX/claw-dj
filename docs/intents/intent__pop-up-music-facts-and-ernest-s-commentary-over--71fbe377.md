# Intent: Pop-up music facts and Ernest's commentary over the stream and videos

<!-- pdd-intent-id: pop-up-music-facts-and-ernest-s-commentary-over--71fbe377 -->
<!-- pdd-intent-sha256: 71fbe3777efb4901993f55c59446c0a4720e8fd3ea5f79a46ee79c2ebf935b32 -->

## Record

- Intent ID: `pop-up-music-facts-and-ernest-s-commentary-over--71fbe377`
- Kind: `add`
- Supersedes: none
- Approval ID: `pop-up-music-facts-and-ernest-s-commentary-over--71fbe377`
- Source kind: `inline`
- Source reference: `not applicable`
- Request SHA-256: `71fbe3777efb4901993f55c59446c0a4720e8fd3ea5f79a46ee79c2ebf935b32`
- Project scope: `repository`
- Adoption scenario: `existing_pdd_change`

- Technology: `not stated`

## Original Request

> I'm streaming on Twitch (https://www.twitch.tv/clawdj) with claw-dj running autonomously on the Mac mini on this network. I want an application that periodically shows, in large text, interesting music facts about the songs and artists we're playing, much like VH1's Pop-Up Video pop-ups while music videos played. I also want to write at length about my thoughts on music, pop culture, the development and progression of hip hop and R&B, and my opinions about hip hop and R&B; the application then pops up snippets of that, or a progression of text from my commentary, either quoting me directly or a distillation of my thoughts. It belongs inside claw-dj as its own mini-application. It runs while the music plays on stream, and can also be used when creating short-form content or long-form full-mix videos. When I'm the one saying something (a direct quote or a distillation of my thoughts), mark it with EY, my initials, or a very small, subtle asterisk or EY icon; otherwise the music facts the agent surfaces are the agent's own and carry no EY mark. My writing is public, so it lives in the repo in a subdirectory named for me, so other people can add their own commentary under their own names in the future.

## Must Stay Unchanged

- None stated.

## Examples

- It runs while the music plays on stream, and can also be used when creating short-form content or long-form full-mix videos.
- When I'm the one saying something (a direct quote or a distillation of my thoughts), mark it with EY, my initials, or a very small, subtle asterisk or EY icon; otherwise the music facts the agent surfaces are the agent's own and carry no EY mark.

## Candidate Product Areas

- The single plan-aware entry to mix composition, callable from both the GUI and the CLI so the two cannot produce different artifacts.
- Sparse override layer at plans/<slug>/transitions.json, stored as a list KEYED BY THE (from_track_id, to_track_id) PAIR rather than by...
- GET lists this plan's activations joined to their library bunches plus each one's span in the current order.
- THE HARNESS-FACING CONTRACT.
