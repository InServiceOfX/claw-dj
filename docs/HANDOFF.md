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

**DONE 2026-07-11 (evening, Linux laptop): the end-to-end MIDI loop is
closed.** The validation the prior effort never reached (April and July
both stalled at "ready to test") now passes: a Note On / CC sent from
Python arrives in Mixxx, runs `clawdj.scripts.js`, and changes the live
engine — verified by reading `[Master],crossfader` over the control API
before (0) and after (1) sending `cc 0x00 127`. Notes on how, because the
Linux setup differs from the macOS IAC design:

- **Linux has no IAC driver; some process must own the virtual ALSA port.**
  `mido.open_output("clawdj", virtual=True)` creates it; when that process
  dies the port vanishes and Mixxx loses the device (restart Mixxx after
  recreating it — PortMidi only scans at startup). `hands/midi_port_server.py`
  is that owner: it holds the port and relays commands written to
  `/tmp/clawdj.fifo` (`note 2` = play deck 1, `cc 0 64` = crossfader
  center). `agent/midi_bridge.py`'s `mido.open_output(name)` (no
  `virtual=True`) is the macOS model and can't create the port on Linux —
  send through the port owner instead.
- **No GUI clicking needed to enable the controller.** Mixxx reads two
  config entries from `~/.mixxx/mixxx.cfg` (written while Mixxx is not
  running; it saves config only on clean quit, not SIGTERM):
  `[Controller]\nclawdj 1` and `[ControllerPreset]\nclawdj clawdj.midi.xml`.
  Device name is whatever PortMidi reports (here exactly `clawdj`),
  sanitized spaces→underscores (`controllermanager.cpp`).
- **Run the patched Mixxx** (fork at `repos/mixxxes/mixxx`, built in
  `BuildGcc/`, binary verified) as
  `./mixxx --developer --controller-debug --control-api-port 9995`; log
  should show `[clawdj] init: clawdj mapping loaded`. The control API
  (`hands/mixxx_control.py` client) is the readback/deterministic-action
  channel; MIDI stays the beat-accurate channel.
- Deck `play` won't hold 1 while the deck is empty — load a track first
  (control API `load` op) before using play for validation.
- **Build note for this laptop (16 cores, 15 GiB RAM):** never `make -j16`
  in `BuildGcc` — RelWithDebInfo link jobs OOM-freeze the machine (that
  caused the 2026-07-11 freeze). Use `nice -n19 make -j4`. The `mixxx`
  binary is already built; only `mixxx-test` was never finished (not
  needed).

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
| `brain/scan_library.py` | Scans one or more music directories' ID3 tags (mutagen) into the crate cache |
| `brain/sync_mixxx_analysis.py` | Merges Mixxx's analyzed bpm/key (read from its own DB) into the crate cache |
| `brain/build_demo_subset.py` | Picks a curated subset from the crate, writes `.m3u` for one-shot Mixxx import |
| `brain/build_lineage_set.py` | Builds the sample-lineage playlist from canonical hip-hop/RnB tracks in the crate |
| `brain/analyze_bpm.py` / `brain/analyze_via_mixxx.py` | Provisional librosa BPM analysis and deterministic Mixxx analysis for the lineage set |
| `brain/playlist_editor.py` | Local browser UI for searching the crate, enabling/disabling tracks, applying the researched R&B/West Coast hit seed, and exporting a Mixxx playlist without dropping BPM/key metadata |
| `brain/playlist.py` | Playlist selection persistence, normalized seed matching, and JSON/`.m3u8` export logic |
| `brain/quick_mix.py` | H-agent-optional six-track sample-lineage planner and live Mixxx quick-mix runner |
| `hands/beatgrid.py` | Reads bpm from Mixxx's DB for a given track path (schema confirmed against a real install) |
| `hands/midi_engine.py` | MIDI execution stub via `python-rtmidi`, made-up note/CC map — **superseded by the ported code below, not yet retired** |
| `hands/midi_port_server.py` | Owns Linux's virtual `clawdj` ALSA MIDI port and relays FIFO commands |
| `hands/mixxx_control.py` / `hands/transition.py` | Client and beat-anchored transition engine for the patched Mixxx JSON control API |
| `hands/mixxx_mapping/` | Real mapping (`clawdj.midi.xml`/`.js`) — **live-validated 2026-07-11**: enabled in Mixxx, commands audibly move decks, beat-tick feedback flows back |
| `core-rust/` | Rust workspace (`clawdj` lib + `clawdj-cli`) — commands, queue, **plus the real-time layer** (`live.rs`): `BeatClock` reads Mixxx's live beat ticks, `clawdj monitor` shows live BPM, `clawdj transition --from 1 --to 2 --beats 16` does a measured-BPM, beat-anchored smoothstep crossfade (validated live: measured 91.47 BPM, 10.5s fade = exactly 16 beats) |
| `brain/set_player.py` | Short-set orchestrator with agent, manual, or control-API loading and MIDI or control-API transitions; BPM-chained set planning |
| `agent/midi_bridge.py` | Ported Python MIDI bridge (`mido`-based), matches the real mapping's note/CC map |
| `agent/hermes-skill/SKILL.md` | Ported Hermes agent-skill definition for a dedicated clawdj dev session |
| `shared/commands.py` | Brain→Hands command schema (intent only, no MIDI/timing) — not yet wired to either MIDI implementation |
| `shared/mixxx_db.py` | Locates + read-only-opens `mixxxdb.sqlite` across platforms |

`brain/data/` (scanned crate, demo subset, `.m3u`) is **gitignored on
purpose** — it's derived from a personal media library with scene-rip-style
folder naming (`.torrent` files, "by Hillside" tags were spotted in the
source directory), not something to commit to a public hackathon repo.
Regenerate it locally with the scripts above.

The hackathon-length live path is documented in `docs/QUICK_MIX_DEMO.md`.
It was validated on 2026-07-11 with one on-beat lineage cut and four
beat-synced blends across six tracks; the final deck stopped cleanly.

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

## Patched Mixxx on the Mac (2026-07-12) — control API live, default app

The patched Mixxx (fork branch `localhost-control-api` at
`repos/mixxxes/mixxx`, Mixxx 2.7.0-alpha base) is now built natively for
arm64 and installed as **the default `/Applications/Mixxx.app`**; stock
2.5.3 is kept at `/Applications/Mixxx-stock.app`. Verified end-to-end:
`hands.mixxx_control.MixxxControl` get/set round-trips against the live app
on port 9995. Launch it as:

```bash
open -a /Applications/Mixxx.app --args --control-api-port 9995
```

Build notes (all verified on this MacBook Pro M5, macOS 26):

- `source tools/macos_buildenv.sh setup` with `BUILDENV_RELEASE=1`, then
  cmake with the CI's arm64 args (`-DMACOS_BUNDLE=ON -DQML=ON` etc.,
  triplet `arm64-osx-min1100-release`) and `cmake --build`. Do NOT call
  `tools/macos_release_buildenv.sh` directly — it's CI-only and exits.
  Full build ≈ 25 min on 10 cores; deps zip auto-downloads during configure.
- The build-tree `Mixxx.app` is NOT self-contained; run
  `cmake --install . --prefix stage` to get the bundled, ad-hoc-signed app.
- **macOS gotcha that cost an hour:** Mixxx's bundle is App-Sandboxed, and
  without `com.apple.security.network.server` in the entitlements the
  control API's listen() dies with "Unknown error" (EPERM) — port never
  opens even though `--control-api-port` parses fine. Fixed in fork commit
  `722eac1bce` (entitlement added + re-sign). Also: `--` is illegal inside
  XML comments; codesign rejects the whole entitlements file with a cryptic
  AMFIUnserializeXML error.
- Because the app is sandboxed, it uses the **container** settings/DB
  (`~/Library/Containers/org.mixxx.mixxx/...`) — same data stock used, so
  the analyzed library and clawdj mapping carried over with zero work. The
  2.7 first launch upgraded that DB's schema in place; a pristine
  pre-upgrade copy sits at `~/Library/Application Support/Mixxx` if stock
  2.5.3 ever balks at the upgraded container DB.

Production demo assets (2026-07-12, all `brain/data/`, gitignored): 58-track
curated set (brief: "Hip-hop and RnB hits that mix well together in a DJ
showcase"), all tracks Mixxx-analyzed, phrase analysis done, 57-transition
~39-minute mix plan built, `hands.run_mix_plan --dry-run` passes (176
events). **First live run 2026-07-12: 103/176 events through the HomePod
before Ernest stopped it (sounding great).** Output chain: Mac + Mixxx both
on the Office HomePod via AirPlay ("AirPlay" CoreAudio device; constant
~2s latency, harmless to the beat-anchored mix, waveforms just lead audio).

DJ-craft feedback from that run, now encoded as defaults (Ernest,
2026-07-12):

- **Tempo direction**: keep energy up — equal-or-slightly-faster transitions
  preferred, at most 2 consecutive slow-downs (`mix_graph.greedy_mix_order`,
  `max_consecutive_slowdowns`). Observed live failure mode: beatsync chained
  track 1's 101 BPM through the entire set; `run_mix_plan.settle_rate` now
  glides each landed track back to native tempo (keylock on) so tempo
  direction is audible.
- **Entry points**: don't open every track from its intro — default to a
  high-energy body phrase (chorus/first verse; `phrase_analysis` now emits
  `intro`/`body` candidates, no 90s cue cap), with roughly every 4th slot
  taking the intro for texture (`build_mix_plan.cue_fields`). Latest plan:
  46 body entries / 12 intro entries.
- **Genre continuity**: dramatic genre switches are a statement, used
  sparingly — same-artist/same-genre transitions get a bonus, an *unbacked*
  cross-genre jump pays a toll plus a cooldown in the greedy tour. A jump is
  "earned" (exempt) when sample lineage or chromagram texture backs it
  (`mix_graph.genre_of`/`load_chroma_pairs`; chroma coverage is currently
  just the 12-track lineage set — extend with `clawdj chroma`).
- **Sample lineage is the foundation**: a researched sample/cover edge
  floors the pair score at 0.92, nearly overriding everything — mixing the
  original into the song that samples it (across genres) is the showcase.
  **`mix_lineage.json` was pruned 40 → 10 edges**: the agent-researched file
  had padded real samples with "era pairing"/"continuum" vibes (that fake
  lineage is exactly what made Beautiful→Bernard Wright look backed — Ernest
  heard it as jarring, and the data was the bug). Same-artist/genre bonuses
  now cover what the soft edges faked. Three originals found on the drive
  and added to the set: Marvin Gaye "T Plays It Cool" (→ Erick Sermon
  "Music"), Isaac Hayes "A Few More Kisses To Go" (→ Ain't No Fun), James
  Brown "Papa Don't Take No Mess" (→ That's the Way Love Goes) — all three
  place adjacent at the 0.92 floor. Remaining lineage edges cite originals
  not on the drive (verify "Beautiful ↔ Mr. Lonely" with a real
  whosampled-style lookup sometime; it smells like more agent hallucination).
- **Segment variety**: rides are no longer uniform — slot rotation gives
  1/2/3-phrase segments (opener gets 2; a confident phrase pick earns an
  extra), so key parts play out while staying showcase-length.
- `brain.analyze_via_mixxx` fix: eject + wait for bpm to drop before each
  load — the deck's stale bpm otherwise satisfies the wait instantly and
  every track after the first silently skips analysis. Mixxx flushes
  analysis to the DB lazily (sometimes ~a minute after eject) — re-run
  `sync_mixxx_analysis` if bpm comes back None right after analyzing.

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

## Linux drive scan + transfer-safe scanning (2026-07-12, `feat/complete-scan-dedupe`)

`brain.scan_library` is now safe to run against a drive with active
downloads/copies: it skips sibling partial-download markers
(`.part`/`.crdownload`/`.!qB`/`.aria2`), zero-byte placeholders, and files
modified within `--min-age-seconds` (default 300), writing the skipped list
to `brain/data/scan_skipped.json` for a later rescan. Records gain
`duration_seconds` + `size_bytes`; `brain.catalog` reports duplicate groups
(normalized artist+title, then split by duration ±4 s so every album's
"Intro" doesn't collapse into one pile). `brain.analyze_via_mixxx` takes
`--tracks <playlist.json>` so the muted-deck BPM/key analysis runs on any
subset, not just the lineage set.

Tag reads are threaded (`--workers`, default 8) — measured serial rate on
the contended USB drive (`/media/ernest/E8D6-7CB8`, exFAT, downloads
running) was ~1 file/s ≈ 3 h for the crate; threaded took 14.5 min.
Result on the Linux box: **9,105 HipHop tracks, 540 artists, 627
duration-confirmed duplicate groups, 2 files skipped mid-download**
(`brain/data/{crate,catalog}.json`, gitignored as always).

Mac rescan 2026-07-12 (`/Volumes/USB322FD/Music/{HipHop,RnB}`, 16 workers,
~600 files/s, 33.6 s): **19,624 tracks (5,859 HipHop + 13,765 RnB), 815
artist tags, 2,275 duplicate groups, 0 skipped** — no transfers were
running, so this scan is complete. The 77 previously Mixxx-analyzed tracks
carried their bpm/key forward; 57/58 hit-seed rows now match the crate.

## Playlist curator branch (2026-07-11)

Work on `feat/playlist-curator-ui` adds a localhost playlist picker and a
researched 50-track starting seed covering Ernest's requested West Coast cuts,
each top-level R&B-folder artist, and eight Sade tracks. On the Mac USB library,
all 50 seed entries matched real audio files. The generated selection and
exports remain gitignored in `brain/data/`.

`brain.scan_library` now accepts multiple roots and carries forward existing
`bpm`, `key`, and `energy` values by absolute path. A real rescan of HipHop +
R&B produced 14,518 tracks and retained all 30 previously analyzed Snoop
tracks. After importing and analyzing the curated playlist, Mixxx had 77 crate
matches; all 49 tracks in the current enabled set have both BPM and key. The
current set intentionally differs from the 50-track seed: two seed tracks were
disabled and The-Dream's "Falsetto" was added.

## Available catalog + agent curation (2026-07-11 evening)

Playlist selection is constrained to **songs physically available** under the
user-chosen roots (e.g. `/Volumes/USB322FD/Music/RnB` + `.../HipHop`).

| Module | Role |
| --- | --- |
| `brain/scan_library.py` | Multi-root **metadata-only** scan (mutagen tags: title/artist/album/genre). ~few ms/file; no BPM analysis. Optional `--catalog`. |
| `brain/catalog.py` | Slim agent index (`catalog.json`) + path-stripped `agent_view` for NemoClaw upload. |
| `brain/playlist_seeds/*.json` | Wikipedia/chart **hit seeds** per folder artist + sample-lineage edges. |
| `brain/mix_graph.py` | Transition scores: BPM (rate-adjust tolerant), Camelot key, sample lineage, title tokens. **No full-library waveform** (too heavy; use Mixxx beatgrids). |
| `brain/curate_playlist.py` | Pipeline: keep user selection → match researched hits to crate → mix-order → optional H-agent **reorder only** (never invents deep cuts). Subjective asks (genre/region/era/mood) are **per-playlist input** via `--brief` and `--seed`, not rules — the default brief is neutral (Ernest, 2026-07-12: the earlier West Coast slant was a one-time ask, don't hardcode it). |
| `brain/playlist_edit.py` | Structured selection edits (`--remove-artist`/`--remove-title`) — the tool surface a NemoClaw/H-agent chat front end calls for asks like "drop the Alicia Keys songs"; re-order afterward with `--mode selection`. **Known gap:** removals aren't sticky — a later `--mode hits` run re-adds seed matches; a persisted exclusion list is the fix. |
| playlist UI | "Add researched hits" + "Order for mixes" (reorder enabled set; never drops picks). |

**Hackathon demo line:** "Yes — H agents curate researched hits from *your*
library; we enrich with sample lineage + lyrics + chromagram; Hands perform a
continuous set playing Mixxx like an instrument."

**Waveform policy:** no full-crate waveform decode. Optional Rust chromagram
on ≤12–16 ordered hits (`clawdj chroma` / `enrich_playlist --chroma`). Mixxx
owns beatgrids for beatmatch.

**Continuous mix path:** `enrich_playlist` → `build_mix_plan` →
`hands.run_mix_plan` (control API). Knobs/docs: `docs/MIX_INSTRUMENT.md`.

### Incremental new-music ingestion (2026-07-12)

`brain/data/library.sqlite3` is now the local source of scan state. It stores
configured roots plus each file's path, size, nanosecond mtime, embedded tags,
availability, first/last-seen times, and analysis fields. `brain.scan_library`
still writes `crate.json` and optional `catalog.json`, so existing curation is
unchanged, but repeat scans only open new or changed files with Mutagen.
Removed files are marked unavailable rather than erasing their history.

Run the CLI once with the desired roots. After that, the playlist editor's
**Check for new music** button reuses those roots, scans in a background thread,
and reports new/changed/unchanged/missing-tag counts. Expensive BPM/key, phrase,
lyrics, and chromagram work remains downstream and scoped to selected tracks.

**Migration caveat (fixed post-hoc 2026-07-12):** the first migration
stamped every row with the same `first_seen_at`, so "which tracks are new"
survived only as a count. Reconstructed exactly via file birthtimes (a
4.5-hour copy gap sat precisely at the 2,695 boundary) and backfilled into
the index; future scans persist real first-seen times naturally.
`sync_mixxx_analysis` now writes bpm/key into the index too and exports
full-fidelity records from it (review fix — crate rewrites used to drop
album/duration and revert re-analyzed bpm on the next scan).

**New-music batch 2026-07-12 (2,695 tracks: 1,817 RnB / 878 HipHop):**
dominated by Charles Aznavour (~1,416 — chanson, in the RnB folder), 50
Cent (332), Fat Joe (177), Aaliyah (170), Keith Murray (193), G-Unit,
Terror Squad; 46 tracks untagged. Agent-facing candidates file:
`brain/data/new_music_agent.json` (path-stripped, short `n####` ids,
metadata only) + `new_music_ids.json` (id → path resolution, stays local).
This is the input for the NemoClaw / H-agent "pick playlist candidates
from the new music" conversation; resolve returned ids locally, never let
the agent touch paths.

**Both agent engines wired and validated live (2026-07-12) —
`brain/pick_candidates.py`:**

- `--engine nemoclaw`: hermes sandbox (NVIDIA Nemotron 3 Super 120B) via
  its OpenAI-compatible API. Plumbing: Docker Desktop must be running
  (gateway silently fails without it — `nemoclaw hermes doctor --fix`
  repairs once Docker is up), then
  `openshell forward start --background 8642 hermes`; auth is
  `nemoclaw hermes gateway-token --quiet` as a Bearer token, model id
  `hermes-agent`. Note `nemoclaw hermes agent` does NOT work for this
  sandbox (hermes runtime exposes the API instead).
- `--engine h-agent`: H Company Agent Platform via `hai_agents`
  planning-only task (Brain, max_steps=4). Auths fine on this Mac via the
  `~/.holo/.env` key fallback.

Real run, same 2,695-track view + brief: Nemotron returned 20 picks with
some junk (a French charity single, G-Unit filler); Holo returned 14
tighter picks and honored "fewer is fine". Picks land in
`brain/data/new_music_picks*.json`; `--add-to-selection` merges them into
the selection for the normal curate → analyze → plan flow.

**"Ask the DJ brain" is in the playlist editor UI (2026-07-12).** Panel
under New music: brief + engine (NemoClaw/H Company) + count → background
agent call (`run_pick`) → picks rendered as checkboxes (pre-checked,
already-in-set and not-in-crate flagged) → "Add checked to set". Endpoints:
GET `/api/brain`, POST `/api/brain/ask`, POST `/api/brain/apply`. Validated
end-to-end with a real NemoClaw call through the HTTP API. Note hermes
agent turns take 1–7 minutes (it's an agent loop, not a raw model); the UI
polls and survives page reloads mid-call. NemoClaw prereqs: Docker Desktop
up + `openshell forward start --background 8642 hermes` once per boot.

UI workflow semantics (Ernest, 2026-07-12): Library = every track on the
drive; Enabled set = the working playlist (user edits are authoritative);
**unchecking = durable exclusion** (`playlist_exclusions.json`) that seed
merges, agent picks, hits-mode curation, and suggestions all respect until
re-enabled; **Finalize for Mixxx** = the lock-in step before analysis.
"Ask the DJ brain" supports Both engines with per-engine cached results
(`brain_picks_{engine}.json`); "Suggest blends" deterministically scores
analyzed/unselected/non-excluded tracks against the current set. Scans
that find new music rebuild `new_music_agent.json` automatically. Next
stage to build: post-finalize "Create the mix" button — flavor presets
(e.g. DJ showcase) + free-text mix description feeding build_mix_plan.

### Mix profiles (2026-07-12, `brain/mix_profiles.py`)

Architecture decision (Ernest asked "should run_mix_plan be very
configurable?"): **configure the plan BUILDER, keep the plan format and
runner deliberately boring.** The plan stays a declarative event list;
every feel knob lives in a `MixProfile` (ride-phrase pattern, transition
scale, flourish density, intro-entry rate) behind named presets:
`dj-showcase` (default; today's tuned values), `club-set`, `warm-up`.
`build_mix_plan --profile <name> --mix-brief "<free text>"` — the brief
maps deterministically onto overrides (keyword pass; agent-backed mapper
is a drop-in later), every adjustment is named in the plan's `profile`
provenance block. Gotcha fixed: negation keywords ("no tricks") must be
checked exclusively before positives ("tricks"). Only knobs validated by
real runs get added — grow one at a time. The "Create the mix" UI button
should be preset buttons + a text box calling exactly this CLI.

### Post-finalize enrichment (2026-07-12, `brain/enrich_set.py`)

Runs over the finalized playlist only, check-before-fetch at every step,
persists into `library.sqlite3` (`lyrics`/`chroma`/`phrases` tables +
bpm/key on `tracks`): muted-deck Mixxx bpm/key for whatever's missing;
full lyrics from LRCLIB (free API, disk-cached); Rust `clawdj chroma`
12-dim fingerprints per track, with `chroma_similarity.json` rewritten as
the full-set pairwise cosine matrix (so ordering/plan techniques get real
texture coverage, not the stale 12-track set); phrase/cue analysis into
the DB + `phrase_analysis.json` export for the planner. First run on the
48-track set: 48/48 enriched, 44 with lyrics (one miss is an instrumental).

**Mixxx analysis-persistence gotcha, worse than the flush lag:** some
tracks' engine analysis (bpm readable over the API) takes many MINUTES to
land in `mixxxdb.sqlite` — clean quit does NOT force it, and a 45s settle
before eject doesn't either; it seems to persist when a LATER track gets
analyzed. If a track stays `bpm=0.0/beats NULL`, keep working and re-check
a few minutes later, or right-click → Analyze in the GUI (always
persists). Cost ~30 min on "In Da Club" before the row appeared on its own.

**NemoClaw:** sandbox `hermes` Ready on this Mac (NVIDIA Nemotron inference).
Separate from host Hermes (`~/.hermes`). Holo3-via-vLLM still `LINUX_PORT.md` §5.

## Phrase-aware full demo mix (2026-07-11)

Branch `feat/phrase-aware-demo-mix` closes the gap between a compatible order
and a performed set. `brain/phrase_analysis.py` decodes Mixxx's
`BeatGrid-2.0` protobuf (BPM plus exact first-beat frame), uses local `ffmpeg`
to rank 16-beat-aligned energy changes in only the selected demo tracks, and
writes cue timestamps to gitignored `brain/data/phrase_analysis.json`.

`brain.build_mix_plan` version 2 consumes those cues and expresses excerpts in
beats. `hands.run_mix_plan` preloads alternating decks, counts live
`beat_active` edges, anchors cuts and blends on beats, respects unsynced cuts,
and performs continuous crossfader/EQ/filter curves. Showcase gestures rotate
instead of firing on every compatible pair: bass swap, scratch preview, loop
roll, and transformer cut.

The generated six-track Mac plan is roughly two minutes: Beautiful -> Fallin'
-> Off the Books -> Round & Round -> Regulate -> Love's Theme. All six cue
points came from Mixxx grids plus local energy scoring. Live autonomous
execution requires the patched Mixxx control API; port 9995 was not listening
on the Mac during this implementation, so the plan was dry-run verified there.
