# Intent: Can you make it so the button Build mix plans allow for more turns?

<!-- pdd-intent-id: can-you-make-it-so-the-button-build-mix-plans-al-5c9db8d4 -->
<!-- pdd-intent-sha256: 5c9db8d4da3a618fd750db3df2975444745b82ff190f52d52df4d96c1f3dcc77 -->

## Record

- Intent ID: `can-you-make-it-so-the-button-build-mix-plans-al-5c9db8d4`
- Kind: `add`
- Supersedes: none
- Approval ID: `can-you-make-it-so-the-button-build-mix-plans-al-5c9db8d4`
- Source kind: `inline`
- Source reference: `not applicable`
- Request SHA-256: `5c9db8d4da3a618fd750db3df2975444745b82ff190f52d52df4d96c1f3dcc77`
- Project scope: `repository`
- Adoption scenario: `existing_pdd_change`

- Technology: `not stated`

## Original Request

> Can you make it so the button Build mix plans allow for more turns?

## Must Stay Unchanged

- None stated.

## Examples

- None stated.

## Candidate Product Areas

- The single plan-aware entry to mix composition, callable from both the GUI and the CLI so the two cannot produce different artifacts.
- Pure function over a dict; DOES NOT import build_mix_plan, so it stays cheap to test and free of the 1895-line module.
