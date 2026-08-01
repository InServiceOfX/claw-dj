# Intent: When Build mix plan runs, every option — NemoClaw order, H Company...

<!-- pdd-intent-id: when-build-mix-plan-runs-every-option-nemoclaw-o-a7c8af36 -->
<!-- pdd-intent-sha256: a7c8af36b409b2b896d2940185c390e19f25ae1f4bf01ea46003a665f984d28b -->

## Record

- Intent ID: `when-build-mix-plan-runs-every-option-nemoclaw-o-a7c8af36`
- Kind: `add`
- Supersedes: none
- Approval ID: `when-build-mix-plan-runs-every-option-nemoclaw-o-a7c8af36`
- Source kind: `inline`
- Source reference: `not applicable`
- Request SHA-256: `a7c8af36b409b2b896d2940185c390e19f25ae1f4bf01ea46003a665f984d28b`
- Project scope: `repository`
- Adoption scenario: `existing_pdd_change`

- Technology: `not stated`

## Original Request

> When Build mix plan runs, every option — NemoClaw order, H Company order, and Feel only — must be free to reorder the finalized playlist as necessary so the mix blends and sounds as good as possible. The order in which the user selected tracks is not a required playback order; the user is only declaring which songs are available for the mix. An LLM may be used to interpret natural-language ordering constraints, but mix-quality ordering itself must not require an LLM and must work in every mode. Preserve every available track exactly once unless the user explicitly requests a subset, and preview the resulting order before Start mix. H Company planning-only ordering must not require or start a local desktop bridge.

## Must Stay Unchanged

- When Build mix plan runs, every option — NemoClaw order, H Company order, and Feel only — must be free to reorder the finalized playlist as necessary so the mix blends and sounds as good as possible.
- An LLM may be used to interpret natural-language ordering constraints, but mix-quality ordering itself must not require an LLM and must work in every mode.
- H Company planning-only ordering must not require or start a local desktop bridge.

## Examples

- When Build mix plan runs, every option — NemoClaw order, H Company order, and Feel only — must be free to reorder the finalized playlist as necessary so the mix blends and sounds as good as possible.

## Candidate Product Areas

- The single plan-aware entry to mix composition, callable from both the GUI and the CLI so the two cannot produce different artifacts.
- Pure stdlib shared types, no I/O and no imports outside the standard library.
- Sparse override layer at plans/<slug>/transitions.json, stored as a list KEYED BY THE (from_track_id, to_track_id) PAIR rather than by...
- The riskiest module in the feature: the only one that changes behaviour inside working, ear-tested ordering code.
- Pure function over a dict; DOES NOT import build_mix_plan, so it stays cheap to test and free of the 1895-line module.
