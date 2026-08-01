# Step 2b: Codebase Scan

**Intent:** `local-intent:i-need-a-way-to-plan-out-multiple-mix-plans-that-fe78e160`
**Repository:** `/Users/ernestyeung/.openclaw/workspace/repos/claw-dj` (remote `git@github.com:InServiceOfX/claw-dj.git`)
**Status:** Scan Complete

> **Output channel note.** The workflow prescribes
> `gh issue comment 3953181291 --repo / --body "..."`. Not executed, same as
> steps 1 and 2: `gh auth status` reports "not logged into any GitHub hosts",
> `GH_TOKEN` is unset, `--repo /` is not a valid repo spec, and the intent's
> source kind is `inline` — no GitHub issue exists. `3953181291` is a
> local-intent id, not an issue number on the real remote. File output follows
> the precedent set by the sibling intent's analysis files.

This is **not** a JS/TS web app. There is no `package.json`, no framework, no
bundler, no `node_modules`. Most of the questions this step asks (App Router,
`tsconfig` path aliases, Tailwind, React Query) have no answer here, and
answering them "Not detected" is the load-bearing finding: **steps 3–9 must not
propose React/Next/Tailwind modules.** The entire GUI is one hand-written
863-line HTML file with inline `<style>` and inline `<script>`, served by
Python's stdlib `http.server`.

---

## Installed Packages

### Python — `pyproject.toml` (`requires-python = ">=3.13"`, setuptools backend)

| Package | Version constraint | Locked (`uv.lock`) | Category |
|---------|--------------------|--------------------|----------|
| `hai-agents[desktop]` | unpinned | 1.0.6 | runtime — LLM agent harness |
| `librosa` | `>=0.11.0` | 0.11.0 | runtime — onset/chroma/beat analysis |
| `mido` | unpinned | 1.3.3 | runtime — MIDI message construction |
| `mutagen` | `>=1.48.1` | 1.48.1 | runtime — audio tag reading |
| `python-dotenv` | unpinned | 1.2.2 | runtime — API key loading |
| `python-rtmidi` | unpinned | 1.5.8 | runtime — MIDI port I/O |
| `numpy` | transitive | 2.4.6 | runtime |
| `scipy` / `numba` / `soundfile` | transitive (librosa) | 1.18.0 / 0.66.0 / 0.14.0 | runtime |

Packages declared: `brain`, `hands`, `shared`. There are **no dev
dependencies declared at all** — no pytest, no linter, no formatter in the
manifest. 68 packages total in the lock file.

### Rust — `core-rust/` cargo workspace (edition 2024, rust-version 1.85)

| Crate | Version | Category |
|-------|---------|----------|
| `anyhow` | 1.0.100 | runtime |
| `clap` (derive) | 4.5.50 | runtime — CLI |
| `midir` | 0.10.3 | runtime — MIDI |
| `rusqlite` (bundled) | 0.37.0 | runtime — SQLite |
| `serde` / `serde_json` | 1.0.228 / 1.0.145 | runtime |
| `tracing` / `tracing-subscriber` | 0.1.41 / 0.3.20 | runtime |
| `once_cell` | 1.21.3 | runtime |
| `realfft` | 3.4.0 | runtime (`clawdj` only) |
| `symphonia` (mp3/aac/flac/isomp4/wav) | 0.5.4 | runtime (`clawdj` only) |

Workspace members: `clawdj` (lib), `clawdj-cli` (bin, named `clawdj`).
Lints: `clippy::all = warn`, `clippy::pedantic = warn` — the only lint config
anywhere in the repo.

> **Relevance to this intent:** essentially zero. `core-rust/` is the absorbed
> prior attempt (see `CLAUDE.md` → "Multiple implementations of the same
> thing"); the live path for mix planning is Python `brain/` + `hands/`.
> Listed for completeness; **do not** route new plan-management modules here.

### JavaScript

None. No `package.json`, no lock file, no dependency of any kind. The GUI's JS
is ~370 lines of vanilla ES2020 inside `brain/web/playlist.html`.

---

## Detected Patterns

- **Authentication:** Not detected — and deliberately so. `playlist_editor.py`
  binds a local server with no auth layer, no sessions, no middleware, no
  CORS handling. The only credential handling anywhere is LLM API keys, in
  `brain/agent.py::_resolve_api_key()`, read from `~/.hai/.env` /
  `~/.holo/.env` via `python-dotenv`. **Do not introduce an auth module.**
- **Data Fetching:** One hand-rolled helper, `brain/web/playlist.html:262` —
  `async function api(path, options)`: `fetch` → `response.json()` → throw
  `new Error(data.error || response.statusText)` if `!response.ok`. Every
  call in the page goes through it. No React Query, no SWR, no axios.
  **Long-running work uses a start/poll pair**, not streaming: `POST
  /api/brain/ask` returns immediately, then `setInterval(pollBrain, 2000)`
  hits `GET /api/brain` until `running` is false. Same shape for
  directives, mix build, enrich, and scan.
- **State Management:** Two layers, both ad hoc.
  - Client: a single module-scope object literal,
    `const state = { analysis:'all', meta:null, page:'curate' }`
    (`playlist.html:252`). No store library. Re-render is
    "refetch and reassign `innerHTML`" — see `loadLibrary`, `loadSelected`.
  - Server: `class PlaylistApp` (`brain/playlist_editor.py:37`) holds
    long-lived in-memory state across requests (crate, selection, agent
    results, background-thread status), mutated directly by endpoint methods.
    **This is gap #2 from step 1** — no mtime or version check on reload, so
    an agent editing JSON on disk is clobbered by the next in-GUI save.
  - Navigation: `showPage()` + `location.hash` + a `hashchange` listener.
    This is the mechanism the requested third tab must extend
    (`playlist.html:266-275`).
- **Error Handling:** No error-boundary concept. Server: each
  `do_POST` branch is wrapped in one `try` that maps exceptions to a JSON
  `{error: ...}` body with an HTTP status. Client: `try/catch` around
  individual button handlers writing `error.message` into a status `<div>`
  (`el('notice')`, `el('brain-detail')`, `el('enrich-detail')`). Failures are
  surfaced as text in the page, never as a thrown-away console error.
- **CSS/Styling:** Plain CSS in a single inline `<style>` block, using
  **CSS custom properties on `:root`** as the design tokens:
  `--ink --muted --line --paper --panel --green --red --focus`.
  `color-scheme: light` only — no dark mode. Layout is CSS Grid with explicit
  `grid-template-columns`, often written inline on the element. No Tailwind,
  no CSS modules, no preprocessor, no external stylesheet.
- **API Client:** Centralized on the client (the `api()` helper), **not**
  centralized on the server. Routing is a literal `if self.path == "..."`
  chain inside `make_handler()` — 6 GET branches, 19 POST branches
  (`playlist_editor.py:1262-1408`). There is no router table, no decorator,
  no path-parameter support. **A plan-scoped API (`/api/plans/<id>/...`)
  cannot be expressed by the current exact-match chain and will require
  either prefix matching or a real route table.**

---

## Reusable Modules

Python packages are imported absolutely (`from brain.library import Track`) —
there are **no path aliases**; `pyproject.toml` declares `brain`, `hands`,
`shared` as top-level packages. The `Track` dataclass in `brain/library.py` is
the closest thing to a shared domain type.

### Foundational — reuse, do not recreate

| File Path | Import Path | Key Exports | Used By |
|-----------|-------------|-------------|---------|
| `brain/library.py` | `brain.library` | `Track` (frozen dataclass), `Energy` (StrEnum), `load_crate()`, `find_next()`, `DEFAULT_CRATE_CACHE` | nearly everything |
| `brain/library_index.py` | `brain.library_index` | `SCHEMA`, `connect()`, `configured_roots()`, `scan_status()`, `export_records()`, `bootstrap_analysis()`, `begin_scan()`, `DEFAULT_INDEX` | scan, editor, enrich, collection |
| `brain/playlist.py` | `brain.playlist` | `load_selection()`, `save_selection()`, `load_exclusions()`, `save_exclusions()`, `export_playlist()`, `track_record()`, `match_seed()`, `SeedMatch`, `DEFAULT_SELECTION`, `DEFAULT_PLAYLIST_JSON` | editor, mix build |
| `brain/collection.py` | `brain.collection` | `derive_mount_base()`, `register_collection()`, `configured_collection()`, `resolve_portable_db()`, `read_or_create_marker()`, `CollectionNotConfiguredError` | scan, portable_library |
| `shared/mixxx_db.py` | `shared.mixxx_db` | `find_mixxxdb()`, `connect_readonly()` | sync, analyze |
| `shared/commands.py` | `shared.commands` | `LoadTrack`, `SetHotcue`, `TriggerHotcue`, `Loop`, `BeatJump`, `Crossfade`, `LoopAction`, `CrossfadeCurve` (frozen dataclasses) | `hands/` |

### Directly on this intent's critical path

| File Path | Import Path | Key Exports | Why it matters here |
|-----------|-------------|-------------|---------------------|
| `brain/playlist_editor.py` (1437 L) | `brain.playlist_editor` | `PlaylistApp` (~40 methods), `make_handler()`, `main()` | The server + every endpoint. Where a plan picker and `3 · Arrange` land. **Already near the size limit for coherent single-prompt regeneration.** |
| `brain/web/playlist.html` (863 L) | served at `/` | the whole GUI | Same size warning. Step 2 recommends splitting the web asset rather than growing it. |
| `brain/mix_order_brief.py` (335 L) | `brain.mix_order_brief` | `parse_constraints()`, `force_adjacent()`, `place_block_in_region()`, `apply_constraints()`, `order_from_brief()`, `REGION_SLICES` | **The existing constraint system** bunches must be promoted from — pairwise `adjacent` / `adjacent_ordered`, not n-ary. The `order_constraints` risk module. |
| `brain/build_mix_plan.py` (1895 L) | `brain.build_mix_plan` | `build_plan()`, `compose_mix_plan()`, `plan_summary()`, `pick_technique()`, `track_directives()`, `beat_index_for_seconds()`, `seconds_for_beat()` | Derives segments. Largest file in the repo. Transition overrides merge here. |
| `brain/mix_graph.py` (415 L) | `brain.mix_graph` | `MixEdge`, `pair_score()`, `greedy_mix_order()`, `transition_report()`, `bpm_compatibility()`, `key_compatibility()`, `parse_key()` | The second orderer; bypasses `mix_order_brief` today. |
| `brain/mix_directives.py` (365 L) | `brain.mix_directives` | `load_playlist()`, `build_prompt()`, `parse_directives()`, `apply_directives()`, `print_diff()`, `run()`, `DIRECTIVE_VOCAB` | The third reorder path; also bypasses constraints. The existing "talk to an LLM about dj_notes" surface the intent wants to extend. |
| `brain/archive_mix_plan.py` | `brain.archive_mix_plan` | `archive_mix_plan()`, `sha256()`, `git_value()`, `DEFAULT_ARCHIVES` | Already snapshots plan+playlist with provenance to `brain/data/archives/`. **The closest existing thing to a plan store** — the "switch between WIP plans" feature should build on it, not beside it. |
| `brain/mix_profiles.py` | `brain.mix_profiles` | `MixProfile`, `apply_brief()`, `profile_provenance()` | Per-plan settings precedent (frozen dataclass + provenance dict). |
| `brain/dj_formats.py` | `brain.dj_formats` | `DjFormat`, `get_format()`, `visible_formats()`, `format_provenance()` | Same pattern; also the registry/`visible_*` idiom a plan list can copy. |
| `brain/catalog.py` | `brain.catalog` | `short_id()`, `catalog_entry()`, `build_catalog()`, `load_catalog()`, `agent_view()`, `find_duplicates()` | `short_id()` is how tracks are named *to LLMs*; a plan-scoped agent view needs it. |
| `brain/agent.py` | `brain.agent` | `Brain`, `AGENT_NAME`, `DEFAULT_MAX_STEPS`, `DEFAULT_MAX_TIME_S` | The LLM call path for the "work with an LLM on transitions" half of the intent. |

### Persistence layout (what a plan store must fit into)

Singleton JSON files under `brain/data/` (**gitignored**, per `CLAUDE.md`):
`playlist_selection.json` (dict), `playlist.json` (list of track records with
`track_id, title, artist, genre, album, bpm, key, energy, duration_seconds,
size_bytes, dj_notes`), `mix_plan.json` (`version: 2`, keys `track_count,
seconds_per_track, profile, phrase_interval_beats, tracks, segments, events,
instrument_map`; each segment `{index, from, to, technique, beats, score,
showcase_move}`), `playlist.m3u8`, `crate.json`, `catalog.json`, plus
`archives/` (currently empty).

SQLite at `brain/data/library.sqlite3` — tables `tracks` (PK `track_id` =
absolute file path; **`dj_notes` is a column here, global per track — step 1's
gap #1**), `roots`, `collections`, `lyrics`, `chroma`, `phrases`,
`beat_phase`, `lyric_timelines`, `scan_state`. Schema is a single `SCHEMA`
string of `CREATE TABLE IF NOT EXISTS` — **no migration framework, no version
table.** Adding plan tables means appending to `SCHEMA`; changing an existing
column has no supported path, which is exactly what makes the
`dj_notes`-override decision load-bearing.

---

## Framework Configuration

- **Framework:** None. Python 3.13 stdlib `http.server.BaseHTTPRequestHandler`
  + `ThreadingHTTPServer`, `sqlite3`, `argparse`, `json`, `pathlib`,
  `threading`, `dataclasses`. Import tally across `brain/hands/shared`:
  `__future__` 41, `json` 33, `pathlib` 32, `argparse` 27 — against `numpy` 2,
  `librosa` 2, `mutagen` 1, `mido` 1. **This is a stdlib codebase.**
- **Router:** Literal `if self.path == "/api/..."` exact-match chain in
  `make_handler()`. `do_GET` parses with `urlparse`/`parse_qs`; `do_POST`
  compares `self.path` raw (so query strings on POST would not match).
  Client-side "routing" is `location.hash` → `showPage()`.
- **Path Aliases:** None. Absolute package imports (`brain.`, `hands.`,
  `shared.`). No `tsconfig.json` — no TypeScript in the repo.
- **CSS Approach:** Inline `<style>`, CSS custom properties as tokens, CSS
  Grid. Single file, no build step.
- **Linting/Formatting:** No `.eslintrc`, no `prettier`, no `ruff`, no `mypy`,
  no `Makefile`, no `.github/` workflows. Only `[workspace.lints.clippy]` in
  the Rust workspace. Code style is enforced by convention and review only.
  Type hints are used consistently (`from __future__ import annotations` in 41
  files, PEP 604 unions like `str | None`) but nothing checks them.
- **Testing:** `unittest` (stdlib) — `class XTest(unittest.TestCase)`, run
  under pytest by discovery. 21 test files in `tests/`. No `pytest.ini`, no
  `conftest.py`, no fixtures, no test dependency declared. Isolation is done
  with `TemporaryDirectory()` + `unittest.mock.patch` of module-level
  `DEFAULT_*` path constants — e.g. `tests/test_mix_editor.py` patches
  `brain.playlist_editor` paths to a temp `playlist.json`. **New modules must
  keep their paths as patchable module-level constants or they won't be
  testable in this style.**
- **Entry points:** `scripts/start.sh`, `scripts/run_mix.sh`; every module has
  an `argparse`-based `main()` and runs as `python -m brain.<module>`.

---

## Naming Conventions

- **Files:** `snake_case.py` throughout `brain/`, `hands/`, `shared/`, `tests/`.
  Tests are `test_<subject>.py`. Docs are `SCREAMING_SNAKE.md` in `docs/`
  (`HANDOFF.md`, `ARCHITECTURE.md`), except `docs/intents/` which uses
  `intent__<slug>.md` / `analysis__<slug>__stepN-<name>.md`. Rust files are
  `snake_case.rs`. Data files are `snake_case.json`.
- **Components:** No component system. HTML nodes are identified by
  **kebab-case `id`** (`page-curate`, `nav-mix`, `mix-presets`,
  `finalized-rows`, `clear-set`) and **kebab-case `class`** (`ingest-detail`,
  `brain-form`, `pick`, `finalized-box`). Templating is template-literal
  functions returning HTML strings, named as lowercase nouns — `row(track)`,
  `pickRow(pick)`, `renderResults(results)`.
- **API Routes:** `/api/<noun>` and `/api/<noun>/<verb>`, **kebab-case**,
  no trailing slash, no versioning, no path parameters anywhere.
  GET (6): `/api/meta`, `/api/tracks`, `/api/ingest`, `/api/brain`,
  `/api/directives`, `/api/mix`.
  POST (19): `/api/selection`, `/api/selection/clear`, `/api/seed`,
  `/api/mix-order`, `/api/export`, `/api/ingest/scan`, `/api/ingest/add-root`,
  `/api/brain/ask`, `/api/brain/apply`, `/api/directives/ask`,
  `/api/directives/apply`, `/api/suggest`, `/api/mix/build`, `/api/mix/start`,
  `/api/mix/sync`, `/api/mix/enrich`, `/api/mix/refresh`,
  `/api/mix/rescan-tags`, `/api/mix/shuffle-opener`.
  **Every resource is a singleton** — the URL space itself encodes the
  one-plan assumption this intent removes.
- **Variables/Functions:** Python `snake_case`; classes `PascalCase`;
  module-level constants `SCREAMING_SNAKE`, with defaults conventionally
  named `DEFAULT_<THING>` and typed `Path`. Domain values are frozen
  dataclasses (`@dataclass(frozen=True)`) — `Track`, `MixProfile`, `DjFormat`,
  `MixEdge`, `SeedMatch`, and all of `shared/commands.py`. Enums subclass
  `str, Enum`. Private helpers take a leading `_`. Background work is a nested
  `def work() -> None:` closure started on a `threading.Thread`, with status
  exposed via a sibling `*_status()` method — repeated 6 times in
  `PlaylistApp`; **this is the idiom any new long-running plan operation
  should follow.** JS is `camelCase` for functions and variables,
  `SCREAMING_SNAKE` for lookup constants (`ENGINE_NAMES`).
- **Database:** Tables are lowercase plural `snake_case` (`tracks`, `roots`,
  `collections`, `lyrics`, `chroma`, `phrases`, `beat_phase`,
  `lyric_timelines`); singular for the singleton `scan_state`. Columns are
  `snake_case`; timestamps are `<verb>_at` REAL epoch seconds
  (`first_seen_at`, `last_scan_at`, `computed_at`); booleans are INTEGER with
  `NOT NULL DEFAULT`. Foreign keys are `track_id` by convention — **there are
  no actual `FOREIGN KEY` constraints declared.** No ORM; raw `sqlite3` with
  `contextlib.closing`.

---

## Carry-forward for Steps 3, 4, 5, 7, 9

1. **Propose nothing from the JS ecosystem.** No React, Next, Tailwind, state
   library, or build step. New UI is vanilla JS + inline CSS variables, or it
   doesn't match this repo.
2. **Reuse `archive_mix_plan.py` as the seed of `plan_store`.** It already
   does snapshot + `sha256` + git provenance to a directory. Step 2's
   "directory-per-plan JSON" recommendation is a generalization of code that
   exists, not a new subsystem.
3. **Routing must change before plan-scoped endpoints exist.** Exact-match
   `if self.path == ...` cannot express `/api/plans/<id>/tracks`. Decide
   prefix-match vs. route table in step 4; it is a prerequisite, not a detail.
4. **Two files are at the regeneration ceiling:** `playlist_editor.py` (1437)
   and `playlist.html` (863). `build_mix_plan.py` (1895) is already past it.
   Plan work should add modules beside these, and split `playlist.html`.
5. **Keep paths as patchable module-level `DEFAULT_*` constants** — the entire
   test suite depends on that for isolation.
6. **`SCHEMA` has no migration path.** Additive tables are cheap; altering
   `tracks.dj_notes` is not. This is independent support for step 2's
   override-layer recommendation over changing the existing column.
7. **The `Track` frozen dataclass + `short_id()` pair is how the codebase talks
   to LLMs.** Any plan-scoped agent view should go through
   `catalog.agent_view()`, not invent a new serialization.

---
*Proceeding to Step 3: Research*
