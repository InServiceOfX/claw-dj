<!-- pdd-story-status: accepted-2026-09-30 -->
<!-- pdd-story-areas: build_mix_plan, mix_optimizer, mix_llm_refine, onset_analysis, enrich_set, playlist.html -->
<!-- pdd-story-prompts: prompts/brain/plan_mix_build_Python.prompt, prompts/brain/mix_optimizer_Python.prompt, prompts/brain/mix_llm_refine_Python.prompt -->

# User Story: Build mix plan picks the best order for the whole set, and every blend keeps the backbeat

## Story

As a DJ, when I press **Build mix plan**, claw-dj chooses the playback order
that blends best across my whole finalized set, not the order I happened to
pick songs on Curate, and every blend matches the snares (the backbeat), not
just the beat ticks. That holds whether I chose DJ showcase, Club set or Mix
to listen. When a blend's snare cannot be verified, the Candidate playback
order tells me so, so I know where to listen. I get a good mix on the first
try without shuffling openers.

Supersedes the NemoClaw / H Company order engines and Shuffle opener from
`story__when_build_mix_plan_runs_every_option_nemoclaw_order_h_company.md`;
the rest of that story (every song once, order is a pool, preview before
Start mix) still holds.

## Acceptance criteria (observable)

1. **Pick order is irrelevant.** The same finalized set builds the same
   candidate order no matter what order the songs were enabled in.
2. **Whole-set best blend.** The order is chosen for blend quality over the
   entire set (BPM, key, sample lineage, genre/texture, energy direction,
   backbeat verifiability), and is never worse than the old one-pass tour.
3. **Backbeat in every profile.** In DJ showcase, Club set and Mix to listen,
   whenever both songs have a reliable snare read, the planned landing puts
   both songs' snares on the same counts. A listener-approved locked ride
   (`trust_ride_beats`) is respected and labelled "locked".
4. **No silent fallbacks.** Each blend in **Candidate playback order** shows
   `snare ✓`, `bar count only` (snare not verifiable on one side) or
   `locked`, and the plan stats show how many blends are matched and
   unverified.
5. **Fewer blind spots.** Weak-snare songs are not placed next to each other
   when a comparable order avoids it. Analyze & enrich re-measures weak
   snare reads on drum-only windows of the song and only accepts a new read
   when several windows agree (no confidence inflation); otherwise the song
   stays unverified and is flagged.
6. **Every song once.** All finalized songs appear exactly once unless a
   brief explicitly asks for a subset.
7. **Shuffle opener is gone.** There is no Shuffle opener button; Build mix
   plan gives the best first try by itself.
8. **Candidate playback order stays.** The numbered list with artist —
   title, key and BPM remains, now with the per-blend backbeat label.

## Out of scope

- Proving by numbers alone that a blend sounds right. A live listen confirms;
  "off by one count" reports still flip the outgoing ride by ±1
  (`story__when_i_blend_i_match_the_snare_not_just_the_beat.md`).

## Related

- `story__when_i_build_a_mix_plan_i_can_use_claude_codex_grok_or_a_local_model.md`
- Request: `docs/intents/request__build_mix_plan_refactor_and_gui_preservation.md`
