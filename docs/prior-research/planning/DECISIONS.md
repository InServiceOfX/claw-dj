# Decisions log (ADR-lite)

Each entry: short title, date, context, decision, consequences.

---

### 2026-04-25 · Use Mixxx, not a custom JS DJ engine

**Context.** User asked for an mlxxx-powered DJ. Web research turned up no
"mlxxx" CLI/JS DJ tool; the only fit is **Mixxx** — open-source, scriptable,
cross-platform, AAC/MP3-capable. Confidence ~95%; flagged for confirmation.

**Decision.** Build atop Mixxx 2.5 stable.

**Consequences.** GPL-3 license posture for our code. We inherit Mixxx's audio
engine, time-stretching, beatgrids, hardware-controller plumbing for free.

---

### 2026-04-25 · Drive Mixxx via virtual MIDI, not patches/forks

**Context.** Mixxx's only sanctioned external write API is its MIDI/HID
controller mapping system (XML + JS in QJSEngine). The OSC client is
unmerged + output-only. There is no IPC API.

**Decision.** Create a virtual MIDI port (CoreMIDI/`midir` on macOS,
ALSA/`midir` on Linux) plus a custom Mixxx mapping (`mixxx-mapping/`) that
interprets our messages.

**Consequences.** Works on stock Mixxx. Hard real-time recipes live inside
Mixxx's JS sandbox, not in our Rust code — IPC happens at the *intent* level.

---

### 2026-04-25 · Rust core, Python sidecar for analysis

**Context.** Ernest prefers Rust. Music analysis libraries (essentia, madmom,
librosa, whisper) are richest in Python.

**Decision.** Rust = library DB, planner, MIDI bridge, scheduler, CLI.
Python = offline analyzer subprocess only. JSON over stdio is the contract.

**Consequences.** Two language toolchains. Rust ships fast; Python is
gated to offline batch work so its slowness never hits the live loop. Future
port of analysis to Rust (`aubio-rs` etc.) is non-breaking — same JSON
contract.

---

### 2026-04-25 · Repo: Monoclaw private branch first, public split later

**Context.** User wants build-in-public, but past mistakes hardcoded private
info. Music libraries are also personal.

**Decision.** Develop on `feat/clawdj-mixxx-harness` in private Monoclaw.
Plan a clean public split (`InServiceOfX/clawdj`) once a `lint-no-private-paths`
hook is enforced and config (paths, library locations) is fully externalized.

**Consequences.** Slower public release, much less risk of accidentally
publishing music-library or account state.

---

### 2026-04-25 · State feedback over a second virtual MIDI port

**Context.** We need to know "which deck is playing, what's the position,
what's the BPM" without polling Mixxx via a custom build (OSC fork is
unmaintained mainline).

**Decision.** A second virtual MIDI port (`clawdj-feedback`) into which our
mapping JS emits status messages. Rust core listens.

**Consequences.** No custom Mixxx build needed; ~10 ms feedback granularity
which is fine for our scheduler (we only need beat-precise).

---

### 2026-04-25 · v1 = classic 2-deck, no stems

**Context.** Mixxx 2.5+ supports stems. More creative options, but adds a build dimension and analysis step.

**Decision.** Classic 2-deck for M0–M3. Revisit stems in M5+.

**Consequences.** Faster path to a live demo. Mapping XML/JS only needs Channel1+Channel2.

---

### 2026-04-25 · v1 = 100% software, no hardware MIDI controller

**Context.** Ernest does not currently have a hardware MIDI controller; we want to minimize moving parts.

**Decision.** Drive Mixxx exclusively through `IAC Driver clawdj` virtual MIDI port from clawdj-core. Hardware controller can be layered in later as a separate Mixxx mapping.

**Consequences.** Setup is purely software — anyone with macOS + Mixxx can replicate. Removes a class of debugging issues (no hardware quirks).

---

### 2026-04-25 · macOS App Store Mixxx is the target

**Context.** Ernest's running install lives at `~/Library/Containers/org.mixxx.mixxx/...` — the App Store sandboxed build, not a `brew --cask install mixxx` Homebrew copy.

**Decision.** Target the sandboxed App Store build. Our mapping path:
`~/Library/Containers/org.mixxx.mixxx/Data/Library/Application Support/Mixxx/controllers/clawdj.midi.xml` (+ `.js`).
Our Rust core never touches Mixxx's process or files at runtime; communication is exclusively over MIDI.

**Consequences.** Easiest install path for end users. Mixxx already has Document-Access tokens for `~/Music`, so it can read the audio files even though sandboxed. Our `clawdj setup` command just verifies port + mapping presence — no entitlement gymnastics needed.

---

### 2026-04-25 · Reuse Mixxx's existing library DB as a bootstrap source

**Context.** Mixxx already maintains `mixxxdb.sqlite` with tags, `track_locations.location` (full file path), durations, and a slot for BPM/key. Ernest's instance has 1,033 tracks indexed (313 West Coast Rap, 175 Rap, 94 R&B — hip-hop heavy as advertised). Only 8/1,033 tracks have BPM/key, so analysis is still required.

**Decision.** `clawdj scan` reads Mixxx's `mixxxdb.sqlite` first (tracks + paths + tags) and only crawls the filesystem for *new* paths. Our deeper analyzer fills BPM/key/sections/lyrics in our *own* DB; we never write to Mixxx's DB except for one specific use:

---

### 2026-04-25 · Track-loading mechanism: "clawdj queue" Mixxx playlist

**Context.** Mixxx's controller-script JS API has *no* `loadTrackByPath` function. Confirmed via Mixxx wiki + community threads. Available routes are:
  - `LoadSelectedTrackFromGroup` — loads whatever is highlighted in the library UI (requires GUI navigation).
  - Auto-DJ queue manipulation.
  - GUI drag-and-drop (not scriptable).

**Decision.** clawdj-core maintains a Mixxx playlist named `__clawdj_queue` by directly inserting/deleting rows in `Playlists` and `PlaylistTracks` tables of `mixxxdb.sqlite`. To load a track into a deck:
  1. Rust core inserts the target `track_id` into `__clawdj_queue` at a known index (e.g. row 0).
  2. Sends a MIDI message to our mapping JS.
  3. Mapping JS issues the official `LoadSelectedTrackFromGroup` against `[Channel<n>]` after pointing the library focus at our playlist row 0 via `[Library]` controls.

**Consequences.** Stable across Mixxx versions because we use the *sanctioned* load API. Direct-DB writes are scoped to one playlist we own; we never modify Mixxx's actual `library` table. We must obtain Mixxx's lock on the DB safely — short writes only, with retry.

---

### 2026-07-03 · Revalidated Mixxx programmability

**Context.** Ernest asked whether the installed Mac mini Mixxx can be
programmatically controlled, and whether we should reinstall, patch, or fork
Mixxx. Current installed app is Mixxx 2.5.6 arm64 in `/Applications/Mixxx.app`,
which matches the current stable version recommended by upstream on 2026-07-03.
Local Mixxx source is clean on `main` at `4ae413dbe8`, a 2.7-alpha development
snapshot.

**Decision.** Do not reinstall Mixxx and do not fork yet. Continue with stock
Mixxx 2.5.6 plus virtual MIDI for all transport/mixer/recipe control. Treat
deterministic track loading as the only likely reason to patch Mixxx.

**Consequences.** Existing `clawdj` mapping remains the right short-term path.
If the `__clawdj_queue` + `LoadSelectedTrack` approach is unreliable in manual
validation, fork Mixxx and add the smallest legacy controller-script API:
`engine.loadTrackFromLocation(group, path, play)`, implemented by routing to
`PlayerManager::slotLoadLocationToPlayer`. Avoid building a broad HTTP/REST
server until there is a real need for external non-MIDI clients.

---

### TBD — `[Open]` Whisper local vs LRCLIB for lyrics

Pending. Recommend: LRC file → LRCLIB API → whisper.cpp local, in that order.

---

### Template for new entries

```
### YYYY-MM-DD · short title

**Context.**

**Decision.**

**Consequences.**
```
