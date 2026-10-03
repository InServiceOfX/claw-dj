# Intent: Loop one bar live, then blend or drop into the next song

<!-- pdd-intent-id: loop-one-bar-live-then-blend-or-drop-into-the-ne-4cbf3ed6 -->
<!-- pdd-intent-sha256: 4cbf3ed6eb1785017c121dd47d62fb82c2b96f0d6319bffd4527ede8f8d459c6 -->

## Record

- Intent ID: `loop-one-bar-live-then-blend-or-drop-into-the-ne-4cbf3ed6`
- Kind: `add`
- Supersedes: none
- Approval ID: `loop-one-bar-live-then-blend-or-drop-into-the-ne-4cbf3ed6`
- Source kind: `inline`
- Source reference: `not applicable`
- Request SHA-256: `4cbf3ed6eb1785017c121dd47d62fb82c2b96f0d6319bffd4527ede8f8d459c6`
- Project scope: `repository`
- Adoption scenario: `existing_pdd_change`

- Technology: `not stated`

## Original Request

> this is fire (i.e. this is great): looping one bar of Diana Ross's I'm Coming Out (grid beats 318-322, the part Mo Money Mo Problems samples) for 3 passes. As a DJ effect to then be able to take this loop repeat 2 or 3 at most 4 times (no hard upper limit but don't want to be annoying) and then mix or blend into another song or deck live would be fire (i.e. great). Is there some way to capture this in general as a technique, first described as a user story (the user the human DJ would like claw-dj to loop a single bar live, and then immediately blend into another song or drop at the right time).

## Must Stay Unchanged

- As a DJ effect to then be able to take this loop repeat 2 or 3 at most 4 times (no hard upper limit but don't want to be annoying) and then mix or blend into another song or deck live would be fire (i.e.

## Examples

- None stated.

## Candidate Product Areas

- The single plan-aware entry to mix composition, callable from both the GUI and the CLI so the two cannot produce different artifacts.
- Model providers for Build mix plan: Claude, Codex and Grok through their signed-in CLIs, Claude/OpenAI/xAI through API keys in the...
- THE HARNESS-FACING CONTRACT.
- THE SINGLE READ THE ARRANGE TAB NEEDS, deliberately one call: ordered tracks, effective notes with their layer (plan|global) and diverged...
- Whole-set playback-order optimizer: directed edge weights from mix_graph.pair_score plus tempo direction and snare-parity verifiability...
