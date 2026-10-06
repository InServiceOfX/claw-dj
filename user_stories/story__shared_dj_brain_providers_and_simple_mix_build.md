<!-- pdd-story-prompts: prompts/brain/llm_providers_Python.prompt, prompts/brain/dj_brain_workflow_Python.prompt, prompts/brain/plan_mix_build_Python.prompt -->

# One DJ brain across curation and mix planning

As a DJ, I can ask for candidates using the same signed-in CLI, API-key or
local models available to the mix planner, then review those picks before
adding them. New music stays scoped to the latest scan; Whole library stays
scoped to my existing collection. NemoClaw and the H desktop/managed agent
runtime are retired from these planning actions.

When I put HAI_API_KEY in my ignored .env, H Company becomes available through
its direct text Models API. Keys never appear in browser responses, plan files
or Git; .env.example documents the names without real credentials.

On Create the mix, I choose a feel, one DJ brain and an optional brief, then
Build mix plan. The same brain is used if I separately preview DJ-note edits.
Experimental formats and note editing stay in Advanced; note edits require
explicit review and Apply. Optimizer-only remains useful without any model.

The builder honors my existing musical rules, effective notes and exclusions,
keeps songs exactly once, and shows the candidate order, dry-run and unverified
backbeats before I choose Start mix. Building or asking never starts playback.
My choices survive provider refresh and idle status polls.

I am told to analyze tracks missing BPM before building; they are not silently
dropped. Unsupported advanced techniques are not advertised as automatic, and
an authored performance cannot be overwritten by the generic builder.

Source: [original request](../docs/intents/intent__shared-dj-brain-providers-and-streamlined-mix-bu-59a37e5d.md).
Evidence: tests/test_dj_brain_providers.py, tests/test_llm_providers.py,
tests/browser/dj_brain_workflow.cjs and the existing musical-rule regressions.
