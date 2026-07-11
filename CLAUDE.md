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

Work happens on feature branches (currently `brain-hands-architecture`),
never directly on `main`/`master`. Ernest reviews and merges to
`main`/`master` himself.

## Data

`brain/data/` (scanned crate, demo subsets, `.m3u` files) is gitignored on
purpose — it's derived from a personal media library, not project code.
Regenerate it locally via `brain/scan_library.py` /
`brain/build_demo_subset.py` rather than expecting it to be there after a
fresh clone.
