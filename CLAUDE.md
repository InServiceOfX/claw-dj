# CLAUDE.md — claw-dj

Before doing anything else in this repo, read `docs/HANDOFF.md` — it links
to `docs/HACKATHON.md` (event context: dates, rules, links, submission
requirements) and `docs/ARCHITECTURE.md` (system design: the brain/hands
split and why). HANDOFF.md has the current build status, what's in
progress, and prioritized next steps.

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
