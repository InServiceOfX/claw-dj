<!-- pdd-story-status: accepted-2026-09-30 -->
<!-- pdd-story-areas: llm_providers, mix_llm_refine, mix_order_brief, playlist_editor, playlist.html -->
<!-- pdd-story-prompts: prompts/brain/llm_providers_Python.prompt, prompts/brain/mix_llm_refine_Python.prompt -->

# User Story: Build mix plan can use Claude, Codex, Grok or a local llama-server, or no model at all

## Story

As a DJ, on Create the mix I choose which model helps build the mix:
**Claude**, **OpenAI Codex** or **Grok** through the apps I'm already signed
in to, the same three through API keys I keep in a local `.env` file, or a
local **llama-server**. Or I choose **No model**. The graph optimizer always
builds a good order; a model reads my brief and reviews that order like a
DJ, and its changes are kept only if they keep the backbeat and blend rules.
NemoClaw and H Company are no longer needed.

## Acceptance criteria (observable)

1. **Choice on Create the mix.** The model dropdown next to Build mix plan
   lists No model plus every provider. A provider that is not ready is shown
   disabled with the reason (not installed, not signed in, key missing,
   server not running).
2. **Sign-in is the vendor's.** For Claude, Codex and Grok, signing in means
   running the vendor's own login once in a terminal (`claude auth login`,
   `codex login`, `grok login --oauth`), which opens the browser. The page
   shows these commands when a CLI is not signed in. claw-dj itself never
   asks for or stores a password or token.
3. **API keys stay local.** Keys go in `.env` at the repository root (never
   committed; `.env.example` lists the names). claw-dj never writes keys
   into plans, logs or the page.
4. **Local model.** With llama-server running, choosing it sends the same
   review to the local server; if it is not running, the page says so.
5. **No model works.** With No model, or when the chosen model fails or
   times out, Build mix plan still completes with the optimizer's order and
   the order notes say what happened.
6. **Rules beat the model.** A model reorder that drops or repeats a song,
   moves a requested opener, splits a requested pairing, adds a blend where
   neither snare is verified, adds more than one unverified blend, or lowers
   blend quality beyond a small allowance is rejected; the note says why.
   An accepted review is noted with the before/after blend score and the
   model's reasons.
7. **DJ-note edits use the same providers.** "Interpret as DJ notes…" offers
   the same signed-in or keyed models.

## Out of scope

- Ask the DJ brain on Curate (still on its existing engines for now).
- Running OAuth inside claw-dj.

## Related

- `story__when_i_build_a_mix_plan_the_order_is_chosen_for_the_best_blend_and_every_blend_keeps_the_backbeat.md`
- Request: `docs/intents/request__build_mix_plan_refactor_and_gui_preservation.md`
