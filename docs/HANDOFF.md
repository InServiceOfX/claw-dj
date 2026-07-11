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

- **`claw-dj`** (this repo) — `git@github.com:InServiceOfX/claw-dj.git`.
  Work happens on feature branches (`master` gets fast-forward-merged by
  Ernest after review — check `git log --oneline` for the current tip, not
  a specific branch name; branch names here will go stale as work continues).
- **`holo-desktop-cli`** — `https://github.com/hcompai/holo-desktop-cli`,
  cloned locally at `repos/holo-desktop-cli` on the Mac this was built on
  (and later on Linux, where its managed runtime turned out not to work).
  H Company's open-source client drives the closed-source
  `hai-agent-runtime` binary over loopback. `claw-dj` no longer uses it on
  Linux; `brain/agent.py` imports `hai_agents`/`hai_agents_local` directly.
- **`Monoclaw`** — private repo, `InServiceOfX/Monoclaw`. Contains an
  **earlier, more advanced attempt at this exact project** under
  `Projects/clawdj/` (2026-04-25 through 2026-07-08, branches
  `feat/clawdj-mixxx-harness` / `feat/clawdj-core-rust-skeleton`, later
  merged to `master`). Ported wholesale into this repo on 2026-07-11 — see
  the next section. Monoclaw's copy is intentionally left to go stale;
  don't look there for the current state, look here.

## holo-desktop-cli vs the `hai_agents.Client()` SDK — ended up needing both

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
legitimate paths to local-desktop control, so the first macOS build used
`holo-desktop-cli`: `holo run "task"` one-liners, `holo doctor` for setup,
and a documented Python API (`holo_desktop.agent_client`).

On Linux, the SDK path became mandatory. `holo-desktop-cli`'s managed
runtime binary is not published for Linux, while `hai-agents[desktop]`
provides a pure-Python local bridge. `brain/agent.py` now follows the SDK
pattern directly; this is the only path confirmed working on this machine.
Keep holo in mind as a possible macOS/Windows path.

Also learned: H Company's computer-use agent is a screenshot →
vision-model → click/type/scroll loop with multi-second latency per action
(confirmed via `hub.hcompany.ai/computer-use-agents/introduction` and the
`computer-use-agents-demos` repo before building anything). That's fine for
judgment calls and visible GUI actions, hopeless for beat-accurate DJ
timing — hence the brain/hands split in ARCHITECTURE.md.

## Ported prior work from Monoclaw (2026-07-11)

While starting on `hands/mixxx_mapping/` (see "known gaps" below, as it
stood before this port), a stray `clawdj.midi.xml`/`.js` was found already
installed in Mixxx's controllers directory, dated April — from an earlier,
separate effort in a different repo (`Monoclaw`, private,
`Projects/clawdj/`) that got substantially further than today's session had
independently: a working Rust core (`cargo fmt`/`test`/`clippy` clean), a
proven Mixxx-integration design, a Python MIDI bridge, and real research
confirming stock Mixxx has no TCP/HTTP/WebSocket API (only the MIDI/JS
controller-mapping surface). Decision: **port it all into `claw-dj` rather
than rebuild it, let Monoclaw's copy go stale.**

What moved, and where:

| From Monoclaw (`Projects/clawdj/`) | To `claw-dj` |
| --- | --- |
| `core-rust/` (Rust workspace: `clawdj` lib + `clawdj-cli` binary) | `core-rust/` — builds, tests (5/5) and runs clean on this machine, verified 2026-07-11 |
| `agent/midi_bridge.py`, `agent/hermes-skill/SKILL.md` | `agent/` — Python MIDI bridge using `mido`, and a Hermes agent-skill definition |
| `mixxx-mapping/clawdj.midi.xml`, `.js` | `hands/mixxx_mapping/` — the actual mapping (replaces the empty placeholder), reinstalled over the stale April copy |
| `scripts/install-mapping-macos.sh` | `hands/mixxx_mapping/install-mapping-macos.sh` — path fixed for its new location |
| `docs/*.md`, `planning/*.md`, `research/*.md` | `docs/prior-research/` — see its own README for what's there and what was deliberately left out (personal-narrative files, one example path scrubbed) |

**This surfaced a real compliance question for the hackathon rule "build
entirely during the event, no prior commits to the repo"** — this code
predates the event (some of it by months). Ernest made the call explicitly:
port it in anyway, Monoclaw can go stale. Worth being able to explain this
choice if asked during judging.

**Two "hands" implementations now coexist and are not yet reconciled:**
this repo's own `hands/midi_engine.py` (written today, uses a made-up
note/CC map) and the ported, more complete `agent/midi_bridge.py` +
`core-rust/` (real note/CC map matching the actual installed mapping,
already has volume/rate/EQ control `hands/midi_engine.py` doesn't). Next
session should pick one — most likely retire `hands/midi_engine.py` in
favor of the ported code — rather than maintaining both. Not done yet
because it wasn't clear which direction was wanted until this port
happened.

**Still not done, inherited from the prior effort:** actually enabling the
mapping in Mixxx (Preferences → Controllers → "IAC Driver clawdj" → Enabled
→ Load Mapping → Apply) and a live end-to-end validation — send one real
MIDI message, confirm Mixxx reacts. The prior effort got all the way to
"ready to test" twice (April and July) and never closed this loop.

## Environment setup on a new machine

### 1a. macOS / Windows: `holo-desktop-cli`

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

### 1b. Linux: `hai-agents[desktop]`

`holo-desktop-cli` itself installs on Linux, but its closed-source
`hai-agent-runtime` binary has no published Linux x86_64 build as of v0.0.2.
The supported alternative from H Company's local-control docs is the
pure-Python desktop bridge used by `brain/agent.py`:

```bash
pip install "hai-agents[cli,desktop]"  # [cli] supplies the hai command
hai login                              # writes ~/.config/hai/.env
hai whoami
sudo apt install gnome-screenshot      # required by pyautogui on GNOME/X11
```

`holo login` and `hai login` are easy to conflate: they authenticate
different H Company products and write different keys (`~/.holo/.env` and
`~/.config/hai/.env`). A key valid for one may return 403 for the other. If
Agent Platform calls return an explicit-deny 403, try a freshly generated
key from `platform.hcompany.ai`; when escalating, include the request ID,
timestamp, and endpoint.

Creating an agent is not idempotent: a duplicate name returns 409.
`brain/agent.py` handles this by fetching the existing agent. A session can
also stall before dispatching any local command, so the Brain defaults to a
180-second timeout rather than hanging forever.

Confirmed environment: Ubuntu/GNOME on X11. Without `gnome-screenshot`,
observations silently fail and the agent runs blind. The model may also try
`hotkey("super")`, which pyautogui does not recognize; prompts that use
direct clicks instead are more reliable. Wayland remains unverified.

### 2. `claw-dj`

```bash
git clone git@github.com:InServiceOfX/claw-dj.git
cd claw-dj
uv venv --python 3.13
uv sync   # installs hai-agents[desktop], mido, python-rtmidi, and mutagen
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
| `brain/agent.py` | `Brain` class — registers/reuses a `hai-agents` desktop agent and drives Mixxx through `hai_agents_local` (confirmed on Linux/X11) |
| `brain/library.py` | `Track`/`Energy` types, `CRATE` loaded from `brain/data/crate.json` |
| `brain/scan_library.py` | Scans a music directory's ID3 tags (mutagen) into the crate cache |
| `brain/sync_mixxx_analysis.py` | Merges Mixxx's analyzed bpm/key (read from its own DB) into the crate cache |
| `brain/build_demo_subset.py` | Picks a curated subset from the crate, writes `.m3u` for one-shot Mixxx import |
| `hands/beatgrid.py` | Reads bpm from Mixxx's DB for a given track path (schema confirmed against a real install) |
| `hands/midi_engine.py` | MIDI execution stub via `python-rtmidi`, made-up note/CC map — **superseded by the ported code below, not yet retired** |
| `hands/mixxx_mapping/` | Real mapping (`clawdj.midi.xml`/`.js`) — **live-validated 2026-07-11**: enabled in Mixxx, commands audibly move decks, beat-tick feedback flows back |
| `core-rust/` | Rust workspace (`clawdj` lib + `clawdj-cli`) — commands, queue, **plus the real-time layer** (`live.rs`): `BeatClock` reads Mixxx's live beat ticks, `clawdj monitor` shows live BPM, `clawdj transition --from 1 --to 2 --beats 16` does a measured-BPM, beat-anchored smoothstep crossfade (validated live: measured 91.47 BPM, 10.5s fade = exactly 16 beats) |
| `brain/set_player.py` | Short-set orchestrator: the H Company agent visibly loads each next track via the GUI while `clawdj transition` mixes beat-accurately; BPM-chained set planning; `--no-agent` for manual-load dry runs (`--no-holo` remains an alias) |
| `agent/midi_bridge.py` | Ported Python MIDI bridge (`mido`-based), matches the real mapping's note/CC map |
| `agent/hermes-skill/SKILL.md` | Ported Hermes agent-skill definition for a dedicated clawdj dev session |
| `shared/commands.py` | Brain→Hands command schema (intent only, no MIDI/timing) — not yet wired to either MIDI implementation |
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

## Live-validated 2026-07-11 (the loop is closed)

The gap that stalled the April and July prior efforts is done: mapping
enabled in Mixxx (`[clawdj] init` in its log), `clawdj cmd play` audibly
started a deck, `clawdj demo-juggle` beat-juggled two copies of "Drop It
Like It's Hot", and the new real-time layer measured live BPM off Mixxx's
beat-tick feedback and executed a beat-anchored 16-beat crossfade
(measured 91.47 BPM → 10.5s fade, exactly right). Two operational gotchas
worth knowing:

- A deck parked at end-of-track accepts `play` but emits no beats — send
  `cue` first (set_player does this).
- The demo-* subcommands originally created a *new* virtual MIDI port and
  demanded a Mixxx restart; fixed to attach to the live port instead
  (commit `a282541`). Don't reintroduce `create_virtual` on macOS.
- One real-world false alarm: "deck 2 is silent" turned out to be **Mixxx
  audio routing**, not the bridge or mapping. `Preferences -> Sound
  Hardware` fixed it. On a new machine, verify master/headphone outputs and
  deck routing early before debugging MIDI, crossfader logic, or deck-2
  commands.
- See `docs/MIX_TWO_TRACKS.md` for the shortest attended runbook (commands
  only, no explanation) when you just need a live transition working fast.

**holo can load a track through Mixxx's real GUI — confirmed working,
unattended.** Backgrounded task: told holo to open the `demo_set` playlist,
pick a track, and load it into deck 2. It took ~15 steps and repeatedly
misclicked the dock (opened Terminal/other apps instead of Mixxx — the dock
icon is unreliable, always click the Mixxx window itself instead) and had
to cancel a stray Controller Setup dialog that grabbed focus, but it
self-corrected every time and finished correctly: right-click a track ->
"Load to" -> "Deck" -> "Deck 2" (three nested submenus), loaded "Press
Play" by Snoop Dogg (85 BPM, key C) into deck 2, and accurately reported
what it did. `brain/set_player.py`'s `LOAD_TASK` prompt now states this
exact menu path explicitly rather than leaving holo to discover it, which
should cut the step count. Net takeaway: holo's GUI actions work, just
budget real wall-clock time and expect some flailing before it lands —
don't read early misclicks as failure, let it keep going unless it's
genuinely stuck (bouncing between the same 2-3 wrong targets 5+ times).

## NemoClaw (Nvidia challenge) status

Source-installed on the Mac from `repos/NemoClaw` (`npm install` →
`nemoclaw v0.0.80` linked on PATH). Integration path researched and
documented in `docs/LINUX_PORT.md` §5: serve H Company's open-weight
Holo3 via vLLM on the NVIDIA box, `nemoclaw onboard` with the
"Other OpenAI-compatible endpoint" provider → the sandboxed agent runs on
H Company models through NemoClaw's routed inference. Onboarding is an
interactive wizard — run with Ernest present. `holo install nemoclaw`
(sandbox bridge MCP) is the optional extra leg, untested.

## Known gaps / next steps, roughly in priority order

1. **Run the full set-player demo end to end**
   (`uv run python -m brain.set_player --tracks 3 --seconds 45`) with the
   hai-agents desktop bridge doing the loads — each piece is validated but
   the whole loop has not run attended yet. GUI reliability is the weak
   link (dock misclicks, focus loss); `--no-agent` is the fallback.
2. **Linux port + NemoClaw/vLLM** — follow `docs/LINUX_PORT.md`.
3. **Retire the superseded Python MIDI stubs** — `hands/midi_engine.py`
   (made-up note/CC map) and possibly `agent/midi_bridge.py` are both
   superseded by `core-rust/`; `shared/commands.py` isn't wired to anything.
4. `Track.energy` is still a placeholder (`MEDIUM` for everything scanned);
   `brain/agent.py`'s `_next_free_deck()` is hardcoded — set_player tracks
   deck alternation itself instead.
5. Double-time BPM suspects ("Don Doggy" 149, "Trust Me" ~160) — set_player
   sidesteps them by BPM-chaining, but verify before juggling on them.
