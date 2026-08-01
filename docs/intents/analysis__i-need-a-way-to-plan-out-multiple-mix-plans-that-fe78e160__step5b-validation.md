# Step 5b — Module Design Completeness Validation

Validates `…__step5b-module-design-corrected.md` (35 modules) against the
original PRD entry `i-need-a-way-to-plan-out-multiple-mix-plans-that-fe78e160`.

**Result: INVALID** — 12 of 15 module-bearing requirements COVERED, 3 PARTIAL,
plus 1 route-precedence ERROR. All three are amendments to existing modules;
no new module is required.

> `gh issue comment 3953181291 --repo /` not executed — no GitHub auth,
> `--repo /` is not a repo spec, intent source kind is `inline`. File output,
> same precedent as steps 1–5.

## Requirements (from `issue_content`, not the Step 1 summary)

R1 multiple plans · R2 "work in progress" state · R3 switch between plans ·
R4 create new · R5 colloquial names · R6 add songs · R7 remove songs ·
R8 LLM adds dj notes on transitions · R9 LLM adjusts transitions and effects ·
R10 load the mix plan · R11 agent-harness writes · R12 press refresh → order +
transitions · R13 bunch n songs in exact order · R14 move bunch as a unit ·
R15 third tab on `#curate` · R16 prior-effort research (Step 1, non-module).

The `portable-music-collection…288cef1d` entry in the same PRD is a prior
accepted intent; its requirements are out of scope here. The one interaction
that matters — a plan referencing a collection that is not mounted — is covered
(`plan.collection_id`, plan renders *unavailable, never deleted*; a note
override on an `available = 0` track is retained and flagged).

## Gap 1 — R2: `status` is read and rendered but never written

Module 18 returns `status` per plan; module 33 renders a "WIP badge" from it.
No module in 1–35 sets it, and no enum defines its values (Step 4 correctly
declined to invent one, noting *"work in progress"* is the PRD's only
enum-adjacent phrase). As designed, every plan is born in an unnamed state that
can never change, so the badge is decoration.

This is the same read/write asymmetry Step 5 itself caught and fixed for the
journal (module 22) — it just wasn't applied to `status`.

**Fix (amendment, no new module):**
- `plan_store` (5) — add `set_status(slug, status, base_rev)`; define the value
  set in `plan_types` (1) as `wip` | `ready` | `archived`, with `wip` the
  creation default. Provenance: `wip` is PRD-sourced; the other two are
  design-sourced and should be labelled as such, not back-attributed to the PRD.
- `api_plan_detail` (20) — accept `{status, base_rev}` on POST alongside the
  existing `{display_name}` rename and `{action:"delete"}`.
- `plan_picker_JS` (33) — badge becomes a control, not a label.
- `plan_cli` (31) — the existing `status` verb reads staleness; adding a writer
  needs a distinct spelling (`plan_cli mark <state>`) or `status` becomes
  ambiguous between "is this plan stale" and "set the WIP flag".

## Gap 2 — R8/R9: no CLI write path for transitions, effects, or notes-on-transitions

The PRD's mechanism for R8/R9 is explicit: an LLM/agent harness makes the
change, the human presses refresh. Step 5's own Integration Points row names
`plan_cli` as *"the harness-facing contract. Without it, agents keep editing
singleton files and the PRD's 'an AI agent changed it, I press refresh' has no
defined write path."*

Module 31's verb list is
`list|new|switch|show|add|remove|move|note|bunch|build|log|status`.
There is no `transition` verb. `note` writes a **track** note (module 9,
`EffectiveNote` keyed by `track_id`); the transition-level `note`, `technique`,
`beats`, `showcase_move`, and `effects` fields live in module 10 and are
reachable **only** over HTTP via module 27.

So the two things the PRD names as the LLM's job — dj notes *on transitions*,
and adjusting *transitions and effects* — are exactly the two the offline
harness contract cannot express. Module 31's own acceptance criteria say it
"runs with no GUI process and no server", which means when the server is down
an agent has no write path at all for R9.

**Fix (amendment, no new module):**
- `plan_cli` (31) — add `transition` (get / set / clear) covering the same
  sparse-patch shape as module 27: `--from`, `--to`, and optional `--technique`,
  `--beats`, `--showcase-move`, `--effects`, `--note`, plus `--base-rev`.
  Add `transition_overrides` (10) to module 31's dependency list — it is
  already listed, so this is a verb addition only.
- `plan_cli` (31) — clarify that `note` is track-scoped, so the split from
  `transition --note` is visible at the CLI surface rather than inferred.
- Documentation row (`AGENTS.md`, `agent/hermes-skill/SKILL.md`) must show the
  transition verb, since that row is what makes the contract discoverable to
  Hermes/Claude/Codex.

## ERROR 1 — `/api/plans/active` is shadowed by `/api/plans/<slug>`

Module 19 registers `GET,POST /api/plans/active`; module 20 registers
`GET,POST /api/plans/<slug>`. Module 16's acceptance criteria specify that
`route(method, path)` matches `<param>` segments but state **no precedence rule
between a literal segment and a parameter segment**. Registration order then
decides whether `GET /api/plans/active` returns the active-plan pointer or a
404 for a plan whose slug is `active` — and the failure is silent and
order-dependent, which is the worst shape for it.

Compounding it: `plan_types.slugify` (1) has no reserved-word list, so
`slugify("Active")` → `active` is a creatable slug that permanently collides
with the pointer route and with `plan_paths.resolve()`'s `active.json` read.

**Fix (amendment, no new module):**
- `api_router` (16) — add to acceptance criteria: a literal segment always
  outranks a `<param>` segment at the same position, independent of
  registration order; add a test asserting `/api/plans/active` reaches module
  19 when module 20 is registered first.
- `plan_types` (1) / `plan_store` (5) — reserve `active`, `.trash`, and any
  leading-dot slug at creation; collision takes the existing `-2`/`-3` suffix
  path rather than erroring.

## What checked out

- **Route 1:1** — 14 distinct URL patterns, 14 modules, nothing collapsed.
- **Entity CRUD** — plan, bunch, `bunch_members`, activation, note override,
  transition override, journal, active pointer all have create/read/update and
  a soft-delete path where deletion is meaningful.
- **Acyclic graph, valid topological sort** — verified per module; every
  dependency's priority is strictly less than its dependent's.
- **Naming** — `bunches` / `bunch_members` / `plan_mix.source_revs` /
  `active.json` are used identically in Steps 4 and 5; `PlanPaths` is
  reconciled to 10 members; prompt basename matches generated filename
  throughout.
- **Wiring** — route registration, `/web/<file>` static serving, entry-point
  delegation (`plan_mix_build`), nav insertion, and the `brain/api/__init__.py`
  package marker each have an Integration Point row; no orphan modules.
- **Commonly-missed** — error handling (16), migrations (15 + 7), logging
  (4/22), pagination (22), loading state (34), shared types (1), API client
  (32) all present. Auth, settings, admin, search, upload, rate limiting, and
  env config are correctly N/A for a single-user localhost server.

## Still open (product calls, not coverage gaps)

Archives-as-importable-plans (gap #8, deferred) and switching plans mid-live-run
(gap #11, designed as refuse-with-409). Neither blocks this gate.
