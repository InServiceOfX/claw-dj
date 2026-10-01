# Intent: Refactor Build mix plan and preserve the Curate/Mix GUI

<!-- pdd-intent-id: refactor-build-mix-plan-and-preserve-the-curate--f4cf5bf3 -->
<!-- pdd-intent-sha256: f4cf5bf3ad62425eeead40ad23e1cd4bd7e885a5346b3a93b3fd200ac611ca7d -->

## Record

- Intent ID: `refactor-build-mix-plan-and-preserve-the-curate--f4cf5bf3`
- Kind: `replace`
- Supersedes: `when-build-mix-plan-runs-every-option-nemoclaw-o-a7c8af36`
- Approval ID: `refactor-build-mix-plan-and-preserve-the-curate--f4cf5bf3`
- Source kind: `file`
- Source reference: `docs/intents/request__build_mix_plan_refactor_and_gui_preservation.md`
- Request SHA-256: `f4cf5bf3ad62425eeead40ad23e1cd4bd7e885a5346b3a93b3fd200ac611ca7d`
- Project scope: `repository`
- Adoption scenario: `existing_pdd_change`

- Technology: `python` (corrected: PDD inferred `cpp` from "llama-cpp")

## Original Request

> # Request: Refactor Build mix plan; preserve the Curate and Create-the-mix GUI
>
> Ernest, 2026-09-30, after the Who Shot Ya three-model continuous mix
> (Grok 4.6, Claude Opus 5.5, GPT Astra 6) passed the backbeat/snare-parity
> stories. That code is the accepted base for this refactor.
>
> Status: proposed (awaiting meaning-level approval).
>
> ```text
> Now we're going to refactor the GUI. As a user I like to start here:
> http://127.0.0.1:8787/#curate I like the drop down for the mix plan to work on
> a previous mix or press New for a new one or to duplicate. I like how to check
> for new music automatically here: "New music 18058 new · 80 changed · 83177
> unchanged · 986 need tags Scanned folders: /Volumes/Elements/Music" and with
> the Check for new music button. Also I like how I can choose which "volume"
> would have my music collection, on this same page on here: Music collection
> ElementsMusic · /Volumes/Elements Known collections Use selected Start new
> collection… As a user I like how I can search for my music in the text field
> and click on buttons to easily add from Library into Enabled set. And also the
> Archive first button to toggle or not, and to clear a set. I also like the
> audio preview player built right in. I also like Finalize for Mixxx button on
> there too. There should be user stories for all of this, because I like all of
> this and we should preserve it. If we don't have a related, even remotely
> related user story, create it. So I'll press Finalize for Mixxx right now.
>
> http://127.0.0.1:8787/#mix on here i like how I can just press Analyze &
> enrich missing and see the log to see which files had gotten lyrics, the bpm
> and key from mixxx, and how I don't have to allow permissions for each and
> every song; we just assume given the volume then recursively all the songs can
> and should be accessible to mixxx. Now once I'm finished with Analyze and
> enrich I like how Build mix plan is ready.
>
> Now here's the part I don't like with Build mix plan. Despite selecting DJ
> show case for quick transitions to showcase the mixing ability of claw-dj, it
> doesn't adhere to some of our rule such as backbeat matching. And then for Mix
> to listen I don't like how it doesn't work consistently to blend nicely. Also,
> I find that Candidate playback order it's following too closely, during the
> first time to how the user chooses it from the first page, in Library and
> Enable, instead of choosing the best order to make the best blend. Also I'm
> not using H company's model at this point much, and I don't think it's the
> right model for it. Also Nemoclaw is too difficult to deploy and keep up. We
> should refactor this build mix plan. It's got to be LLM powered and if it's
> not yet LLM powered, then just optimize its "computational graph" (we
> calculate for each song a metric of compatibility to blend with each other,
> don't we? if not, then i'm mistaken, and ignore) and create the mix without
> LLM. But at this point, allow for user to either for Claude, authorize with
> OAuth (on the browser?) with Claude, or likewise codex, or likewise Grok. Also
> for each of these 3, Claude, Grok, and OpenAI's GPT codex, be able to provide
> a .env that'll have the API keys (or the best way to do that to have this
> local application keep the API keys). OR, finally, use llama-cpp's
> llama-server, and call that for help. Keep Candidate playback order list, that
> looks nice. But yeah we gotta refactor from the step Build mix plan. Shuffle
> opener doesn't help much either in creating, a one shot or best first try mix.
> that also follows our user stories too. Help!
> ```
>
> ## Inferred actions
>
> - **Constraint (preserve):** Curate page plan picker (open / New / Duplicate),
>   New-music scan summary + Check for new music, collection chooser (Known
>   collections, Use selected, Start new collection…), search + add from Library
>   into Enabled set, Archive first toggle + Clear set, built-in audio preview,
>   Finalize for Mixxx; Create-the-mix Analyze & enrich missing with a per-file
>   log, Candidate playback order list.
> - **Correct:** Analyze & enrich must not depend on per-song file permission
>   prompts; access is granted per volume (recursively). Supersedes the
>   "macOS may still prompt per track" acceptance note in
>   `story__when_i_finalize_a_set_i_enrich_build_a_mix_plan_and_start_mixxx.md`.
> - **Correct:** Build mix plan ordering must not echo selection order; it must
>   optimize blend quality over the whole set, with backbeat (snare) matching as
>   a hard rule in every profile, including DJ showcase and Mix to listen.
> - **Remove:** NemoClaw and H Company as Build-mix-plan order engines; Shuffle
>   opener.
> - **Add:** model providers for Build mix plan — Claude, OpenAI Codex/GPT, Grok
>   (each by browser sign-in or by locally stored API key) and a local
>   llama.cpp `llama-server`; with no provider, a deterministic graph optimizer
>   builds the mix.

## Must Stay Unchanged

- unchanged · 986 need tags Scanned folders: /Volumes/Elements/Music" and with
- If we don't have a related, even remotely
- and key from mixxx, and how I don't have to allow permissions for each and
- Now here's the part I don't like with Build mix plan.
- to listen I don't like how it doesn't work consistently to blend nicely.

## Examples

- doesn't adhere to some of our rule such as backbeat matching.

## Candidate Product Areas

- The single plan-aware entry to mix composition, callable from both the GUI and the CLI so the two cannot produce different artifacts.
- Model providers for Build mix plan: Claude, Codex and Grok through their signed-in CLIs, Claude/OpenAI/xAI through API keys in the...
