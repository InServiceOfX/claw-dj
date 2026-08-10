<!-- pdd-story-status: observed-working-baseline-2026-08-09 -->
<!-- pdd-story-areas: collection, scan_library, playlist_editor, pick_candidates -->

# User Story: Mount a music volume, index it once, curate a set with the DJ brain

## Story

As a DJ working from external music volumes, I can register a mounted volume
as a music collection with its own SQLite index, scan it for local tags on
first use, re-check for only new or changed files later, ask an agent to
suggest tracks against that library, and add or remove songs on a working
playlist — so that switching volumes does not wipe prior libraries and
routine “check for new music” stays cheap after the first full index.

## Acceptance criteria (observable)

1. **New volume / collection**
   - I can start a new music collection from the Curate page (or CLI
     `brain.collection new`) pointed at a mounted volume (e.g.
     `/Volumes/Elements`).
   - A per-volume database is created under that volume’s `clawdj/` data
     directory (e.g. `/Volumes/Elements/clawdj/library.sqlite3`).
   - The previous collection remains listed and can be re-activated later.

2. **First-pass metadata (local only)**
   - After create (or “Scan after creating” / “Check for new music”), the
     system discovers audio files under the configured roots and writes
     local tag metadata into that collection’s SQLite.
   - This pass does **not** require lyrics APIs, chroma, or Mixxx analysis
     for every track.

3. **Incremental re-check**
   - When I press **Check for new music** again on an already-indexed
     collection, the log shows nearly all files as **unchanged (skipped)**
     and only **new/changed** files get tag reads.
   - Example of a healthy re-check (Elements, observed):
     - `discovered 73937 audio files under 1 root(s)`
     - `73899 unchanged … reading tags for 8 new/changed file(s)`
     - Editor reports track count ≈ unchanged + newly indexed (e.g. 73899).

4. **Ask the DJ brain**
   - From Curate I can describe a set brief; an agent returns candidate
     picks for review.
   - **New music only** searches the latest scan’s additions.
   - **Whole library** searches the active collection (keyword-pre-filtered).
   - I can uncheck picks, then **Add checked to set**, and continue editing
     the set (enable/disable, clear, seed hits, order tools) without losing
     the active collection context.

5. **Startup default**
   - Restarting the playlist editor reuses the last-used active collection
     without forcing a “which volume?” prompt every time.

## Out of scope for this story

- Full-library Analyze & Enrich (BPM/key via Mixxx, lyrics, chroma) for every
  track on first scan.
- Multi-machine sync of the same volume’s DB beyond the portable marker /
  per-volume path design already in place.
- Guaranteeing a specific cloud agent (NemoClaw / H Company) is online —
  engines may fail closed with a clear error when their runtime is down.

## Engines note (operations, not product behavior)

- **nemoclaw** needs Docker + a running NemoClaw sandbox + port forward to
  `127.0.0.1:8642` (see `brain/pick_candidates.py` / HANDOFF).
- **h-agent** needs H Company credentials.
- **generic** needs `CLAWDJ_LLM_*` env vars (e.g. xAI).

## Evidence of current baseline (2026-08-09, this machine)

- Active collection: `ElementsMusic` → `/Volumes/Elements`,
  DB `/Volumes/Elements/clawdj/library.sqlite3`.
- Legacy local library still registered and switchable.
- After full index, re-scan skipped ~73.9k unchanged and tagged a small delta.
- Product intent for multi-volume collections:
  `docs/intents/intent__load-a-new-music-collection-from-a-chosen-volume-1830f5e2.md`
  and related Elements intent under `docs/intents/`.

## PDD follow-ups (optional)

- Promote acceptance checks into a story contract under
  `user_stories/contracts/` if we want automated regression.
- Keep implementation brownfield: no full-repo regenerate; changes stay in
  collection / scan / playlist_editor / pick_candidates modules already
  adopted.
