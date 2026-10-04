# Intent: Blend with gentle faders: no agent moves them fast

<!-- pdd-intent-id: blend-with-gentle-faders-no-agent-moves-them-fas-b18167b2 -->
<!-- pdd-intent-sha256: b18167b20bd3a78be6785134c9380a44506292bb54dc20d6f768e1aee0ec164e -->

## Record

- Intent ID: `blend-with-gentle-faders-no-agent-moves-them-fas-b18167b2`
- Kind: `add`
- Supersedes: none
- Approval ID: `blend-with-gentle-faders-no-agent-moves-them-fas-b18167b2`
- Source kind: `inline`
- Source reference: `not applicable`
- Request SHA-256: `b18167b20bd3a78be6785134c9380a44506292bb54dc20d6f768e1aee0ec164e`
- Project scope: `repository`
- Adoption scenario: `existing_pdd_change`

- Technology: `not stated`

## Original Request

> As a DJ, every blend into a different song moves the faders gently, and claw-dj enforces it in code so no AI agent or harness (one-shot mix builds, hand-written live scripts, any model) can move them fast. Ernest, 2026-10-03, watching Mixxx during the Mo Money -> Ariana blend: "you're blending the channel faders moving them in which should be a gentle blend TOO FAST. I've noticed this when asking for any one shot build the mix. You and any other AI agent, AI harness has to STOP doing that. Stop moving it that fast. blend it in gently."
> 1. A blend into a different song moves each channel fader (and the crossfader) on a steady linear ramp over at least 16 counts, fading in as well as fading out; a fader never sweeps faster than full travel per 16 counts.
> 2. Exempt only when marked: beat juggling, deliberate on-beat cuts, platter/echo/filter exits, and same-song handoffs of identical material (short 4-beat blends were approved there). An exemption is explicit in the code or plan, never the default.
> 3. The plan builder never schedules a blend shorter than 16 counts, including when a quick/short brief or a per-pair override asks for less; quick briefs shorten rides and cuts, not blends.
> 4. The live runner refuses a plan with a too-short blend before anything plays, naming each offending transition.
> 5. The live toolkit refuses a too-fast channel-fader move before writing anything, and its shared moves (riff crossover, fade out) stay gentle even when their EQ part is short.
> 6. Tests fail when any of these produce a fast fader move.

## Must Stay Unchanged

- A blend into a different song moves each channel fader (and the crossfader) on a steady linear ramp over at least 16 counts, fading in as well as fading out; a fader never sweeps faster than full travel per 16 counts.
- An exemption is explicit in the code or plan, never the default.
- The plan builder never schedules a blend shorter than 16 counts, including when a quick/short brief or a per-pair override asks for less; quick briefs shorten rides and cuts, not blends.

## Examples

- I've noticed this when asking for any one shot build the mix.
- Exempt only when marked: beat juggling, deliberate on-beat cuts, platter/echo/filter exits, and same-song handoffs of identical material (short 4-beat blends were approved there).
- The plan builder never schedules a blend shorter than 16 counts, including when a quick/short brief or a per-pair override asks for less; quick briefs shorten rides and cuts, not blends.
- The live toolkit refuses a too-fast channel-fader move before writing anything, and its shared moves (riff crossover, fade out) stay gentle even when their EQ part is short.
- Tests fail when any of these produce a fast fader move.

## Candidate Product Areas

- Reusable live Mixxx moves for live mini-experiments and hand-built live mixes: library lookup by artist/title (folder hint for duplicate...
- The single plan-aware entry to mix composition, callable from both the GUI and the CLI so the two cannot produce different artifacts.
- Sparse override layer at plans/<slug>/transitions.json, stored as a list KEYED BY THE (from_track_id, to_track_id) PAIR rather than by...
