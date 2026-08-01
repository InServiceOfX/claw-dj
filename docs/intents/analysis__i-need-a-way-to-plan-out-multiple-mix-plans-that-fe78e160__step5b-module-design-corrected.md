# Step 5: Module Design (Corrected)

**Status:** Design Complete

Intent: `i-need-a-way-to-plan-out-multiple-mix-plans-that-fe78e160`
Supersedes: `…__step5-design.md` (which still carries the round-1 gaps — kept for comparison, do not feed to Step 6).

> **On `gh issue comment 3953181291 --repo /`:** not executed. `gh auth status` reports "not logged into any GitHub hosts", `GH_TOKEN` is unset, `--repo /` is not a repo spec, and the intent's source kind is `inline` — no GitHub issue exists. File output, same precedent as steps 1–5.

## What changed in this round

The completeness gate found 3 partial requirements and 1 consistency error, and concluded **all three fixes are amendments to existing modules — no new module is warranted.** I agree, and added none. Adding a module per gap here would have produced e.g. a `plan_status` module that depends on `plan_store` and is consumed by one route to set one field; that is a worse design than a `set_status` method on the module that already owns every other `plan.json` write.

Priorities therefore remain **1–35, unchanged**. The amendments are marked **[R2 fix]**, **[R8/R9 fix]**, and **[shadowing fix]** in the table below.

Carried forward from round 1 and still load-bearing:

- **Naming rule:** under PDD, `api_plan_notes_Python.prompt` generates `api_plan_notes.py`. Modules 17–30 are named so prompt basename == filename, and `api_static_assets` lives in `brain/api/` with its 13 siblings. Step 7 would otherwise write to the wrong paths.
- **`PlanPaths` arity is 10**, canonical here and superseding step 4's abbreviated 8-member row: `root`, `plan_json`, `selection`, `exclusions`, `playlist`, `mix_plan`, `notes`, `bunches`, `transitions`, `journal`.

---

### Module List

| Priority | Module (filename) | Filepath | Dependencies | Interface Type | Acceptance Criteria |
|---|---|---|---|---|---|
| 1 | `plan_types_Python.prompt` | `brain/plan_types.py` | [] | module (shared types) | `PlanMeta`, `PlanPaths`, `Rev`, `Bunch`, `OrderConstraints`, `TransitionOverride`, `EffectiveNote` importable as frozen dataclasses; `validate_slug("2001 Mix")` raises, `slugify("2001 expanded 25th anniversary mix")` → `2001-expanded-25th-anniversary-mix`; `header_safe(name)` strips CR/LF; no imports outside stdlib, no I/O. **[R2 fix]** Adds `PlanStatus` with exactly `wip`\|`ready`\|`archived` — `wip` is **PRD-sourced** (*"work in progress"*), `ready` and `archived` are **design-sourced**; do not back-attribute the latter two to the PRD. **[shadowing fix]** Adds `RESERVED_SLUGS = {"active", "trash"}` plus a leading-dot rule; `slugify("Active")` must **not** return `active` — it routes through the same `-2`/`-3` collision path as a duplicate name, because a slug of `active` collides with both the `/api/plans/active` route and `plan_paths.resolve()`'s `active.json` read. **Tests needed:** every `PlanStatus` value round-trips through `plan.json`; `slugify` on each reserved word and on `".hidden"` yields a non-reserved slug |
| 2 | `plan_paths_Python.prompt` | `brain/plan_paths.py` | [plan_types] | module | `DEFAULT_PLANS_DIR` module constant patchable by tests; `resolve(slug)` returns a `PlanPaths` with **all 10 declared members** under `plans/<slug>/`; `resolve()` with no slug reads `active.json`, falling back to the legacy singletons when no plans dir exists; traversal attempt (`../`, absolute) raises rather than escaping the plans dir |
| 3 | `plan_revision_Python.prompt` | `brain/plan_revision.py` | [plan_types, plan_paths] | module | `file_rev(path)` = `hashlib.file_digest` sha256 hex, `""` for a missing file; `plan_rev(paths)` = digest over per-file digests in fixed key order; `write_checked(path, data, base_rev)` atomic-replaces via temp-in-same-dir + `os.replace` and raises `StalePlanError` carrying `{current_rev, changed_files, summary}`; two writes inside one filesystem tick produce different revs |
| 4 | `plan_journal_Python.prompt` | `brain/plan_journal.py` | [plan_paths] | module | `append(slug, actor, action, detail, rev_before, rev_after)` writes one compact JSON line, `O_APPEND`, no read-modify-write; `read(slug, limit)` returns newest-first and tolerates a truncated final line instead of raising; unknown `actor` outside `gui`\|`cli`\|`agent` rejected |
| 5 | `plan_store_Python.prompt` | `brain/plan_store.py` | [plan_types, plan_paths, plan_revision, plan_journal] | module | `create/list/get/rename/duplicate/delete/purge/set_active/get_active`; `list()` is a **directory scan** of `plans/*/plan.json`, no registry file; `rename` changes `display_name` only; `duplicate` uses `shutil.copytree` (3.13-compatible) with fresh `plan_id`, `origin=duplicated`; `delete` moves to `plans/.trash/<slug>/` + tombstone, never `rm -rf`; slug collision appends `-2`, `-3`. **[R2 fix]** Adds **`set_status(slug, status, base_rev)`** — the writer that R2 was missing; `create()` births a plan at `status="wip"` so the state is never unset; a value outside `PlanStatus` raises rather than being persisted; a status change is journaled like any other mutation; reserved slugs from module 1 go through the collision suffix. **Tests needed:** a plan created then read back reports `wip` without an explicit write; `set_status` with a stale `base_rev` → `StalePlanError`; `set_status(slug, "archived")` leaves the directory in place (archived ≠ deleted) |
| 6 | `plan_context_Python.prompt` | `brain/plan_context.py` | [plan_types, plan_paths, plan_store] | module | `for_request(query, body)` resolves scope in precedence order `body.plan` → `?plan=` → `active.json`; **stateless** — no caching, no module-level mutable state (the `PlaylistApp.selection` clobber bug is the reason); unknown slug → structured `PlanNotFound`; safe to call concurrently from `ThreadingHTTPServer` threads |
| 7 | `bunch_store_Python.prompt` | `brain/bunch_store.py` | [plan_types] *(+existing `brain/library_index`)* | module | Appends `bunches` + `bunch_members` `CREATE TABLE IF NOT EXISTS`; **sets `PRAGMA foreign_keys = ON` per connection** or the declared cascade is a no-op; **overlapping bunches are accepted**; a bunch below 2 members is archived with a journal note; every call uses `with closing(sqlite3.connect(db, timeout=30))` |
| 8 | `plan_bunch_activation_Python.prompt` | `brain/plan_bunch_activation.py` | [plan_paths, plan_revision, bunch_store] | module | `activate/deactivate/list_active` over `plans/<slug>/bunches.json`; **an activation intersecting an already-enabled bunch is rejected naming the conflicting `bunch_id`** — the disjointness gate lives here and nowhere else; `region` validated against imported `mix_order_brief.REGION_SLICES` (verified at `mix_order_brief.py:28`); archived-bunch activation returned with a warning flag, not pruned |
| 9 | `plan_notes_Python.prompt` | `brain/plan_notes.py` | [plan_paths, plan_revision] *(+existing `brain/library_index`)* | module | `get_effective(slug, track_ids)` → `EffectiveNote` with `layer` = `plan`\|`global` and `diverged`; `set_override/clear_override` **never write `tracks.dj_notes`**; clearing falls back to the global note, never to `""`; an override whose track is `available = 0` is retained and flagged. **Scope note:** these are **track**-scoped notes. Transition-scoped notes belong to module 10 — the distinction is what the CLI must surface (see module 31) |
| 10 | `transition_overrides_Python.prompt` | `brain/transition_overrides.py` | [plan_types, plan_paths, plan_revision] | module | Records stored as a **list keyed by the `(from_track_id, to_track_id)` pair**; `merge(segments, overrides)` patches only non-null fields and sets `overridden` + `override_fields`; `reconcile(order, overrides)` marks a non-adjacent pair `orphaned` and **restores it to `active` on re-adjacency**; `technique`/`showcase_move` are free strings (a closed enum breaks the runtime-composed `f"dj_format_{recipe}"` at `build_mix_plan.py:1288`) |
| 11 | `order_constraints_Python.prompt` | `brain/order_constraints.py` | [plan_types, bunch_store] | module | `contract(rows, groups)` collapses each n-ary group to one pseudo-track; `expand(order, table)` restores members; `assert_intact` raises on non-contiguity; chaining `(A,B)` then `(B,C)` yields `[A,B,C]` and **does not strand A** (the defect at `mix_order_brief.py:199`, verified); **no pseudo id may appear in any returned order** |
| 12 | `plan_mix_envelope_Python.prompt` | `brain/plan_mix_envelope.py` | [plan_types, plan_revision, plan_bunch_activation, plan_notes, transition_overrides] | module | `decorate(plan_dict, slug, paths)` returns a `version: 3` envelope adding `plan_id`, `plan_slug`, `dj_format`, `bunches[]` provenance, `source_revs{…}`; **readers accept 2 and 3**; does not narrow `event.op` (all 9 survive round-trip); pure function over a dict — does not import `build_mix_plan` |
| 13 | `plan_mix_build_Python.prompt` | `brain/plan_mix_build.py` | [plan_paths, plan_notes, transition_overrides, order_constraints, plan_mix_envelope] | module | Single plan-aware entry to mix composition, callable from both the GUI and the CLI: `build(slug, **opts)` resolves every path from `PlanPaths` (never `MIX_PLAN_PATH`/`DEFAULT_PLAYLIST_JSON`), injects effective notes + constraints + overrides, calls the existing `compose_mix_plan`, wraps the result through `decorate()`, and writes to `plans/<slug>/mix_plan.json` with a journal entry. `playlist_path(slug)` and `mix_plan_path(slug)` are exported so `start_mix`/`reexport_finalized`/`start_enrich` resolve the same way. **Tests needed:** building against plan A leaves plan B's `mix_plan.json` byte-identical; the written artifact is `version: 3` with populated `source_revs` on the GUI path, not only the CLI path. Exists as a module and not as an inline diff because `playlist_editor.py` (1437 lines) is past the single-prompt ceiling |
| 14 | `plan_staleness_Python.prompt` | `brain/plan_staleness.py` | [plan_paths, plan_revision, plan_mix_envelope] | module | `is_stale(slug)` compares `mix_plan.source_revs` to current file revs; **detects a changed dj_note, a changed transition, and a pure reorder** — the three cases `_plan_stale` (`playlist_editor.py:618-635`) is blind to; a v2 plan with no `source_revs` reports `stale=True, reason="no_source_revs"`; never triggers a rebuild itself |
| 15 | `plan_migration_Python.prompt` | `brain/plan_migration.py` | [plan_store, plan_bunch_activation, plan_notes, transition_overrides] | module | Promotes the legacy singletons into plan #1 with `origin=migrated` and `status="wip"`; **atomic or aborted**; guarded by `PRAGMA user_version` so a rerun is a no-op and a half-finished run is loud; `--dry-run` prints the backfill report and writes nothing |
| 16 | `api_router_Python.prompt` | `brain/api_router.py` | [plan_types, plan_context] | module (dispatch) | Replaces the literal `if self.path == …` chain (`playlist_editor.py:1262-1414`, 6 GET + 19 POST, exact match, **no path parameters**); `route(method, path)` matches `<param>` segments; **all 25 existing routes still resolve unchanged**; unknown path → 404, wrong method → 405; a handler raising `StalePlanError` becomes **409 with the conflict payload in the body**. **[shadowing fix]** New acceptance criterion: **a literal segment outranks a `<param>` segment at the same position regardless of registration order.** Without this rule, registration order silently decides whether `/api/plans/active` reaches module 19 or is swallowed by module 20's `<slug>` and 404s on an unknown plan. **Tests needed:** register module 20 (`/api/plans/<slug>`) *first*, then module 19 (`/api/plans/active`); assert `GET /api/plans/active` still dispatches to 19; assert `GET /api/plans/some-mix` still dispatches to 20 |
| 17 | `api_static_assets_Python.prompt` | `brain/api/api_static_assets.py` | [api_router] | api (`GET /web/<file>`) | Serves `brain/web/*.js` and `*.css` with correct `Content-Type`; path confined to `WEB_ROOT`, `..` and absolute rejected; `ETag`/304 |
| 18 | `api_plans_collection_Python.prompt` | `brain/api/api_plans_collection.py` | [plan_store, plan_staleness, api_router] | api (`GET,POST /api/plans`) | GET returns every plan with `slug`, `display_name`, `status`, `updated_at`, `track_count`, `stale`, sorted by `last_opened_at` desc; POST creates from `{display_name}` and returns the slug; duplicate display name allowed; empty name → 400, not 500. **[R2 fix]** `status` is now a `PlanStatus` value written by module 5, not a free string — a created plan comes back `wip` immediately; optional `?status=` filters the list. Archived plans are excluded by default and included with `?status=archived` |
| 19 | `api_plans_active_Python.prompt` | `brain/api/api_plans_active.py` | [plan_store, plan_context, api_router] | api (`GET,POST /api/plans/active`) | POST `{slug}` sets the pointer and returns the plan payload; **refuses with 409 while `app.mix_state.running`**; unknown slug → 404, pointer unchanged. **[shadowing fix]** Depends on module 16's literal-over-param precedence to be reachable at all — see module 16's test |
| 20 | `api_plan_detail_Python.prompt` | `brain/api/api_plan_detail.py` | [plan_store, plan_staleness, api_router] | api (`GET,POST /api/plans/<slug>`) | GET returns `PlanMeta` + `rev` + staleness with an `ETag` built from the rev — **slug-substituted, never `display_name`**; POST `{display_name}` renames without moving the directory; POST `{action:"delete"}` soft-deletes; every mutation carries `base_rev`, 409 on mismatch. **[R2 fix]** POST additionally accepts **`{status, base_rev}`** and delegates to `plan_store.set_status` — this is the HTTP write surface R2 lacked; a status outside `PlanStatus` → 400 naming the legal values, not 500. **Tests needed:** rename and status-set in separate requests both work; an unknown status string is rejected before any write touches disk |
| 21 | `api_plan_duplicate_Python.prompt` | `brain/api/api_plan_duplicate.py` | [plan_store, api_router] | api (`POST /api/plans/<slug>/duplicate`) | Copies the full directory including `notes.json` and `transitions.json`; fresh `plan_id` + `origin_ref`; the copy is born `wip` even when duplicating a `ready` plan; source byte-identical afterwards; uses on-disk state, never in-memory |
| 22 | `api_plan_journal_Python.prompt` | `brain/api/api_plan_journal.py` | [plan_journal, api_router] | api (`GET /api/plans/<slug>/journal`) | `?limit=` (default 50, cap 500), newest-first, each entry `{at, actor, action, detail, rev_before, rev_after}`; a plan with no journal returns `{entries: []}`, not 404; a truncated final line is skipped, not fatal. The read surface that makes `plan_journal` non-write-only and answers *"the agent reordered my mix — what did it do?"* |
| 23 | `api_plan_arrange_Python.prompt` | `brain/api/api_plan_arrange.py` | [plan_bunch_activation, plan_notes, transition_overrides, plan_mix_envelope, plan_staleness, api_router] | api (`GET /api/plans/<slug>/arrange`) | **The single read the `3 · Arrange` tab needs** — ordered tracks, effective notes with `layer`, derived-then-merged segments, active bunches with member spans, per-file revs, composite rev, staleness; one response, so refresh cannot show a half-updated view; a plan with no built mix returns the order with `segments: []` rather than 404 |
| 24 | `api_plan_order_Python.prompt` | `brain/api/api_plan_order.py` | [plan_revision, plan_bunch_activation, order_constraints, api_router] | api (`POST /api/plans/<slug>/order`) | `{track_ids[], base_rev}` full replacement (no index arithmetic to desync) and `{move_bunch, to_index}` for **move-as-a-unit**; 422 naming the group when the order breaks an active bunch; rejects a non-permutation of the current selection; calls `transition_overrides.reconcile` in the same write |
| 25 | `api_plan_tracks_Python.prompt` | `brain/api/api_plan_tracks.py` | [plan_revision, plan_paths, plan_journal, transition_overrides, api_router] | api (`POST /api/plans/<slug>/tracks`) | `{add: [track_id], remove: [track_id], base_rev}` in one rev-guarded write to `selection.json` + `exclusions.json`; returns the new rev and the resulting membership. Adds append at the end preserving existing order; removes drop the id from selection and from any active bunch (a bunch falling below 2 members deactivates with a named warning, never silently); calls `transition_overrides.reconcile` so a removal orphans rather than deletes its transitions; an `add` of an already-present id is a no-op, not a duplicate. **Tests needed:** add+remove of the same id in one body → 400; removal of the last member of an active bunch; stale `base_rev` → 409 with `changed_files` |
| 26 | `api_plan_notes_Python.prompt` | `brain/api/api_plan_notes.py` | [plan_revision, plan_notes, api_router] | api (`POST /api/plans/<slug>/notes`) | `{track_id, note, author, base_rev}` writes a **track**-scoped plan override; `{track_id, clear:true}` removes it and the response shows the global note that took over; `author` recorded so an LLM-written note is distinguishable; `tracks.dj_notes` untouched by every path |
| 27 | `api_plan_transitions_Python.prompt` | `brain/api/api_plan_transitions.py` | [plan_revision, transition_overrides, api_router] | api (`POST /api/plans/<slug>/transitions`) | Sparse patch `{from_track_id, to_track_id, technique?, beats?, showcase_move?, effects?, note?, base_rev}` — sending only `note` leaves the derived technique intact; a non-adjacent pair is accepted and stored `orphaned`; `{clear:true}` reverts the segment to derived. **[R8/R9]** This is the HTTP half of the LLM-edits-transitions requirement; module 31's `transition` verb is the offline half and must mirror this payload field-for-field |
| 28 | `api_plan_bunches_Python.prompt` | `brain/api/api_plan_bunches.py` | [plan_revision, bunch_store, plan_bunch_activation, api_router] | api (`GET,POST /api/plans/<slug>/bunches`) | GET lists activations joined to library bunches plus their span in the order; POST `{bunch_id, enabled, region?, base_rev}`; **an overlapping activation returns 409 naming the conflicting bunch and its shared tracks** |
| 29 | `api_bunches_collection_Python.prompt` | `brain/api/api_bunches_collection.py` | [bunch_store, api_router] | api (`GET,POST /api/bunches`) | GET lists library bunches with member titles, `?track_id=` filters; POST `{label, track_ids[], ordered, notes}`; **fewer than 2 members → 400**; creating a bunch overlapping an existing one **succeeds** (step 4 Blocker 1) |
| 30 | `api_bunch_item_Python.prompt` | `brain/api/api_bunch_item.py` | [bunch_store, api_router] | api (`GET,POST /api/bunches/<bunch_id>`) | GET one bunch hydrated; POST updates `label`/`notes`/`ordered`/`track_ids` (members rewritten wholesale, `position` dense); `{action:"archive"}` soft-deletes leaving activations dangling-but-restorable; dropping below 2 auto-archives with a journal entry |
| 31 | `plan_cli_Python.prompt` | `brain/plan_cli.py` | [plan_revision, plan_store, plan_journal, bunch_store, plan_bunch_activation, plan_notes, transition_overrides, order_constraints, plan_mix_build] | entrypoint (CLI) | `python -m brain.plan_cli list\|new\|switch\|show\|add\|remove\|move\|note\|**transition**\|**mark**\|bunch\|build\|log\|status`; **`show --json` is the same shape the arrange route returns**, so a harness and the GUI cannot disagree about what the plan is; `build` calls `plan_mix_build` so CLI and GUI produce the identical artifact; every mutation takes `--base-rev` or `--force` and prints the new rev; runs with no GUI process and no server. **[R8/R9 fix]** Adds **`transition get\|set\|clear`** mirroring module 27's sparse patch exactly: `--from --to [--technique --beats --showcase-move --effects --note] --base-rev`. Without it the two things the PRD explicitly assigns to the LLM (*"add dj notes on transitions"*, *"adjust transitions and effects"*) are reachable **only over HTTP**, while this module is specified as the offline harness contract — the contradiction the gate caught. **[R2 fix]** Adds **`mark <wip\|ready\|archived>`** calling `plan_store.set_status`; the pre-existing **`status`** verb is documented as *reads staleness*, and `mark` as *writes lifecycle state* — they were one word away from being confused. **Clarified:** `note` is **track**-scoped (module 9); transition-scoped notes go through `transition set --note` (module 10). **Tests needed:** `transition set --note` alone leaves the derived technique unchanged in the resulting `--json`; `mark ready` then `list` shows the new status; `transition` and module 27 accept identical field names |
| 32 | `plan_client_JS.prompt` | `brain/web/plan_client.js` | [api_plans_collection, api_plans_active, api_plan_detail, api_plan_duplicate, api_plan_journal, api_plan_arrange, api_plan_order, api_plan_tracks, api_plan_notes, api_plan_transitions, api_plan_bunches, api_bunches_collection, api_bunch_item] | module (browser, vanilla ES) | Fetch wrappers threading `base_rev` into every mutation body automatically; a 409 surfaces a "changed underneath you" banner with Reload and **discards the local optimistic buffer instead of retrying**; `refreshPlan()` re-fetches `/arrange` and repaints from the response only; `fetchJournal(slug, limit)` for the what-changed strip; `setStatus(slug, status)` for the WIP control; no framework, no bundler, no `node_modules` |
| 33 | `plan_picker_JS.prompt` | `brain/web/plan_picker.js` | [plan_client_JS] | component (browser) | Header-level plan picker **above** the `1 · Curate set` / `2 · Create the mix` nav — a plan is a scope, not a wizard step; display name + status badge + stale dot; switch, New, Rename, Duplicate, Delete inline; rename updates the label with no URL change or reload. **[R2 fix]** The status badge is a **control, not decoration** — clicking it sets `wip`\|`ready`\|`archived` via `plan_client.setStatus` and repaints from the response; a 409 shows the standard changed-underneath banner. Round 1 rendered a WIP badge that no module could ever change |
| 34 | `arrange_tab_JS.prompt` | `brain/web/arrange.js` | [plan_client_JS, plan_picker_JS] | page (browser tab) | Registers `3 · Arrange` as a third nav button; renders the order with the transition between each adjacent pair; **bunched tracks render as one visually contiguous unit that drags as one block and cannot be split by a drop between its members**; select 2+ rows → "Bunch these"; **per-row Add / Remove calling `POST …/tracks`, plus an "Add from Curate selection" action**; a collapsible **"What changed"** strip rendering `fetchJournal`; a `Refresh` button repaints from `/arrange`; **an explicit in-flight state on the blocking `/arrange` fetch** — disable Refresh and show a pending row rather than a frozen tab |
| 35 | `transition_editor_JS.prompt` | `brain/web/transition_editor.js` | [plan_client_JS] | component (browser) | Click a transition → editable technique / beats / showcase move / effects / note; an overridden field is visually marked with a per-field Revert to derived; an `orphaned` override is shown greyed with its stored pair, not hidden; saves are sparse |

---

### Dependency Graph

```
plan_types ─┬─> plan_paths ─┬─> plan_revision ─┬─> plan_store ──> plan_context ──> api_router
            │               │                  │       ^                              │
            │               ├─> plan_journal ──┘       │                              │
            │               ├─> plan_notes ────────────┤                              │
            │               └─> transition_overrides ──┤                              │
            │                                          │                              │
            ├─> bunch_store ──> plan_bunch_activation ─┤                              │
            │        └────────> order_constraints ─────┤                              │
            │                                          v                              │
            │              plan_mix_envelope ─┬─> plan_staleness                      │
            │                                 └─> plan_mix_build                      │
            │                                        ^                                │
            │                 [plan_paths, plan_notes, transition_overrides,          │
            │                  order_constraints] ───┘                                │
            └─────────────────────────────────────────────────────────────────────────┤
                                                                                      v
   api_static_assets, api_plans_collection, api_plans_active, api_plan_detail,
   api_plan_duplicate, api_plan_journal, api_plan_arrange, api_plan_order,
   api_plan_tracks, api_plan_notes, api_plan_transitions, api_plan_bunches,
   api_bunches_collection, api_bunch_item
                                       │
                                       v
                                 plan_client_JS ─┬─> plan_picker_JS ─> arrange_tab_JS
                                                 └─> transition_editor_JS

Edges added or made load-bearing this round:

  plan_types.PlanStatus ──> plan_store.set_status ──> api_plan_detail  (R2 write path)
                                     └─────────────> plan_cli mark
                                     └─────────────> api_plans_collection (status filter)
  plan_client.setStatus ──> plan_picker_JS badge-as-control            (R2 read/write loop closed)

  transition_overrides ──> plan_cli transition get|set|clear           (R8/R9 offline path)
       (already in plan_cli's dependency list — no new edge, the verb was simply absent)

  api_router literal-over-param precedence ──> api_plans_active reachable
       (module 19 was shadowed by module 20's <slug> under registration order)

  plan_types.RESERVED_SLUGS ──> plan_store slug allocation
       (a plan named "Active" must not produce slug `active`)

Unchanged from round 1:
  api_plan_journal ──> plan_journal
  api_plan_tracks  ──> plan_revision, plan_paths, plan_journal, transition_overrides
  plan_mix_build   ──> consumed by playlist_editor.build_mix / start_mix /
                       reexport_finalized / start_enrich  AND by plan_cli build
  plan_migration   ──> [plan_store, plan_bunch_activation, plan_notes, transition_overrides]
```

No cycles. Every module's priority exceeds all of its dependencies'. No module was renumbered this round — none was added.

---

### Interface Sketches

#### plan_types
- Type: module (shared types)
- `PlanMeta`, `PlanPaths`, `Rev`, `Bunch`, `OrderConstraints`, `TransitionOverride`, `EffectiveNote` (frozen dataclasses)
- `PlanStatus` — `wip` (PRD-sourced) | `ready` | `archived` (design-sourced) **[R2 fix]**
- `RESERVED_SLUGS: frozenset[str]`, `slugify(str) -> str`, `validate_slug(str)`, `header_safe(str) -> str` **[shadowing fix]**
- `PlanPaths` members, canonical: `root`, `plan_json`, `selection`, `exclusions`, `playlist`, `mix_plan`, `notes`, `bunches`, `transitions`, `journal` (10)

#### plan_paths
- Type: module
- `DEFAULT_PLANS_DIR`, `resolve(slug: str | None = None) -> PlanPaths`, `legacy_paths() -> PlanPaths`, `list_slugs() -> list[str]`

#### plan_revision
- Type: module
- `file_rev(Path) -> str`, `plan_rev(PlanPaths) -> Rev`, `read_with_rev(Path)`, `write_checked(Path, obj, base_rev)`, `StalePlanError.payload() -> dict`

#### plan_journal
- Type: module
- `append(slug, actor, action, detail, rev_before, rev_after)`, `read(slug, limit=50) -> list[dict]` (newest-first)

#### plan_store
- Type: module
- `create(display_name, *, collection_id=None)` → born `status="wip"`, `list(*, status=None)`, `get(slug)`, `rename(slug, display_name)`, **`set_status(slug, status, base_rev)`** **[R2 fix]**, `duplicate(slug, display_name)`, `delete(slug)`, `purge(slug)`, `get_active()`, `set_active(slug)`

#### plan_context
- Type: module
- `for_request(query: dict, body: dict) -> PlanScope`, `PlanScope = (meta, paths, rev)`

#### bunch_store
- Type: module
- `SCHEMA_ADDITIONS`, `connect(db_path)` *(sets `PRAGMA foreign_keys = ON`)*, `create(label, track_ids, ordered, source, notes)`, `get`, `list(include_archived=False)`, `list_for_track(track_id)`, `update_members(bunch_id, track_ids)`, `archive(bunch_id)`

#### plan_bunch_activation
- Type: module
- `list_active(slug)`, `activate(slug, bunch_id, *, region=None, base_rev)`, `deactivate(slug, bunch_id, *, base_rev)`, `check_disjoint(slug, bunch_id) -> Conflict | None`

#### plan_notes
- Type: module — **track**-scoped
- `get_effective(slug, track_ids) -> list[EffectiveNote]`, `set_override(slug, track_id, note, author, base_rev)`, `clear_override(slug, track_id, base_rev)`

#### transition_overrides
- Type: module — **transition**-scoped
- `load(slug)`, `upsert(slug, override, base_rev)`, `clear(slug, from_id, to_id, base_rev)`, `merge(segments, overrides)`, `reconcile(order, overrides)`

#### order_constraints
- Type: module
- `from_activations(slug) -> OrderConstraints`, `contract(rows, groups)`, `expand(order, table)`, `assert_intact(order, groups)`, `merge_groups(pairs) -> groups`

#### plan_mix_envelope / plan_staleness
- Type: module
- `decorate(plan, slug, paths) -> dict` (v3); `read_tolerant(path) -> dict` (accepts v2); `is_stale(slug) -> {stale, changed_inputs}`

#### plan_mix_build
- Type: module
- `build(slug, *, profile=None, dj_format=None, seconds_per_track=None, …) -> dict` — resolves paths from `PlanPaths`, injects effective notes / constraints / overrides, calls the existing `compose_mix_plan`, wraps through `decorate()`, writes `plans/<slug>/mix_plan.json`, journals
- `playlist_path(slug) -> Path`, `mix_plan_path(slug) -> Path` — the accessors `start_mix` / `reexport_finalized` / `start_enrich` use instead of the module-level singletons

#### api_router
- Type: module (dispatch)
- `register(pattern, methods, handler)`, `route(method, path) -> (handler, params)`
- **Matching rule [shadowing fix]:** segments are scored per position, literal > `<param>`; the highest-scoring registered pattern wins, **independent of registration order**. Ties are impossible because two identical patterns cannot both register.

#### API modules (17–30)
- Type: api. One module per distinct URL path; each exports `PATTERN`, `METHODS`, and `handle(app, params, method, body, query) -> (payload, status)`, registered into `api_router` at server start.

#### plan_cli
- Type: entrypoint (CLI)
- `list | new | switch | show | add | remove | move | note | transition | mark | bunch | build | log | status`
- **`transition get|set|clear`** — `--from --to [--technique --beats --showcase-move --effects --note] --base-rev`, sparse, field-for-field identical to module 27 **[R8/R9 fix]**
- **`mark <wip|ready|archived>`** — `--base-rev`; writes lifecycle state **[R2 fix]**
- `status` — reads *staleness*, not lifecycle state; the two are deliberately different verbs
- `note` — **track**-scoped; transition notes go through `transition set --note`

#### Browser modules (32–35)
- Type: module / component / page, vanilla ES, loaded by `<script src>` from `api_static_assets`. No build step.
- `plan_client` adds `setStatus(slug, status)`; `plan_picker` renders the status badge as an interactive control.

---

### Integration Points (Entry Point Wiring)

| Module | Entry Point File | Action | Detail |
|---|---|---|---|
| `api_router` | `brain/playlist_editor.py` (`make_handler`, 1262-1414) | `replace_dispatch` | Swap the exact-match chain for `router.route(method, parsed.path)`. **All 25 existing routes must keep resolving** — highest-regression-risk change in the feature. `StalePlanError → 409` translation lives here so no route repeats it. **The literal-over-param precedence rule is part of this swap**, not a later refinement — without it `/api/plans/active` is a coin flip on registration order. |
| 17–30 (all API modules) | `brain/playlist_editor.py` (`main`) | `register_routes` | Import each and `router.register(mod.PATTERN, mod.METHODS, mod.handle)` at server start. **A module not registered here never executes** — this row is the orphan check, and it includes `api_plan_journal` and `api_plan_tracks`. Registration order is deliberately *not* significant (see precedence rule). |
| *(package init)* | `brain/api/__init__.py` | `create_package` | Empty package marker so `brain.api.*` imports resolve. Not a prompt module. |
| `api_static_assets` | `brain/playlist_editor.py` (`do_GET`, 1282) | `add_route` | Add `/web/<file>` before the 404 fallthrough. Without it, modules 32–35 are unreachable orphans. |
| `plan_context` | `brain/playlist_editor.py` (`PlaylistApp.__init__`, `metadata`, `set_enabled`, `export`) | `replace_state` | `self.selection` / `self.selected` / `self.by_id` stop being authoritative; each request resolves its plan and reads from disk. The silent-clobber fix. |
| `plan_mix_build`, `plan_paths`, `plan_mix_envelope` | `brain/playlist_editor.py` — `MIX_PLAN_PATH` :31, `DEFAULT_PLAYLIST_JSON` :32, `build_mix` :1091-1183 (in-process `compose_mix_plan` at :1172-1183), `start_mix` :1200, `reexport_finalized` :645, `start_enrich` :948, `_plan_stale` reads :638-643, :1135-1142, :1211-1226 | `inject_path` | Verified in code: the GUI **never shells out** to `build_mix_plan.py`, so routing `--plan` into that script does not make the GUI plan-aware; the two module constants are read at 18 sites. Replace both constants' direct use with `plan_mix_build.playlist_path(slug)` / `mix_plan_path(slug)` resolved from the request's `PlanPaths`, and delegate `build_mix` to `plan_mix_build.build`. **Without this, `/api/mix/build` writes the legacy singleton while `api_plan_arrange` reads `plans/<slug>/mix_plan.json` — the Arrange tab is permanently `segments: []` and `/api/mix/start` plays the wrong plan under a live run.** Keep the constants as the legacy fallback so existing tests' `patch`-the-constant idiom survives. |
| `plan_revision`, `api_plan_tracks` | `brain/playlist_editor.py` — `/api/selection` :1294, `/api/selection/clear` :1299, `/api/seed` :1308 | `add_guard` | These three are today's only add/remove path and carry **no `base_rev`**. Retrofit each to resolve a plan, accept optional `base_rev`, and route the write through `plan_revision.write_checked`; a request without `base_rev` keeps working (legacy single-plan callers) but is journaled as `unguarded`. New GUI code calls `POST /api/plans/<slug>/tracks` instead. |
| `plan_paths` | `brain/playlist.py` (13-17, `load_selection`, `save_selection`, `load_exclusions`, `save_exclusions`, `write_playlist`) | `inject_path` | Functions already take injectable `path=` args — **no signature change**; callers pass a `PlanPaths` member. Keep `DEFAULT_*` as the legacy fallback. |
| `plan_mix_envelope`, `order_constraints`, `transition_overrides`, `plan_notes` | `brain/build_mix_plan.py` (`compose_mix_plan` :1656, `main` :1812, `load_dj_notes_lookup` :101) | `add_hook` | Add `--plan <slug>`; resolve `--playlist`/`--out` from `PlanPaths`; route `load_dj_notes_lookup` through `plan_notes.get_effective`; pass constraints into ordering; wrap through `decorate()`. **Bounded diff — 1895 lines, do not regenerate.** |
| `order_constraints` | `brain/mix_graph.py` (`greedy_mix_order` :317) | `add_param` | Optional `constraints`; contract → tour → expand → `assert_intact`. |
| `order_constraints` | `brain/mix_order_brief.py` (`parse_constraints` :113, `force_adjacent` :199, `apply_constraints` :245 — all verified) | `replace_impl` | Delegate to the n-ary implementation; `force_adjacent` strands A on chained pairs and nothing checks the post-condition. Keep the existing dict shape as input. |
| `plan_paths`, `plan_mix_build` | `brain/mix_directives.py`, `brain/preview_transitions.py`, `brain/enrich_playlist.py`, `brain/curate_playlist.py`, `hands/run_mix_plan.py`, `hands/attended_mix_run.py`, `scripts/run_mix.sh` | `add_flag` | Add `--plan <slug>` defaulting to the active plan. Until this lands, the CLI path and the GUI can be looking at different plans. |
| `plan_staleness` | `brain/playlist_editor.py` (`_plan_stale` :618-635) | `replace_impl` | Delete the track-id set comparison; call `plan_staleness.is_stale`. |
| `bunch_store` | `brain/library_index.py` (`SCHEMA` :18-141, `connect`) | `extend_schema` | Append two `CREATE TABLE IF NOT EXISTS` blocks; set `PRAGMA foreign_keys = ON` in `connect()`. Safe **because** no existing table declares a constraint. |
| `plan_store` | `brain/archive_mix_plan.py` | `reuse` | Already a proto plan store. Lift its slugify + collision-suffix logic (:56-60) and **extend it with the reserved-word set** — the existing implementation has none. Archive-import-as-plan stays **deferred** (gap #8). |
| `plan_migration` | `pyproject.toml` `[project.scripts]` / `PROGRESS.md` | `add_command` | One-shot `python -m brain.plan_migration`, documented as required so an existing working set isn't stranded. |
| `plan_picker_JS`, `arrange_tab_JS` | `brain/web/playlist.html` (nav :104-106, `showPage` :266, listeners :354) | `add_to_layout` | Plan-picker container above `.nav`; `3 · Arrange` as a third button; `<script src="/web/*.js">` tags. **Markup + wiring only** — 863 lines, at the ceiling. |
| `plan_cli` | `AGENTS.md`, `PROGRESS.md`, `agent/hermes-skill/SKILL.md` | `document` | The harness-facing contract. **[R8/R9 fix]** The docs must show the **`transition get\|set\|clear`** verb and the `note`-is-track-scoped distinction explicitly — Hermes, Claude, and Codex discover this surface only by reading these files, so an undocumented verb is a verb that does not exist for them. Must also show **`mark`** vs **`status`**. Without this row, agents keep editing singleton files and the PRD's *"an AI agent changed it, I press refresh"* has no defined write path. |

---

### Guard/Cross-Cutting Concern Impacts

| Module | Concern | Required Action |
|---|---|---|
| *(all)* | **Auth** | **None — no auth exists or is needed.** `127.0.0.1:8787`, single local user, no login/sessions/tokens. Do not introduce an auth module. |
| `api_plans_active`, `api_plan_detail` (delete), `api_plan_order`, `api_plan_tracks` | **Live-run guard** | Refuse with 409 while `app.mix_state.running`. Membership change sits under this guard too — removing a track from a plan that is currently playing is the same class of race as switching plans. A **status change is not guarded** — marking a running plan `ready` is harmless. Gap #11 remains a product call; this is the safe default. |
| every mutating module (3, 5, 8, 9, 10, 13, 20–31) | **Concurrency / staleness** | `base_rev` in the request body → `plan_revision.write_checked` → 409 with `{current_rev, changed_files, summary}`. **Not `If-Match`/412** — not standard for POST, and all 19 existing mutations are POST+JSON. Emit `ETag` on plan GETs anyway. `set_status` and the CLI's `transition`/`mark` are in this list. |
| `api_router`, `plan_types`, `plan_paths` | **Route/slug namespace collision** | **[shadowing fix]** Two independent defenses, both required: literal-outranks-param in the router, **and** a reserved-slug set so no plan can ever own the slug `active`. Either alone leaves a hole — the router rule doesn't stop `plans/active/` from shadowing `active.json` on disk, and the reserved set doesn't stop registration order from misrouting. |
| `api_plan_detail`, `api_plans_collection`, `api_plan_journal`, any export | **CRLF header injection** | `display_name` is free-form user text and `http.server`'s `send_header()` does not validate CRLF. Anything reaching `ETag`, `Location`, or `Content-Disposition` goes through `plan_types.header_safe()`; use the slug. Journal `detail` payloads stay in the body, never a header. |
| `plan_store`, `plan_notes`, `bunch_store`, `api_plan_tracks` | **Irreplaceable human work** | Delete is soft (`.trash/` + tombstone); `status="archived"` hides a plan without touching its directory; a bunch below 2 members archives; clearing a note override falls back to global. **Removing a track never deletes its notes or transitions** — the note override is retained and the transitions go `orphaned`, so re-adding restores both. |
| `plan_paths`, `plan_store` | **Portability (sibling intent)** | `track_id` is an absolute path, so a plan resolves only where the collection mounts identically. `plan.collection_id` makes a mismatch detectable; an unmounted collection renders the plan **unavailable, never deleted**. |
| all new modules | **Testability** | Module-level `DEFAULT_*` path constants only — the suite isolates by `patch`-ing them. Run `uv run python -m unittest discover -s tests` (**not pytest — not installed**; baseline 168 tests, OK, 9.0s). |
| all new modules | **Python floor** | 3.13-compatible (`shutil.copytree`, not `Path.copy()`). Never reference `sqlite3.version` — removed in 3.14. |
| `plan_journal`, `api_plan_journal`, `api_*`, `plan_cli` | **Provenance** | Every mutation records `actor` (`gui`\|`cli`\|`agent`) and `author` (`human`\|`agent`\|`llm`) — and module 22 + the module 34 strip render it. A CLI-issued `transition set` is journaled as `actor=cli`, so an LLM's transition edit is attributable. |
| `arrange_tab_JS` | **Loading / in-flight state** | `/arrange` is a single blocking fetch; disable Refresh and render a pending row while it is in flight. Localhost makes this cosmetic, not correctness. |
| `plan_types`, `plan_store`, `api_plans_collection`, `plan_picker_JS` | **Enum provenance** | `PlanStatus.wip` is PRD-sourced (*"work in progress"*); `ready` and `archived` are design-sourced. Labelled as such so a later step does not cite the PRD as authority for values the PRD never stated. The PRD defines no other enum. |

---

### Additions Made

**This round (5b, iteration 2) — amendments only, no new modules.** The completeness gate's own finding was that all three gaps are amendments; adding a module per gap would have produced single-method modules that make the graph worse. Priorities are unchanged at 1–35.

- **[R2 — "work in progress" had a reader but no writer]** `plan_types` gains `PlanStatus` (`wip`\|`ready`\|`archived`, provenance labelled per value); `plan_store` gains `set_status` and births plans at `wip`; `api_plan_detail` accepts `{status, base_rev}`; `plan_cli` gains `mark`; `plan_picker_JS`'s badge becomes a control. Round 1 had module 18 *returning* `status` and module 33 *rendering* a badge with nothing in between — every plan born in an unnamed state it could never leave. This is the same read/write asymmetry round 1 caught for the journal and fixed with module 22; it simply wasn't applied to `status`.
- **[R8/R9 — the LLM's two named jobs were HTTP-only]** `plan_cli` gains `transition get|set|clear`, mirroring module 27's sparse patch field-for-field, and the docs row now requires it in `AGENTS.md` / `agent/hermes-skill/SKILL.md`. `transition_overrides` was already in module 31's dependency list — the verb was simply absent, so the module the design calls "the harness-facing contract… runs with no GUI process and no server" could not express the two things the PRD explicitly assigns to the LLM. Also clarified `note` as track-scoped and disambiguated `status` (reads staleness) from `mark` (writes lifecycle).
- **[Consistency — `/api/plans/active` shadowed by `/api/plans/<slug>`]** `api_router` gains a literal-outranks-param precedence rule with a registration-order-independence test; `plan_types` gains `RESERVED_SLUGS`. Both are needed: the router rule alone doesn't stop a plan named "Active" from creating `plans/active/` next to `active.json`, and the reserved set alone doesn't stop registration order from misrouting.

**Carried from round 1** (recorded here because that round's file was never written to disk — verified: `docs/intents/` contained only `…step5-design.md` and `…step5b-validation.md`, and the former has zero hits for these three names):

- **Added `plan_mix_build` (13)** — the GUI's `build_mix` calls `compose_mix_plan` **in-process** against `MIX_PLAN_PATH` (`playlist_editor.py:31, :1172-1183`), so a `--plan` flag on `build_mix_plan.py` never reaches it. Without this the Arrange tab returns `segments: []` forever and `/api/mix/start` plays the legacy plan. A module rather than an inline diff because `playlist_editor.py` is 1437 lines, past the single-prompt ceiling.
- **Added `api_plan_tracks` (25)** — closes R6/R7 (add & remove songs), which had no owning module: `api_plan_order` explicitly rejects non-permutations, so it structurally cannot add or remove.
- **Added `api_plan_journal` (22)** — closes R12's second half; `plan_journal.read()` existed with no HTTP surface and no renderer.
- **New Integration Points** for the GUI mix paths and for the three unguarded mutations (`/api/selection`, `/api/selection/clear`, `/api/seed`).
- **Renamed modules 17–30** so prompt basename matches generated filename; moved `api_static_assets` into `brain/api/`; dropped the `_route` suffix on `api_plan_notes`.
- **Reconciled `PlanPaths` to 10 declared members** — step 4 listed 8, step 5 asserted 9; `root` and `plan_json` were undeclared.

---

### Still open — product calls only Ernest can settle

These are unchanged by this round and do not block Step 6:

1. **Archives as importable plans** (gap #8) — currently deferred; `brain/archive_mix_plan.py` stays a source of lifted logic, not a plan importer.
2. **Switching plans mid-live-run** (gap #11) — the data model permits it; the design refuses with 409 as the safe default. That is a guess at the preference, not a derived requirement.

---
*Module design corrected. Proceeding to Step 6: Research Dependencies*
