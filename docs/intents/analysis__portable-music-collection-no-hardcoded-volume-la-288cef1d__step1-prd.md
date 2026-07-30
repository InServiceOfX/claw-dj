# Step 1: PRD Analysis

Intent: [`portable-music-collection-no-hardcoded-volume-la-288cef1d`](intent__portable-music-collection-no-hardcoded-volume-la-288cef1d.md)
Workflow: agentic architecture, step 1 of 13.
Output target: the workflow prescribed `gh issue comment 3248734095 --repo /`. There is
no such GitHub issue — the intent's source kind is `inline`, source reference `not
applicable`, route `local_full_architecture`, and issue 3248734095 does not exist in
`InServiceOfX/claw-dj`. This file is the step-1 output in its place.

**Status:** Analysis Complete

## Project Summary

- **Title:** Portable music collection: no hardcoded volume label, safe availability,
  deferred relative identity
- **Goals:** Make claw-dj's music library index portable across machines by recording the
  collection's identity (stable id + current mount base) as data in the index rather than
  as constants in code, and harden availability reconciliation so a flaky, empty, or
  unmounted volume can never be mistaken for a mass deletion that orphans irreplaceable
  enrichment and human `dj_notes`.

## Features Identified

1. **No hardcoded volume label or mount prefix in code/config defaults.** One real
   violation exists: `brain/portable_library.py:44`
   (`DEFAULT_USB_DB = Path("/Volumes/USB322FD/clawdj/library.sqlite3")`), used as the
   default for both `export_db` and `import_db` and as the `--usb-db` argparse default.
   Occurrences in `brain/scan_library.py:15-16` (usage docstring) and across
   `docs/SETUP_NEW_MACHINE.md`, `docs/HANDOFF.md`, `README.md`, `PROGRESS.md` are
   documentation, not defaults. `tests/test_catalog_curate.py:14-49` uses the label as
   fixture strings.
2. **User-specified collection with per-machine mount resolution.** No collection concept
   exists today. The index has a flat `roots` table of absolute paths
   (`brain/library_index.py:40-44`); nothing records "which collection is this" or "where
   is it mounted right now on this machine."
3. **Scan roots stay user-specified and relative to the collection.** Roots are already
   user-supplied rather than hardcoded (CLI positional args, GUI "Add music folder" at
   `brain/web/playlist.html:117-118`), and are persisted per machine — pinned by
   `tests/test_music_collection_identity.py:159`. They are currently stored absolute
   (`brain/scan_library.py:216-220`, `configured_roots()` at
   `brain/library_index.py:116`), so "relative to the collection" is the new part.
4. **Record mount base + stable collection id in the library index.** Requirement is
   explicitly that identity be re-derivable *without reading code* — so this is a schema
   change plus a backfill, not a config constant.
5. **Track identity stays the absolute file path (Tier 1).** Deliberate, decision recorded
   2026-07-30, and pinned as a tripwire by
   `tests/test_music_collection_identity.py:44` (`test_track_id_is_the_absolute_file_path`).
6. **Documented volume-label contract.** Because identity is the absolute path, a
   replacement volume must be named identically or every `track_id` and every `dj_notes`
   row orphans. `docs/SETUP_NEW_MACHINE.md:10-14,93-96` explains identity-is-absolute-path
   and name collisions, but does not state the replacement-volume rule. This is a
   documentation deliverable, not just an implementation one.
7. **Guard against a mass availability flip.** The known gap is
   `brain/scan_library.py:309-315`: every indexed track under a scanned root that isn't in
   the discovered set is flipped to `available=0`, unconditionally. On the real library a
   root that exists but yields zero files silently flips ~54k rows. Currently pinned as
   *undesired* behavior by `test_present_but_empty_root_currently_marks_all_tracks_unavailable`
   (`tests/test_music_collection_identity.py:124`), which is documented to be replaced by
   its positive form when the guard lands.
8. **An unmounted collection is never read as deleted.** Already held by the root-existence
   precheck before the DB is opened (`brain/scan_library.py:183-186`), pinned by
   `tests/test_music_collection_identity.py:73`. Must not regress. The residual hole is a
   mount point that *exists but is wrong* — an empty `/Volumes/<name>` directory, or a
   partially mounted ExFAT volume — which passes the precheck and falls into feature 7.
9. **Three equivalent initial-population surfaces.** All three converge on
   `incremental_scan()` today: CLI `brain/scan_library.py:343` (`main`), GUI "Check for new
   music" → `PlaylistApp.start_scan` (`brain/playlist_editor.py:82-117`, button at
   `brain/web/playlist.html:119`), and agent-run (an agent invoking the same CLI module).
   Their *post-scan* work already diverges — see gap 5.
10. **Never re-read tags for already-indexed unchanged files.** Held by the
    `size_bytes` + `mtime_ns` equality check at `brain/scan_library.py:235`; unchanged
    files only get `available`/`last_seen_at` touched. Covered by
    `tests/test_incremental_scan.py`.
11. **Atomic, fail-loud Tier-2 identity migration (deferred).** If `track_id` ever becomes
    collection-relative, the stored keys and the scan's identity function must change
    together; a partial migration must fail loudly rather than duplicate rows or drop
    lookups. Deferred until a real trigger (Linux, or moving off the USB stick), but the
    architecture must leave room for it — today there is no schema version marker and no
    recorded identity style, so a partial migration would be undetectable.

## Tech Stack (Explicit/Inferred)

PRD states `Technology: not stated`. Inferred from the existing repo, unambiguously:

- **Backend:** Python 3 (stdlib `argparse`, `sqlite3`, `threading`,
  `concurrent.futures`, `http.server`); `mutagen` for tag reads; `uv` for env/deps
  (`pyproject.toml`, `uv.lock`).
- **Frontend:** single hand-written HTML/CSS/vanilla-JS page
  (`brain/web/playlist.html`) served by the stdlib HTTP server in
  `brain/playlist_editor.py`. No framework, no build step.
- **Database:** SQLite — `brain/data/library.sqlite3`, schema literal at
  `brain/library_index.py:18-101`. Derived JSON exports (`crate.json`, `catalog.json`)
  are compatibility artifacts consumed by the curation pipeline.
- **Other:** macOS `/Volumes` mount semantics are load-bearing for the current Tier-1
  identity choice. `core-rust/` exists (prior attempt; chromagram) but is not on this
  intent's path. Mixxx control API is out of scope here.

## Non-Functional Requirements

- **Data safety is the dominant constraint.** `track_id` is the foreign key for
  `lyrics`, `chroma`, `phrases`, `lyric_timelines`, `beat_phase`, and human `dj_notes`
  (`brain/library_index.py:47-85`). These are expensive or impossible to regenerate
  (`brain/portable_library.py:1-15`). Any identity or availability change risks
  irreversible orphaning at ~54k-row scale.
- **Fail loudly over silent corruption.** Explicit in the PRD for migration; the same
  posture already governs `dj_notes` merge conflicts (`brain/portable_library.py:128-131`)
  and should govern the availability guard.
- **Idempotency.** A second scan must be a no-op (`tests/test_incremental_scan.py:28-36`);
  a second import must be a no-op (`brain/portable_library.py:33`).
- **Performance at 10k+ files.** Threaded tag reads plus the unchanged-file skip are what
  make a contended USB scan tractable (~1 s/file serial —
  `brain/scan_library.py:135-138`). The no-re-read requirement is as much a performance
  invariant as a correctness one, and mount resolution must not add a per-file cost.
- **Cross-machine portability.** Mac→Mac works today via identical `/Volumes` paths;
  Linux differs and is deferred (`docs/LINUX_PORT.md`, `PROGRESS.md`).
- **Progress observability.** The GUI polls `scan_state` every 750ms
  (`brain/scan_library.py:176-181`, `brain/web/playlist.html:286-293`); new refusal or
  guard states must be reportable through that same row.
- **Privacy.** `brain/data/` is gitignored on purpose; personal library data must not be
  committed or sent anywhere.

## Development Requirements

- **Local testing:** Established pattern is `tempfile.TemporaryDirectory()` plus
  `patch("brain.scan_library._read_record", side_effect=_record)` so tests need no real
  audio (`tests/test_music_collection_identity.py:30-40`). New fixtures implied: a fake
  mount base (temp dir standing in for a mounted volume), an "unmounted" variant (path
  absent), a "present but empty/stale mount" variant (path exists, zero files), and a
  registered-collection index fixture. No emulator or auth needed. Migration tests need a
  pre-change index to upgrade from.
- **Dev-only UI:** none detected. The GUI is already local-only and already has the
  "Add music folder" affordance; the collection/mount base may need a read-only display
  alongside `roots-detail` (`brain/web/playlist.html:114`), but that is product UI, not a
  debug panel.
- **Utility modules:** implied by the PRD's verbs — *resolve* (collection id → current
  mount base on this machine), *record* (write collection identity into the index),
  *re-derive* (read identity back without reading code), *guard/refuse* (block a mass
  availability flip), *migrate* (Tier-2 relative-path migration, atomic + fail-loud).
  Reads as: a collection/mount-resolution module, an index-migration module with a
  version + identity-style marker, and a guard inside `incremental_scan`.
- **Migration/setup scripts:** yes. (a) Additive SQLite schema for collection id + mount
  base, with backfill for existing indexes — the current seam is `connect()`
  (`brain/library_index.py:104-113`), which does `executescript(SCHEMA)` plus one ad-hoc
  `PRAGMA table_info` column check and has no version table. (b)
  `brain/portable_library.py` must carry the new collection rows across machines
  (`_TRACK_COLUMNS`/`_CACHE_TABLES`/roots-union all need extending). (c) A designed-but-
  deferred Tier-2 identity migration with a partial-state detector.
- **Environment variables:** none required by this PRD. Existing unrelated ones:
  `CLAWDJ_LLM_BASE_URL`, `CLAWDJ_LLM_API_KEY`, `CLAWDJ_LLM_MODEL`
  (`brain/pick_candidates.py:164-171`), `HAI_API_KEY`, `XDG_CONFIG_HOME`
  (`brain/agent.py:43-51`). Whether mount specification arrives via env var is an open
  question — see gap 1.

## Gaps & Ambiguities

1. **Where the user specifies the collection is undefined.** CLI flag, config file, GUI
   field, index row, or env var? This determines which of the three surfaces change and
   how they stay equivalent. Highest-impact gap for architecture.
2. **Collection id derivation is unspecified.** "Stable collection id" could be a
   generated UUID stored in a marker file on the stick, the volume UUID from `diskutil`,
   or a hash of collection contents. The choice decides whether an identically-named
   replacement volume is recognized as the same collection or a different one — which
   directly interacts with the documented replacement-volume rule.
3. **The availability-guard threshold is unspecified.** "Suddenly returns no files" is
   unambiguous at zero, but a root returning 1 of 54k files is the same hazard. Need a
   policy (refuse-at-zero vs. refuse-above-N%-loss) and an escape hatch for genuine bulk
   deletion, or the guard will block legitimate cleanups.
4. **What the scan does when it refuses is unspecified.** Hard error, warn-and-leave-
   availability-untouched, or record a "suspect" state? Affects the `scan_state` schema
   and how all three surfaces report it.
5. **"Same result" across the three surfaces is underspecified, and they already differ.**
   CLI writes `crate.json`, `scan_skipped.json`, and `catalog.json` only under `--catalog`
   (`brain/scan_library.py:377-395`). The GUI writes `crate.json`, always writes the
   catalog, refreshes the new-music view, and writes no skipped report
   (`brain/playlist_editor.py:100-111`). Which side is normative?
6. **"Agent-run" is not a distinct code path today** — an agent shells out to the CLI
   module. If the PRD means it must be a first-class surface, its interface is undefined.
7. **Documentation location for the replacement-volume rule.**
   `docs/SETUP_NEW_MACHINE.md` is the natural home; the PRD says "must be documented"
   without saying where or at what prominence.
8. **Single vs. multiple collections.** The PRD says "the collection" (singular). Whether
   the index must support more than one changes the schema shape — a `collections` table
   with per-root foreign keys vs. columns on a singleton row.
9. **Linux interaction.** Explicitly deferred, but recording a mount base is precisely the
   enabling step (`docs/LINUX_PORT.md`). Unclear whether this intent should make Linux
   resolution work or merely not block it.
10. **Storage form of `roots` under the new model.** If roots become "relative to the
    collection" while `track_id` stays absolute, that mixed state needs an explicit
    decision: changing `roots.path` to a relative value is itself a stored-key change
    touching `configured_roots()`, the GUI roots display, `catalog.py`'s `roots=` argument,
    the `root IN (...)` scoping query at `brain/scan_library.py:310-313`, and
    `portable_library`'s roots union.
11. **Do test fixtures count as "code"?** `tests/test_catalog_curate.py:14-49` hardcodes
    `/Volumes/USB322FD/...` as literal strings. Harmless as test data; step 2 should decide
    whether the no-hardcoding rule reaches fixtures.
12. **Tech stack ambiguity: none to resolve.** PRD says "not stated," but the existing
    repo fixes it (Python + SQLite + vanilla-JS local GUI). Step 2 needs no technology
    decision, only placement within these modules.

---
*Proceeding to Step 2: Deep Analysis*
