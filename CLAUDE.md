# CLAUDE.md — claw-dj

Before doing anything else in this repo, read `PROGRESS.md` (current
state, run commands, prioritized next steps — kept agent-agnostic for any
harness) and `docs/HANDOFF.md` — the deep context: it links to
`docs/HACKATHON.md` (event context) and `docs/ARCHITECTURE.md` (system
design: the brain/hands split and why). Keep both updated as you work.

Keep `docs/HANDOFF.md` updated as work progresses — especially "known gaps
/ next steps" and "what's built so far" — so it stays accurate for the next
machine/session, not just this one.

## Git

Work happens on feature branches, never directly on `main`/`master` — check
`git branch --show-current` before every commit (the checked-out branch can
change mid-session if Ernest merges to `master` himself, which he does
frequently after reviewing). If it's `master`, create or switch to a branch
first. Ernest reviews and merges to `main`/`master` himself.

## Multiple implementations of the same thing

This project absorbed a more mature prior attempt at itself (`core-rust/`,
`agent/` — see `docs/prior-research/` and `docs/HANDOFF.md`). Don't assume
the newest-written code in `hands/` is the current direction by default;
check `docs/HANDOFF.md`'s "known gaps" for which implementation is actually
live.

## Data

`brain/data/` (scanned crate, demo subsets, `.m3u` files) is gitignored on
purpose — it's derived from a personal media library, not project code.
Regenerate it locally via `brain/scan_library.py` /
`brain/build_demo_subset.py` rather than expecting it to be there after a
fresh clone.
