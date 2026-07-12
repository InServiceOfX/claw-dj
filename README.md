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
- **Hackathon context** (event rules, links, submission requirements):
  [docs/HACKATHON.md](docs/HACKATHON.md).

`core-rust/` and `agent/` are a more mature Mixxx-driving implementation
(Rust core + Python MIDI bridge) ported in from earlier work on this same
idea — see [docs/prior-research/](docs/prior-research/) for provenance and
`docs/HANDOFF.md` for how it relates to `hands/`.

## Curate a playlist

Scan one or more library roots, merge Mixxx's existing BPM/key analysis, and
open the local playlist picker:

```bash
uv run python -m brain.scan_library /path/to/HipHop /path/to/RnB
uv run python -m brain.sync_mixxx_analysis
uv run python -m brain.playlist_editor --open
```

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
