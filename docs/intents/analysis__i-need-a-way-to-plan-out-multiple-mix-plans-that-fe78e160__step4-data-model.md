# Step 4: Data Model Design

**Intent:** `local-intent:i-need-a-way-to-plan-out-multiple-mix-plans-that-fe78e160`
**Repository:** `/Users/ernestyeung/.openclaw/workspace/repos/claw-dj`
**Status:** Data Model Complete

> **On `gh issue comment 3953181291 --repo /`:** not executed, re-verified this session —
> `gh auth status` reports "not logged into any GitHub hosts", `GH_TOKEN` is unset, `--repo /`
> is not a repo spec, and the intent's source kind is `inline`, so no GitHub issue exists to
> comment on. The real remote is `git@github.com:InServiceOfX/claw-dj.git`; `3953181291` is a
> local-intent id, not an issue number there. File output, same precedent as steps 1, 2, 2b, 3.

---

## Decisions this step had to make (the two step-3 blockers)

Step 3 ended with two items marked "still blocking step 4." Step 4 cannot produce entities
without them, so both are resolved here. Flag either if you disagree — each moves entities.

### Blocker 1 — Bunch scope: **library-level records, plan-level activation**

Steps 1–3 framed this as either/or: plan-local bunch, or library object. It is neither, and
the reason matters.

*"They sound very good with each other"* is a durable fact about the songs — so the record
belongs in the library index, next to `tracks.dj_notes`, and survives deleting the plan that
discovered it. But **disjointness cannot be a property of the library.** You will legitimately
learn that A→B is great *and* that B→C is great; a library that refuses to store both is
throwing away real knowledge. Disjointness is a property of *one ordering*: within a single
plan, a track can only sit in one contiguous run.

So: `bunches` / `bunch_members` are SQLite tables in `library.sqlite3` where **overlap is
legal**, and each plan holds a list of *activated* bunch ids where **overlap is rejected at
activation time**. This dissolves the constraint that made the either/or hard, and it gives
the PRD's "move them all together as a unit" a home that outlives the plan.

Consequence for step 5: `plan_bunches` splits into a library-side module and a thin
plan-side activation set. It is no longer purely foundational-to-plans.

### Blocker 2 — `requires-python`: **keep `>=3.13`; write 3.13-compatible code**

The declared floor (`>=3.13`) and the installed interpreter (3.14.3) disagree. Recommend
keeping the floor and writing to it, rather than bumping to match the machine:

- The only 3.14 affordance in play is `Path.copy()` for `plan_store.duplicate()`, and
  `shutil.copytree(src, dst)` is the same one line on both.
- The sibling portable-collection intent is premised on *this repo running on more than one
  machine*. Raising the floor to match the newest laptop trades away a machine for a
  convenience method.
- Nothing in this data model needs 3.14. `hashlib.file_digest` (rev tokens) is 3.11+.

Independent of the floor: **`sqlite3.version` was removed in 3.14** and must not appear in new
code. It does not appear in existing code — verified.

---

### Core Entities

Two stores, split on a single rule: **facts about *tracks* go in SQLite; facts about *a plan*
go in that plan's JSON directory.** Justification is in Storage Decision.

#### SQLite — `brain/data/library.sqlite3` (existing index; additive)

| Entity | Fields | Primary Key | Notes |
|--------|--------|-------------|-------|
| `tracks` *(existing, unchanged)* | `track_id: TEXT` (absolute file path), `root`, `size_bytes`, `mtime_ns`, `title`, `artist`, `album?`, `genre?`, `duration_seconds?`, `bpm?`, `key?`, `energy?`, `dj_notes: TEXT NOT NULL DEFAULT ''`, `first_seen_at`, `last_seen_at`, `available: INTEGER`, `tag_status: TEXT` | `track_id` (natural) | **No schema change.** `dj_notes` stays the *global default* note. Per-plan divergence is an override layer, never a move — required by the sibling intent's "must not orphan enrichment and human dj_notes." |
| `bunches` **(new)** | `bunch_id: TEXT` (uuid4, surrogate) **req**; `label: TEXT` **req** (free-form, e.g. "Dre triple"); `ordered: INTEGER NOT NULL DEFAULT 1` (1 = members play in stored order; 0 = contiguous but order free); `source: TEXT NOT NULL DEFAULT 'human'` (`human` \| `agent` \| `imported`); `notes: TEXT NOT NULL DEFAULT ''` (why they work together); `created_at: REAL` **req**; `updated_at: REAL` **req**; `archived_at: REAL?` (soft delete) | `bunch_id` | Library-scoped and durable. **Overlapping bunches are legal here** — see Blocker 1. |
| `bunch_members` **(new)** | `bunch_id: TEXT` **req**; `position: INTEGER` **req** (0-based, dense); `track_id: TEXT` **req** | composite `(bunch_id, position)` | Unique index on `(bunch_id, track_id)` — a track appears at most once per bunch. `position` is dense and rewritten wholesale on edit. **≥2 members** enforced in application code (SQLite cannot express it); a bunch that falls to <2 is archived, not left invalid. |

Cardinality note on "small n": the PRD says *"2, 3, 4, or some small n"*. Modelled as
**minimum 2, no hard maximum**, with a soft warning above a threshold left as a product call.
No upper bound is invented here because the PRD does not state one.

#### JSON — `brain/data/plans/` (new; gitignored via existing `brain/data/`)

One directory per plan. Every file carries its own `version` int and is written by
atomic replace (temp file in the same directory → `flush` → `os.replace`), per step 3.

| Entity | File | Fields | Primary Key | Notes |
|--------|------|--------|-------------|-------|
| `active_pointer` | `plans/active.json` | `version: int` **req**; `active_slug: str \| null` **req**; `updated_at: float` **req** | singleton | The only registry file. Read by every module and every CLI entrypoint; `--plan <slug>` overrides it. |
| `plan` | `plans/<slug>/plan.json` | `version: int` **req**; `plan_id: str` (uuid4, **immutable surrogate**) **req**; `slug: str` (natural key = directory name, `[a-z0-9-]{1,64}`, **frozen at creation**) **req**; `display_name: str` **req** (the colloquial name — "2001 expanded 25th anniversary mix"; free-form, any unicode); `description: str` (default `""`); `status: enum` **req** (`wip` \| `ready` \| `archived`); `created_at: float` **req**; `updated_at: float` **req**; `last_opened_at: float?`; `collection_id: str?` (from `collections`, so a plan built against a different drive is *detectable* rather than mysterious); `origin: enum` **req** (`created` \| `duplicated` \| `migrated` \| `imported_archive`); `origin_ref: str?` (source slug or archive dir) | `slug` (addressing) / `plan_id` (identity) | **Rename changes `display_name` only.** The slug and directory never move, so an agent's `--plan` reference and any journal entry stay valid across a rename. This is a deliberate departure from slug-follows-name. |
| `plan_selection` | `plans/<slug>/selection.json` | `version: int`; `track_ids: [str]` **req**, ordered, de-duplicated | — | Same shape as today's `playlist_selection.json` (`brain/playlist.py:95`), so `load_selection`/`save_selection` work unchanged once pointed at a plan path. |
| `plan_exclusions` | `plans/<slug>/exclusions.json` | `version: int`; `track_ids: [str]` **req** | — | Same shape as today's `playlist_exclusions.json`. Per-plan: removing a song from the BIG tribute must not remove it from the 2001 mix. |
| `plan_playlist` | `plans/<slug>/playlist.json` | `version: int`; ordered `[track_record]` where `track_record` = `asdict(Track)` with `energy` flattened to its `.value` (`brain/playlist.py:100`) | ordinal position | Finalized order. Unchanged record shape — this is what `build_mix_plan` and the Hands runner consume. |
| `plan_note_override` | `plans/<slug>/notes.json` | `version: int`; `overrides: [ { track_id: str **req**; note: str **req**; updated_at: float **req**; author: enum **req** (`human` \| `agent` \| `llm`); global_note_at_override: str? } ]` | `track_id` within the plan | Effective note = plan override **??** `tracks.dj_notes`. `global_note_at_override` is optional and exists for one purpose: letting the UI say *"the library note changed since you overrode it"* instead of silently diverging. |
| `transition_override` | `plans/<slug>/transitions.json` | `version: int`; `overrides: [ { from_track_id: str **req**; to_track_id: str **req**; technique: str?; beats: int?; showcase_move: str?; effects: [object]?; note: str?; pinned: bool **req** (default `true`); updated_at: float **req**; author: enum **req** (`human` \| `agent` \| `llm`); status: enum **req** (`active` \| `orphaned`) } ]` | `(from_track_id, to_track_id)` | **A list of records, not a keyed map** — `track_id` is an absolute path, and any delimiter-joined composite key is a bug waiting for a filename with the delimiter in it. Uniqueness on the pair is an application-level rule. Every field except the pair is nullable: an override is *sparse*, patching only what the human changed over the derived segment. `status: orphaned` is how an override survives its pair no longer being adjacent (quarantine, not delete — see Relationships). |
| `plan_bunch_activation` | `plans/<slug>/bunches.json` | `version: int`; `activated: [ { bunch_id: str **req**; enabled: bool **req** (default `true`); region: enum? (`early` \| `first_half` \| `middle` \| `second_half` \| `late` \| `anywhere`); pinned_position: int?; activated_at: float **req** } ]` | `bunch_id` within the plan | **The disjointness gate.** Activating a bunch whose members intersect an already-enabled bunch is rejected with the conflicting id named. `region` reuses `mix_order_brief.REGION_SLICES` verbatim so bunches and LLM-derived regions speak one vocabulary. |
| `plan_mix` | `plans/<slug>/mix_plan.json` | `version: 3` **req**; existing v2 keys `track_count`, `seconds_per_track`, `profile`, `phrase_interval_beats`, `tracks[]`, `segments[]`, `events[]`, `instrument_map{}`; **new**: `plan_id: str`, `plan_slug: str`, `dj_format: str?`, `bunches: [ {bunch_id, label, track_ids[], honored: bool} ]` (provenance), `source_revs: { selection: str, playlist: str, notes: str, bunches: str, transitions: str }` | — | **`version: 3`; readers must tolerate 2.** `source_revs` is the significant addition: staleness becomes "the inputs I was built from have changed," which is exact, replacing `_plan_stale`'s set-comparison heuristic (`brain/playlist_editor.py:618`) that cannot see a note or transition edit at all. Individual `segments[]` entries gain `overridden: bool` + `override_fields: [str]` when a `transition_override` merged into them. |
| `plan_journal` | `plans/<slug>/journal.jsonl` | append-only JSON lines: `{ at: float, actor: enum (`gui` \| `cli` \| `agent`), action: str, detail: object, rev_before: str?, rev_after: str? }` | append order | Not a cache and not authoritative — an audit trail. It is the only record that answers "the agent changed my order, what did it do?", which is the PRD's refresh story from the other direction. |

#### Derived, deliberately not stored

| Concept | Derivation | Why not a column |
|---|---|---|
| `rev` (revision token) | `hashlib.file_digest(f, "sha256")` per plan file; plan-level composite = digest over the per-file digests in fixed key order | Storing it invites the stored value and the file disagreeing — which is precisely the failure the token exists to detect. `st_mtime_ns` + `st_size` is a legitimate fast pre-check to skip hashing, never the token. |
| plan registry / list | Directory scan of `plans/*/plan.json` | **This corrects step 2's proposed `plans/index.json`.** An agent harness will `cp -r` a plan directory; a registry file makes that plan invisible and makes "the index disagrees with the directory" a permanent class of bug. Dozens of plans scan instantly. Only `active.json` remains. |
| effective `dj_notes` | plan override ?? `tracks.dj_notes` | Materializing it duplicates human work in two places with no merge rule. |
| effective segment | derived `segments[]` ← merged `transition_override` | Keeps the beatgrid/phrase/lyric derivation authoritative. |

---

### Relationships

| From | To | Cardinality | Foreign Key | Cascade |
|------|----|-------------|-------------|---------|
| `collections` | `plan` | 1:N | `plan.collection_id` (soft — no FK, cross-store) | **None.** A plan whose collection is unmounted is *unavailable*, never deleted. Direct inheritance of the sibling intent's "an unmounted collection must never be read as deleted." |
| `plan` | `plan_selection` / `plan_exclusions` / `plan_playlist` / `plan_note_override` / `transition_override` / `plan_bunch_activation` / `plan_mix` / `plan_journal` | 1:1 each (composition — the plan **owns** them) | co-location in `plans/<slug>/` | Delete plan → **soft delete**: move the directory to `plans/.trash/<slug>/` and write a tombstone. Hard delete only on explicit purge. `notes.json` is irreplaceable human work; an `rm -rf` on a mis-click is not recoverable. |
| `plan` | `tracks` | N:M, **ordered** | join = `plan_selection.track_ids[]` (candidate pool) | Removing a track from a plan touches only that plan's arrays. Never touches `tracks`. |
| `plan` | `tracks` | N:M, **ordered** | join = `plan_playlist[].track_id` (finalized order) | Same. Position in the array *is* the ordering — there is no separate ordinal column to drift. |
| `plan_note_override` | `tracks` | N:1 | `track_id` (soft) | Track becomes `available = 0` → override **retained**, marked unavailable in the UI. Deleting the override falls back to global, never to empty. |
| `transition_override` | `tracks` ×2 | N:1 ×2 | `from_track_id`, `to_track_id` (soft) | Pair no longer adjacent in the current order → `status = 'orphaned'`, **quarantined not deleted**. Re-adjacency reactivates it. This is what makes an override survive an unrelated reorder — the reason step 2 chose pair-keying over index-keying. |
| `bunches` | `bunch_members` | 1:N | `bunch_members.bunch_id → bunches.bunch_id` — **real FK, `ON DELETE CASCADE`** | Deleting a bunch removes its members. Requires `PRAGMA foreign_keys = ON` per connection — see the warning below. |
| `bunch_members` | `tracks` | N:1 | `track_id` — **deliberately NOT a declared FK** | Track unavailable → member retained, bunch flagged incomplete. Bunch shrinks only on explicit user removal; **dissolves (archives) at <2 members**, with a journal entry — this settles step 2's gap #5 as shrink-then-dissolve. No FK because a future `DELETE FROM tracks` cleanup would otherwise silently vaporize hand-curated groupings. |
| `plan` | `bunches` | **N:M** | join = `plan_bunch_activation.activated[].bunch_id` | Delete plan → activations go with it, **bunches survive**. Delete/archive bunch → activations become dangling and are ignored on read with a warning; they are not silently pruned, so re-activating an un-archived bunch restores the plan. |
| `bunches` ↔ `bunches` | — | overlap | — | **Overlap legal library-wide, rejected per plan** at activation. The load-bearing asymmetry from Blocker 1. |
| `plan_mix` | `segments[]` / `events[]` / `tracks[]` | 1:N embedded | array position | Embedded, not normalized — the mix plan is a *build artifact* consumed whole by `hands/run_mix_plan.py`. Rebuild replaces it atomically. |
| `plan_mix` | `plan_selection` / `notes` / `bunches` / `transitions` | N:1 (snapshot) | `plan_mix.source_revs.*` | Not a live reference — a record of which input revisions were built from. Mismatch = stale badge, never auto-rebuild. |

> **⚠️ `PRAGMA foreign_keys = ON` is per-connection and defaults to OFF.** Verified: the repo
> currently declares **zero** foreign keys and never sets the pragma. So `ON DELETE CASCADE` on
> `bunch_members` is a no-op unless `brain/library_index.connect()` sets the pragma on every
> connection. Enabling it is safe precisely *because* no existing table declares a constraint —
> nothing starts being enforced retroactively. If the pragma is not enabled, cascade must be
> done in application code; declaring it and assuming it works is the trap.

---

### Storage Decision

- **Primary store (track-scoped facts): SQLite** — `brain/data/library.sqlite3`, existing
  `brain/library_index.py`. Bunches are durable facts about songs that must outlive any plan,
  need set queries ("which bunches contain this track?"), and belong with `tracks.dj_notes`
  and the other per-track enrichment tables (`lyrics`, `chroma`, `phrases`, `beat_phase`,
  `lyric_timelines`) that already establish this pattern. They also travel with the collection
  under the sibling portable-collection intent, which the plans directory does not.

- **Primary store (plan-scoped state): file-based JSON, directory-per-plan** —
  `brain/data/plans/<slug>/`. Three reasons, in order of force:

  1. **The PRD requires it.** *"when changes get made by an AI agent harness or something like
     you hermes-agent, or claude, codex, I can press refresh"* — the harnesses must edit a plan
     with `cat`/`jq`/`Edit`. SQLite forces every harness through a client library and makes the
     agent's work invisible to `git diff`, `grep`, and the user's own eyes.
  2. **The repo has no migration framework.** `SCHEMA` is one `CREATE TABLE IF NOT EXISTS`
     string with ad-hoc `PRAGMA table_info` additive patches and no `user_version`
     (`brain/library_index.py:18-141`; verified `user_version` appears nowhere). Plan payloads
     are the shapes most likely to churn — putting the churn in versioned JSON documents and
     leaving SQLite for the two stable append-only tables puts each shape where its evolution
     is cheapest.
  3. **It generalizes code that already exists.** `brain/archive_mix_plan.py` is already a
     proto plan store: directory-per-snapshot, `manifest.json`, `sha256` per file, git
     provenance. Plans are that, made live and named.

- **Cache layer: none.** Single local user on `127.0.0.1:8787`; the working set is a few
  hundred tracks. Redis or any in-process cache would introduce exactly the stale-read problem
  the rev-token design exists to eliminate. The one legitimate memoization —
  `PlaylistApp`'s in-memory selection — is what currently **causes** the silent-clobber bug and
  must become rev-checked rather than be extended.

- **File storage:** unchanged. Audio stays on the collection; `track_id` remains the absolute
  path. Plans store ids only, never audio.

- **Format:** JSON with `indent=2` and a trailing newline (matching `brain/playlist.py:97`),
  except `journal.jsonl` which is one compact object per line. Every write atomic-replaces.

---

### Schema/ORM Recommendation

- **ORM / query builder: none — raw `sqlite3` with parameterized SQL.** Not a default, a
  constraint: the repo declares no ORM, the server and GUI are stdlib-only, and the two new
  tables are an append-only pair with no relational complexity. Adding SQLAlchemy for
  `bunches` + `bunch_members` would introduce the project's first heavyweight data dependency
  and a second, conflicting transaction model. Follow the established per-call pattern from
  `brain/mix_directives.py:115`:

  ```python
  with closing(sqlite3.connect(db_path, timeout=30)) as db:
      ...
  ```

  **Never a module-level long-lived connection** — `ThreadingHTTPServer` gives every request
  its own thread and `check_same_thread` defaults to `True`, so a shared connection is a latent
  `ProgrammingError`. Stay on default `LEGACY_TRANSACTION_CONTROL`; do not adopt `autocommit=`
  in new modules while the rest of the repo is on the old model.

- **Migration tool: none (no Alembic).** Extend the existing two-tier approach and add the
  missing third tier:
  1. **New tables** → append `CREATE TABLE IF NOT EXISTS` to `SCHEMA`. Idempotent, safe, and
     how `collections`, `beat_phase`, and `lyric_timelines` all arrived.
  2. **New columns on existing tables** → the existing `PRAGMA table_info` guard + `ALTER TABLE
     … ADD COLUMN` idiom (`brain/library_index.py:124-140`).
  3. **Adopt `PRAGMA user_version`** *(new, recommended)*. Tiers 1–2 cannot express "backfill"
     or "this ran already"; `plan_migration` (promoting today's singleton
     `playlist_selection.json` / `playlist.json` / `mix_plan.json` into plan #1) is exactly that
     kind of one-shot. A single integer read/written in the same transaction as the migration
     makes a half-finished promotion detectable — which the intent demands: *"a partial
     migration must fail loudly rather than silently duplicate rows or drop lookups."*

- **JSON schema approach: per-file `version` int + a tolerant reader, no validation library.**
  Each plan file already carries `version`; readers accept the current version and the one
  below it (`mix_plan.json`: read 2 and 3, write 3). Validation is hand-written predicate
  functions returning structured errors — pydantic/jsonschema would be the project's first
  validation dependency for perhaps 80 lines of checks.

- **Schema organization:**
  - **SQLite:** one `SCHEMA` string in the existing library-index module. Do **not** split into
    per-entity schema files — the schema's value here is that it is one readable, commented
    block, and the existing comments (lines 45-99) are load-bearing documentation.
  - **Plan JSON:** **one module per document type**, each owning its read / write / validate /
    default-shape functions for exactly one file. This is the pattern that keeps modules under
    the single-prompt ceiling that step 2b flagged (`playlist_editor.py` at 1437 lines and
    `playlist.html` at 863 are already at it).
  - **Path resolution is centralized in exactly one place.** Every module takes an injected
    path (or a resolved plan-paths object) with a module-level `DEFAULT_*` constant, because
    the entire test suite isolates by `patch`-ing those constants — a new module that hardcodes
    a path is untestable in this repo's established style.
  - **Note:** exact file paths are determined in Step 5, not here.

---

### Enums (Verbatim from PRD)

**The PRD defines no explicit enumerations.** It is a natural-language product intent; the only
enum-adjacent phrase is *"work in progress"* as a plan state. Rather than invent enums and
present them as PRD-sourced, the table below marks the provenance of every enumeration in this
data model. The codebase-sourced values are reproduced **verbatim and complete** — those are the
ones where fidelity is actually at risk, because new code must not silently narrow them.

| Enum Name | Values (complete) | Source |
|-----------|-------------------|--------|
| `PlanStatus` | `wip`, `ready`, `archived` | **PRD (partial)** — *"work in progress"* is stated verbatim (→ `wip`); `ready` and `archived` are **proposed**, needed for lifecycle. Flag if you want a different vocabulary. |
| `PlanOrigin` | `created`, `duplicated`, `migrated`, `imported_archive` | **Proposed** — PRD implies create-new and switch-between; `migrated`/`imported_archive` come from step 2's `plan_migration` and the existing `brain/data/archives/`. |
| `Author` (notes, transitions) | `human`, `agent`, `llm` | **PRD (paraphrase)** — the PRD names *"an AI agent harness … hermes-agent, or claude, codex"* as distinct from the user's own edits, and separately *"work with an LLM"*. Three actors, not two. |
| `JournalActor` | `gui`, `cli`, `agent` | **Proposed** — the three write paths that exist today. |
| `BunchSource` | `human`, `agent`, `imported` | **Proposed.** |
| `OverrideStatus` | `active`, `orphaned` | **Proposed** — quarantine semantics. |
| `Energy` | `low`, `medium`, `high`, `peak` | **Codebase, verbatim** — `brain/library.py:17-21`. All 4 values; serialized as `.value` in track records. |
| `Region` | `early`, `first_half`, `middle`, `second_half`, `late`, `anywhere` | **Codebase, verbatim** — `mix_order_brief.REGION_SLICES`. All 6. Reused unchanged by `plan_bunch_activation.region`. |
| `DjFormat.name` | `none`, `hiphop-rnb-8bar`, `hiphop-rnb-guided` | **Codebase, verbatim** — `brain/dj_formats.py FORMATS`. All 3, including the archived one: archived formats still work when invoked directly, so a plan may legitimately reference one. |
| `DjFormat.status` | `active`, `experimental`, `archived` | **Codebase, verbatim** — `brain/dj_formats.py:36`. All 3. |
| `MixProfile.name` | `dj-showcase`, `club-set`, `mix-to-listen` | **Codebase, verbatim** — `brain/mix_profiles.PROFILES`. All 3. |
| `order_engine` | `nemoclaw`, `h-agent`, `none` | **Codebase, verbatim** — `brain/mix_order_brief.py` docstring. All 3. |
| `tracks.tag_status` | `ok`, `missing_tags` | **Codebase, verbatim.** Both. |
| `cue_source` | `dj_notes`, `dj_notes_landing`, `lyric_verse`, `guided_human_downbeat`, `fraction_fallback` | **Codebase, verbatim** — all 5 emitted values in `brain/build_mix_plan.py`. |
| `segment.technique` | **Open vocabulary, NOT an enum** — observed: `smooth_blend`, `standard_blend`, `gentle_blend`, `key_blend`, `key_adjusted_blend`, `key_clash_blend`, `halftime_blend`, `halftime_backbeat_blend`, `chroma_matched_blend`, `sample_callback_blend`, `tempo_ramp_blend`, `tempo_bridge_blend`, `tempo_gap_blend`, `verse_landing_blend`, `beat_drop_entry`, `echo_out_exit`, `filter_drop_exit`, plus `dj_format_{recipe}` composed at runtime | **Codebase.** ⚠️ Modelling `technique` as a closed enum would **break the builder** — `brain/build_mix_plan.py:1288` composes `f"dj_format_{recipe}"` dynamically. `transition_override.technique` must be a free string validated against the *currently derivable* set, not a fixed list. |
| `showcase_move` | Open vocabulary — observed: `beat_drop`, `echo_out`, `filter_drop`, `gentle_blend`, `halftime_backbeat_blend`, `smooth_opening`, `tempo_ramp_blend`, `verse_landing`, plus recipe names | **Codebase.** Same reasoning — free string. |
| `event.op` | `reset_instrument`, `load`, `start`, `play_body`, `transition`, `preload_after_transition`, `opener_effect`, `finale`, `stop_all` | **Codebase, verbatim** — all 9 ops present in the current `mix_plan.json`. Consumed by `hands/run_mix_plan.py`; a v3 reader must not narrow this set. |

---

### Shared Types

Types crossing module boundaries. Per PDD guidance these are the ones that should become their
own modules in step 5 — a shared type defined inside a consumer becomes an import cycle.

| Type | Shape | Used by |
|------|-------|---------|
| `PlanSlug` / `PlanId` | `str` newtype; slug `[a-z0-9-]{1,64}`, id uuid4 | every plan-aware module, the HTTP layer, every CLI entrypoint |
| `PlanMeta` | the `plan.json` record | plan store, HTTP layer, GUI, migration |
| `PlanPaths` | `(selection, exclusions, playlist, mix_plan, notes, bunches, transitions, journal)` resolved for one slug | every consumer that reads plan state; the single point that ends hardcoded singleton paths |
| `Rev` | opaque `str` (sha256 hex) + `{file: rev}` map | revision/staleness logic, HTTP layer, GUI, every CLI writer |
| `Bunch` | `{bunch_id, label, ordered, track_ids[], source, notes}` (joined view of the two tables) | library-side bunch module, activation, order constraints, mix builder, GUI |
| `OrderConstraints` | `{use_only, opener_id, groups: [[track_id,…]], ordered_flags, regions, notes}` — **the n-ary generalization** of today's `{use_only, opener_id, adjacent, adjacent_ordered, regions, notes}` (`mix_order_brief.parse_constraints`) | `mix_graph.greedy_mix_order`, `mix_order_brief`, `mix_directives`, `build_mix_plan` |
| `TransitionOverride` | the record above | override store, mix builder (merge), GUI, HTTP layer |
| `EffectiveNote` | `{track_id, note, layer: 'plan' \| 'global', diverged: bool}` | notes module, mix builder, GUI, directives |
| `Track` *(existing)* | `brain/library.py:24` frozen dataclass | already shared repo-wide — **unchanged** |
| `segment` dict *(existing)* | `{index, from, to, technique, beats, score, showcase_move, format_compliance?}` **+ new** `overridden`, `override_fields[]` | mix builder, Hands runner, GUI, override merge |
| mix-plan v3 envelope *(existing v2 + additions)* | see `plan_mix` above | mix builder, Hands runner, archiver, GUI |
| `Energy`, `MixProfile`, `DjFormat` *(existing)* | `brain/library.py`, `brain/mix_profiles.py`, `brain/dj_formats.py` | unchanged |

### Module-Local Types

Internal to one module; leaking these is what turns a boundary into a dependency.

| Type | Internal to |
|------|-------------|
| `slugify()` collision-suffix state (`-2`, `-3`) | plan store — mirrors `archive_mix_plan.py:56-60` |
| tombstone record (`{deleted_at, reason, prior_slug}`) in `plans/.trash/` | plan store |
| `StalePlanError` / conflict payload `{current_rev, changed_files[], summary}` | revision module (its *serialized* 409 body is the shared contract, the exception class is not) |
| `(mtime_ns, size)` fast-path pre-check tuple | revision module — an optimization, never a token |
| supernode contraction table `{pseudo_id → [track_id,…]}`, entry/exit feature vectors | order-constraints module. This is step 3's contraction-over-penalty-M recommendation; **nothing outside should see a pseudo-track** — a leaked pseudo id in a playlist or plan is a corrupt set |
| bunch-intact post-condition assertion result | order-constraints module |
| adjacency map used to mark overrides `orphaned` | transition-override module |
| SQLite row → `Bunch` hydration helpers | library-side bunch module |
| DnD drag-state, selection highlight, optimistic-order buffer | GUI |
| legacy-singleton detection + backfill report | migration module |

---

## Things step 5 needs to carry forward

1. **`plan_paths` is the highest-leverage boundary in the whole design.** Every module that
   today opens `DEFAULT_SELECTION` / `DEFAULT_PLAYLIST_JSON` / `mix_plan.json` becomes correct
   for free once it takes a resolved path; and the test suite's `patch`-the-constant idiom keeps
   working. Nothing else in this feature has that ratio.

2. **`source_revs` in `plan_mix` retires `_plan_stale`.** The current heuristic
   (`brain/playlist_editor.py:618-635`) compares track-id sets, so it is structurally blind to a
   changed dj_note, a changed transition, or a reorder. Once revs are recorded at build time,
   staleness is exact, and the PRD's "press refresh and see the truth" becomes true rather than
   approximately true.

3. **Overlap-legal-in-library / disjoint-per-plan is the one design idea here that is easy to
   lose.** If a later step "simplifies" by enforcing global disjointness, the model quietly
   stops being able to record that A→B and B→C are both good — which is the actual musical
   knowledge the PRD is asking to capture.

4. **Still open, product calls only (research cannot settle them):** archives vs. named plans
   (should `brain/data/archives/*` import as plans? — gap #8), and switching plans during a live
   run (gap #11 — the data model permits it; whether the GUI should is a safety question).

---
*Proceeding to Step 5: Design*
