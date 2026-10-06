# Intent: Evidence-gated advanced techniques in the generic mix builder

<!-- pdd-intent-id: evidence-gated-advanced-techniques-in-the-generi-7ab3a6e9 -->
<!-- pdd-intent-sha256: 7ab3a6e91f45e92df0d61c47e4c1dd212e0cfb096be37b5e17d69bc1ed589b20 -->

## Record

- Intent ID: `evidence-gated-advanced-techniques-in-the-generi-7ab3a6e9`
- Kind: `add`
- Supersedes: none
- Approval ID: `evidence-gated-advanced-techniques-in-the-generi-7ab3a6e9`
- Source kind: `file`
- Source reference: `external-local-file:clawdj-advanced-request.txt`
- Request SHA-256: `7ab3a6e91f45e92df0d61c47e4c1dd212e0cfb096be37b5e17d69bc1ed589b20`
- Project scope: `repository`
- Adoption scenario: `existing_pdd_change`

- Technology: `python`

## Original Request

> git tag and push to origin the master branch, then your branch currently, after you've git committed the relevant files: "ernestyeung@Ernests-Mac-mini claw-dj % git status
> On branch feat/shared-dj-brain-providers
> Changes not staged for commit:
>   (use "git add/rm <file>..." to update what will be committed)
>   (use "git restore <file>..." to discard changes in working directory)
> 	modified:   .env.example
> 	modified:   .pddrc
> 	modified:   PROGRESS.md
> 	modified:   architecture.json
> 	modified:   brain/llm_providers.py
> 	modified:   brain/mix_directives.py
> 	modified:   brain/pick_candidates.py
> 	modified:   brain/playlist_editor.py
> 	modified:   brain/web/playlist.html
> 	modified:   docs/HANDOFF.md
> 	modified:   docs/PRODUCT_INTENT.md
> 	modified:   prompts/brain/llm_providers_Python.prompt
> 	modified:   prompts/brain/plan_mix_build_Python.prompt
> 	modified:   tests/test_llm_providers.py
> 	modified:   tests/test_mix_order_brief.py
> 	deleted:    tests/test_nemoclaw_sandbox_resolve.py
>
> Untracked files:
>   (use "git add <file>..." to include in what will be committed)
> 	docs/H_COMPANY_MODELS_API.md
> 	docs/LISTENING_LOG_50_CENT_G_UNIT_TRIBUTE_VOL_1_2026-09-05.md
> 	docs/OVERLAP_PARITY_REVIEW_2026-09-05.md
> 	docs/PLAN_REPRODUCIBILITY_50_CENT_G_UNIT_TRIBUTE_VOL_1_2026-09-05.md
> 	docs/WHO_SHOT_YA_LISTENING_REVIEW_2026-09-05.md
> 	docs/intents/intent__shared-dj-brain-providers-and-streamlined-mix-bu-59a37e5d.md
> 	docs/intents/request__jadakiss_who_shot_ya_next_to_k_dot.md
> 	docs/intents/request__jealous_backbeat_parity.md
> 	docs/intents/request__stunt_101_backbeat_repair.md
> 	prompts/brain/dj_brain_workflow_Python.prompt
> 	tests/browser/
> 	tests/run_dj_workflow_checks.py
> 	tests/test_dj_brain_providers.py
> 	user_stories/story__shared_dj_brain_providers_and_simple_mix_build.md
>
> no changes added to commit (use "git add" and/or "git commit -a")
> ernestyeung@Ernests-Mac-mini claw-dj % " , tag that and then like do the change to generic builder in the stages you mentioned, do those changes where we're adding those advanced techniques with those musical safeguards into the generic builder, and once those are git committed, tag that too. Also, for .env.example or in general, can you get me the latest model name I should be using for H compnay, because it's a tedious step to get the right model name and latest one, so this is good in .env.example so far, just double check it's the latest and greatest: CLAWDJ_HCOMPANY_MODEL=holo3-1-35b-a3b

## Must Stay Unchanged

- None stated.

## Examples

- None stated.

## Candidate Product Areas

- Brownfield workflow contract across pick_candidates.py, mix_directives.py, playlist_editor.py and web/playlist.html: provider-based...
- The single plan-aware entry to mix composition, callable from both the GUI and the CLI so the two cannot produce different artifacts.
- Shared text providers for curation, DJ-note previews and mix planning: Claude/Codex/Grok signed-in CLIs, Claude/OpenAI/xAI/H Company API...
