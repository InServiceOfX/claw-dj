# clawdj architecture

## Goals

1. **Live, two-way collaboration.** Ernest chats; Grimlock (OpenClaw main agent)
   responds *and* can drive the decks. Either side can override.
2. **Cross-platform.** macOS (primary, Apple Music m4a/aac files) and Linux
   (secondary, mp3 + flac).
3. **Low-latency live control.** Everything that needs to fire on a beat is a
   pre-built MIDI message; no blocking work in the live loop.
4. **Offline pre-analysis.** BPM, key, energy curve, beat grid, breakdown markers,
   lyric timecodes — all computed once and cached.
5. **Reproducible sets.** Every set is a JSON timeline; we can replay or remix.

## High-level diagram

```
                        ┌────────────────────────────────────────────┐
                        │  Ernest  (chat in OpenClaw web/mobile UI)  │
                        └──────────────────────┬─────────────────────┘
                                               │ natural language
                                               ▼
   ┌──────────────────────────────┐   ┌──────────────────────────────┐
   │  OpenClaw main agent         │   │ Sub-agents (Codex/Claude     │
   │  (Grimlock, "the DJ brain")  │◀──│  Code) for build/refactor    │
   │                              │   │  tasks (offline)             │
   └──────────────┬───────────────┘   └──────────────────────────────┘
                  │ JSON commands ("crossfade A→B over 32 bars at first drop")
                  ▼
   ┌──────────────────────────────┐    pre-analysis JSON / SQLite
   │  clawdj-core  (Rust)         │◀───┐
   │  - library scanner           │    │
   │  - planner / scheduler       │    │
   │  - MIDI sender (midir)       │    │
   │  - OSC listener (state)      │    │
   └──────────────┬───────────────┘    │
                  │ MIDI bytes          │
                  ▼                     │
   ┌──────────────────────────────┐    │
   │  Virtual MIDI port            │    │
   │  - macOS: IAC Driver bus      │    │
   │  - Linux: snd-virmidi / a2j   │    │
   └──────────────┬───────────────┘    │
                  │                     │
                  ▼                     │
   ┌──────────────────────────────┐    │
   │  Mixxx                        │    │
   │  + clawdj-mapping (XML/JS)    │    │
   │  + Mixxx OSC client (output)  │────┘   (state feedback every 0.5s)
   └──────────────────────────────┘
                  ▲
                  │ audio out
                  ▼
              speakers / DAC
```

## Component contracts

### clawdj-core (Rust, the backbone)

CLI (sketch):

```
clawdj scan ~/Music/Hip-Hop                       # build/update library DB
clawdj analyze --missing                          # call Python sidecar for unanalyzed
clawdj plan --vibe "90s boom-bap, build energy"   # produce a setlist proposal
clawdj live                                       # interactive REPL + MIDI bridge
clawdj cmd '{"op":"load","deck":1,"path":"..."}'  # one-shot JSON command (for agents)
```

Library DB schema (SQLite, `~/.local/share/clawdj/library.db`):

```sql
CREATE TABLE tracks (
  id          INTEGER PRIMARY KEY,
  path        TEXT UNIQUE NOT NULL,
  title       TEXT, artist TEXT, album TEXT, year INT, genre TEXT,
  duration_s  REAL,
  bpm         REAL,
  key_camelot TEXT,        -- "8A", "8B", etc.
  energy      REAL,        -- 0..1
  analyzed_at TIMESTAMP
);
CREATE TABLE beat_grid  (track_id INT, beat_index INT, t_s REAL, downbeat INT);
CREATE TABLE sections   (track_id INT, kind TEXT, start_s REAL, end_s REAL);
                                  -- kind: intro|verse|chorus|breakdown|drop|outro|acapella
CREATE TABLE lyrics     (track_id INT, t_s REAL, line TEXT);
```

JSON command protocol (for agents → core):

```json
{"op": "load",      "deck": 2, "track_id": 1421}
{"op": "play",      "deck": 2, "at_beat": 0}
{"op": "crossfade", "from_deck": 1, "to_deck": 2,
                    "duration_bars": 16, "ease": "equal_power"}
{"op": "set",       "control": "[Channel2].rate", "value": 0.024}
{"op": "cue_jump",  "deck": 1, "marker": "drop"}
{"op": "eq_kill",   "deck": 1, "band": "low", "ms": 250}
```

### clawdj-analysis (Python sidecar)

- Single-file `analyze.py track.mp3 --out-json -` for one track.
- Batch mode reads paths from stdin, writes JSON lines.
- Libraries: `librosa` (BPM/beat grid via DBN tracker), `essentia` (key,
  Camelot), `madmom` optional for downbeat detection, `whisper` (or local
  whisper.cpp) for lyric timestamps when LRC files are missing.
- Output JSON shape mirrors the SQLite schema above; `clawdj-core` does the
  insert.

### clawdj-mapping (Mixxx side)

- `mixxx-mapping/clawdj.midi.xml` — declares virtual controller, lists the MIDI
  notes/CCs we will use.
- `mixxx-mapping/clawdj.scripts.js` — receives those MIDI events, calls
  `engine.setValue("[Channel1]", "play", 1)` etc.
- Conventions:
  - Channel 16 reserved for clawdj.
  - Notes 0..15 = transport ops (play/pause/cue/sync/load).
  - CCs 0..63 = continuous (rate, EQ, crossfader).
  - Notes 16..31 = "atomic recipes" (e.g. "kill-low-then-cut" — implemented in JS
    so timing stays inside Mixxx and is sample-accurate).

### Live loop

See [`LIVE_LOOP.md`](LIVE_LOOP.md). Short version: agent decides → core enqueues
MIDI events with absolute beat timestamps → core's scheduler thread fires them
within a few ms of the target beat using Mixxx's reported beat position.

## Latency budget (target)

| stage                           | budget |
|---------------------------------|--------|
| chat → agent decision           | seconds (it's planning, not playing) |
| agent → core (JSON over stdin)  | < 5 ms |
| core → MIDI port                | < 1 ms |
| MIDI → Mixxx engine.setValue    | < 5 ms |
| sample-accurate ops             | done in JS inside Mixxx (zero IPC)   |

The "live" hard real-time work happens **inside Mixxx's JS engine**. Our Rust
core only schedules *intent*. Important architectural point.
