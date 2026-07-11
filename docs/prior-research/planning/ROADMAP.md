# Roadmap

Milestones are sized so each ends with a *demo Ernest can hear*. Sub-agent tasks
inside each milestone live in [`TASKS.md`](TASKS.md).

## M0 — Plumbing (week 1)

**Demo:** "Type `clawdj load 1 ~/Music/foo.mp3` and Mixxx loads the track."

- [ ] Decide repo (✅ Monoclaw private, branch `feat/clawdj-mixxx-harness`).
- [ ] Confirm with Ernest: `mlxxx` = Mixxx ✅ / 95%; AAC files DRM-free ✅?
- [ ] Install Mixxx 2.5 on macOS; verify launches and reads `~/Music`.
- [ ] Set up macOS IAC Driver virtual MIDI bus named `clawdj`.
- [ ] Set up Linux test box virtual MIDI (snd-virmidi or `midir` virtual port).
- [ ] Hand-write `mixxx-mapping/clawdj.midi.xml` with 4 messages: load, play,
      pause, crossfade.
- [ ] Hand-write `mixxx-mapping/clawdj.scripts.js` to handle them.
- [ ] Stand up `core-rust` Cargo workspace; depend on `midir`.
- [ ] CLI subcommands: `clawdj setup`, `clawdj cmd`, `clawdj load <deck> <path>`.
- [ ] Manual end-to-end: cargo run → Mixxx plays the file. ✅ demo.

## M1 — Library + analysis (week 2)

**Demo:** "Show me what's in `~/Music/Hip-Hop` and which keys are compatible."

- [ ] SQLite schema + migrations.
- [ ] `clawdj scan` walks a folder, reads tags (`lofty` crate),
      inserts/updates rows.
- [ ] Python sidecar `analysis-python/analyze.py` (BPM + key only at first).
- [ ] `clawdj analyze --missing` runs the sidecar in a pool, ingests JSON.
- [ ] `clawdj list --key 8A --bpm 88..96` query.
- [ ] Output: table of compatible candidates for any seed track.

## M2 — Pre-computed transitions + planner (week 3)

**Demo:** "Plan me a 30-min hip-hop set that builds energy from 88 to 96 BPM."

- [ ] Add sections + downbeats to analyzer (madmom/essentia).
- [ ] Camelot wheel + BPM-delta scoring.
- [ ] Greedy planner producing a JSON timeline with transition windows.
- [ ] `clawdj plan --vibe "..." --duration 30` outputs the timeline.

## M3 — Live execution (week 4)

**Demo:** "Run the planned set live; cut between decks at the planned points."

- [ ] Beat-active feedback bus (second virtual MIDI in).
- [ ] Scheduler thread fires queued ops near target beats.
- [ ] In-Mixxx JS recipes for crossfade, bass-swap, EQ-kill.
- [ ] `clawdj live` REPL + Unix socket.

## M4 — Agent harness (week 5)

**Demo:** "Chat with Grimlock in OpenClaw, watch Mixxx mix."

- [ ] OpenClaw skill `~/Prop/openclaw/skills/clawdj/SKILL.md`.
- [ ] Tool surface: `clawdj_status`, `clawdj_propose`, `clawdj_execute`.
- [ ] Co-pilot mode (suggestion + confirm) by default.
- [ ] Heartbeat-driven event tail so agent can react to "track ending soon".

## M5 — Lyric-aware + polish (week 6+)

**Demo:** "Use the acapella punch-line at 1:30 of A to bring in B's first verse."

- [ ] `.lrc` import; `syncedlyrics` fallback; whisper.cpp local fallback.
- [ ] Lyric-aware transition planner.
- [ ] Set-replay tool.
- [ ] Public split: extract `clawdj-core` to `InServiceOfX/clawdj` if all
      personal info is config-only.

## Stretch

- Mixxx 2.5 stems integration (drop a-cappella from any track).
- VST/LV2 effect routing per transition.
- Browser dashboard (htmx) showing the timeline + agent reasoning live.
- "Battle mode" — two OpenClaw agents share a controller and trade 4-bar
  phrases.
