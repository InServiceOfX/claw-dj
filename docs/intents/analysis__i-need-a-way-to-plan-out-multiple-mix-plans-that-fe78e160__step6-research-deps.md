# Step 6: Dependency Research

**Intent:** `i-need-a-way-to-plan-out-multiple-mix-plans-that-fe78e160`
**Status:** Research Complete
**Date:** 2026-07-31
**Input:** `…__step5b-module-design-corrected.md` (round 3, 35 modules, priorities 1–35)

> **Output location note.** The workflow prescribes
> `gh issue comment 3953181291 --repo / --body "..."`. Not executable, not attempted. Re-verified
> this step: `gh auth status` → "You are not logged into any GitHub hosts", `GH_TOKEN` unset,
> `--repo /` is not a repo spec, and the intent record's source kind is `inline` — there is no
> GitHub issue. `3953181291` is a local-intent id. Written to a file, matching steps 1–5b.

---

## What this step changed

Step 3 already produced a technology-level doc table. This step is narrower: **which URL belongs in
which module's `context_urls`**, and it turned up five things step 3 did not, all of which change
what the generated code must do.

| # | Finding | Affects | Consequence |
|---|---|---|---|
| 1 | **`.js` must be served as a JavaScript MIME type.** MDN: *"JavaScript content should always be served with the MIME type `text/javascript` … you should not assume scripts served with any MIME type other than `text/javascript` will always load or run."* CSS is stronger — *"must be sent with `text/css`"*, and `text/plain`/`application/octet-stream` are *"ignored"* by most browsers. | 17 | This is the **second** silent failure mode on the same path as [G1]. G1 was wrong filename → 404. This is right filename, wrong `Content-Type` → fetched and refused. Both produce a nav button that never appears with nothing in the server log. |
| 2 | **`mimetypes.guess_type` is machine-dependent.** Verified on this machine (`.venv/bin/python`, 3.14.3): `.js` → `text/javascript`, `.css` → `text/css`, `.mjs` → `text/javascript`. But `mimetypes.knownfiles` includes `/etc/apache2/mime.types` and seven other system files read at module init, so the answer is *this box's* answer, not a guarantee. | 17 | Module 17 should carry a **two-entry literal map** (`.js` → `text/javascript`, `.css` → `text/css`) and use `guess_type` only as a fallback. A stdlib call whose result depends on `/etc` is not a contract. |
| 3 | **`type="module"` is a decision, not a detail — and it is still open.** Verified: `brain/web/playlist.html` has exactly one `<script>` tag (line 251, inline) and `brain/playlist_editor.py` has **no `/web/` route at all**. Modules 32–35 are the first external JS in this repo. If they use `import`/`export`, the tags must be `type="module"`; MDN: module scripts are **deferred** (`defer` has no effect) and *"require the use of the CORS protocol for cross-origin fetching"* (same-origin here, so moot). If they instead attach to `window`, they are classic scripts and load order matters. | 17, 32–35 | Step 5's integration row emits four bare `<script src>` tags. Pick one model and state it in the prompt, or Step 7 generates `export const` in a file loaded as a classic script — a `SyntaxError` at parse time and, again, no tab. |
| 4 | **`PRAGMA foreign_keys` is a no-op inside a transaction.** SQLite docs: it is per-connection, off by default, and *"you cannot enable or disable foreign keys inside a transaction"* — the statement silently does nothing there. | 7, 15, 30 | Module 7's criterion "sets `PRAGMA foreign_keys = ON` per connection" must specify **immediately after `connect()`, before any statement opens a transaction**. Issued mid-transaction it reports success and the declared cascade stays dead — exactly the failure the criterion exists to prevent. |
| 5 | **RFC 7396 (JSON Merge Patch) means the opposite of module 27's sparse patch.** Verified: in 7396, a member **absent** from the patch is left untouched *and* a member set to **`null` means delete*. Module 27 treats `null` as "leave alone" and uses `{clear:true}` for delete. | 10, 27, 31, 35 | Cite 7396 as the **contrast**, not the model. If an implementer or an LLM harness assumes merge-patch semantics, `{"beats": null}` deletes the beat count instead of leaving it — a silent data loss on the exact path the PRD hands to an LLM. |

Two smaller confirmations that pin design choices already made: `StrEnum` (3.11+, `auto()` → lower-cased
member name) is the right carrier for `PlanStatus`/`Author`/`Actor` and keeps them JSON-serializable
without a converter; `shutil.copytree(dirs_exist_ok=…)` defaults to **False** and raises
`FileExistsError`, which is the behaviour module 5's `duplicate` wants — a collision must surface,
not merge into the existing plan directory.

---

## Module Context URLs

### Shared HTTP baseline (modules 16–30)

Every API module inherits these; they are listed once here rather than repeated 15 times, and
should be attached to `api_router` (16) with per-module additions below.

| URL | Purpose |
|-----|---------|
| https://docs.python.org/3/library/http.server.html | threading_http_server_and_crlf_header_warning |
| https://docs.python.org/3/library/urllib.parse.html | urlparse_path_vs_query_string |
| https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/409 | conflict_is_resource_state_not_syntax |

---

#### plan_types (1)
| URL | Purpose |
|-----|---------|
| https://docs.python.org/3/library/dataclasses.html | frozen_dataclass_and_slots_semantics |
| https://docs.python.org/3/library/enum.html | strenum_json_safe_status_and_author |
| https://docs.python.org/3/library/unicodedata.html | nfkd_normalization_for_slugify |
| https://docs.python.org/3/library/re.html | slug_character_class_and_collision_suffix |

#### plan_paths (2)
| URL | Purpose |
|-----|---------|
| https://docs.python.org/3/library/pathlib.html | resolve_and_is_relative_to_containment_check |
| https://docs.python.org/3/library/os.path.html | realpath_vs_abspath_symlink_difference |

> `Path.resolve()` is the only method that eliminates `..`; `relative_to()` *assumes no symlinks are
> present*, so the traversal guard is `resolve()` **then** containment, in that order.

#### plan_revision (3)
| URL | Purpose |
|-----|---------|
| https://docs.python.org/3/library/hashlib.html | file_digest_sha256_rev_token |
| https://docs.python.org/3/library/os.html | os_replace_atomic_same_filesystem |
| https://docs.python.org/3/library/tempfile.html | named_temp_file_in_target_directory |
| https://www.rfc-editor.org/rfc/rfc9110#section-13.2 | precondition_evaluation_before_payload |
| https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Conditional_requests | mid_air_collision_workflow |

#### plan_journal (4)
| URL | Purpose |
|-----|---------|
| https://jsonlines.org/ | one_valid_json_value_per_line |
| https://docs.python.org/3/library/os.html | o_append_single_write_no_read_modify_write |
| https://docs.python.org/3/library/json.html | compact_separators_single_line_dumps |

#### plan_store (5)
| URL | Purpose |
|-----|---------|
| https://docs.python.org/3/library/shutil.html | copytree_dirs_exist_ok_false_raises |
| https://docs.python.org/3/library/pathlib.html | directory_scan_and_rename |
| https://docs.python.org/3/library/enum.html | planstatus_validation_on_write |

#### plan_context (6)
| URL | Purpose |
|-----|---------|
| https://docs.python.org/3/library/http.server.html | thread_per_request_no_shared_state |
| https://docs.python.org/3/library/urllib.parse.html | parse_qs_plan_query_param |

#### bunch_store (7)
| URL | Purpose |
|-----|---------|
| https://sqlite.org/foreignkeys.html | pragma_per_connection_noop_in_transaction |
| https://docs.python.org/3/library/sqlite3.html | check_same_thread_and_legacy_transaction_control |
| https://docs.python.org/3/library/contextlib.html | closing_connection_per_call |

#### plan_bunch_activation (8)
| URL | Purpose |
|-----|---------|
| https://docs.python.org/3/library/pathlib.html | glob_plans_activating_reverse_lookup |
| https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/409 | overlap_rejection_is_state_conflict |

#### plan_notes (9)
| URL | Purpose |
|-----|---------|
| https://docs.python.org/3/library/sqlite3.html | read_only_global_dj_notes_access |

#### transition_overrides (10)
| URL | Purpose |
|-----|---------|
| https://www.rfc-editor.org/rfc/rfc7396 | merge_patch_null_semantics_deliberately_not_used |
| https://docs.python.org/3/library/dataclasses.html | optional_author_field_backward_compatible |

#### order_constraints (11)
| URL | Purpose |
|-----|---------|
| https://arxiv.org/abs/2007.05254 | clustered_tsp_contraction_reduction |
| https://pmc.ncbi.nlm.nih.gov/articles/PMC3950363/ | ordered_cluster_contiguity_constraint |

#### plan_mix_envelope (12)
| URL | Purpose |
|-----|---------|
| https://docs.python.org/3/library/json.html | version_tolerant_envelope_round_trip |

#### plan_mix_build (13)
| URL | Purpose |
|-----|---------|
| https://docs.python.org/3/library/pathlib.html | per_plan_path_resolution |
| https://docs.python.org/3/library/unittest.mock.html | patch_default_path_constants_in_tests |

#### plan_staleness (14)
| URL | Purpose |
|-----|---------|
| https://docs.python.org/3/library/hashlib.html | source_rev_comparison |

#### plan_migration (15)
| URL | Purpose |
|-----|---------|
| https://sqlite.org/pragma.html#pragma_user_version | version_flip_last_inside_transaction |
| https://sqlite.org/foreignkeys.html | pragma_outside_transaction_ordering |
| https://docs.python.org/3/library/shutil.html | copy_before_promote_rollback |
| https://docs.python.org/3/library/os.html | atomic_replace_or_abort |

#### api_router (16)
| URL | Purpose |
|-----|---------|
| https://docs.python.org/3/library/http.server.html | no_path_parameters_dispatch_is_yours |
| https://docs.python.org/3/library/urllib.parse.html | match_on_path_never_raw_self_path |
| https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/405 | 405_must_carry_allow_header |
| https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/409 | staleplanerror_translation_point |

> Verified on MDN: a 405 response **must** include an `Allow` header listing the methods the path
> does support. Module 16 already knows the registered methods per pattern, so emitting it is free —
> and without it an agent harness probing `/api/plans/<slug>` cannot tell a typo'd path from a
> wrong verb.

#### api_static_assets (17)
| URL | Purpose |
|-----|---------|
| https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/MIME_types | text_javascript_and_text_css_required |
| https://docs.python.org/3/library/mimetypes.html | guess_type_reads_system_files_use_literal_map |
| https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/script/type | module_scripts_deferred_and_cors_fetched |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules | es_modules_in_browser_without_bundler |
| https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/ETag | asset_etag_generation |
| https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/If-None-Match | weak_comparison_on_get |
| https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/304 | headers_required_on_not_modified |
| https://docs.python.org/3/library/pathlib.html | web_root_containment_check |

> The heaviest `context_urls` list in the feature, on purpose: this is the module whose failures are
> invisible server-side. Findings 1–3 above all land here.

#### api_plans_collection (18)
| URL | Purpose |
|-----|---------|
| https://docs.python.org/3/library/urllib.parse.html | status_filter_query_param |
| https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/400 | empty_display_name_is_400_not_500 |

#### api_plans_active (19)
*(shared HTTP baseline only — 409-while-running is the whole contract)*

#### api_plan_detail (20)
| URL | Purpose |
|-----|---------|
| https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/ETag | rev_as_entity_tag_slug_substituted |
| https://docs.python.org/3/library/http.server.html | send_header_does_not_validate_crlf |
| https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/400 | unknown_status_string_rejected_early |

#### api_plan_duplicate (21)
| URL | Purpose |
|-----|---------|
| https://docs.python.org/3/library/shutil.html | copytree_full_directory_including_notes |

#### api_plan_journal (22)
| URL | Purpose |
|-----|---------|
| https://jsonlines.org/ | truncated_final_line_is_skippable |
| https://docs.python.org/3/library/urllib.parse.html | limit_actor_author_query_filters |

#### api_plan_arrange (23)
| URL | Purpose |
|-----|---------|
| https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/ETag | composite_rev_as_etag_on_single_read |

#### api_plan_order (24)
| URL | Purpose |
|-----|---------|
| https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/422 | valid_syntax_unsatisfiable_bunch_constraint |
| https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/409 | stale_base_rev_distinct_from_422 |

> The two codes are not interchangeable here and the design uses both on one route: **409** = the
> plan moved underneath you (state conflict); **422** = your body was well-formed and the server
> understood it but the requested order breaks an active bunch. MDN: a 422 client *"should expect
> that repeating the request without modification will fail with the same error"* — true of the
> bunch violation, false of the stale rev.

#### api_plan_tracks (25)
| URL | Purpose |
|-----|---------|
| https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/409 | stale_base_rev_with_changed_files |
| https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/400 | add_and_remove_same_id_rejected |

#### api_plan_notes (26)
*(shared HTTP baseline only)*

#### api_plan_transitions (27)
| URL | Purpose |
|-----|---------|
| https://www.rfc-editor.org/rfc/rfc7396 | merge_patch_contrast_null_is_not_delete_here |

#### api_plan_bunches (28)
| URL | Purpose |
|-----|---------|
| https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/409 | conflict_body_carries_bunch_id_and_shared_tracks |

#### api_bunches_collection (29)
| URL | Purpose |
|-----|---------|
| https://docs.python.org/3/library/sqlite3.html | per_call_connection_with_timeout |
| https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/400 | fewer_than_two_members_rejected |

#### api_bunch_item (30)
| URL | Purpose |
|-----|---------|
| https://sqlite.org/foreignkeys.html | cascade_on_member_rewrite |
| https://docs.python.org/3/library/sqlite3.html | dense_position_rewrite_in_one_transaction |

#### plan_cli (31)
| URL | Purpose |
|-----|---------|
| https://docs.python.org/3/library/argparse.html | add_subparsers_with_set_defaults_per_verb |
| https://docs.python.org/3/library/json.html | show_json_matches_arrange_shape |
| https://www.rfc-editor.org/rfc/rfc7396 | sparse_flag_semantics_mirror_module_27 |

> `add_subparsers(dest=…, required=…)` — `required` defaults to **False**, so `plan_cli` with no
> verb parses successfully and does nothing unless it is set. The documented pattern is
> `add_parser()` + `set_defaults(func=…)` per verb, which is what keeps the 13 verbs (and the
> nested `transition`/`bunch` sub-verbs) from becoming an if-ladder.

#### plan_client_JS (32)
| URL | Purpose |
|-----|---------|
| https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch | post_json_stringify_and_check_response_ok |
| https://developer.mozilla.org/en-US/docs/Web/API/Response/ok | fetch_does_not_reject_on_409 |
| https://developer.mozilla.org/en-US/docs/Web/API/AbortController | cancel_superseded_arrange_fetch |
| https://developer.mozilla.org/en-US/docs/Web/API/AbortSignal | signal_is_single_use_per_request |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules | module_boundary_between_client_and_views |

> `fetch()` **fulfills** on a 409 — it only rejects on network failure. A wrapper that does
> `.then(r => r.json())` without checking `r.ok` swallows every conflict this design defends with,
> and the "changed underneath you" banner never fires.

#### plan_picker_JS (33)
| URL | Purpose |
|-----|---------|
| https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles/status_role | plan_switch_announcement |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules | import_plan_client |

#### arrange_JS (34)
| URL | Purpose |
|-----|---------|
| https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API | dragover_preventdefault_or_drop_never_fires |
| https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Guides/Live_regions | announce_moved_to_position |
| https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Attributes/aria-live | polite_not_assertive_for_reorder |
| https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles/log_role | what_changed_strip_is_a_log |
| https://www.smashingmagazine.com/2018/01/dragon-drop-accessible-list-reordering/ | keyboard_pickup_move_drop_fallback |
| https://react-aria.adobe.com/blog/drag-and-drop | move_up_down_buttons_alongside_drag |
| https://developer.mozilla.org/en-US/docs/Web/API/Element/moveBefore | state_preserving_move_not_baseline_avoid |
| https://developer.mozilla.org/en-US/docs/Web/API/AbortController | in_flight_state_on_blocking_arrange_fetch |

#### transition_editor_JS (35)
| URL | Purpose |
|-----|---------|
| https://www.rfc-editor.org/rfc/rfc7396 | sparse_save_sends_only_changed_fields |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules | import_plan_client |
| https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles/status_role | revert_to_derived_confirmation |

---

## Cross-cutting URLs (attach to every generated module's prompt)

| URL | Purpose |
|-----|---------|
| https://docs.python.org/3/whatsnew/3.14.html | sqlite3_version_removed_and_313_vs_314_floor |
| https://docs.python.org/3/library/unittest.mock.html | patch_where_the_name_is_looked_up |

> `unittest.mock` docs, verbatim: *"it matters that you patch objects in the namespace where they
> are looked up."* This repo's entire test style is patching module-level `DEFAULT_*` constants, so
> a new module that does `from plan_paths import DEFAULT_PLANS_DIR` binds a **copy** and becomes
> unpatchable; it must do `import plan_paths` and read `plan_paths.DEFAULT_PLANS_DIR` at call time.
> This applies to all 15 new `brain/` modules and is the difference between testable and not.

---

## Modules with no module-specific docs

`api_plans_active` (19) and `api_plan_notes` (26) get the shared HTTP baseline and nothing more —
their contracts are entirely internal (live-run guard, note layering), and inventing a URL for them
would add noise to the generated prompt.

---

## Summary

- **Total modules:** 35
- **Total distinct URLs:** 49
- **Total context_url assignments:** 94 rows as written — 89 per-module, plus a 3-URL shared HTTP
  baseline inherited by modules 16–30 and a 2-URL cross-cutting pair inherited by all 35. Expanded
  per module for `architecture.json`, that is 89 + (3 × 15) + (2 × 35) = **204** entries
- **Modules with no module-specific docs:** `api_plans_active` (19), `api_plan_notes` (26)
- **New runtime dependencies implied:** none — every URL is stdlib, a web standard, or an
  algorithm reference
- **Findings that change module criteria before Step 7:** 5 (see table above) — the `text/javascript`
  requirement and the `guess_type` machine-dependence on module 17; the classic-vs-module script
  decision on 17 and 32–35; `PRAGMA foreign_keys` ordering on 7/15/30; RFC 7396's inverted null
  semantics on 10/27/31/35

## Recommended amendments to Step 5 before generation

Small, and all of the same kind — a criterion that is currently satisfiable by code that fails:

1. **Module 17** — add: serves `.js` as `text/javascript` and `.css` as `text/css` from a literal
   map, not `mimetypes.guess_type`; the `playlist.html` script-tag assertion added in [G1] should
   check the served `Content-Type` too, not only that the file exists.
2. **Modules 17, 32–35** — state the script model explicitly (`type="module"` with `import`/`export`,
   **or** classic scripts with a single global namespace). Step 5 leaves it implied.
3. **Module 7** — amend "sets `PRAGMA foreign_keys = ON` per connection" to "**immediately after
   `connect()`, before any statement opens a transaction**"; add a test asserting
   `PRAGMA foreign_keys` reads back `1` on a connection returned by `bunch_store.connect`.
4. **Modules 10, 27, 31, 35** — state that `null` means *leave unchanged*, deletion is `{clear:true}`,
   and that this is a deliberate divergence from RFC 7396.
5. **All 15 `brain/` modules** — the `import module` / `module.DEFAULT_*` rule, so `patch` works.
6. **Module 16** — "wrong method → 405" becomes "→ 405 **with an `Allow` header** naming the
   registered methods for that pattern"; MDN documents the header as mandatory on 405.

---
*Proceeding to Step 7: Generate*

Sources:
[dataclasses](https://docs.python.org/3/library/dataclasses.html) ·
[enum](https://docs.python.org/3/library/enum.html) ·
[hashlib](https://docs.python.org/3/library/hashlib.html) ·
[shutil](https://docs.python.org/3/library/shutil.html) ·
[os](https://docs.python.org/3/library/os.html) ·
[pathlib](https://docs.python.org/3/library/pathlib.html) ·
[mimetypes](https://docs.python.org/3/library/mimetypes.html) ·
[argparse](https://docs.python.org/3/library/argparse.html) ·
[unittest.mock](https://docs.python.org/3/library/unittest.mock.html) ·
[sqlite3](https://docs.python.org/3/library/sqlite3.html) ·
[SQLite foreign keys](https://sqlite.org/foreignkeys.html) ·
[PRAGMA user_version](https://sqlite.org/pragma.html#pragma_user_version) ·
[JSON Lines](https://jsonlines.org/) ·
[RFC 7396 JSON Merge Patch](https://www.rfc-editor.org/rfc/rfc7396) ·
[RFC 9110 §13.2](https://www.rfc-editor.org/rfc/rfc9110#section-13.2) ·
[MDN MIME types](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/MIME_types) ·
[MDN script type](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/script/type) ·
[MDN JavaScript modules](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules) ·
[MDN Using Fetch](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch) ·
[MDN Response.ok](https://developer.mozilla.org/en-US/docs/Web/API/Response/ok) ·
[MDN AbortController](https://developer.mozilla.org/en-US/docs/Web/API/AbortController) ·
[MDN AbortSignal](https://developer.mozilla.org/en-US/docs/Web/API/AbortSignal) ·
[MDN ETag](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/ETag) ·
[MDN If-None-Match](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/If-None-Match) ·
[MDN 304](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/304) ·
[MDN 409](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/409) ·
[MDN 422](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/422) ·
[MDN conditional requests](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Conditional_requests) ·
[MDN ARIA live regions](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Guides/Live_regions) ·
[MDN aria-live](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Attributes/aria-live) ·
[MDN log role](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles/log_role) ·
[MDN Drag and Drop API](https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API) ·
[MDN Element.moveBefore](https://developer.mozilla.org/en-US/docs/Web/API/Element/moveBefore) ·
[Smashing: Accessible List Reordering](https://www.smashingmagazine.com/2018/01/dragon-drop-accessible-list-reordering/) ·
[React Aria: Taming the dragon](https://react-aria.adobe.com/blog/drag-and-drop) ·
[Clustered TSP via TSP methods](https://arxiv.org/abs/2007.05254) ·
[Ordered Clustered TSP](https://pmc.ncbi.nlm.nih.gov/articles/PMC3950363/)
