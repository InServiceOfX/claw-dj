<!-- pdd-story-status: accepted-2026-09-30 -->
<!-- pdd-story-areas: showcase_moves, build_mix_plan, llm_providers, playlist.html -->
<!-- pdd-story-prompts: prompts/brain/showcase_moves_Python.prompt, prompts/brain/plan_mix_build_Python.prompt -->

# User Story: In DJ showcase, the model I pick choreographs claw-dj's most impressive moves

## Story

As a DJ, when I choose **DJ showcase** and a model (Claude, Codex, Grok, or
llama-server), the model plans each transition's move so the mix shows off
as much of claw-dj's technique as it can: loop rolls, stutters, censor
fills, transformer cuts, bass swaps, and the occasional dramatic echo-out
or filter drop where it lands best. My DJ notes and the mixing rules still
come first.

## Acceptance criteria (observable)

1. With DJ showcase and a model selected, Build mix plan's Transitions list
   marks model-chosen moves (✦) and shows the model's reason on hover; the
   order notes summarize how many moves it chose and which kinds.
2. Moves vary across the set, using the flourishes and dramatic exits the
   runner can play live.
3. The opening blends stay smooth. Dramatic exits are never back to back,
   at most one in four transitions, and never on a sample-lineage pair.
4. A song's DJ notes win: no_flourish, a noted exit or entry style, cue and
   ride notes.
5. Backbeat (snare) matching is unchanged by the choreography.
6. With no model, a model failure, or another Mix feel, DJ showcase keeps
   its built-in move rotation and the build still succeeds.

## Out of scope (next)

- Three or more decks at once (vocal A + vocal B over an instrumental bed):
  needs runner and Mixxx deck 3/4 support first; see
  `story__when_i_mix_the_same_beat_or_sample_lineage_i_use_the_instrumental_as_a_short_bridge.md`.

## Related

- Request: `docs/intents/request__dj_showcase_model_choreography.md`
