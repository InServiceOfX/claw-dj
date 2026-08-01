# Step 2: Deep Analysis

Intent: [`i-need-a-way-to-plan-out-multiple-mix-plans-that-fe78e160`](intent__i-need-a-way-to-plan-out-multiple-mix-plans-that-fe78e160.md)
Workflow: agentic architecture, step 2 of 13.
Previous step: [`…__step1-prd.md`](analysis__i-need-a-way-to-plan-out-multiple-mix-plans-that-fe78e160__step1-prd.md)

Output target: the workflow prescribed `gh issue comment 3953181291 --repo /`. Not executable
here, for the same reasons recorded in step 1, re-verified now: `gh auth status` reports "You
are not logged into any GitHub hosts", `--repo /` is not a repository, and the intent's source
kind is `inline` (no GitHub issue exists to comment on). This file is the step-2 output in its
place.

**Status:** Analysis Complete

---

## Correction to Step 1 (found while decomposing feature 8)

Step 1 asserted that the three orderers "have no constraint input today." That is **wrong for
one of them**, and the correction changes the shape of the bunch work substantially.

`brain/mix_order_brief.py` already implements an order-constraint vocabulary:
`{use_only, opener_id, adjacent, adjacent_ordered, regions, notes}` (`_normalize_constraints`,
`142-196`), applied deterministically by `apply_constraints` (`245-301`) via `force_adjacent`
(`199-220`) and `place_block_in_region` (`223-242`), and recorded as provenance in the built
plan (`brain/build_mix_plan.py:1728-1736`).

So an "adjacent, in this exact order" primitive exists. It is not usable as-is for five
specific reasons, and each one is a requirement on the new module:

1. **Pairwise, not n-ary.** `adjacent` is a list of 2-tuples. A 4-song bunch must be encoded
   as a chain of pairs, and `force_adjacent` is applied one pair at a time by re-anchoring
   around `min(i_left, i_right)` — applying `(A,B)` then `(B,C)` can displace `A`. Nothing
   verifies the post-condition, so a chain can silently fail to produce a contiguous run.
2. **`adjacent_ordered` is one global boolean** (`193`), not per-group. You cannot say "these
   three are in exact order, that other pair may go either way." The PRD explicitly wants
   *exact* internal order, per bunch.
3. **Ephemeral and LLM-derived.** Constraints are parsed out of an LLM reply per build
   (`order_from_brief`, `304+`) and survive only as provenance. There is no durable,
   human-authored constraint record — which is exactly what the PRD asks for.
4. **Repair-after-the-fact, not constraint-aware search.** `apply_constraints` runs
   `greedy_mix_order` over the whole pool *first*, then forcibly splices pairs together
   (`275-283`). The tour never scores the bunch as a unit, so the seams *into* and *out of*
   the forced run are whatever the splice produced, with no rescore.
5. **Only reachable on one of three paths.** It runs only when `order_engine != "none"`. The
   GUI's `mix_order` calls `greedy_mix_order` directly (`brain/playlist_editor.py:533-557`),
   and the `mix_directives` reorder path validates only that the result is an exact
   permutation (`brain/mix_directives.py:208-247`). Both would happily break a bunch.

Net effect: bunches are a **promotion and generalization** of an existing ephemeral concept,
not greenfield — but the enforcement surface (three orderers, one shared post-condition
check) is genuinely new. Step 1's conclusions about plan identity, per-plan `dj_notes`, and
editable transitions are unaffected and still hold.

---

## Architecting assumptions (Step 1's blocking gaps, resolved provisionally)

Step 1 ended by asking whether to settle gaps #1 and #9 before proceeding. Step 2 cannot
produce module boundaries without answers, so it adopts the following. **Each is a
recommendation, not a decision — flag any you disagree with and the affected modules change.**

| Gap | Decision taken | Why this one |
|-----|----------------|--------------|
| #1 per-plan `dj_notes` | **Override layer.** `tracks.dj_notes` stays the global default; a plan may store a sparse per-track override. Effective note = plan override ?? global. | The only option satisfying both constraints at once: notes diverge per plan (PRD), *and* no existing hand-verified note is orphaned or moved — which the sibling intent `portable-music-collection-…-288cef1d` requires explicitly. Moving notes into the plan breaks `load_dj_notes_lookup` (`brain/build_mix_plan.py:101-108`) and the enrichment reuse the global column exists to provide. |
| #2 editable transitions | **Sparse overrides merged over derived segments.** `compose_mix_plan` keeps computing `segments`; a plan stores overrides keyed by the `(from_track_id, to_track_id)` pair, merged after composition and marked `pinned` in the payload. | Keeps the derivation pipeline authoritative (it encodes real beatgrid/phrase/lyric analysis) while making "adjust *this* transition" a first-class, rebuild-surviving action. Keying by track pair rather than segment index means an override survives a reorder of unrelated tracks. |
| #3 what a WIP plan *is* | **All three stages**, in one directory per plan: selection → finalized → built. Switching never auto-rebuilds; a stale built plan shows a badge (reuse `_plan_stale`, `brain/playlist_editor.py:619-635`). | The PRD wants switching to be cheap and non-destructive. Auto-rebuild on switch would be a multi-second surprise and would trip the live-run guard. |
| #7 how agents address a plan | **Active-plan pointer file** read by every module, plus an explicit `--plan <slug>` override on CLI entrypoints. Env var only as an escape hatch, not the primary mechanism. | Agents edit out-of-band with plain file tools; a pointer file is greppable and inspectable. An env var alone would make a harness's plan invisible to the GUI. |
| #9 tab vs. picker | **Both, but different levels.** A plan picker in the header, *above* the nav, scoping both existing steps; plus a third tab `3 · Arrange` for order/bunches/transitions. `#curate` and `#mix` hash routes unchanged; add `#arrange`. | A plan is a *scope*, not a step — modelling it as `3 · …` in a numbered linear wizard tells the user to do it last, which is backwards. This answers the PRD's own open question ("Should we have another tab…"). |
| #12 plan store layout | **Directory-per-plan** at `brain/data/plans/<slug>/`, JSON files, not SQLite rows. | The PRD implicitly requires an external agent harness to read and write a plan with plain file tools. SQLite would force every harness through a client. Also keeps plans inside the already-gitignored `brain/data/`. |

---

## Feature Decomposition

| Feature (Step 1 #) | Functional Units | Candidate Module |
|---|---|---|
| 1, 2, 3 — several named plans, create / switch / rename / duplicate / delete | slugify colloquial name; plan metadata record; directory layout; list; create; activate; rename; duplicate; soft-delete; active-plan pointer read/write | `plan_store` |
| 1, 7 — every existing consumer must stop hardcoding singletons | resolve `(selection, playlist, mix_plan, exclusions)` paths for a plan; precedence `explicit --plan` > pointer file > legacy singleton; legacy fallback when no plan store exists | `plan_paths` |
| 7 — agent edits + GUI refresh without lost updates | compute a revision token per plan file (mtime+size+hash); compare-and-swap write; `changed underneath you` conflict result; drop `PlaylistApp`'s unconditional in-memory authority | `plan_revision` |
| 5 — per-plan dj_notes | read effective notes for a plan (override ?? global); write an override; clear an override back to global; expose provenance (`which layer won`) to the UI and to `mix_directives` | `plan_notes` |
| 8 — bunches | bunch record (id, ordered member list, label); validation: members ⊆ plan, groups pairwise disjoint, ≥2 members; integrity on member removal / unavailable file; group / ungroup / move-as-unit | `plan_bunches` |
| 8 — bunches honored by all three orderers | n-ary contiguity+order constraint type; constraint-aware wrapper over `greedy_mix_order`; permutation validator extension for `mix_directives`; post-condition check `assert_bunches_intact(order)`; generalize `adjacent`/`adjacent_ordered` from `mix_order_brief` | `order_constraints` |
| 6 — adjust transitions and effects | override record keyed by track pair; merge over derived `segments`; validate endpoints are adjacent in the current order; drop/quarantine an override whose pair is no longer adjacent | `transition_overrides` |
| 1, 5 — adopt existing state without loss | promote current `playlist_selection.json` / `playlist.json` / `mix_plan.json` into plan #1; backfill notes layer; optionally import `brain/data/archives/*` as plans; fail loudly and atomically on partial migration | `plan_migration` |
| 3, 4, 7, 9 — HTTP surface | plan CRUD routes; plan-scoped versions of existing routes; rev token in every plan-mutating request/response; live-run guard on switch and delete | `plan_api` (retrofit of `brain/playlist_editor.py`) |
| 9, 10 — GUI | header plan picker; `3 · Arrange` tab; order list with drag-reorder; bunch grouping affordance + move-as-unit; per-transition editor; refresh that reconciles rev tokens | `plan_ui` (`brain/web/playlist.html`) |

Features 4 (add/remove songs) and 10 (render order + transitions) are deliberately **not**
their own modules — 4 becomes plan-scoping applied to the existing `set_enabled` /
`apply_picks` / `playlist_edit` paths (it lives in `plan_paths` + `plan_api`), and 10 is a
richer payload from `plan_summary` plus rendering (`plan_api` + `plan_ui`). Making either a
module would create a boundary with no independent logic behind it.

---

## Shared Concerns

- **Auth:** none, and none introduced. The server binds `127.0.0.1:8787`
  (`brain/playlist_editor.py:1418`, `scripts/start.sh:14`), single local user, no credentials
  anywhere in the repo, and the PRD implies no multi-user story. The only authorization-shaped
  rule is the existing **live-run guard** — `build_mix` refuses while a mix is playing
  (`1118-1119`) — which must be extended to plan switch, plan delete, and any write to the
  plan a run is currently reading. Treat it as a state guard, not auth.
- **Error handling:** repo posture is **fail loud, never silently corrupt** — the sibling
  intent states it outright ("a partial migration must fail loudly rather than silently
  duplicate rows or drop lookups"), and `mix_directives` already raises rather than repairing
  a bad LLM reply. Existing mechanics: HTTP handlers return `{"error": "..."}` JSON with a
  status; long operations run on threads and expose a polled status dict (`ingest_status`,
  `brain_status`, `directives_status`, `mix_status`). New error classes needed:
  `StalePlanError` (rev mismatch → conflict response carrying the current rev, never a
  blind overwrite), `BunchViolationError` (an orderer produced a split bunch — reject, do not
  auto-repair, consistent with the exact-permutation rule), `PlanNotFoundError`, and a
  migration abort that leaves the legacy singleton files untouched.
- **Validation:** two hard rules already exist in `brain/mix_directives.py:1-27` and must be
  preserved and extended, not replaced — (a) every returned `track_id` is validated against the
  finalized playlist, (b) a reorder must be an exact permutation. Extensions: plan slug
  charset + uniqueness; bunch groups pairwise disjoint with members ⊆ plan; a permutation must
  additionally preserve every bunch's contiguity and internal order; a transition override's
  two endpoints must be adjacent in the current order; an override layer may only name
  `track_id`s present in the plan.
- **Logging / observability:** HTTP request logging is deliberately suppressed
  (`log_message`, `1409`). Provenance is the real observability story here — `archive_mix_plan`
  writes `manifest.json` + `RUN.md` with sha256 and git metadata (`26-40`, `76-103`), and
  `build_mix_plan` records `profile_provenance` / `format_provenance` / `order_constraints`
  into the plan (`1728-1736`). New plan mutations should follow that precedent: an append-only
  per-plan change journal recording *who* changed what (human / GUI / `mix_directives` /
  external harness), which is what makes "press refresh and see what the agent did" legible
  rather than mysterious.
- **Configuration:** today configuration *is* the module-level path constants —
  `brain/playlist.py:12-17`, `brain/playlist_editor.py:30-34`, `brain/archive_mix_plan.py:14-16`
  — which is precisely what this feature dismantles. `plan_paths` becomes the single
  configuration seam. No new environment variables; existing `CLAWDJ_LLM_BASE_URL` /
  `CLAWDJ_LLM_API_KEY` / `CLAWDJ_LLM_MODEL` already cover the conversational path.

---

## Tech Stack (Confirmed)

No ambiguity to resolve. The PRD says `Technology: not stated`, but the repository fixes every
choice, and the PRD's own constraints (a GUI at `http://127.0.0.1:8787/#curate`, agents editing
out-of-band) confirm rather than challenge them.

- **Language / runtime:** Python 3, `uv` for env and deps (`pyproject.toml`, `uv.lock`).
- **Server:** stdlib `http.server.BaseHTTPRequestHandler` with hand-rolled path dispatch
  (`brain/playlist_editor.py:1248-1408`), `threading` for background work. **No web framework
  is to be introduced** — 27 existing routes are string-compared in two `if` ladders, and the
  ~12 new plan routes must follow that idiom.
- **Frontend:** one hand-written HTML/CSS/vanilla-JS file (`brain/web/playlist.html`, 863
  lines), served whole at `/`, routed by `location.hash` (`268`, `357`, `856`). No framework,
  no bundler, no build step. Note there is currently **no drag-and-drop anywhere** in that file
  — manual reordering is new UI, not a tweak.
- **Persistence:** SQLite at `brain/data/library.sqlite3`, schema literal in
  `brain/library_index.py:18-120` with additive `ALTER TABLE` migrations guarded by
  `PRAGMA table_info` (`124-140`) — that is the established migration pattern for anything that
  lands in the DB. Plan state stays plain JSON under `brain/data/` (gitignored).
- **LLM:** pluggable engines `nemoclaw` / `h-agent` / `generic` via `brain/pick_candidates.py`;
  `litellm_cache.sqlite` at repo root.
- **Tests:** `unittest` + `tempfile.TemporaryDirectory` with injected paths
  (`tests/test_mix_plan.py`, `tests/test_mix_directives.py`,
  `tests/test_music_collection_identity.py`).

**Constraint on module design that follows from the stack:** `brain/playlist_editor.py` is
~1420 lines and `brain/web/playlist.html` is 863; both are already at the edge of what a single
PDD prompt can regenerate coherently. Step 4/5 should expect to split the web asset (at
minimum, extract the JS) rather than grow it by another few hundred lines.

---

## Module Candidates

**Foundational (no dependencies on other new modules):**

1. **`plan_store`** — plan identity and lifecycle. Owns the `brain/data/plans/<slug>/` layout,
   the plan metadata record (slug, colloquial name, created/updated, notes, soft-delete flag),
   the active-plan pointer, and create/list/get/rename/duplicate/delete. Knows nothing about
   tracks, bunches, or transitions.
2. **`plan_revision`** — concurrency primitive. Computes a revision token for a plan file, and
   provides read-with-rev / compare-and-swap-write / conflict detection. Pure filesystem, no
   plan semantics. This is the module that makes "an agent edited it, press refresh" correct
   instead of a lost-update race.
3. **`plan_bunches`** — the bunch data type and its invariants: ordered member list, disjoint
   groups, membership validation, integrity policy under member removal. Pure data + rules, no
   I/O, no ordering algorithms.
4. **`transition_overrides`** — the transition-override data type and the merge function over a
   derived `segments` list. Pure data + merge, no composition logic.

**Dependent:**

5. **`plan_paths`** (→ `plan_store`) — resolves the four file paths for a plan, with the
   precedence chain and the legacy-singleton fallback. Thin, but it is the seam every existing
   module touches (`build_mix_plan`, `run_mix_plan`, `preview_transitions`, `archive_mix_plan`,
   `attended_mix_run`, `playlist`, `playlist_edit`, `mix_directives`), so it earns its own
   boundary. *Merge candidate:* could fold into `plan_store` if step 4 finds the interface is
   two functions.
6. **`plan_notes`** (→ `plan_store`, `brain/library_index`) — the per-plan `dj_notes` override
   layer, effective-note resolution, and layer provenance.
7. **`order_constraints`** (→ `plan_bunches`; consumed by `mix_graph`, `mix_directives`,
   `build_mix_plan`) — turns bunches into an n-ary contiguity+order constraint, enforces it
   across all three ordering paths, and supplies the shared post-condition check. Generalizes
   the pairwise `adjacent` / global `adjacent_ordered` vocabulary already in
   `brain/mix_order_brief.py` (see the correction section). **The riskiest module** — it is the
   one that changes behavior inside existing, working, ear-tested ordering code.
8. **`plan_migration`** (→ all of 1–7) — one-way adoption of the current singleton state as
   plan #1, notes backfill, optional archive import. Atomic or aborted; never partial.
9. **`plan_api`** (→ all) — retrofit of `brain/playlist_editor.py`: plan CRUD routes, plan
   scoping for the existing routes, rev tokens threaded through every mutation, live-run
   guards. Also where `PlaylistApp`'s in-memory `self.selection` / `self.selected` / `self.by_id`
   stops being authoritative.
10. **`plan_ui`** (→ `plan_api`) — header plan picker, `3 · Arrange` tab, drag-reorder, bunch
    grouping and move-as-unit, per-transition editor, rev-aware refresh.

Suggested build order: 1–4 in parallel → 5, 6, 7 → 8 → 9 → 10. `order_constraints` (7) is on
the critical path and should get research attention in step 3 disproportionate to its size.

---

## Inter-Module Interfaces

- `plan_paths` → `plan_store`: `resolve(slug | None) -> PlanPaths(selection, playlist, mix_plan, exclusions)`; falls back to legacy singletons when no plan store exists.
- `plan_store` → `plan_revision`: every plan read returns `(payload, rev)`; every write takes an expected `rev` and raises `StalePlanError` on mismatch.
- `plan_notes` → `plan_store` + `library_index`: `effective_notes(slug) -> {track_id: (note, layer)}`; `set_override(slug, track_id, note, expected_rev)`.
- `order_constraints` → `plan_bunches`: `constraints_for(slug) -> OrderConstraints(groups=[[track_id,…],…])`.
- `mix_graph.greedy_mix_order` ← `order_constraints`: new optional `constraints=` keyword; bunches enter the tour as a single super-node (entry key/BPM from the first member, exit from the last) so seams are *scored*, not spliced.
- `mix_directives.parse_directives` ← `order_constraints`: the existing exact-permutation check gains a bunch-intact check; violation raises rather than repairs.
- `build_mix_plan.compose_mix_plan` ← `order_constraints` + `plan_notes` + `transition_overrides`: constraints feed the DJ-format planner; notes come from the plan layer instead of `load_dj_notes_lookup`'s global read; overrides merge over `segments` after composition.
- `mix_order_brief.apply_constraints` ← `order_constraints`: LLM-derived and human-authored constraints merge into one object; human bunches win on conflict.
- `plan_api` → everything: routes call the modules; no route touches a path constant directly.
- `plan_ui` → `plan_api`: JSON over `fetch`, `rev` echoed on every mutation; a 409-style response drives a "changed underneath you — reload?" prompt instead of a silent overwrite.
- `plan_migration` → `plan_store` + `plan_notes` + legacy paths: read-only on the legacy files until the whole migration commits.

---

## Cross-Cutting Concerns (from PRD)

- **Auth / access control:** not needed by any module. The *state guard* (refuse while a mix is
  running) is needed by `plan_api` (switch, delete) and `plan_store` (delete).
- **Error handling:** every module. `plan_revision`, `plan_migration`, and `order_constraints`
  carry the fail-loud burden — they are the three places where silent success would corrupt
  irreplaceable human work (`dj_notes`, plan order).
- **Logging / provenance:** `plan_store` (change journal), `plan_api` (attribution: which
  actor), `build_mix_plan` (existing provenance block extended with bunch + override
  provenance).
- **Validation:** `plan_store` (slug), `plan_bunches` (disjointness, membership),
  `order_constraints` (permutation + bunch intact), `transition_overrides` (adjacency),
  `plan_notes` (track membership), `plan_api` (request shape).
- **Concurrency / staleness:** `plan_revision` owns it; `plan_api` and `plan_ui` must honor it;
  every CLI writer (`playlist_edit`, `mix_directives`, `build_mix_plan`) must pass a rev or
  explicitly opt out. This is the cross-cutting concern the PRD cares most about without naming
  it — "I can press refresh and see the refreshed order" is a consistency requirement.
- **Portability:** inherited from the sibling intent. Plans reference `track_id` = absolute
  file path, so a plan is only meaningful where the collection mounts identically. `plan_store`
  should record the collection id alongside the plan so a mismatch is detectable rather than
  mysterious.

---

## Identified Shared Identifiers

**Database tables (existing, in `brain/library_index.py:18-120`):** `tracks` (carries the
global `dj_notes` column, line 32), `roots`, `collections`, `lyrics`, `chroma`, `phrases`,
`beat_phase`, `lyric_timelines`, `scan_state`.

**New persisted structures** — files, not tables, per the layout decision:
`brain/data/plans/index.json` (plan registry + active pointer),
`brain/data/plans/<slug>/plan.json` (metadata),
`brain/data/plans/<slug>/selection.json`, `…/playlist.json`, `…/mix_plan.json`,
`…/exclusions.json`, `…/notes.json` (override layer), `…/bunches.json`,
`…/transitions.json` (overrides), `…/journal.jsonl` (change log).

**API endpoints (existing):** `GET /api/meta|tracks|ingest|brain|directives|mix`;
`POST /api/selection|selection/clear|seed|mix-order|export|ingest/scan|ingest/add-root|brain/ask|brain/apply|directives/ask|directives/apply|suggest|mix/build|mix/start|mix/sync|mix/enrich|mix/refresh|mix/rescan-tags|mix/shuffle-opener`.

**API endpoints (new, proposed):** `GET /api/plans`, `GET /api/plan`,
`POST /api/plans/create|activate|rename|duplicate|delete`,
`POST /api/plan/order`, `POST /api/plan/bunch|bunch/delete|bunch/move`,
`POST /api/plan/transition`, `POST /api/plan/notes`. Existing plan-scoped routes gain an
optional `plan` field and a required `rev` on mutations.

**Shared types:** existing — `Track`, `SeedMatch` (`brain/playlist.py:26`), `MixEdge`
(`brain/mix_graph.py:76`), `MixProfile` (`brain/mix_profiles.py:20`), `DjFormat`
(`brain/dj_formats.py:19`), the `segment` dict `{index, from, to, technique, beats, score,
showcase_move, format_compliance}`, the mix-plan v2 envelope `{version, track_count,
seconds_per_track, profile, dj_format, phrase_interval_beats, tracks, segments, events,
instrument_map}`, and the constraints dict `{use_only, opener_id, adjacent, adjacent_ordered,
regions, notes}`. New — `PlanId`/slug, `PlanMeta`, `PlanPaths`, `Rev`, `Bunch`,
`OrderConstraints`, `TransitionOverride`, `NoteLayer`.

**Environment variables:** existing `CLAWDJ_LLM_BASE_URL`, `CLAWDJ_LLM_API_KEY`,
`CLAWDJ_LLM_MODEL`. None new required (an optional `CLAWDJ_PLAN` escape hatch is noted but not
recommended as the primary addressing mechanism).

**Mix-plan version bump:** `mix_plan.json` is `version: 2`. Merged transition overrides and
bunch provenance change its shape → step 4 should plan a `version: 3` and a reader that
tolerates 2.

---

## Open questions carried into Step 3

Answered here provisionally (see the assumptions table): gaps #1, #2, #3, #7, #9, #12.
Still genuinely open and needing research or a product call:

- **Bunch scope** (step 1 gap #4): plan-local or a reusable library object? "They sound very
  good with each other" is a durable musical fact about the *songs*, which argues for a
  library-level object referenced by plans. This changes whether `plan_bunches` is foundational
  or sits on `library_index`. **Recommend deciding before step 4.**
- **Bunch integrity on member removal** (gap #5): shrink, dissolve, or block? Suggest shrink
  with a journal entry, dissolve at <2 members.
- **Archives vs. named plans** (gap #8): does auto-archive-before-rebuild
  (`brain/playlist_editor.py:1131-1150`) become per-plan version history, or go away as
  redundant once plans are non-destructive?
- **Switching during a live run** (gap #11): refuse, or isolate the running plan's files?
- **Plan lifecycle policy** (gap #10): retention, soft vs. hard delete, plans whose tracks are
  no longer available.

---
*Proceeding to Step 3: Research*
