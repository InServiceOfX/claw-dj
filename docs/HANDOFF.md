# Handoff / continuation notes

Written 2026-07-11 mid-hackathon so work can resume on a different machine
(Linux desktop) with full context. See also [HACKATHON.md](HACKATHON.md)
(event rules/links) and [ARCHITECTURE.md](ARCHITECTURE.md) (system design).

## The two goals, simultaneously

1. Win the H Company Computer Use Hackathon (SF, 2026-07-11/12) — Computer
   Use track, must use H Company's agent.
2. Seed a longer-running personal project: an autonomous/semi-autonomous DJ
   that mixes like a hip-hop DJ (beat juggling, crate selection, reading a
   crowd), controlling Mixxx.

Both goals point at the same architecture, so there's one codebase.

## Repos

- **`claw-dj`** (this repo) — `git@github.com:InServiceOfX/claw-dj.git`,
  branch `brain-hands-architecture` (not `master` — all work happens here).
- **`holo-desktop-cli`** — `https://github.com/hcompai/holo-desktop-cli`,
  cloned locally at `repos/holo-desktop-cli` on the Mac this was built on.
  This is H Company's open-source client that drives their closed-source
  `hai-agent-runtime` binary (downloads itself on first run, sha256-verified)
  over loopback. `claw-dj`'s `brain/agent.py` imports it as a library
  (`holo_desktop.agent_client`), it isn't shelled out to as a CLI.

## Why holo-desktop-cli, not the `hai_agents.Client()` SDK snippet

An H Company engineer's first answer to "how do I do local desktop control"
was this SDK snippet:

```python
from hai_agents import Client
client = Client()
agent = client.agents.create_agent(
    name="local-desktop",
    environments=[{"id": "my-laptop", "kind": "desktop", "host": "user_device"}],
)
```

A second H Company engineer pointed at `holo-desktop-cli` instead. Both are
legitimate paths to the same local-desktop capability (`holo` is almost
certainly what that `user_device` environment talks to under the hood) —
we went with `holo-desktop-cli` because it's the faster path to a working
demo: `holo run "task"` one-liners, `holo doctor` for diagnosing setup, and
a documented Python API (`holo_desktop.agent_client`) instead of hand-rolled
SDK orchestration. If `create_agent` turns out to be a hard requirement
somewhere, that's the fallback.

Also learned: H Company's computer-use agent is a screenshot →
vision-model → click/type/scroll loop with multi-second latency per action
(confirmed via `hub.hcompany.ai/computer-use-agents/introduction` and the
`computer-use-agents-demos` repo before building anything). That's fine for
judgment calls and visible GUI actions, hopeless for beat-accurate DJ
timing — hence the brain/hands split in ARCHITECTURE.md.

## Environment setup on a new machine

### 1. `holo-desktop-cli` (H Company's local desktop agent)

```bash
git clone https://github.com/hcompai/holo-desktop-cli
cd holo-desktop-cli
make setup        # uv sync --all-groups + pre-commit hooks
make install-dev   # uv tool install --editable . --force -> global `holo` command
holo login          # opens browser to portal.hcompany.ai — use the SAME account
                     # that has the hackathon's hk-... API key on platform.hcompany.ai
holo doctor         # checks binary/login/permissions
```

**Platform-specific gotchas found on macOS, unverified on Linux:**

- macOS: the runtime needs Accessibility + Screen Recording granted in
  System Settings → Privacy & Security, and a restart after granting.
  `holo doctor` can't query these automatically, only reminds you.
- macOS `mixxxdb.sqlite` lives at
  `~/Library/Containers/org.mixxx.mixxx/Data/Library/Application Support/Mixxx/mixxxdb.sqlite`
  (Mixxx is sandboxed there, not directly under `~/Library/Application
  Support/`). On Linux it should be the simpler `~/.mixxx/mixxxdb.sqlite` —
  `shared/mixxx_db.py` already has both as candidate paths, but the Linux
  path is unverified, confirm it there.
- The double-Esc kill switch relies on a global key listener; per holo's own
  README, **Wayland has no global key listener** — use `holo stop` bound to
  a compositor hotkey instead.
- Watch for focus-stealing: in this session, other apps popping to the
  front (a stray permission dialog, the user nudging the mouse mid-run)
  repeatedly caused the agent to click the wrong app's menu bar. Worth
  keeping hands off the mouse/keyboard while a `holo run` is active.

### 2. `claw-dj`

```bash
git clone git@github.com:InServiceOfX/claw-dj.git
cd claw-dj
git checkout brain-hands-architecture
uv venv --python 3.13
uv sync   # installs holo-desktop-cli (PyPI) + python-rtmidi + mutagen
```

### 3. Mixxx

Install Mixxx (mixxx.org) for real — needed for both the GUI the Brain
drives and the analyzed-track database Hands reads BPM/key from.

### 4. Music library

The demo crate was built from a real drive: `/Volumes/USB322FD/Music/HipHop`
(a Mac-specific mount path — irrelevant on Linux). None of that data is
committed (see below), so on a new machine:

```bash
uv run python -m brain.scan_library /path/to/your/music
uv run python -m brain.build_demo_subset   # edit the artist/filter criteria
                                             # in brain/build_demo_subset.py
                                             # first if the crate differs
```

## What's built so far

| File | Purpose |
| --- | --- |
| `docs/ARCHITECTURE.md` | Brain/Hands design, MVP cut-list, judging-criteria mapping |
| `brain/agent.py` | `Brain` class — spawns/attaches the holo runtime daemon, drives Mixxx's GUI via `holo_desktop.agent_client` |
| `brain/library.py` | `Track`/`Energy` types, `CRATE` loaded from `brain/data/crate.json` |
| `brain/scan_library.py` | Scans a music directory's ID3 tags (mutagen) into the crate cache |
| `brain/sync_mixxx_analysis.py` | Merges Mixxx's analyzed bpm/key (read from its own DB) into the crate cache |
| `brain/build_demo_subset.py` | Picks a curated subset from the crate, writes `.m3u` for one-shot Mixxx import |
| `hands/beatgrid.py` | Reads bpm from Mixxx's DB for a given track path (schema confirmed against a real install) |
| `hands/midi_engine.py` | MIDI execution stub via `python-rtmidi` — **not tested against real Mixxx MIDI mapping yet** |
| `hands/mixxx_mapping/` | **Empty.** Needs a live Mixxx session to iterate the actual MIDI CC/note mapping — biggest remaining gap |
| `shared/commands.py` | Brain→Hands command schema (intent only, no MIDI/timing) |
| `shared/mixxx_db.py` | Locates + read-only-opens `mixxxdb.sqlite` across platforms |

`brain/data/` (scanned crate, demo subset, `.m3u`) is **gitignored on
purpose** — it's derived from a personal media library with scene-rip-style
folder naming (`.torrent` files, "by Hillside" tags were spotted in the
source directory), not something to commit to a public hackathon repo.
Regenerate it locally with the scripts above.

## Demo subset — analyzed, real BPM/key in hand

Criteria chosen this session: **Snoop Dogg-centric, ~30 tracks, studio
albums only** (excludes mixtapes/soundtracks/promo singles/interludes/skits;
includes both `Snoop Dogg` and `Snoop Doggy Dogg` ID3 artist tags since
early albums are tagged with his original stage name). Generated via
`brain/build_demo_subset.py`, output at `brain/data/demo_set.{json,m3u}`
(gitignored — rerun the script to regenerate).

**Status: done.** Three `holo run` attempts at driving Mixxx failed —
first from losing window focus to other apps mid-task, then from a wrong
UI target (the agent, and an early version of these instructions, assumed
File → Import Playlist; Mixxx's actual path is **right-click "Playlists"
in the sidebar → Import Playlist**, confirmed against the official manual:
https://manual.mixxx.org/2.3/en/chapters/library.html). Given the repeated
failures, Ernest did the import + select-all + right-click → Analyze by
hand instead — a couple of clicks, faster than debugging the agent further.
`brain/sync_mixxx_analysis.py` confirmed all 30/30 demo-subset tracks now
have real bpm/key (e.g. "Gin And Juice" 94.62 BPM / Bbm, "Drop It Like
It's Hot" 92 BPM / Cm).

**Lesson for next time a playlist needs importing:** tell `holo` to
right-click "Playlists" in the sidebar directly, don't send it hunting
through menus.

**One thing to sanity-check before relying on it for beat-juggling:**
"Don Doggy" (149 BPM) and "Trust Me" (~160 BPM) look like they might be
double-time detections (Mixxx's beat detector sometimes locks onto 2x/0.5x
the real tempo on hip-hop/rap) rather than the track's actual BPM — worth
eyeballing against the actual songs before scheduling beat-accurate moves
against them.

## Known gaps / next steps, roughly in priority order

1. **`hands/mixxx_mapping/`** — no real MIDI mapping exists yet. Needs a
   live Mixxx session: create a virtual MIDI port, point Mixxx's Controller
   preferences at it, confirm `hands/midi_engine.py`'s note/CC numbers
   actually move a deck. This is the biggest gap between "agent can open
   Mixxx" and "agent can actually DJ."
2. `Track.energy` is still a placeholder (`MEDIUM` for everything scanned)
   — no LOW/HIGH/PEAK tagging exists. Either hand-curate energy for the
   ~30-track demo set, or decide it's out of scope for the hackathon demo.
3. `brain/agent.py`'s `_next_free_deck()` is hardcoded to `2` — no real
   deck-state tracking.
4. Nothing in `hands/` has been exercised against a live Mixxx MIDI session
   yet — `midi_engine.py` is unverified beyond importing cleanly.
