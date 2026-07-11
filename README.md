# claw-dj

Autonomous / semi-autonomous DJ. Started at the H Company Computer Use
Hackathon (SF, 2026-07-11/12); also the seed of a longer-running personal
project toward an agent that can mix like a hip-hop DJ — beat juggling,
crate selection, reading a crowd.

Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Short version —
the H Company computer-use agent (`brain/`) makes judgment calls and visibly
drives Mixxx's GUI; a deterministic MIDI engine (`hands/`) executes anything
beat-critical, because a screenshot-loop agent is too slow for that.

## Setup

```
uv venv --python 3.13
source .venv/bin/activate
uv pip install -e .
export HAI_API_KEY="hk-..."   # from platform.hcompany.ai
```

Mixxx must be running locally with the `claw-dj` controller mapping loaded
(see `hands/mixxx_mapping/README.md` — not written yet, do this first on
hackathon day).

## Status

Scaffolding only — command schema and module layout are in place, nothing
is wired to a real Mixxx instance yet.
