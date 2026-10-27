# First pitch-play experiment — original source, monophonic

First scope approved by Ernest on 2026-10-15. **Implemented and synthetic-tested;
not yet live-auditioned or audio-measured.** Existing Mixxx binary is unchanged.
This is a standalone experiment, not yet a generic plan gesture.

## What it does

- Python validates the exact indexed original, current mandatory source notes,
  source hash and session ownership; Rust schedules; Mixxx plays/pitch-shifts.
- Six attacks by default: `0, 0, 0, +1, +2, 0` semitones. Absolute offsets, not
  cumulative pitch-up button presses. Narrow ±3-semitone range only.
- `--bpm` defines the note clock, not a new rate for the recording. With rate=1
  and keylock on, the original plays at native tempo while notes are transposed.
- Uses a source-second cue (`--cue-seconds`), so no saved hotcue is created,
  overwritten or converted to a loop. New notes stop/retrigger the same voice.
- Gates use mute/transport as deliberate instrument articulation, not faster
  track-transition faders. No rendered audio, tags, stems, recording or backing
  deck. Existing effects are bypassed during the session and restored afterward.

## Run from repository root

Release executor was built here. Rebuild after moving machines/changing Rust:

```sh
(cd core-rust && cargo build --release -p clawdj-cli)
```

The studio album original was found read-only in the current library index:

```sh
SOURCE="/Volumes/Elements/Music/RnB/Alicia Keys - Discography/01. Albums/(2003) Alicia Keys - The Diary Of Alicia Keys/05 Alicia Keys - You Don't Know My Name.mp3"

.venv/bin/python -m hands.pitch_play \
  --source "$SOURCE" \
  --cue-seconds 0 --source-end-seconds 2 \
  --deck 3 --bpm 90 \
  --pitches 0,0,0,1,2,0 \
  --gate-beats 0.5 --interval-beats 2 \
  --dry-run
```

**0–2 s is only a technical dry-run example, NOT an audition-approved musical
cue or transcription of the TikTok.** This dry-run succeeded against the real
indexed file with no Mixxx connection; six note-ons run from 0.100 to 6.767 s,
final note-off 7.100 s. Choose/review the actual useful attack before evaluating
the musical effect. Keep the exclusive `source-end-seconds` inside a permitted
source region with room for every gate plus the lateness margin. It is a guard,
not the length of the entire song or phrase.

To audition after choosing the cue: stop every deck, disable AutoDJ, stop other
mix/audition controllers and **eject deck 3**, lower monitoring volume, then run
the same command replacing `--dry-run` with **`--live`**. Set `--port` if the
patched Mixxx API uses a nondefault port. Do not directly invoke the internal
Rust `pitch-play --live` protocol: it requires the wrapper's source checks and
prepared deck. No playback was started by the implementing agent.

Other flags: `--prepare-seconds` (0.1), `--max-late-seconds` (0.05), `--binary`.
Use `--pitches=-2,-1,0` for an argument starting with minus. Values outside ±3
are intentionally refused in the first scope. All four channel groups and the
required safety controls must exist; missing controls fail closed rather than
assuming a safe default. No visible pitch-pad bank is required.

## Safety and limits

1. Dry-run defaults to print-only, with no control connection, media writes or
   scheduler. It reads ffprobe metadata and the current library index read-only.
2. Live refuses an active known mix/audition process, AutoDJ, a playing deck,
   nonempty selected deck, missing original or unknown/malformed source limits.
   This is not a cross-application lock: do not manipulate decks or start another
   controller during the experiment. Concurrent external changes are unsupported.
3. Load is paused and muted. Source identity is tied to the requested original
   by loading into an empty deck and comparing hashes; loaded duration/sample
   rate come from Mixxx. Transport, routing and pitch settings are snapshotted.
4. A native inward-rounded engine loop contains all source audio inside the
   reviewed region even if the external scheduler stalls. Rust verifies the
   guard and prepared controls before its first write. Containment can repeat
   allowed audio on a stall; it is not a guarantee of silence after an outage.
5. Notes use absolute monotonic deadlines and abort beyond configured lateness;
   no fast catch-up burst. Pitch is prepared while muted/stopped with control
   readback before attack. Readback does NOT prove DSP settling or sample-atomic
   attack timing. Real latency/attack and click/artifact quality remain untested.
6. Success/error/Ctrl-C joins/terminates the child before cleanup. Cleanup tries
   mute+stop+eject while retaining the source guard; only after confirming empty
   and stopped does it disable the loop and restore touched settings, including
   original empty-deck positions. It never restores a playing transport. On a
   dead stream it reconnects once; persistent failures are reported and require
   manual deck stop/eject. No network client can guarantee restoration during
   a persistent Mixxx/network failure. No saved library cue writes are issued.

## Verification (2026-10-15)

- **18 new Python tests**: score math, invalid/nonfinite/overlapping input,
  connection-free deterministic dry-run, current boundaries/skips, changed
  restrictions/source, fractional cue rounding, AutoDJ/busy/nonempty refusals,
  source guard/setup/original load, error/Ctrl-C, reconnect, no unverified unmute,
  no premature guard removal, state restoration and child termination/join.
- **8 new Rust unit tests**: score/pitch math, validation, gate/schedule, preflight
  zero-write refusal, injected clock jitter/cancellation, late TCP ACK abort and
  attempting stop even after mute cleanup fails.
- **3 new Rust CLI subprocess tests**: default dry-run with unusable port 0,
  invalid live score refused before connection, unknown fields rejected.
- `cargo test --workspace`: **46 tests pass** (42 library + 3 pitch CLI + 1
  gated MIDI test; no CLAWDJ_LIVE opt-in, no live MIDI probe).
- Python pitch-play + existing live-kit/control-port suites: **46 pass**.
- Release build, `cargo fmt --all`, Clippy with `-D warnings`, strict deterministic
  prompt checks and `git diff --check` pass.
- Broader existing performance suites: **29/31 pass**, two errors outside this
  feature: stale `SimpleNamespace` fixture missing `selection` in generic-build
  protection; offline-render test's FFmpeg lacks the requested `soxr` resampler.
  Neither unrelated production code nor those tests were changed for pitch play.
- **Not run:** real Mixxx playback/capture, frequency/onset/gate measurement,
  human listening, reference reconstruction, semantic PDD story certification.
  Automated control tests are not proof of good-sounding pitch play.

## Source and next step

Code: `hands/pitch_play.py`, `core-rust/clawdj/src/pitch_play.rs`, CLI subcommand
in `core-rust/clawdj-cli/src/main.rs`. Specs: matching Python/Rust prompts and
architecture/.pddrc entries. Acceptance:
`user_stories/story__play_one_original_source_cue_at_deliberate_pitches_live.md`.
Approval/tooling evidence: `docs/intents/PITCH_PLAY_APPROVAL.md`.

Next is a short **human-run live audition** of a chosen cue, then a known-tone
capture to establish actual pitch/timing accuracy. Only after those pass should
we author the reference score or integrate backing/landing in a full plan.
