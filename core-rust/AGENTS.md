# AGENTS.md — core-rust

Ported from Monoclaw's `Projects/clawdj/AGENTS.md` (2026-07-11), paths
adjusted for living at the repo root instead of a subdirectory. See
[`docs/prior-research/README.md`](../docs/prior-research/README.md) for full
provenance.

## Scope

Rust workspace for the clawdj CLI + library — MIDI dispatch, Mixxx queue
bootstrap. Keep this directory portable: no hardcoded music-library paths,
no credentials, no committed caches.

## Setup

- Read `README.md` and `docs/prior-research/docs/ARCHITECTURE.md` (or this
  repo's own `docs/ARCHITECTURE.md`) before editing.
- Mixxx DB path comes from `CLAWDJ_MIXXX_DB` or defaults to the macOS sandbox
  location under `~/Library/Containers/org.mixxx.mixxx/.../Mixxx/mixxxdb.sqlite`
  (see `shared/mixxx_db.py` at the repo root for the Python equivalent — keep
  these two in sync if either changes).

## Common commands

- Build: `cargo build --workspace`
- Test: `cargo test --workspace`
- Lint: `cargo clippy --workspace --all-targets -- -D warnings`
- Format: `cargo fmt --all`
- Live MIDI probe: `CLAWDJ_LIVE=1 cargo test -p clawdj --test live_midi -- --nocapture`

## Conventions

- Queue writes must be limited to Mixxx `Playlists` / `PlaylistTracks` rows
  owned by `__clawdj_queue`; never modify `library` or `track_locations`.
- Update `docs/HANDOFF.md` at the repo root when work here completes or when
  leaving the tree in a useful partial state — same convention the original
  project used with its own `PROGRESS.md`, consolidated into this repo's one
  handoff doc instead of a second one.

## Completion signal

1. `cargo fmt --all`
2. `cargo clippy --workspace --all-targets -- -D warnings`
3. `cargo test --workspace`
4. Update `docs/HANDOFF.md`
