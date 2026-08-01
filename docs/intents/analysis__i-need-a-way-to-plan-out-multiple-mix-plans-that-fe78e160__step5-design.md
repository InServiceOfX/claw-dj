# Step 5: Module Design

**Intent:** `local-intent:i-need-a-way-to-plan-out-multiple-mix-plans-that-fe78e160`
**Repository:** `/Users/ernestyeung/.openclaw/workspace/repos/claw-dj`
**Status:** Design Complete

> **On `gh issue comment 3953181291 --repo /`:** not executed, re-verified this session —
> `gh auth status` reports "not logged into any GitHub hosts", `GH_TOKEN` is unset, `--repo /`
> is not a repo spec, and the intent's source kind is `inline`, so no GitHub issue exists to
> comment on. The real remote is `git@github.com:InServiceOfX/claw-dj.git`; `3953181291` is a
> local-intent id, not an issue number there. File output, same precedent as steps 1, 2, 2b, 3, 4.

---

## Two things about the prompt column, read these before the table

**1. This repo has no prompt suite.** Verified: no `.pddrc`, no `architecture.json`, no
`prompts/` directory, and zero `*.prompt` files anywhere under `repos/claw-dj`. The `Module
(filename)` column below follows PDD's `<base>_<LangOrFramework>.prompt` convention because
this workflow requires it, and proposes `prompts/` at the repo root. Adopting it is a real
decision with a cost — a prompt-owned file is regenerated from its prompt, so hand-edits to
`brain/plan_store.py` would be overwritten. **The module boundaries and the `Filepath` column
stand on their own merits regardless of that choice.** If you'd rather not adopt PDD here,
read the table as a file plan and ignore the first column.

**2. Three existing files are past the single-prompt ceiling and are deliberately NOT modules.**
`brain/build_mix_plan.py` (1895 lines), `brain/playlist_editor.py` (1437), `hands/run_mix_plan.py`
(1224), `brain/web/playlist.html` (863). Step 2b flagged this. Every change to those four files
appears in **Integration Points** as a bounded diff, never as a prompt that regenerates the file.
This is the constraint that shaped the decomposition: new behavior goes in new small modules,
and the big files get wiring only.

---

### Module List

| Priority | Module (filename) | Filepath | Dependencies | Interface Type | Acceptance Criteria |
|----------|-------------------|----------|--------------|----------------|---------------------|
| 1 | `plan_types_Python.prompt` | `brain/plan_types.py` | [] | module (shared types) | `PlanMeta`, `PlanPaths`, `Rev`, `Bunch`, `OrderConstraints`, `TransitionOverride`, `EffectiveNote` importable as frozen dataclasses; `validate_slug("2001 Mix")` raises, `slugify("2001 expanded 25th anniversary mix")` → `2001-expanded-25th-anniversary-mix`; `header_safe(name)` strips CR/LF (step 3's `send_header` warning); no imports outside stdlib, no I/O |
| 2 | `plan_paths_Python.prompt` | `brain/plan_paths.py` | [plan_types] | module | `DEFAULT_PLANS_DIR` module constant patchable by tests; `resolve(slug)` returns a `PlanPaths` with all 9 members under `plans/<slug>/`; `resolve()` with no slug reads `active.json`, and falls back to the legacy singletons (`playlist_selection.json`, `playlist.json`, `mix_plan.json`) when no plans dir exists; traversal attempt (`../`, absolute) raises rather than escaping the plans dir |
| 3 | `plan_revision_Python.prompt` | `brain/plan_revision.py` | [plan_types, plan_paths] | module | `file_rev(path)` = `hashlib.file_digest` sha256 hex, `""` for a missing file; `plan_rev(paths)` = digest over per-file digests in fixed key order, stable across reads; `write_checked(path, data, base_rev)` atomic-replaces via temp-in-same-dir + `os.replace` and raises `StalePlanError` carrying `{current_rev, changed_files, summary}` when `base_rev` mismatches; two writes inside one filesystem tick produce different revs (the mtime failure this module exists to avoid) |
| 4 | `plan_journal_Python.prompt` | `brain/plan_journal.py` | [plan_paths] | module | `append(slug, actor, action, detail, rev_before, rev_after)` writes one compact JSON line, `O_APPEND`, no read-modify-write; `read(slug, limit)` tolerates a truncated final line instead of raising; unknown `actor` outside `gui\|cli\|agent` rejected |
| 5 | `plan_store_Python.prompt` | `brain/plan_store.py` | [plan_types, plan_paths, plan_revision, plan_journal] | module | `create/list/get/rename/duplicate/delete/purge/set_active/get_active`; `list()` is a **directory scan** of `plans/*/plan.json` with no registry file (a `cp -r`'d plan appears); `rename` changes `display_name` only and leaves slug + directory untouched; `duplicate` copies via `shutil.copytree` (3.13-compatible) with fresh `plan_id`, `origin=duplicated`, `origin_ref=<src slug>`; `delete` moves to `plans/.trash/<slug>/` + tombstone, never `rm -rf`; slug collision appends `-2`, `-3`; `create` records `collection_id` from the `collections` table |
| 6 | `plan_context_Python.prompt` | `brain/plan_context.py` | [plan_types, plan_paths, plan_store] | module | `for_request(query, body)` resolves plan scope in precedence order `body.plan` → `?plan=` → `active.json`, returning `(PlanMeta, PlanPaths, Rev)`; **stateless** — no caching, no module-level mutable state (the `PlaylistApp.selection` clobber bug is the reason); unknown slug → structured `PlanNotFound`, not `KeyError`; safe to call concurrently from `ThreadingHTTPServer` threads |
| 7 | `bunch_store_Python.prompt` | `brain/bunch_store.py` | [plan_types] *(+existing `brain/library_index`)* | module | Appends `bunches` + `bunch_members` `CREATE TABLE IF NOT EXISTS` to the existing `SCHEMA` string; **sets `PRAGMA foreign_keys = ON` per connection** or the declared `ON DELETE CASCADE` is a no-op (verified: repo has zero FKs today); `create/get/list/list_for_track/update_members/archive`; **overlapping bunches are accepted** — a second bunch containing an already-bunched track must succeed; a bunch dropping below 2 members is archived with a journal note, never left invalid; every call uses `with closing(sqlite3.connect(db, timeout=30))`, no module-level connection |
| 8 | `plan_bunch_activation_Python.prompt` | `brain/plan_bunch_activation.py` | [plan_paths, plan_revision, bunch_store] | module | `activate/deactivate/list_active` over `plans/<slug>/bunches.json`; **activating a bunch whose members intersect an already-enabled bunch is rejected and the response names the conflicting `bunch_id`** — this is the disjointness gate, and it lives here and nowhere else; `region` values validated against `mix_order_brief.REGION_SLICES` (imported, not re-listed); an activation whose bunch was archived is returned with a warning flag, not silently pruned |
| 9 | `plan_notes_Python.prompt` | `brain/plan_notes.py` | [plan_paths, plan_revision] *(+existing `brain/library_index`)* | module | `get_effective(slug, track_ids)` → `EffectiveNote` per track with `layer` = `plan`\|`global` and `diverged`; `set_override/clear_override` touch only `notes.json` and **never write `tracks.dj_notes`** (the sibling portable-collection intent forbids orphaning hand-verified notes); clearing an override falls back to the global note, never to `""`; an override whose track is `available = 0` is retained and flagged, not dropped |
| 10 | `transition_overrides_Python.prompt` | `brain/transition_overrides.py` | [plan_types, plan_paths, plan_revision] | module | Records stored as a **list keyed by the `(from_track_id, to_track_id)` pair**, not a delimiter-joined map key (track ids are absolute paths); `merge(segments, overrides)` returns segments with `overridden: bool` + `override_fields: [str]`, patching only non-null override fields; `reconcile(order, overrides)` marks a pair that is no longer adjacent `status="orphaned"` and **restores it to `active` when the pair becomes adjacent again** — quarantine, never delete; `technique` and `showcase_move` accepted as free strings (a closed enum breaks `build_mix_plan.py:1288`'s runtime `f"dj_format_{recipe}"`) |
| 11 | `order_constraints_Python.prompt` | `brain/order_constraints.py` | [plan_types, bunch_store] | module | `contract(rows, groups)` collapses each n-ary group into one pseudo-track — entry features from the first member, exit features from the last — and `expand(order, table)` restores members; **step 3's contraction, not a penalty-M edge weight**, because `greedy_mix_order` is nearest-neighbour and a greedy pass can strand a member at any finite M; `assert_intact(order, groups)` raises when any group is non-contiguous or out of order; chaining `(A,B)` then `(B,C)` yields the single group `[A,B,C]` and **does not strand A** — the defect verified at `mix_order_brief.py:199`; **no pseudo id may appear in any returned order** |
| 12 | `plan_mix_envelope_Python.prompt` | `brain/plan_mix_envelope.py` | [plan_types, plan_revision, plan_bunch_activation, plan_notes, transition_overrides] | module | `decorate(plan_dict, slug, paths)` returns a `version: 3` envelope adding `plan_id`, `plan_slug`, `dj_format`, `bunches[]` provenance (`honored: bool` per bunch) and `source_revs{selection,playlist,notes,bunches,transitions}`; **readers must accept `version` 2 and 3**; does not narrow `event.op` (all 9 values survive round-trip) or `technique`; pure function over a dict — does not import `build_mix_plan` |
| 13 | `plan_staleness_Python.prompt` | `brain/plan_staleness.py` | [plan_paths, plan_revision, plan_mix_envelope] | module | `is_stale(slug)` compares `mix_plan.source_revs` to current file revs and returns `{stale, changed_inputs[]}`; **detects a changed dj_note, a changed transition, and a pure reorder** — the three cases `_plan_stale` (`playlist_editor.py:618-635`, set comparison) is structurally blind to; a v2 mix plan with no `source_revs` reports `stale=True, reason="no_source_revs"` rather than crashing; never triggers a rebuild itself |
| 14 | `plan_migration_Python.prompt` | `brain/plan_migration.py` | [plan_store, plan_bunch_activation, plan_notes, transition_overrides] | module | Promotes the legacy singletons into plan #1 with `origin=migrated`; **atomic or aborted** — a mid-run failure leaves the singletons untouched and no half-built plan directory; guarded by `PRAGMA user_version` so a second run is a no-op and a half-finished run is *detectable and loud*, per the sibling intent's "a partial migration must fail loudly"; `--dry-run` prints the backfill report and writes nothing |
| 15 | `api_router_Python.prompt` | `brain/api_router.py` | [plan_types, plan_context] | module (dispatch) | Replaces the literal `if self.path == …` chain (`playlist_editor.py:1262-1414`, 6 GET + 19 POST, exact match, **no path parameters** — `/api/plans/<slug>` is physically unreachable today); `route(method, path)` matches registered patterns with `<param>` segments and returns `(handler, params)`; **all 25 existing routes still resolve unchanged** — this is the regression that matters; unknown path → 404, known path + wrong method → 405; a handler raising `StalePlanError` becomes **409 with the conflict payload in the body** (step 3: `If-Match`/412 is not standard for POST and all mutations here are POST+JSON) |
| 16 | `api_static_assets_Python.prompt` | `brain/api_static_assets.py` | [api_router] | api (`GET /web/<file>`) | Serves `brain/web/*.js` and `*.css` with correct `Content-Type` (today only `playlist.html` is served); path confined to `WEB_ROOT` — `..` and absolute paths rejected; `ETag`/304 so a refresh is cheap |
| 17 | `api_plans_collection_Python.prompt` | `brain/api/plans_collection.py` | [plan_store, api_router] | api (`GET,POST /api/plans`) | GET returns every plan with `slug`, `display_name`, `status`, `updated_at`, `track_count`, `stale`, sorted by `last_opened_at` desc; POST creates from `{display_name}` alone and returns the assigned slug; duplicate display name is **allowed** (slug disambiguates); empty/whitespace name → 400 with a message, not a 500 |
| 18 | `api_plans_active_Python.prompt` | `brain/api/plans_active.py` | [plan_store, plan_context, api_router] | api (`GET,POST /api/plans/active`) | POST `{slug}` sets the active pointer and returns the new plan payload; **refuses with 409 while a mix run is live** (`app.mix_state.running`) — gap #11 is a product call, and this is the safe default; POST with an unknown slug → 404 and the pointer is unchanged |
| 19 | `api_plan_detail_Python.prompt` | `brain/api/plan_detail.py` | [plan_store, plan_staleness, api_router] | api (`GET,POST /api/plans/<slug>`) | GET returns `PlanMeta` + `rev` + staleness, and emits an `ETag` header built from the rev — **slug-substituted, never the free-form `display_name`** (CRLF); POST with `{display_name}` renames without moving the directory; POST `{action:"delete"}` soft-deletes to `.trash/`; every mutation carries `base_rev` and returns 409 on mismatch |
| 20 | `api_plan_duplicate_Python.prompt` | `brain/api/plan_duplicate.py` | [plan_store, api_router] | api (`POST /api/plans/<slug>/duplicate`) | Copies the full directory including `notes.json` and `transitions.json`; the copy gets a fresh `plan_id` and `origin_ref` pointing at the source; the source is byte-identical afterwards; duplicating a plan mid-edit uses the on-disk state, not any in-memory state |
| 21 | `api_plan_arrange_Python.prompt` | `brain/api/plan_arrange.py` | [plan_bunch_activation, plan_notes, transition_overrides, plan_mix_envelope, plan_staleness, api_router] | api (`GET /api/plans/<slug>/arrange`) | **The single read the `3 · Arrange` tab needs** — ordered tracks, effective notes with `layer`, derived-then-merged segments between each adjacent pair, active bunches with their member spans, per-file revs and composite rev, staleness; one response, so refresh is one request and cannot show a half-updated view; a plan with no built mix returns the order with `segments: []` rather than 404 |
| 22 | `api_plan_order_Python.prompt` | `brain/api/plan_order.py` | [plan_revision, plan_bunch_activation, order_constraints, api_router] | api (`POST /api/plans/<slug>/order`) | Accepts `{track_ids[], base_rev}` (full replacement, not a delta — no index arithmetic to desync) and `{move_bunch: bunch_id, to_index}` for **move-as-a-unit**; rejects with 422 and names the group when the submitted order breaks an active bunch (`order_constraints.assert_intact`); rejects an order that is not a permutation of the current selection; calls `transition_overrides.reconcile` so overrides orphan/reactivate in the same write |
| 23 | `api_plan_notes_Python.prompt` | `brain/api/plan_notes_route.py` | [plan_revision, plan_notes, api_router] | api (`POST /api/plans/<slug>/notes`) | `{track_id, note, author, base_rev}` writes a plan override; `{track_id, clear:true}` removes it and the response shows the global note that took over; `author` recorded so an LLM-written note is distinguishable from yours; the library `dj_notes` column is untouched by every path through this route |
| 24 | `api_plan_transitions_Python.prompt` | `brain/api/plan_transitions.py` | [plan_revision, transition_overrides, api_router] | api (`POST /api/plans/<slug>/transitions`) | `{from_track_id, to_track_id, technique?, beats?, showcase_move?, effects?, note?, base_rev}` — a **sparse** patch, so sending only `note` leaves the derived technique intact; a pair that is not currently adjacent is accepted and stored `orphaned` (you can pre-plan a transition); `{clear:true}` deletes the override and the segment reverts to derived |
| 25 | `api_plan_bunches_Python.prompt` | `brain/api/plan_bunches.py` | [plan_revision, bunch_store, plan_bunch_activation, api_router] | api (`GET,POST /api/plans/<slug>/bunches`) | GET lists activations joined to their library bunches plus their current span in the order; POST `{bunch_id, enabled, region?, base_rev}` activates/deactivates; **an overlapping activation returns 409 naming the conflicting bunch and its shared tracks** — the user sees which songs collide, not just "rejected" |
| 26 | `api_bunches_collection_Python.prompt` | `brain/api/bunches_collection.py` | [bunch_store, api_router] | api (`GET,POST /api/bunches`) | GET lists library bunches with member titles, `?track_id=` filters to bunches containing that track; POST `{label, track_ids[], ordered, notes}` creates one; **fewer than 2 members → 400**; creating a bunch overlapping an existing one **succeeds** (library-level overlap is legal by design — see step 4 Blocker 1) |
| 27 | `api_bunch_item_Python.prompt` | `brain/api/bunch_item.py` | [bunch_store, api_router] | api (`GET,POST /api/bunches/<bunch_id>`) | GET one bunch hydrated; POST updates `label`/`notes`/`ordered`/`track_ids` (members rewritten wholesale, `position` dense); POST `{action:"archive"}` soft-deletes and leaves plan activations dangling-but-restorable; dropping to <2 members auto-archives with a journal entry rather than storing an invalid bunch |
| 28 | `plan_cli_Python.prompt` | `brain/plan_cli.py` | [plan_revision, plan_store, bunch_store, plan_bunch_activation, plan_notes, transition_overrides, order_constraints] | entrypoint (CLI) | `python -m brain.plan_cli list\|new\|switch\|show\|add\|remove\|move\|note\|bunch\|status`; **`show --json` output is the same shape the GUI's arrange route returns**, so a harness and the GUI cannot disagree about what the plan is; every mutation takes `--base-rev` or `--force` and prints the new rev; runs with no GUI process and no server |
| 29 | `plan_client_JS.prompt` | `brain/web/plan_client.js` | [17,18,19,20,21,22,23,24,25,26,27] | module (browser, vanilla ES) | Fetch wrappers that thread `base_rev` into every mutation body automatically; a 409 surfaces a "changed underneath you" banner with a Reload action and **discards the local optimistic buffer instead of retrying** (a blind retry is the clobber this whole design exists to prevent); `refreshPlan()` re-fetches `/arrange` and repaints from the response only; no framework, no bundler, no `node_modules` — the repo has none and step 2b says keep it that way |
| 30 | `plan_picker_JS.prompt` | `brain/web/plan_picker.js` | [plan_client_JS] | component (browser) | Header-level plan picker **above** the `1 · Curate set` / `2 · Create the mix` nav — a plan is a scope, not a wizard step; shows display name + WIP badge + stale dot; switch, New plan, Rename, Duplicate, Delete inline; a rename updates the label without any URL or reload |
| 31 | `arrange_tab_JS.prompt` | `brain/web/arrange.js` | [plan_client_JS, plan_picker_JS] | page (browser tab) | Registers `3 · Arrange` as a third nav button; renders the order with the transition between each adjacent pair; **bunched tracks render as one visually contiguous unit that drags as one block and cannot be split by a drop between its members** — the PRD's move-as-a-unit; select 2+ rows → "Bunch these"; a `Refresh` button repaints from `/arrange` so an agent's edit appears without a page reload |
| 32 | `transition_editor_JS.prompt` | `brain/web/transition_editor.js` | [plan_client_JS] | component (browser) | Click a transition → editable technique / beats / showcase move / effects / note; an overridden field is visually marked and has a per-field Revert to derived; an `orphaned` override is shown greyed with its stored pair, not hidden; saves are sparse (only changed fields go in the body) |

---

### Dependency Graph

```
plan_types ─┬─> plan_paths ─┬─> plan_revision ─┬─> plan_store ──> plan_context ──> api_router
            │               │                  │       ^                              │
            │               ├─> plan_journal ──┘       │                              │
            │               │                          │                              │
            │               ├─> plan_notes ────────────┤                              │
            │               └─> transition_overrides ──┤                              │
            │                                          │                              │
            ├─> bunch_store ──> plan_bunch_activation ─┤                              │
            │        └────────> order_constraints      │                              │
            │                                          v                              │
            │              plan_mix_envelope ──> plan_staleness                        │
            │                                                                          │
            └──────────────────────────────────────────────────────────────────────────┤
                                                                                       v
   api_static_assets, api_plans_collection, api_plans_active, api_plan_detail,
   api_plan_duplicate, api_plan_arrange, api_plan_order, api_plan_notes,
   api_plan_transitions, api_plan_bunches, api_bunches_collection, api_bunch_item
                                       │
                                       v
                                 plan_client_JS ─┬─> plan_picker_JS ─> arrange_tab_JS
                                                 └─> transition_editor_JS

plan_migration ──> [plan_store, plan_bunch_activation, plan_notes, transition_overrides]
plan_cli ────────> [plan_revision, plan_store, bunch_store, plan_bunch_activation,
                    plan_notes, transition_overrides, order_constraints]
```

No cycles. Every module's priority exceeds all of its dependencies'.

---

### Interface Sketches

#### plan_types
- Type: module (shared types)
- `PlanMeta`, `PlanPaths`, `Rev`, `Bunch`, `OrderConstraints`, `TransitionOverride`, `EffectiveNote` (frozen dataclasses); `slugify(str) -> str`, `validate_slug(str)`, `header_safe(str) -> str`

#### plan_paths
- Type: module
- `DEFAULT_PLANS_DIR`, `resolve(slug: str | None = None) -> PlanPaths`, `legacy_paths() -> PlanPaths`, `list_slugs() -> list[str]`

#### plan_revision
- Type: module
- `file_rev(Path) -> str`, `plan_rev(PlanPaths) -> Rev`, `read_with_rev(Path)`, `write_checked(Path, obj, base_rev)`, `StalePlanError.payload() -> dict`

#### plan_store
- Type: module
- `create(display_name, *, collection_id=None)`, `list()`, `get(slug)`, `rename(slug, display_name)`, `duplicate(slug, display_name)`, `delete(slug)`, `purge(slug)`, `get_active()`, `set_active(slug)`

#### plan_context
- Type: module
- `for_request(query: dict, body: dict) -> PlanScope`, `PlanScope = (meta, paths, rev)`

#### bunch_store
- Type: module
- `SCHEMA_ADDITIONS`, `connect(db_path)` *(sets `PRAGMA foreign_keys = ON`)*, `create(label, track_ids, ordered, source, notes)`, `get(bunch_id)`, `list(include_archived=False)`, `list_for_track(track_id)`, `update_members(bunch_id, track_ids)`, `archive(bunch_id)`

#### plan_bunch_activation
- Type: module
- `list_active(slug)`, `activate(slug, bunch_id, *, region=None, base_rev)`, `deactivate(slug, bunch_id, *, base_rev)`, `check_disjoint(slug, bunch_id) -> Conflict | None`

#### plan_notes
- Type: module
- `get_effective(slug, track_ids) -> list[EffectiveNote]`, `set_override(slug, track_id, note, author, base_rev)`, `clear_override(slug, track_id, base_rev)`

#### transition_overrides
- Type: module
- `load(slug)`, `upsert(slug, override, base_rev)`, `clear(slug, from_id, to_id, base_rev)`, `merge(segments, overrides) -> list[segment]`, `reconcile(order, overrides) -> list[TransitionOverride]`

#### order_constraints
- Type: module
- `from_activations(slug) -> OrderConstraints`, `contract(rows, groups) -> (rows, table)`, `expand(order, table) -> order`, `assert_intact(order, groups)`, `merge_groups(pairs) -> groups` *(n-ary closure over pairwise input)*

#### plan_mix_envelope / plan_staleness
- Type: module
- `decorate(plan, slug, paths) -> dict` (v3); `read_tolerant(path) -> dict` (accepts v2); `is_stale(slug) -> {stale, changed_inputs}`

#### API modules (17–27)
- Type: api. One module per distinct URL path; each exports `PATTERN`, `METHODS`, and
  `handle(app, params, method, body, query) -> (payload, status)`, registered into
  `api_router` at server start.

#### Browser modules (29–32)
- Type: module / component / page, vanilla ES, loaded by `<script src>` from
  `api_static_assets`. No build step.

---

### Integration Points (Entry Point Wiring)

| Module | Entry Point File | Action | Detail |
|--------|-----------------|--------|--------|
| `api_router` | `brain/playlist_editor.py` (`make_handler`, lines 1262-1414) | `replace_dispatch` | Swap the exact-match `if self.path == …` chain for `router.route(method, parsed.path)`. **All 25 existing routes must keep resolving** — this is the highest-regression-risk change in the feature. Also add the `StalePlanError → 409` translation here so no route repeats it. |
| 17–27 (all API modules) | `brain/playlist_editor.py` (`main`) | `register_routes` | Import each module and `router.register(mod.PATTERN, mod.METHODS, mod.handle)` at server start. **A module not registered here never executes** — this table is the orphan check. |
| `api_static_assets` | `brain/playlist_editor.py` (`do_GET`, line 1282) | `add_route` | Today only `playlist.html` is served; add `/web/<file>` before the 404 fallthrough. Without this, modules 29–32 are unreachable orphans. |
| `plan_context` | `brain/playlist_editor.py` (`PlaylistApp.__init__`, `metadata`, `set_enabled`, `export`) | `replace_state` | `self.selection` / `self.selected` / `self.by_id` stop being authoritative; each request resolves its plan and reads from disk. This is the silent-clobber fix — an agent's on-disk edit currently loses to the next in-GUI save. |
| `plan_paths` | `brain/playlist.py` (lines 13-17, `load_selection`, `save_selection`, `load_exclusions`, `save_exclusions`, `write_playlist`) | `inject_path` | Functions already take injectable `path=` args — **no signature change needed**, callers pass a `PlanPaths` member. Keep the `DEFAULT_*` constants as the legacy fallback so the existing tests' `patch`-the-constant idiom keeps working. |
| `plan_mix_envelope`, `order_constraints`, `transition_overrides`, `plan_notes` | `brain/build_mix_plan.py` (`compose_mix_plan` :1656, `main` :1812, `load_dj_notes_lookup` :101) | `add_hook` | Add `--plan <slug>`; resolve `--playlist`/`--out` from `PlanPaths`; route `load_dj_notes_lookup` through `plan_notes.get_effective`; pass constraints into ordering; wrap the composed dict in `decorate()` before writing. **Bounded diff — the file is 1895 lines, past the single-prompt ceiling; do not regenerate it.** |
| `order_constraints` | `brain/mix_graph.py` (`greedy_mix_order` :317) | `add_param` | Optional `constraints: OrderConstraints \| None`; when present, contract → tour → expand → `assert_intact`. Contiguity becomes structurally impossible to violate, and bunch seams finally get scored. |
| `order_constraints` | `brain/mix_order_brief.py` (`parse_constraints` :113, `force_adjacent` :199, `apply_constraints` :245) | `replace_impl` | Delegate to the n-ary implementation. `force_adjacent` pulls both members out and reinserts, so chaining `(A,B)` then `(B,C)` **strands A and nothing checks the post-condition** — verified. Keep the existing dict shape as the input format. |
| `plan_paths` | `brain/mix_directives.py`, `brain/preview_transitions.py`, `brain/enrich_playlist.py`, `brain/curate_playlist.py`, `hands/run_mix_plan.py`, `hands/attended_mix_run.py`, `scripts/run_mix.sh` | `add_flag` | Add `--plan <slug>` defaulting to the active plan. Until this lands, the CLI path and the GUI can be looking at different plans — the exact confusion the feature is meant to remove. |
| `plan_staleness` | `brain/playlist_editor.py` (`_plan_stale` :618-635) | `replace_impl` | Delete the track-id set comparison; call `plan_staleness.is_stale`. The current heuristic cannot see a changed note, a changed transition, or a reorder. |
| `bunch_store` | `brain/library_index.py` (`SCHEMA` :18-141, `connect`) | `extend_schema` | Append two `CREATE TABLE IF NOT EXISTS` blocks; set `PRAGMA foreign_keys = ON` in `connect()`. Safe **because** no existing table declares a constraint — nothing starts being enforced retroactively. |
| `plan_store` | `brain/archive_mix_plan.py` | `reuse` | Already a proto plan store (directory-per-snapshot, `manifest.json`, sha256, git provenance). Lift its slugify + collision-suffix logic (`:56-60`) rather than writing a second one. Archive-import-as-plan stays **deferred** — gap #8 is unresolved. |
| `plan_migration` | `pyproject.toml` `[project.scripts]` / `PROGRESS.md` | `add_command` | One-shot `python -m brain.plan_migration`; document it as a required step so an existing working set isn't stranded outside the plans directory. |
| `plan_picker_JS`, `arrange_tab_JS` | `brain/web/playlist.html` (nav :104-106, `showPage` :266, listeners :354) | `add_to_layout` | Add the plan-picker container above `.nav`; add `3 · Arrange` as a third button; add `<script src="/web/*.js">` tags. **Markup + wiring only** — the tab's logic lives in modules 29–32 because the file is already 863 lines at the ceiling. |
| `plan_cli` | `AGENTS.md`, `PROGRESS.md`, `agent/hermes-skill/SKILL.md` | `document` | The harness-facing contract. Without it, agents keep editing singleton files and the PRD's "an AI agent changed it, I press refresh" has no defined write path. |

---

### Guard/Cross-Cutting Concern Impacts

| Module | Concern | Required Action |
|--------|---------|-----------------|
| *(all)* | **Auth** | **None — no auth exists or is needed.** Server binds `127.0.0.1:8787`, single local user, no login, no sessions, no tokens. Step 3's auth guidance is not applicable; do not introduce an auth module. |
| `api_plans_active`, `api_plan_detail` (delete), `api_plan_order` | **Live-run guard** | Refuse with 409 while `app.mix_state.running` is truthy. Switching or reordering a plan under a running mix is the one destructive race the GUI can create on its own. Gap #11 is a product call — this is the safe default until you overrule it. |
| every mutating module (3, 5, 8, 9, 10, 19–27, 28) | **Concurrency / staleness** | `base_rev` in the request body → `plan_revision.write_checked` → 409 with `{current_rev, changed_files, summary}`. **Not `If-Match`/412**: MDN documents `If-Match` as strong-comparison and not a standard use with POST, and all 19 existing mutations are POST+JSON. Emit `ETag` on plan GETs anyway — free, and useful to `curl`-driven harnesses. |
| `api_plan_detail`, `api_plans_collection`, any export | **CRLF header injection** | `display_name` is free-form user text. `http.server`'s `send_header()` does **not** validate CRLF. Any name reaching `ETag`, `Location`, or `Content-Disposition` goes through `plan_types.header_safe()` first. Use the slug, not the display name. |
| `plan_store`, `plan_notes`, `bunch_store` | **Irreplaceable human work** | `notes.json` and hand-curated bunches have no regeneration path. Delete is soft (`.trash/` + tombstone), a bunch shrinking below 2 archives rather than vanishes, and clearing a note override falls back to global rather than to empty. |
| `plan_paths`, `plan_store` | **Portability (sibling intent)** | `track_id` is an absolute path, so a plan only resolves where the collection mounts identically. `plan.collection_id` makes a mismatch *detectable*; an unmounted collection renders the plan **unavailable, never deleted**. |
| all new modules | **Testability** | Module-level `DEFAULT_*` path constants only — the entire suite isolates by `patch`-ing them. A module that hardcodes a path is untestable in this repo's style. Run with `uv run python -m unittest discover -s tests` (**not pytest — it is not installed**; current baseline 168 tests, OK, 9.0s). |
| all new modules | **Python floor** | Write 3.13-compatible code (`shutil.copytree`, not `Path.copy()`), even though the installed interpreter is 3.14.3. Never reference `sqlite3.version` — removed in 3.14. |
| `plan_journal`, `api_*` | **Provenance** | Every mutation records `actor` (`gui`\|`cli`\|`agent`) and `author` (`human`\|`agent`\|`llm`). This is what answers "the agent reordered my mix — what did it do?", which is the PRD's refresh requirement from the other side. |

---

## Three things I'd want you to push back on before Step 6

1. **32 modules is a lot for one intent.** The count is driven by PDD's one-module-per-URL-path
   rule, which produced 11 route modules (17–27). If you'd rather have fewer, larger files, the
   honest collapse is `api/plans_*.py` → one `brain/api/plans.py` and `api/bunches_*.py` → one
   `brain/api/bunches.py`, taking the total to 23. The core module boundaries (1–14) I would not
   collapse — each one is where a specific failure gets caught.

2. **`api_router` is the sleeper risk, not `order_constraints`.** Step 2 named
   `order_constraints` the risky module and it still is *musically*. But `api_router` rewrites
   the dispatch for **all 25 working routes** at once, and the entire GUI depends on every one of
   them. Ordering regressions you hear; a routing regression takes the whole app down. It is
   priority 15 and unavoidable — `/api/plans/<slug>` is literally unreachable without it — but it
   deserves a route-by-route test before anything is layered on top.

3. **Two gaps are still open and only you can settle them,** carried from step 4: archives as
   importable plans (gap #8 — currently deferred, `archive_mix_plan.py` is reused for its slug
   logic only), and switching plans during a live run (gap #11 — designed as *refuse with 409*,
   which is a guess at your preference, not a research finding).

---
*Proceeding to Step 6: Research Dependencies*
