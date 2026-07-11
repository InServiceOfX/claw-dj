# Prior research — ported from Monoclaw

This folder is research, planning, and design docs from an earlier session
(2026-04-25 through 2026-07-08) that worked on the same idea — an AI-driven
DJ harness on top of Mixxx — under `Projects/clawdj/` in a different, private
repo (`InServiceOfX/Monoclaw`, branches `feat/clawdj-mixxx-harness` and
`feat/clawdj-core-rust-skeleton`, plus a `master` commit on 2026-07-08 adding
a Python MIDI bridge and a Hermes agent skill). That work reached a real Rust
core skeleton (`cargo fmt`/`test`/`clippy` clean) and a proven Mixxx
integration design, but stalled before an actual live Mixxx validation run.

Rather than re-derive this research from scratch during the hackathon, it's
ported here wholesale (2026-07-11) — code under [`core-rust/`](../../core-rust/)
and [`agent/`](../../agent/) at the repo root, the Mixxx mapping under
[`hands/mixxx_mapping/`](../../hands/mixxx_mapping/), and these docs here for
reference. Monoclaw's copy is left to go stale; this is now the canonical
location.

**What's genuinely load-bearing here, if you only read one thing:**
[`docs/MIXXX_INTEGRATION.md`](docs/MIXXX_INTEGRATION.md) — confirms (as of a
2026-07-03 recheck against Mixxx 2.5.6 and a local `main` source checkout)
that stock Mixxx has *no* TCP/HTTP/WebSocket/REST API, and documents the
`__clawdj_queue` playlist trick for loading tracks by path, which our own
`hands/` didn't have a solution for yet.

## Layout (mirrors the original)

- `docs/ARCHITECTURE.md`, `ANALYSIS.md`, `LIVE_LOOP.md`,
  `MIXXX_INTEGRATION.md`, `SETUP_MACOS.md` — system design, the offline
  analysis pipeline (not yet built), the live loop, Mixxx integration
  research, and macOS setup notes.
- `planning/DECISIONS.md`, `ROADMAP.md`, `TASKS.md` — ADR-style decision log,
  milestones, atomic tasks.
- `research/mixxx-controls.md`, `prior-art.md` — catalog of Mixxx's
  `[group, key]` control surface, and a survey of comparable projects.

## Known divergence from this repo's own docs

This repo's own [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) (written fresh
during the hackathon) and this folder's `docs/ARCHITECTURE.md` describe
overlapping but not identical designs — both converged independently on
"Mixxx + virtual MIDI, judgment layer separate from real-time execution,"
but our hackathon doc frames it as brain (H Company computer-use agent) /
hands (deterministic MIDI), while this one frames it as
clawdj-core (Rust) + an OpenClaw agent for high-level planning. Reconciling
these into one architecture is an open task — see the main
[`docs/HANDOFF.md`](../HANDOFF.md) for current status.

## What was deliberately left out of this port

- `LATER.md`, `PROGRESS.md`, top-level `AGENTS.md`/`README.md` from the
  original — narrative/resume-tracking files specific to that session, some
  containing personal context not appropriate for a repo that may go public
  for hackathon judging. Their factual content (what's done, what's not, a
  few engineering gotchas worth keeping) was folded into this repo's own
  `docs/HANDOFF.md` instead.
- One example file path in `ANALYSIS.md` was genericized
  (`/Users/ernestyeung/Music/...` → `/path/to/your/Music/...`).
- Everything else was audited for hardcoded personal paths/credentials before
  porting (none found beyond that one doc example — the original work was
  already careful about this, per its own `AGENTS.md`: "no hardcoded
  music-library paths, no credentials, no committed caches").
