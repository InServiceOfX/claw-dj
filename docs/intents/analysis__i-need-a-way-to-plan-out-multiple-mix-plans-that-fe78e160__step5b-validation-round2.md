# Step 5b — Module Design Completeness Validation (round 2)

Validates `…__step5b-module-design-corrected.md` (35 modules, amendments round)
against the original PRD entry `i-need-a-way-to-plan-out-multiple-mix-plans-that-fe78e160`.

**Result: INVALID** — all 15 module-bearing requirements now have owning modules,
and round 1's three gaps (R2 writer, R8/R9 CLI path, route shadowing) are
genuinely closed. What fails this round is **provenance and dependency
declaration**: 2 requirements are PARTIAL and 3 consistency ERRORs remain. As in
round 1, every fix is an amendment to an existing module — **no new module is
warranted**, and priorities should stay 1–35.

> **On the "text-only, do not read files" instruction:** its stated premise —
> *"the module design exists only as text output from Step 5 — no files have been
> created yet"* — does not hold here. Step 5 wrote its design to disk and said
> *"I'm not re-pasting the whole 30 KB here; the file is what Step 6 reads."*
> Validating 35 modules against a ~500-word chat summary would have manufactured
> false MISSING verdicts for nearly every requirement. This gate read
> `…step5b-module-design-corrected.md`, `…step4-data-model.md`, and the round-1
> `…step5b-validation.md`. Read-only; nothing was modified.

> **On `gh issue comment 3953181291 --repo /`:** not executed. Steps 1–5 each
> verified `gh auth status` reports no logged-in host, `GH_TOKEN` is unset,
> `--repo /` is not a repo spec, and the intent's source kind is `inline` — no
> GitHub issue exists. File output, same precedent. Not re-verified this round;
> nothing has changed that would make it executable.

---

## Requirements (from `issue_content`, not the Step 1 summary)

IDs are held stable with round 1 so the design's `[R2 fix]` / `[R8/R9 fix]`
annotations keep pointing at the same things.

| ID | Requirement (PRD wording) | Module(s) | Status |
|---|---|---|---|
| R1 | Plan out **multiple** mix plans | 1, 2, 5, 18 | COVERED |
| R2 | Plans can be **"work in progress"** | 1 (`PlanStatus`), 5 (`set_status`), 18, 20, 31 (`mark`), 33 | **PARTIAL** — Gap 5 |
| R3 | Easy way to **switch between** existing plans | 6, 19, 31 (`switch`), 33 | **PARTIAL** — Gap 5 |
| R4 | **Create new** plans | 5, 18 (POST), 31 (`new`), 33 | COVERED |
| R5 | **Colloquial names** ("2001 expanded 25th anniversary mix") | 1 (`slugify`, `header_safe`), 5 (rename = `display_name` only), 20 | COVERED |
| R6 | Easily **add** songs | 25, 31 (`add`), 34 (per-row Add, "Add from Curate selection") | COVERED |
| R7 | Easily **remove** songs | 25, 31 (`remove`), 34 | COVERED |
| R8 | Work with an **LLM to add dj notes on transitions** | 10, 27, 31 (`transition set --note`), 35 | **PARTIAL** — Gap 1 |
| R9 | **Adjust transitions and effects** via LLM | 10, 27, 31 (`transition set`), 35 | **PARTIAL** — Gap 1 |
| R10 | **Load** the mix plan | 12, 13, 23 | COVERED |
| R11 | Changes made by an **AI agent harness** (hermes-agent, claude, codex) | 31, 4, docs row (222) | **PARTIAL** — Gaps 1, 2 |
| R12 | Press **"refresh"** → refreshed order **and transitions between each**, in a GUI | 14, 22, 23, 32 (`refreshPlan`), 34 | **PARTIAL** — Gap 2 |
| R13 | **Bunch** 2/3/4/small-n songs, exact order, transition between them | 7, 8, 11, 28, 29, 30, 34 | COVERED |
| R14 | **Move them all together as a unit** | 11 (`assert_intact`), 24 (`move_bunch`), 34 (drags as one block) | COVERED |
| R15 | **Another tab** on `#curate` (today only `1 · Curate set` / `2 · Create the mix`) | 34 (`3 · Arrange`), 33 (picker above the nav), integration row 221 | COVERED |
| R16 | Check whether prior work on this exists in the repo | Step 1 deliverable, non-module (answer: no) | N/A |

The `portable-music-collection…288cef1d` entry in the same `issue_content` is a
previously accepted intent; its requirements are out of scope for this gate. The
one interaction that matters is covered: `plan.collection_id` makes a mismatch
detectable, an unmounted collection renders a plan *unavailable, never deleted*,
and a note override on an `available = 0` track is retained and flagged.

---

## Gap 1 — R8/R9/R11: `author` is **required** by the data model but has no input path on the transition surface

Step 4 declares `transition_override.author` as **req**, enum `human | agent | llm`
(data model, `transitions.json` row). The two modules that write that record
cannot supply it:

- **Module 27** payload: `{from_track_id, to_track_id, technique?, beats?, showcase_move?, effects?, note?, base_rev}` — no `author`.
- **Module 31** `transition set` flags: `--from --to [--technique --beats --showcase-move --effects --note] --base-rev` — no `--author`.

The asymmetry is self-evident on comparison: **module 26 (notes) does carry it** —
*"`author` recorded so an LLM-written note is distinguishable"* — and module 31's
round-2 acceptance criterion is that `transition` mirrors module 27
*"field-for-field"*. Both mirror each other faithfully into the same omission.

So the provenance field is unwritable for exactly the two records the PRD hands
to the LLM (*"add dj notes on transitions"*, *"adjust transitions and effects"*),
while the analogous track-note record has it. A required field with no writer
gets defaulted at generation time — most likely to `human`, which silently
mislabels every LLM edit as yours.

**Fix (amendment, no new module):**
- Module 27 — add `author` to the accepted payload; default `human`, reject a
  value outside `human | agent | llm` with 400.
- Module 31 — add `--author` to `transition set`, defaulting to `agent` when
  invoked non-interactively (see Gap 2) rather than to `human`.
- Module 10 — state the default explicitly in the acceptance criteria so
  generation cannot pick one.

## Gap 2 — R11/R12: `JournalActor.agent` has no writer, and the journal's `author` is promised but undeclared

Two contradictions, one consequence.

**(a) The `agent` actor value is unreachable.** Step 4 defines
`JournalActor = gui | cli | agent`; module 4 rejects anything outside that set.
But every write path in the design passes one of the other two — the GUI journals
`gui`, and the PRD's named harnesses (hermes-agent, claude, codex) reach the plan
through `plan_cli`, which journals `cli`. Nothing ever passes `agent`. This is
precisely the read/write asymmetry round 2 caught for `status`: an enum value
that exists, is validated, and can never be written.

**(b) Guard row 239 promises a field three other places don't declare.** It
states: *"Every mutation records `actor` (gui|cli|agent) **and** `author`
(human|agent|llm) — and module 22 + the module 34 strip render it."* But:

- module 4's signature is `append(slug, actor, action, detail, rev_before, rev_after)` — no `author`;
- module 22's entry shape is `{at, actor, action, detail, rev_before, rev_after}` — no `author`;
- step 4's `plan_journal` row is the same six keys — no `author`.

Consequence for the PRD: module 22's stated purpose is answering *"the agent
reordered my mix — what did it do?"*, and module 34 renders that as the "What
changed" strip. As specified, an agent's edit is journaled `actor=cli`,
indistinguishable from you typing the same command in a terminal. The strip can
show *what* changed but not *who* changed it — which is the half R11 is about.

**Fix (amendment, no new module):** pick one, don't ship both half-done.
- *Preferred* — `plan_cli` takes `--actor {cli,agent}` (or reads a
  `CLAW_DJ_ACTOR` env var so a harness sets it once), defaulting to `cli`;
  `AGENTS.md` / `agent/hermes-skill/SKILL.md` (integration row 222) must require
  agents to pass `agent`. Zero schema change; makes the existing enum value real.
- *Or* — add `author` to module 4's signature, module 22's entry shape, and step
  4's journal record, and have module 34 render it. Larger, and duplicates what
  `actor` already almost says.

Either way, drop the unsupported half of guard row 239 so a later step doesn't
cite it as authority for a field that isn't in any interface.

## Gap 3 — ERROR: two modules declare interfaces they lack the dependencies to implement

Under PDD the dependency list *is* the generation contract, so an undeclared edge
is not a documentation nit — the generated module won't have the import.

- **Module 11 (`order_constraints`)** — deps `[plan_types, bunch_store]`, but its
  interface exports **`from_activations(slug) -> OrderConstraints`**. Resolving a
  slug to its activated bunches requires module 8 (`plan_bunch_activation`) and
  `plan_paths`; neither is declared. The likely generation outcome is module 11
  re-implementing `bunches.json` reading — directly against the design's own rule
  that *"the disjointness gate lives here [module 8] and nowhere else."*
- **Module 23 (`api_plan_arrange`)** — promises *"active bunches with member
  spans"*, which is a join of activations to library bunches. Module 28 does the
  same join and correctly declares **both** `bunch_store` and
  `plan_bunch_activation`; module 23 declares only the latter. `bunch_store` is
  missing, and `plan_paths` is reachable only transitively through
  `plan_mix_envelope → plan_revision`.

Both are priority-safe: 8 (< 11) and 7 (< 23), so adding the edges creates no
cycle and forces no renumbering.

**Fix:** add `plan_bunch_activation` + `plan_paths` to module 11; add
`bunch_store` + `plan_paths` to module 23. Alternatively move `from_activations`
out of 11 into 13, which already depends on both — but declaring the edges is
smaller.

## Gap 4 — ERROR: journal writes with no journal dependency, and a plan-scoped journal asked to hold library-scoped events

- **Module 13 (`plan_mix_build`)** — acceptance criteria say it *"writes to
  `plans/<slug>/mix_plan.json` **with a journal entry**"*, but its dependency
  list `[plan_paths, plan_notes, transition_overrides, order_constraints,
  plan_mix_envelope]` omits `plan_journal` (4). Same class as Gap 3; 4 < 13, so
  the edge is free.
- **Modules 7 and 30** — both specify that a bunch falling below 2 members
  *"auto-archives with a journal entry"* (step 4 says the same). But the only
  journal in the design is **plan-scoped**, `plans/<slug>/journal.jsonl`, and
  `bunches` are **library-scoped** by the deliberate Blocker-1 asymmetry. A
  library bunch has no owning plan, so there is no file for that entry to land
  in, and neither module declares `plan_journal` either.

**Fix:** add `plan_journal` to module 13. For the bunch case, settle where a
library-scoped event goes — the cheapest consistent answer is to journal the
archival into **every plan that currently activates that bunch** (module 8
already knows them, and that is where the consequence is felt), and to say so in
modules 7 and 30 rather than leaving "a journal entry" unaddressed.

## Gap 5 — R2/R3 PARTIAL: archiving the **active** plan is unspecified

The round-2 R2 fix is otherwise complete, but three criteria don't compose:

- module 5 — `set_status(slug, "archived")` *"leaves the directory in place
  (archived ≠ deleted)"*, and says nothing about `active.json`;
- module 18 — *"archived plans are excluded by default"*, so the picker (33)
  stops listing it;
- module 19 / module 2 — `set_active` and `resolve()` with no slug still point at
  it.

Archive the plan you're working on and the GUI is scoped to a plan the picker no
longer shows: the Arrange tab keeps rendering it, and there is no listed entry to
switch away *from*. That is a dangling-pointer state of the same family as the
route shadowing round 2 caught, and it lands on both R2 and R3.

**Fix (amendment, no new module):** add one acceptance criterion to module 5 —
archiving the active plan either clears `active.json` (and the GUI shows an
explicit "no plan selected" state) or is refused with a named error telling you
to switch first. Pick one; also add to module 19 that activating an archived plan
is rejected rather than silently re-pointing at a hidden plan.

---

## Smaller inconsistencies — worth fixing in the same pass, not gate-blocking

- **`plan_store.purge()` has no caller anywhere** — no HTTP route, no CLI verb
  (module 31's verb list has neither `delete` nor `purge`). Hard delete is
  reachable only from Python. Either add a CLI verb or state that purge is
  intentionally not exposed, so a later step doesn't invent a route for it.
- **Guard row 232's range `20–31`** as "every mutating module" sweeps in modules
  22 and 23, which are GET-only. Cosmetic, but the row is what a generation step
  will read to decide whether a handler needs `base_rev`.

## What checked out

- **Round-1 gaps genuinely closed.** R2 now has a writer end to end (1 → 5 → 20 →
  31 → 33); `plan_cli transition get|set|clear` exists and is required by the docs
  row; the router has literal-outranks-param **with** an adversarial
  registration-order test, plus `RESERVED_SLUGS`. Applying both shadowing
  defenses rather than one was the right call — the disk-side collision
  (`plans/active/` beside `active.json`) is not addressed by the router rule.
- **Route 1:1** — 14 distinct URL patterns, 14 modules, nothing collapsed;
  `/api/plans/<slug>/duplicate|journal|arrange|order|tracks|notes|transitions|bunches`
  each own a module.
- **Acyclic, valid topological sort** — every declared dependency has a strictly
  lower priority than its dependent. The Gap 3/4 additions preserve this.
- **Entity CRUD** — plan, bunch, `bunch_members`, activation, note override,
  transition override, journal, active pointer all have create/read/update and a
  soft-delete path where deletion is meaningful.
- **Wiring** — route registration (row 206), `/web/<file>` static serving,
  `brain/api/__init__.py` marker, entry-point delegation for the GUI mix paths
  (row 210, the highest-value row in the table), nav insertion, and the harness
  docs row. No orphan modules.
- **Commonly-missed** — error handling (16), migrations (15 + 7 + `user_version`),
  logging/audit (4, 22), pagination (22), loading state (34), shared types (1),
  API client (32). Auth, settings, admin, search, upload, rate limiting, and env
  config are correctly **N/A** for a single-user localhost server — and the
  design says so explicitly rather than silently omitting them, which is what
  keeps a later step from bolting on an auth module.
- **The load-bearing idea survived.** Overlap-legal-in-library /
  disjoint-per-plan is intact in modules 7, 8, and 29; step 4 flagged this as the
  one thing a "simplifying" later step would destroy.

## Still open (product calls, not coverage gaps)

Archives-as-importable-plans (gap #8, deferred) and switching plans mid-live-run
(gap #11, designed as refuse-with-409). Neither blocks this gate.

---

**VALIDATION_RESULT: INVALID** — 5 gaps, all amendments to existing modules.
Re-run Step 5 to fold them in; do not add modules or renumber.
