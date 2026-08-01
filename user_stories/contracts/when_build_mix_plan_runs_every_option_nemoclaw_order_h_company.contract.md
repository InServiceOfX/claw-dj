<!-- pdd-story-contract derived-from-story="../story__when_build_mix_plan_runs_every_option_nemoclaw_order_h_company.md" story-hash="802e1b91f4932576" issue-ref="/Users/ernestyeung/.openclaw/workspace/repos/claw-dj/docs/intents/intent__when-build-mix-plan-runs-every-option-nemoclaw-o-a7c8af36.md" -->

# Contract: Intent: When Build mix plan runs, every option — NemoClaw order, H Company...

> Generated from the human-verified user story + issue. Do not hand-edit:
> it is regenerated to align whenever the Story changes. Humans verify the
> Story (`../story__when_build_mix_plan_runs_every_option_nemoclaw_order_h_company.md`), not this contract.

## Covers
- AC1: Build mix plan may reorder the selected songs into the best-sounding playback order instead of preserving selection order.
- AC2: The planned playback order is previewed before starting the mix.
- AC3: Every selected track is preserved exactly once in the planned order unless the user explicitly asked for a subset.
- R1: Reordering freedom applies in every ordering mode named by the issue, including NemoClaw order, H Company order, and Feel only.
- R2: Mix-quality ordering must work without requiring an LLM.
- R3: H Company planning-only ordering must not require or start a local desktop bridge.

## Context
The user has chosen a set of songs for a mix and invokes Build mix plan before starting playback. The selected-track list defines which songs are available to the planner, not a required final playback sequence. The system may support multiple ordering modes, including NemoClaw order, H Company order, and Feel only. The story concerns the generated plan that the user can inspect before Start mix, not the actual playback execution.

## Acceptance Criteria
1. Given multiple selected songs and Build mix plan is run in any supported ordering mode, when the plan is produced, then the resulting playback order may differ from the user’s selection order and is presented as the proposed mix sequence to preview before Start mix.
2. Given a set of selected songs and no explicit request to use only a subset, when Build mix plan completes, then every selected track appears in the previewed plan exactly once.
3. Given Build mix plan is run in NemoClaw order, H Company order, or Feel only mode, when the plan is produced, then that mode is still allowed to reorder tracks as needed for mix quality rather than being forced to keep the original selection order.
4. Given Build mix plan is run in a mode that performs planning only with H Company ordering, when the plan is generated, then no local desktop bridge is required or started as a prerequisite for producing the previewed order.
5. Given natural-language ordering constraints are absent or any LLM capability is unavailable, when Build mix plan runs, then it can still produce a reordered preview plan that includes all selected tracks exactly once.

## Oracle
These details matter for pass/fail:
- The observable output of Build mix plan includes a previewable ordered track list before Start mix.
- The planned order is allowed to differ from input selection order; validation must fail if the system treats selection order as mandatory playback order.
- For a normal full-set plan, each selected track is present once and only once in the planned sequence.
- The same reorder freedom applies across the named modes in scope: NemoClaw order, H Company order, and Feel only.
- Planning succeeds without requiring an LLM for mix-quality ordering itself.
- In H Company planning-only operation, no local desktop bridge startup or dependency is triggered.

## Non-Oracle
These details should not matter:
- The exact algorithm, scoring method, heuristics, or internal data structures used to choose the order.
- Whether an LLM is optionally used to interpret user-written ordering constraints, so long as core ordering does not depend on it.
- The exact wording, layout, or styling of the preview, as long as the ordered track sequence is observable before Start mix.
- The specific final order chosen, provided it is a reordered plan consistent with the selected tracks and mode behavior.
- Whether the feature is invoked from GUI or CLI, as long as the user-observable planning outcome matches the story.

## Negative Cases
- Treating the order in which tracks were selected as a required final playback order.
- Dropping a selected track, duplicating a selected track, or otherwise failing to include each selected track exactly once in a normal full-set plan.
- Producing no previewable order before Start mix.
- Requiring an LLM in order to perform mix-quality ordering.
- Starting or requiring a local desktop bridge for H Company planning-only ordering.
- Allowing one of the named modes to bypass reordering and simply preserve selection order by default when reordering is needed for the mix.

## Non-Goals
- Proving that the chosen order is objectively the best possible mix.
- Defining the exact natural-language constraint syntax or how such constraints are interpreted.
- Covering explicit subset-selection behavior beyond recognizing that the “every selected track exactly once” rule is waived only when the user explicitly requests a subset.
- Specifying playback, export, or post-plan execution behavior after the previewed plan is accepted.

## Candidate Prompts
- `plan_mix_build_Python.prompt` — Owns plan-aware mix composition and ordering behavior that this story validates (primary)

## Notes
- The issue explicitly pins three mode names in scope for this story: NemoClaw order, H Company order, and Feel only.
- The contract intentionally checks observable planning outcomes and forbidden dependencies, not internal implementation choices.
- “Best-sounding” and “flows smoothly” are made machine-checkable here through the narrower promise that the planner is free to reorder for mix quality and must not be locked to selection order.
