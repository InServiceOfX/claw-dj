# Step 1: PRD Analysis

Intent: [`i-need-a-way-to-plan-out-multiple-mix-plans-that-fe78e160`](intent__i-need-a-way-to-plan-out-multiple-mix-plans-that-fe78e160.md)
Workflow: agentic architecture, step 1 of 13.
Output target: the workflow prescribed `gh issue comment 3953181291 --repo /`. There is no
such GitHub issue — the intent's source kind is `inline`, source reference `not
applicable`, and the repo argument is the literal `/`. `gh` is also unauthenticated here
(`GH_TOKEN` unset), and `agent/pdd-skill/SKILL.md:231` forbids inferring authorization for
GitHub issue comments. This file is the step-1 output in its place, matching the
precedent set by
[`analysis__portable-music-collection-…__step1-prd.md`](analysis__portable-music-collection-no-hardcoded-volume-la-288cef1d__step1-prd.md).

**Status:** Analysis Complete

## Answer to the PRD's direct question: was any of this started before?

**No.** Nothing in this repository mentions multiple, named, or work-in-progress mix
plans, plan switching, or song bunches — outside of the intent record itself. Evidence:

- Repo-wide grep for `bunch`, `as a unit`, `multiple mix plans`, `switch between`,
  `work in progress`/`WIP` over `*.md`, `*.py`, `*.html`, `*.js`: the only hits are
  `docs/PRODUCT_INTENT.md:19,27` and
  `docs/intents/intent__…fe78e160.md:1,22` (this same request), plus an unrelated status
  legend in `docs/prior-research/planning/TASKS.md:8`.
- `git log --all -i --grep="mix plan"` returns eight commits, all about *building* or
  *archiving* the single plan (`c69dd42`, `2e643bd`, `141edc2`, `fc066b2`, …); none about
  managing several.
- No branch, local or remote, corresponds to this work. `origin/feat/per-playlist-brief`
  sounds related but is fully merged into `master` with no unique commits, and concerns
  the mix-brief text box, not plan identity.
- `PROGRESS.md:1516-1548` ("Next steps") and `docs/HANDOFF.md:539` ("Known gaps / next
  steps") do not list it.

So this is a genuine greenfield feature on top of a mature single-plan pipeline. The
prior Claude session did not start it.

## Project Summary

- **Title:** Multiple work-in-progress mix plans — named plan workspaces, GUI switching,
  LLM co-editing with refresh, and locked song bunches
- **Goals:** Promote claw-dj's single implicit in-progress mix from a set of fixed
  singleton files into several named, independently editable, non-destructively
  switchable mix plans; and give the GUI a surface where the human, an external AI agent
  harness, and the existing LLM directive engine can all edit the same chosen plan —
  order, dj_notes, transitions, effects — with a refresh that shows the current truth,
  plus a way to lock small runs of songs into an ordered "unit" that moves together.

## Features Identified

1. **Several mix plans coexist as work-in-progress.** Today there is exactly one of
   everything: `brain/data/playlist_selection.json` (enabled set),
   `brain/data/playlist.json` (finalized snapshot), `brain/data/mix_plan.json` (built
   plan) — `brain/playlist.py:12-17`, `brain/playlist_editor.py:30-32`. Every consumer
   hardcodes those defaults: `brain/build_mix_plan.py:29`, `hands/run_mix_plan.py:24`,
   `brain/preview_transitions.py:38`, `brain/archive_mix_plan.py:14-15`,
   `hands/attended_mix_run.py:23`. Plan identity does not exist as a concept.
2. **Colloquial per-plan names** ("2001 expanded 25th anniversary mix", "Notorious BIG
   tribute mix"). The closest existing primitive is the *archive label*: a free-text
   `label` slugified into `brain/data/archives/<stamp>_<slug>/` and recorded in
   `manifest.json` (`brain/archive_mix_plan.py:53-60,76-92`). Names exist today only as
   snapshot annotations, never as the identity of a live editable thing.
3. **Switch between existing plans, and create new ones.** Both current "start something
   else" paths are destructive-then-archive, not switch:
   `PlaylistApp.clear_selection` archives and then empties the selection
   (`brain/playlist_editor.py:432-459`), and `build_mix` auto-archives the existing
   `mix_plan.json` before overwriting it in place
   (`brain/playlist_editor.py:1131-1150`). Archives are **write-only** — restoring is a
   documented manual file copy in the generated `RUN.md`
   (`brain/archive_mix_plan.py:93-103`); there is no restore function, no list function,
   and no API route for either. So "switch" is the genuinely new verb; "name" and
   "snapshot" partly exist.
4. **Add and remove songs within the chosen plan.** Partly exists, scoped to the
   singleton: `POST /api/selection` toggles one track
   (`brain/playlist_editor.py:501-517`, route at `1294`), `POST /api/brain/apply` bulk-adds
   agent picks (`416-430`), `brain/playlist_edit.py` does structured CLI removals, and a
   durable exclusions list guards against re-adds (`brain/playlist.py:17`). All of it
   needs a plan scope.
5. **Conversational LLM editing of dj_notes, transitions, and effects.** The engine
   exists and is good: `brain/mix_directives.py` turns a free-text brief into
   `dj_notes` directive tokens plus a reorder, grounded in real synced lyrics, with two
   hard safety rules — every returned `track_id` is validated against the finalized
   playlist, and a reorder must be an exact permutation (`brain/mix_directives.py:1-27`).
   It is dry-run by default and surfaced in the GUI as ask → preview-diff → apply
   (`brain/playlist_editor.py:223-288`; routes `1340`, `1350`; UI at
   `brain/web/playlist.html:227-232`). **The blocking conflict:** `dj_notes` is a column
   on the `tracks` table keyed by `track_id` (`brain/library_index.py:32`, added by
   migration at `125-126`) — it is *global per song*, so the same track cannot carry
   different notes in two different plans. This is the single largest schema collision in
   the intent.
6. **"Adjust transitions and effects" — no editable transition record exists.**
   Transitions are *derived*, not stored: `compose_mix_plan` computes `segments`
   (`brain/build_mix_plan.py:1534`) from per-track `dj_notes` directives plus the profile
   and DJ format, and writes them into `mix_plan.json` (`version: 2`, keys
   `version / track_count / seconds_per_track / profile / phrase_interval_beats / tracks /
   segments / events / instrument_map`). A real segment looks like
   `{index, from, to, technique, beats, score, showcase_move}`. The only human/LLM-editable
   surface is the per-track `dj_notes` string; there is no per-transition object anyone
   edits directly. Making "adjust this transition" a first-class action is a data-model
   change, not just a UI one.
7. **External agent harness edits + a GUI "refresh".** Partly exists. `GET /api/mix`
   re-reads `mix_plan.json` from disk when no in-memory summary is held
   (`brain/playlist_editor.py:1042-1049`, via `_load_plan_summary` at `637-643`), and a
   "Refresh list" button maps to `POST /api/mix/refresh` → `reexport_finalized`
   (`brain/web/playlist.html:190`, `brain/playlist_editor.py:645-664`, route `1389`).
   **The hazard:** `PlaylistApp` keeps `self.selection` / `self.selected` / `self.by_id`
   in memory, refreshed only by an explicit `reload()` (`brain/playlist_editor.py:69-75`).
   An agent that edits `playlist_selection.json` on disk gets silently clobbered by the
   next in-GUI `save_selection` — a lost-update race with no mtime or version check
   anywhere. "Press refresh and see the truth" therefore needs a defined ownership and
   staleness contract, not just a button.
8. **Bunches: n adjacent songs, fixed internal order, moved as one unit.** Nothing like
   it exists. Ordering today is whole-set and unconstrained: `mix_order` runs
   `greedy_mix_order` over the entire enabled set (`brain/playlist_editor.py:533-557`),
   and the LLM path may only produce an exact permutation. A bunch is a *constraint* that
   must be honored by three independent orderers — the greedy mix graph, the LLM reorder,
   and the DJ-format planner inside `compose_mix_plan` — none of which has a constraint
   input today. The GUI also has no manual reordering at all (no drag handling in
   `brain/web/playlist.html`), so "move them together as a unit" implies adding manual
   reordering as well as grouping.
9. **A new GUI tab.** The nav is two hardcoded buttons — `1 · Curate set` and
   `2 · Create the mix` (`brain/web/playlist.html:105-106`) — driven by a hash router
   (`268`, `357`, `856`) over `#curate` / `#mix`. Adding a third numbered step conflicts
   with the existing linear-wizard metaphor (see gap 9).
10. **Render order + transitions "in a nice GUI way".** Largely reusable: `plan_summary`
    already returns `tracks` and `segments` (`brain/build_mix_plan.py:1780-1810`) and the
    mix page renders segments in a `.mix-segments` list
    (`brain/web/playlist.html:67-68`). Note `plan_summary`'s per-track projection drops
    `dj_notes` and `cue_seconds` (keeping only `track_id/artist/title/bpm/key/cue_source`),
    so a notes-and-transitions view needs a richer payload.

## Tech Stack (Explicit/Inferred)

PRD states `Technology: not stated`. Inferred from the existing repo, unambiguously:

- **Backend:** Python 3, stdlib only for the server — `http.server.BaseHTTPRequestHandler`
  with hand-rolled path dispatch (`brain/playlist_editor.py:1248-1408`), `threading` for
  background scans/builds/runs, `sqlite3`, `argparse`. `uv` for env/deps
  (`pyproject.toml`, `uv.lock`).
- **Frontend:** one hand-written 863-line HTML/CSS/vanilla-JS file
  (`brain/web/playlist.html`) served whole at `/`. No framework, no build step, no bundler,
  no client-side router beyond `location.hash`.
- **Database:** SQLite at `brain/data/library.sqlite3` (schema literal in
  `brain/library_index.py`) for track metadata, enrichment, and `dj_notes`. Plan-adjacent
  state is plain JSON files in `brain/data/` (gitignored).
- **LLM:** pluggable engines `nemoclaw` / `generic` (`brain/pick_candidates.py:217`) plus
  `h-agent`; configured by `CLAWDJ_LLM_BASE_URL` / `CLAWDJ_LLM_API_KEY` /
  `CLAWDJ_LLM_MODEL`. `litellm_cache.sqlite` exists at repo root.
- **Other:** Mixxx control API is the playback target (`hands/`); `core-rust/` is prior
  research and not on this path. The GUI binds `127.0.0.1:8787` (`scripts/start.sh:14`,
  `brain/playlist_editor.py:1418`) — local, single-user, no auth.

## Non-Functional Requirements

- **Switching must be non-destructive.** The repo's existing posture is
  archive-before-destroy (`clear_selection`, `build_mix`). Under multiple plans, that
  becomes the weaker requirement: an unselected plan must simply keep existing, byte-for-
  byte, with no snapshot ritual needed.
- **Concurrent editors are now first-class.** GUI, an agent harness, and CLI modules all
  write the same files. The intent explicitly wants agent edits visible on refresh, which
  makes the current in-memory/on-disk divergence (feature 7) a correctness requirement,
  not a nicety. Repo posture is fail-loud over silent corruption.
- **`dj_notes` are irreplaceable human work.** They are hand-verified per track and feed
  every cue decision (`brain/build_mix_plan.py:101-108,1704-1706`). Any per-plan notes
  model must not orphan or overwrite existing global notes — this directly interlocks with
  the sibling intent `portable-music-collection-…-288cef1d`.
- **Plans reference `track_id` = absolute file path**, so plan portability inherits the
  volume-label contract from that same sibling intent. A plan file is only meaningful on a
  machine where the collection mounts identically.
- **Live-run safety.** `build_mix` already refuses while a mix is playing
  (`brain/playlist_editor.py:1118-1119`); plan switching needs an equivalent guard.
- **No framework, no build step.** A third tab plus a plan switcher must stay inside the
  single vanilla-JS file, and the API stays stdlib string-matched routes.
- **Performance.** All plan state is small JSON; listing/switching should be file reads in
  the low milliseconds. The expensive operations (scan, enrich, build) are already
  backgrounded and polled — switching must not silently trigger a rebuild.
- **Privacy.** `brain/data/` is gitignored on purpose; plan files live there and must not
  be committed.

## Development Requirements

- **Local testing:** the established pattern is `unittest` + `tempfile.TemporaryDirectory`
  with paths injected (`tests/test_mix_plan.py`, `tests/test_mix_directives.py`,
  `tests/test_music_collection_identity.py`). New fixtures implied: a plan store containing
  ≥2 named plans; a plan whose selection was edited on disk while the app held it in memory
  (lost-update test); a bunch that the greedy orderer, the LLM permutation validator, and
  the DJ-format planner must each preserve; a plan whose bunch member was removed. Note
  that `brain/playlist_editor.py` currently has no test file at all and reads module-level
  path constants directly — testability work is a prerequisite.
- **Dev-only UI:** none detected. The GUI is already local-only and the whole app is a
  personal tool; a plan switcher is product UI, not a debug panel.
- **Utility modules implied by PRD verbs:** *create / name / slug* a plan, *list*,
  *switch (activate)*, *rename*, *duplicate*, *delete or archive*, *add/remove* songs
  scoped to a plan, *group / ungroup* (bunch), *move as a unit*, *refresh / reload from
  disk*, and *migrate* the existing singleton state into the first named plan. Reads as: a
  plan-store module (identity, paths, active-plan pointer), a bunch/constraint module
  consumed by all three orderers, and a staleness/version token threaded through the
  existing JSON API.
- **Migration/setup scripts:** yes, at least one — adopt the current
  `playlist_selection.json` + `playlist.json` + `mix_plan.json` as plan #1 without data
  loss, ideally preserving the user's current in-progress set as the active plan. Possibly
  a second: per-plan `dj_notes` storage (new SQLite table or per-plan JSON overlay) with a
  backfill from the global `tracks.dj_notes` column. Optionally an importer that surfaces
  existing `brain/data/archives/*` as named plans.
- **Environment variables:** none new. Existing LLM vars (`CLAWDJ_LLM_BASE_URL`,
  `CLAWDJ_LLM_API_KEY`, `CLAWDJ_LLM_MODEL`) already cover the conversational path.

## Gaps & Ambiguities

1. **Where per-plan `dj_notes` live — the highest-impact gap.** Notes are global per
   `track_id` today (`brain/library_index.py:32`). Options: keep global (a song's notes are
   the same everywhere — simple, but "Juicy" can't open one plan and land mid-verse in
   another), per-plan override layer, or move notes into the plan entirely (breaks
   `load_dj_notes_lookup` at `brain/build_mix_plan.py:101-108` and the enrichment reuse the
   global column exists to provide). Must be decided before anything else.
2. **"Adjust transitions and effects" has no editable object.** Segments are computed
   outputs. Does the architecture add a stored, human/LLM-editable per-transition record
   that survives rebuild — or does the LLM keep expressing transition intent only through
   per-track `dj_notes` tokens (`brain/mix_directives.py` `DIRECTIVE_VOCAB`)? The PRD's
   phrasing implies the former; the current pipeline only supports the latter.
3. **What a "mix plan" *is* at WIP stage.** The pipeline has three stages — enabled
   selection → finalized `playlist.json` → built `mix_plan.json` — each with its own file.
   Is a named plan all three, or just the selection with the rest rebuilt on demand? Does
   switching to a plan whose built plan is stale (`_plan_stale`,
   `brain/playlist_editor.py:619-635`) auto-rebuild, warn, or show as-is?
4. **Bunch semantics are underspecified.** Does a bunch pin only internal order, or also
   the transitions/notes between its members? Are its transitions frozen against rebuild?
   Is a bunch a plan-local object or a reusable library object shared across plans (the
   phrasing "they sound very good with each other" suggests a durable musical fact, which
   argues for reusable)? For the greedy orderer, is a bunch a single super-node with the
   first member's entry key/BPM and the last member's exit? What happens when the LLM
   returns a permutation that splits a bunch — reject, or auto-repair?
5. **Bunch integrity under edits.** If a member is removed from the plan, or its file goes
   unavailable, does the bunch shrink, dissolve, or block the removal?
6. **The refresh contract.** Manual button only, or polled? Does the GUI ever write over
   disk state it didn't read? A version/mtime token on each plan file plus a "changed
   underneath you" response is the obvious answer, but the PRD doesn't say, and today
   nothing in `PlaylistApp` compares before writing.
7. **How agents address a plan.** A `--plan <name>` flag on every CLI module, an
   active-plan pointer file that all modules read, or an env var? This decides whether
   `hands/run_mix_plan.py`, `brain/build_mix_plan.py`, `brain/preview_transitions.py`, and
   `brain/mix_directives.py` change signature or merely change their default path
   resolution. Also: when a human switches plans in the GUI, does a running agent's next
   CLI call follow?
8. **Relationship between named plans and existing archives.** Does archiving become
   "save a version of plan X"? Do `brain/data/archives/*` entries appear in the new tab?
   Does the auto-archive-before-rebuild behavior (`brain/playlist_editor.py:1131-1150`)
   survive, become per-plan history, or go away as redundant?
9. **Tab vs. global plan picker.** The nav is a numbered linear wizard
   (`1 · Curate set` → `2 · Create the mix`). A plan chooser is orthogonal to both steps —
   it scopes them — so a third numbered tab arguably models it wrong; a plan selector in
   the header above both tabs, plus a new tab for the per-plan song/transition editor, may
   fit better. The PRD asks the question ("Should we have another tab…") rather than
   answering it, so it needs a design decision, and it affects the hash-router contract
   (`#curate` / `#mix` are user-visible URLs).
10. **Plan lifecycle policy.** How many plans, retention, deletion (soft vs. hard), and
    what happens to a plan whose tracks are no longer available.
11. **Switching during a live run.** `run_mix_plan` may be playing from `mix_plan.json`
    while the user switches plans in the GUI. Refuse, or isolate the running plan?
12. **Plan store layout.** Directory-per-plan (`brain/data/plans/<slug>/…`) vs. rows in
    `library.sqlite3`. Interacts with gitignore, USB portability
    (`brain/portable_library.py`), and how easily an external agent harness can read and
    write a plan with plain file tools — which the PRD implicitly requires, since agents
    are expected to edit plans out-of-band.
13. **Multi-user/auth:** out of scope — the server binds `127.0.0.1` with no auth and the
    PRD implies a single local user. Assumed unchanged.
14. **Tech stack ambiguity: none to resolve.** PRD says "not stated," but the repo fixes it
    (Python 3 stdlib server + SQLite + single vanilla-JS page). Step 2 needs no technology
    decision, only placement within these modules.

---
*Proceeding to Step 2: Deep Analysis*
