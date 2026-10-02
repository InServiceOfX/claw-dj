# Intent: Live mini-experiments on a section of a mix

<!-- pdd-intent-id: live-mini-experiments-on-a-section-of-a-mix-48d34784 -->
<!-- pdd-intent-sha256: 48d347841a85b6ecb50cf22701901d41ec0d9ebef79ae9b673be7d5ba0cc4052 -->

## Record

- Intent ID: `live-mini-experiments-on-a-section-of-a-mix-48d34784`
- Kind: `add`
- Supersedes: none
- Approval ID: `live-mini-experiments-on-a-section-of-a-mix-48d34784`
- Source kind: `inline`
- Source reference: `not applicable`
- Request SHA-256: `48d347841a85b6ecb50cf22701901d41ec0d9ebef79ae9b673be7d5ba0cc4052`
- Project scope: `repository`
- Adoption scenario: `existing_pdd_change`

- Technology: `not stated`

## Original Request

> i like the idea of the audition and we ought to audition more experimental things in the future. currently this audition in particular doesn't sound great and might not be a good idea. In particular backbeat sync isn't there it's off by 1 beat. I'd encourage these one off auditions in the future for things we want to experiment with. Becaue now we found out if an idea is good or not! (this specific time it might not be). So how about this, I want to try, so this won't modify the full mix with all the songs, and htis should be a user story because I've been thinkign about it a long time, while working with a LLM whether in claude code, codex, grok build, hermes agent, etc., we want to be able to "test" and "experiment" on smaller sections of a mix, whether it's a transition, or cueing a part of a song to repeat and loop over and over, or to create a new blend and new sound, whether 2 or 3 or more decks, without having for the user to listen and sit through entire mix and reconstructing netire mix. Our claw-dj "harness" should allow for this "mini" expeirmentation, work and iterative with the LLM or AI agent, AI harness on smaller parts of the mix which if successful will be incorporated into the larger mix with all the songs.
>
> Earlier in the same conversation: let's not rely on ffmpeg at all; we want to mix live. no rendered WAV. use mixxx or tools, functions using mixxx and mix live.

## Must Stay Unchanged

- So how about this, I want to try, so this won't modify the full mix with all the songs, and htis should be a user story because I've been thinkign about it a long time, while working with a LLM whether in claude code, codex, grok build, hermes agent, etc., we want to be able to "test" and "experiment" on smaller sections of a mix, whether it's a transition, or cueing a part of a song to repeat and loop over and over, or to create a new blend and new sound, whether 2 or 3 or more decks, without having for the user to listen and sit through entire mix and reconstructing netire mix.

## Examples

- None stated.

## Candidate Product Areas

- THE HARNESS-FACING CONTRACT.
- The single plan-aware entry to mix composition, callable from both the GUI and the CLI so the two cannot produce different artifacts.
- Library-scoped SQLite storage appending two CREATE TABLE IF NOT EXISTS blocks (bunches, bunch_members) to brain/library_index.py's SCHEMA.
- Model providers for Build mix plan: Claude, Codex and Grok through their signed-in CLIs, Claude/OpenAI/xAI through API keys in the...
- Sparse override layer at plans/<slug>/transitions.json, stored as a list KEYED BY THE (from_track_id, to_track_id) PAIR rather than by...
