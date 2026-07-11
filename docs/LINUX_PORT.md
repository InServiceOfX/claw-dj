# Linux port guide

Written 2026-07-11 on the macOS machine where the original path was built and
live-validated, then updated on the Linux desktop. Read `CLAUDE.md` and
`docs/HANDOFF.md` first for project context; this file is only the
macOS→Linux delta. Items still marked **[verify]** worked on macOS but remain
untested on Linux.

## What "working" looks like (the macOS baseline to reproduce)

1. Mixxx open with the `clawdj` controller mapping enabled on a virtual MIDI
   port; `[clawdj] init: clawdj mapping loaded` in Mixxx's log.
2. `cargo run -p clawdj-cli -- setup` sees the port; `cmd '{"op":"play","deck":1}'`
   audibly starts a deck.
3. `clawdj monitor` prints live beat ticks with measured BPM (~92 for
   "Drop It Like It's Hot") while a deck plays.
4. `clawdj transition --from 1 --to 2 --beats 16` does a beat-anchored
   crossfade (measured BPM ≈ analyzed BPM, fade length = beats × 60/BPM).
5. `uv run python -m brain.set_player --tracks 3` plays a short set — the
   hai-agents desktop bridge loads each next track via the GUI, and Rust
   transitions between them.

Steps 2–4 are exactly `docs/MIX_TWO_TRACKS.md`'s runbook (commands only, no
narration) — use it directly once the port + mapping (§1–2 below) are up,
instead of re-deriving the command sequence.

**Also confirmed on macOS:** holo really can load a track through Mixxx's
GUI unattended (right-click a track -> "Load to" -> "Deck" -> "Deck N"),
though it takes real wall-clock time and some flailing (dock-icon
misclicks, stray dialogs stealing focus) before it lands — see
`docs/HANDOFF.md`'s "Live-validated" section for the full account. Don't
read early misclicks in a holo run as failure; only intervene if it's
genuinely stuck bouncing between the same wrong targets repeatedly.

## 1. Virtual MIDI port

macOS used the IAC Driver bus named `clawdj` (created in Audio MIDI Setup).
Linux equivalents, pick one:

- **Preferred [verify]:** ALSA sequencer virtual port. `midir` (Rust) and
  `python-rtmidi` can create one directly, no root:
  `MidiOutput::create_virtual("clawdj")` / `rtmidi` virtual ports. Note we
  *removed* the `create_virtual` path from clawdj-cli (commit `a282541`)
  because on macOS the port pre-existed and Mixxx held it open. On Linux you
  may want it back behind a `--virtual` flag: a long-lived process must own
  the port (it disappears when its creator exits) — a `clawdj serve` daemon
  or `snd-virmidi` avoids that.
- **Alternative:** `sudo modprobe snd-virmidi` → persistent kernel virtual
  ports (`hw:Virtual,0`); survives process exits, needs root once.

Port-name matching in `core-rust/clawdj/src/midi.rs` (`MIDI_TARGET_HINTS`)
matches any port containing `clawdj` case-insensitively — name the Linux
port accordingly and nothing needs changing. **[verify]** ALSA may render
names like `clawdj:clawdj 128:0`; substring match should still hit.

The Rust workspace now builds on Linux and passes `cargo fmt --check`, all
five tests, and `cargo clippy -D warnings`. Linux required converting
`midir::ConnectError` to `anyhow::Error` with `map_err` because that error is
not `Sync` on this backend; MIDI behavior is unchanged. A real virtual-port
session still needs the live validation above.

## 2. Mixxx paths

| Thing | macOS (verified) | Linux **[verify]** |
| --- | --- | --- |
| `mixxxdb.sqlite` | `~/Library/Containers/org.mixxx.mixxx/Data/Library/Application Support/Mixxx/mixxxdb.sqlite` | `~/.mixxx/mixxxdb.sqlite` |
| Controller mappings | `.../Mixxx/controllers/` | `~/.mixxx/controllers/` |
| Mixxx log | `.../Mixxx/mixxx.log` | `~/.mixxx/mixxx.log` |

- `shared/mixxx_db.py` and `core-rust`'s `default_mixxx_db_path()` already
  try the Linux path (and honor `CLAWDJ_MIXXX_DB` env in Rust) — just verify.
- `hands/mixxx_mapping/install-mapping-macos.sh` is macOS-only: on Linux,
  `cp hands/mixxx_mapping/clawdj.{midi.xml,scripts.js} ~/.mixxx/controllers/`
  then Mixxx Preferences → Controllers → the clawdj port → Enabled → Load
  Mapping "clawdj" → Apply. Write the `install-mapping-linux.sh` twin when
  the path is confirmed.
- A Flatpak/Snap Mixxx sandboxes these paths differently — prefer a distro
  package or the official binary. **[verify whichever install you use]**

## 3. Music library + demo set

Nothing is committed (personal library). On the Linux box:

```bash
uv run python -m brain.scan_library /path/to/music
uv run python -m brain.build_demo_subset
# import brain/data/demo_set.m3u in Mixxx: right-click "Playlists" in the
# sidebar → Import Playlist (NOT the File menu). Select all → Analyze.
uv run python -m brain.sync_mixxx_analysis
uv run python -m brain.build_demo_subset   # again, to bake bpm into demo_set.json
```

## 4. H Company agent on Linux

- `holo-desktop-cli` does not currently run here: its managed
  `hai-agent-runtime` artifacts cover macOS Apple Silicon and Windows x86_64,
  not Linux x86_64 (v0.0.2).
- Use `hai-agents[desktop]`, which provides the pure-Python
  `hai_agents_local` bridge used by `brain/agent.py`: `pip install
  "hai-agents[cli,desktop]"`, then `hai login` and `hai whoami`.
- On GNOME/X11, install `gnome-screenshot`; pyautogui's screenshot backend
  needs it. The working bridge uses pyautogui/python-xlib, so X11 is the
  confirmed path. Wayland remains unverified.
- `hai login` and `holo login` use separate products, keys, and files
  (`~/.config/hai/.env` versus `~/.holo/.env`). A key valid for one may 403
  on the other.
- Give the agent specific UI targets ("right-click 'Playlists' in the
  sidebar") rather than broad goals, and keep hands off the mouse/keyboard
  while it runs. Use `--no-agent` for manual loads while debugging.

## 5. NemoClaw (Nvidia challenge) — main reason the Linux box matters

Status from the macOS side: source-installed from `repos/NemoClaw`
(`npm install` → `nemoclaw v0.0.80-20-gdfee1160a` linked on PATH), macOS
Docker-driver path exists but **the GPU story belongs on the Linux desktop**.

The integration that satisfies "run the H Company models through NemoClaw":

1. Serve H Company's open-weight model locally on the NVIDIA GPU:
   `vllm serve Hcompany/Holo3-35B-A3B --host 0.0.0.0 --port 8000`
   (8000 is one of NemoClaw's bundled host-gateway ports; MoE ~3B active
   params. `repos/holo-desktop-cli/docs/self-hosting.md` has ready vLLM
   configs.) **[verify VRAM fit; quantized configs in that doc]**
2. `nemoclaw onboard` → provider "Other OpenAI-compatible endpoint" →
   `http://localhost:8000/v1` + the model ID. The sandboxed agent
   (OpenClaw by default) then runs on H Company's model, routed through
   NemoClaw's gateway — that's the challenge sentence, literally.
3. On a platform with a supported holo runtime, optionally point holo at the same server (`holo run --base-url
   http://localhost:8000/v1 ...`) so the *desktop* agent is also running on
   locally-served Holo3 — nothing leaves the machine.
4. On a platform with a supported holo runtime, optionally `holo install nemoclaw` — holo's README lists NemoClaw as an
   MCP host ("sandbox bridge"), letting the sandboxed agent delegate
   desktop tasks to holo on the host. **[verify — untested]**

Docs live in `repos/NemoClaw/docs/` (see
`inference/set-up-openai-compatible-endpoint.mdx`,
`inference/set-up-vllm.mdx`). The onboard wizard is interactive — run it
with Ernest present, not headless.

## 6. Suggested first hour on the Linux box

1. Clone claw-dj, `uv venv --python 3.13 && uv sync`; install Rust if
   needed, `cargo build` in `core-rust/`.
2. Virtual MIDI port up (§1) → Mixxx mapping installed + enabled (§2) →
   `clawdj setup` sees it.
3. Library scan → demo_set import/analyze/sync (§3).
4. Load a track, `clawdj cmd play`, `clawdj monitor` — beat ticks flowing.
5. `clawdj transition` between two loaded decks — audible beat-matched fade.
6. `uv run python -m brain.set_player --tracks 3 --no-agent`, then with the
   hai-agents desktop bridge once §4 checks out.
7. NemoClaw + vLLM (§5) for the Nvidia-challenge leg.
