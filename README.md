# claw-dj

Autonomous / semi-autonomous DJ. Started at the H Company Computer Use
Hackathon (SF, 2026-07-11/12); also the seed of a longer-running personal
project toward an agent that can mix like a hip-hop DJ — beat juggling,
crate selection, reading a crowd.

Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Short version —
the H Company computer-use agent (`brain/`) makes judgment calls and visibly
drives Mixxx's GUI; a deterministic MIDI engine (`hands/`) executes anything
beat-critical, because a screenshot-loop agent is too slow for that.

- **Need a live two-track transition immediately?**
  [docs/MIX_TWO_TRACKS.md](docs/MIX_TWO_TRACKS.md) is the shortest attended
  runbook.
- **Need the short hackathon set?**
  [docs/QUICK_MIX_DEMO.md](docs/QUICK_MIX_DEMO.md) runs a six-track,
  sample-lineage mix with optional H Company agent ordering.

- **Picking up this project on a new machine?** Start with
  [docs/HANDOFF.md](docs/HANDOFF.md) — full environment setup, what's built,
  what's in progress, known gaps.
- **Recreating the dedicated Hermes `clawdj` agent?** Use the lightweight,
  Git-based [docs/HERMES_AGENT_SETUP.md](docs/HERMES_AGENT_SETUP.md) rather
  than copying private session databases, caches, logs, or credentials.
- **Hackathon context** (event rules, links, submission requirements):
  [docs/HACKATHON.md](docs/HACKATHON.md).

`core-rust/` and `agent/` are a more mature Mixxx-driving implementation
(Rust core + Python MIDI bridge) ported in from earlier work on this same
idea — see [docs/prior-research/](docs/prior-research/) for provenance and
`docs/HANDOFF.md` for how it relates to `hands/`.

## Curate a playlist

Playlist data is **only songs available on this machine**. Scan one or more
library roots for metadata (title/artist/album/genre via mutagen — no audio
analysis; typically a few ms/file), optionally hand the slim catalog to an
agent, then export a Mixxx playlist:

```bash
# first scan records the roots; later runs only reopen new/changed files
uv run python -m brain.scan_library \
  /Volumes/USB322FD/Music/RnB /Volumes/USB322FD/Music/HipHop --catalog

# researched hits per library artist → mix-ordered (BPM/key/sample lineage)
# always keeps your current UI selection unless --replace-user
uv run python -m brain.curate_playlist --mode hits --planner mix-graph

# H Company agent reorders that hit pool for blend storytelling (planning only)
uv run python -m brain.curate_playlist --mode hits --planner h-agent

# reorder only what you already enabled in the picker
uv run python -m brain.curate_playlist --mode selection --planner h-agent

# browser picker: enable hits, "Order for mixes", export
# it also provides a one-click incremental "Check for new music" workflow
uv run python -m brain.playlist_editor --open

# find beatgrid-aligned entry phrases for the short demo subset
uv run python -m brain.phrase_analysis --tracks 6

# enrich hit pool (sample lineage + lyrics + optional Rust chromagram)
uv run python -m brain.enrich_playlist --chroma --chroma-limit 12

# continuous multi-song mix plan → perform in Mixxx
uv run python -m brain.build_mix_plan --tracks 6 --phrase-beats 32
uv run python -m hands.run_mix_plan --dry-run
# Mixxx with --control-api-port 9995:
uv run python -m hands.run_mix_plan

# after Mixxx analyzes newly imported tracks
uv run python -m brain.sync_mixxx_analysis
```

See [`docs/MIX_INSTRUMENT.md`](docs/MIX_INSTRUMENT.md) for Mixxx knobs/buttons
and transition techniques.

The picker can add the researched R&B/West Coast seed, search and filter all
scanned tracks, enable or disable individual songs, and export
`brain/data/playlist.m3u8` plus a metadata-preserving JSON snapshot. Import the
`.m3u8` into Mixxx, analyze newly added tracks there, then rerun the sync. All
generated library and playlist data stays under gitignored `brain/data/`. See
[`docs/RNB_HITS_RESEARCH.md`](docs/RNB_HITS_RESEARCH.md) for the source-linked
artist-by-artist choices and local match results.

## Setup

See [docs/HANDOFF.md](docs/HANDOFF.md#environment-setup-on-a-new-machine)
for the full walkthrough (H Company SDK login, Mixxx, music
library). Short version:

```
uv venv --python 3.13
uv sync
hai login    # from hai-agents[cli] — see HANDOFF.md
```

## Status

See [docs/HANDOFF.md](docs/HANDOFF.md#whats-built-so-far) — actively being
built during the hackathon, updated as work progresses.

## Persistent mix plans

The editor keeps several **work-in-progress** mixes side by side — the
"2001 expanded 25th anniversary mix" and the "Notorious BIG tribute mix" as
separate, switchable plans instead of one hardcoded
`playlist_selection.json` / `playlist.json` / `mix_plan.json` trio.

The implemented feature has PDD source specifications and executable
characterization. Its design lives in four tracked places:

| File | What it holds |
|------|---------------|
| [`architecture.json`](architecture.json) | 37 modules, priorities, dependency graph, per-module interfaces and reference URLs |
| [`.pddrc`](.pddrc) | Maps each prompt basename to its generated file path |
| [`prompts/`](prompts/) | Module-level `.prompt` source specifications, filled from the reviewed architecture |
| [`docs/intents/`](docs/intents/) | The intent record and the step-by-step analysis it was derived from |

What is implemented:

- **Plans are directories.** `plans/<slug>/` holds `plan.json`, `selection.json`,
  `notes.json`, `bunches.json`, `transitions.json`, `journal.jsonl`. No registry
  file — the directory scan *is* the list, so `cp -r` on a plan just works.
- **Bunches.** 2–4 songs that sound good together, held contiguous and moved as
  one unit. Stored in the library index (overlap is legal — you can know both
  that A→B works and that B→C works) and *activated* per plan, where overlap is
  rejected.
- **Agents are first-class writers.** `python -m brain.plan_cli` is the offline
  contract for Hermes / Claude / Codex; every mutation is rev-guarded and lands
  in an append-only journal recording both `actor` (which surface) and `author`
  (who composed it — including `llm`). The GUI's "What changed" strip reads that
  journal, which is what makes "press Refresh and see the truth" true.
- **A third `3 · Arrange` tab**, with the plan picker above the nav rather than
  inside it — a plan is a *scope*, not a wizard step.

### Agent and PDD workflow

```
uv run python -m brain.plan_cli list --json
uv run python -m brain.plan_cli show --plan <slug> --json
pdd contracts check prompts/ --stories user_stories/
pdd sync plan_types --dry-run   # inspect drift; do not regenerate blindly
```

Prompt paths mirror their output modules under `prompts/`. The checked-in
implementation is the reviewed brownfield baseline; a future `pdd sync` must
be scoped and reviewed rather than used to rewrite the subsystem wholesale.

### Configuration

The editor binds `127.0.0.1:8787`, single local user, no auth or login.
`CLAWDJ_MIXXX_CONTROL_PORT` is an optional explicit runtime override; otherwise
`scripts/start.sh` validates and reuses the actual patched Mixxx control port.

### Tests

```
uv run python -m unittest discover -s tests
```

Note `-s tests` without `-t .`: `tests/` has no `__init__.py`. pytest is **not**
installed. New modules keep their path constants at module level
(`DEFAULT_*`) and read them as `module.DEFAULT_X` at call time, because the
suite isolates by patching those constants and a `from ... import` binds an
unpatchable copy.
