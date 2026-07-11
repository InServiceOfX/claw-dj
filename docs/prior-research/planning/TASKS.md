# TASKS — sub-agent ready

Each task is sized for a single Codex/Claude Code session (~30 min – 4 h).
**Owner: agent or human?** column tells the harness who should pick it up.
**Spawn cmd** is exact CLI for the OpenClaw `coding-agent` skill (Codex/Claude
Code).

Status legend: `TODO` `WIP` `BLOCKED` `DONE`.

## Conventions

- Branch off `feat/clawdj-mixxx-harness`. Sub-feature branches:
  `feat/clawdj-<short-slug>`.
- All paths relative to `Projects/clawdj/` unless noted.
- No hardcoded music paths or user-identifying info in committed code.
- Tests required for every Rust crate task; Python sidecar gets `pytest`.
- macOS Mixxx data root resolved via env or default to:
  `${XDG_DATA_HOME:-$HOME/Library/Containers/org.mixxx.mixxx/Data/Library/Application Support}/Mixxx/`.
- MIDI port name constant: `IAC Driver clawdj` (macOS), `clawdj` (Linux/ALSA).

---

## M0 — Plumbing

### T0.1 — `setup-doc-mac` · TODO · agent
Write `docs/SETUP_MACOS.md`: install Mixxx 2.5, enable IAC Driver "clawdj"
bus, point Mixxx Preferences → Controllers → IAC Driver clawdj → Enable +
load `mixxx-mapping/clawdj.midi.xml`. Include screenshots placeholders.
**Spawn cmd:**
```
codex "read Projects/clawdj/docs/MIXXX_INTEGRATION.md and write Projects/clawdj/docs/SETUP_MACOS.md per the instructions there"
```

### T0.2 — `setup-doc-linux` · TODO · agent
Same as T0.1 but for Linux (snd-virmidi + `midir`). Write
`docs/SETUP_LINUX.md`.

### T0.3 — `mapping-skeleton` · TODO · agent
Hand-write `mixxx-mapping/clawdj.midi.xml` and `clawdj.scripts.js`
implementing: note 0=load deck1, 1=load deck2, 2=play1, 3=play2,
4=pause1, 5=pause2; CC 0=crossfader. Reference Mixxx's
[ControllerMapping.dtd](https://github.com/mixxxdj/mixxx/blob/main/res/controllers/mapping_template.xml).
Include header comment with our channel allocation table.

### T0.4 — `core-rust-skeleton` · TODO · agent
`cargo new --lib core-rust/clawdj`, add `clawdj-cli` bin crate. Deps:
`midir`, `clap`, `anyhow`, `serde`, `serde_json`, `tracing`. Implement
`clawdj setup` (prints virtual MIDI port name), `clawdj load <deck> <path>`
(emits the right MIDI bytes). No analysis yet.
**Spawn cmd:**
```
codex "create a Cargo workspace at Projects/clawdj/core-rust per docs/ARCHITECTURE.md, with one library crate `clawdj` and one binary crate `clawdj-cli`. Implement only the `setup` and `load` subcommands using midir."
```

### T0.4b — `clawdj-queue-bootstrap` · TODO · agent
Add a `clawdj queue init` subcommand that opens Mixxx's `mixxxdb.sqlite`
(path: `$HOME/Library/Containers/org.mixxx.mixxx/Data/Library/Application Support/Mixxx/mixxxdb.sqlite` on macOS)
and creates a hidden Mixxx playlist named `__clawdj_queue` if it does not
exist. Provides `clawdj queue set <deck> <track_id>` which inserts the track
at row 0 and `clawdj queue clear`. Use SQLite WAL mode + retry on lock; never
write to Mixxx's `library` or `track_locations` tables. See DECISIONS.md
"Track-loading mechanism".

### T0.5 — `m0-end-to-end-test` · TODO · human
Manual: open Mixxx with mapping loaded; run `clawdj load 1
~/Music/clean-test.mp3`; confirm deck 1 has the track. Document any gotchas
in `docs/SETUP_MACOS.md`.

---

## M1 — Library + analysis

### T1.1 — `db-schema` · TODO · agent
Add `core-rust/migrations/0001_init.sql` matching the schema in
`docs/ARCHITECTURE.md`. Wire up `rusqlite` + `refinery` for migrations.

### T1.2 — `tag-scanner` · TODO · agent
`clawdj scan <dir>` walks recursively, reads tags via `lofty`, upserts
`tracks` rows. Detect file moves via `(sha256_first_1MB, size)`.

### T1.3 — `analyzer-bpm-key-py` · TODO · agent
`analysis-python/analyze.py` with `librosa` + `essentia`. Reads paths from
stdin, writes JSON lines. Single-track BPM + Camelot key.
Provide `pyproject.toml` (uv-managed, `essentia-tensorflow` optional).

### T1.4 — `analyzer-driver-rs` · TODO · agent
`clawdj analyze --missing` finds rows with `bpm IS NULL`, pipes paths into
the Python sidecar (multiprocess pool), ingests results.

### T1.5 — `query-cli` · TODO · agent
`clawdj list` with filters: `--key`, `--bpm-min`, `--bpm-max`, `--genre`,
`--neighbors-of <camelot>`. Pretty-print as table.

---

## M2 — Planner

### T2.1 — `analyzer-deep` · TODO · agent
Extend `analyze.py` with sections (essentia/MSAF) and downbeats (madmom).
Update JSON schema. Cache in `~/.local/share/clawdj/cache/`.

### T2.2 — `transition-scorer` · TODO · agent
Pure Rust function: given two analyzed tracks, return a list of viable
transition windows scored 0..1. Properties used: Camelot distance, BPM
delta, energy match at window boundaries, section types.

### T2.3 — `set-planner` · TODO · agent
`clawdj plan --vibe "..." --duration <min>` greedy planner using T2.2.
Output JSON timeline of `{deck, track, in_at, out_at, transition}` items.

### T2.4 — `vibe-parser` · TODO · agent
Tiny grammar for vibe strings → constraints: era, genre, BPM range, energy
arc. Stub for now: regex + keyword tables; LLM upgrade later.

---

## M3 — Live execution

### T3.1 — `feedback-bus` · TODO · agent
Add a second virtual MIDI port `clawdj-feedback`. In `clawdj.scripts.js`
register `engine.connectControl` for `playposition`, `bpm`, `beat_active`
on each deck and emit MIDI back through `midi.sendShortMsg`. Document the
return-message format in the XML header.

### T3.2 — `scheduler` · TODO · agent
Rust thread: priority queue of `(target_beat, midi_msg)`; subscribes to
feedback bus; fires events with latency compensation. Tests via fake clock.

### T3.3 — `recipes-js` · TODO · agent
Implement in-Mixxx JS recipes triggered by notes 16..31 ch16:
`crossfade_bars`, `bass_swap`, `eq_kill_low`, `cue_jump`, `loop_roll_4`.

### T3.4 — `live-repl` · TODO · agent
`clawdj live` long-running process: opens MIDI in/out, listens on
`/tmp/clawdj.sock` for JSON commands and emits JSON events.

### T3.5 — `m3-demo-set` · TODO · human
Record a 5-min planned hip-hop set executed live. Add audio file (gitignored)
and notes to `examples/m3-demo.md`.

---

## M4 — OpenClaw harness

### T4.1 — `openclaw-skill` · TODO · agent
Create `~/Prop/openclaw/skills/clawdj/SKILL.md`. Tools: `clawdj_status`,
`clawdj_propose`, `clawdj_execute`, `clawdj_panic`. All shell out to
`clawdj` CLI / socket. Triggers: "DJ", "spin", "mix", "drop a set".

### T4.2 — `event-tail-cron` · TODO · agent
A heartbeat-style cron job (or background tail) that reads
`/tmp/clawdj.events` and wakes Grimlock when a track has <30 s left so the
agent can propose the next move.

### T4.3 — `copilot-prompts` · TODO · agent
Prompt templates for: "propose next track", "pick transition window",
"react to user steer".

### T4.4 — `safety-gate` · TODO · agent
Default mode is co-pilot: every executed command requires explicit human
confirmation (or autopilot opt-in for the current set).

---

## M5 — Lyric + public split

### T5.1 — `lrc-import` · TODO · agent
Read `.lrc` files next to audio; populate `lyrics` table.
### T5.2 — `lyric-fallback-syncedlyrics` · TODO · agent
Add `syncedlyrics` to Python sidecar; only run when no LRC present.
### T5.3 — `lyric-fallback-whisper` · TODO · agent
Optional: whisper.cpp word-level alignment.
### T5.4 — `lyric-transitions` · TODO · agent
Extend transition scorer with lyric-punch detection.
### T5.5 — `public-split` · TODO · human-led, agent-assisted
Audit `core-rust/`, `analysis-python/`, `mixxx-mapping/` for any private
info; if clean, push to a new public repo `InServiceOfX/clawdj`.

---

## Cross-cutting

### TX.1 — `ci-rust` · TODO · agent
GitHub Actions: build + test on macOS-14 + ubuntu-22.04.
### TX.2 — `ci-py` · TODO · agent
ruff + pytest for `analysis-python/`.
### TX.3 — `pre-commit` · TODO · agent
`.pre-commit-config.yaml`: rustfmt, clippy, ruff, leak-checker for music
paths.
### TX.4 — `lint-no-private-paths` · TODO · agent
Custom hook: forbid `/Users/`, `/home/`, `~/Music`, `Apple Music`, library
account markers in code.
