# Tone play: handoff to an agent on another computer

## Assignment and current status

Continue the existing **original-source pitch-play** experiment using Phil
Harris's tone-play explanation as supporting research. Start by reproducing
synthetic checks and evaluating what is already implemented. This handoff is
documentation only: no new runtime behavior, saved plan, musical cue selection,
library note, audio render or live action was performed in its preparation.

Inspected base: `118c218` (local master when this handoff was written). Research
source: [Phil Harris note](research/PHIL_HARRIS_TONE_PLAY.md). Recheck the actual
checkout; a later commit or a new human audition can supersede this status.
The existing experiment docs report synthetic testing, with real pitch/onset
measurement and listening still pending. This handoff does not refresh that
test evidence or convert it into a listening approval.

## Read before work

1. `AGENTS.md`, `BOTS.md`, current `PROGRESS.md` and `docs/HANDOFF.md`.
2. `docs/PITCH_PLAY_EXPERIMENT.md` (current runnable scope),
   `docs/PITCH_PLAY_RESEARCH.md` (control evidence and unresolved acoustics),
   `docs/requirements/pitch-play.md` (epic and staged scope).
3. `docs/intents/PITCH_PLAY_APPROVAL.md`,
   `user_stories/story__play_one_original_source_cue_at_deliberate_pitches_live.md`,
   `prompts/hands/pitch_play_Python.prompt`, `prompts/core/pitch_play_Rust.prompt`,
   and their exact `.pddrc`/`architecture.json` entries before changing code.
4. `docs/SETUP_NEW_MACHINE.md`, `docs/MIXXX_CONTROL_SURFACE.md`,
   `docs/LIVE_MINI_EXPERIMENTS.md`, `docs/LIVE_MIX_LESSONS.md`,
   `docs/SOURCE_AUDIO_BOUNDARIES.md`, `docs/SHARED_PERFORMANCE.md`.

Use a feature branch and preserve unrelated edits. Do not commit/push/PR unless
requested. Do not assume paths, installed binaries, library identity, API port,
active mix or human listening approvals transfer to this computer. No need to
copy personal music/databases into Git or another model's context.

## Reuse these pieces

| Piece | Responsibility |
| --- | --- |
| `hands/pitch_play.py` | Read-only source/note validation, standalone deck ownership, paused load, guard setup, child lifecycle, eject/restore |
| `core-rust/clawdj/src/pitch_play.rs` | Pure score validation, absolute monotonic note deadlines and guarded control execution |
| `core-rust/clawdj-cli/src/main.rs` | Internal `pitch-play` score protocol; dry-run can compile without a connection |
| `tests/test_pitch_play.py` | Synthetic library/control/process lifecycle tests |
| `core-rust/clawdj-cli/tests/` | Locate pitch CLI integration tests before choosing test filters |

Python is already the validated setup boundary; **Rust already handles timing**.
Keep Mixxx responsible for decoding/pitch DSP. Do not bypass the wrapper by
calling the internal Rust live command on unvalidated original music.

Current first scope: one empty reserved channel, monophonic notes, absolute
offsets within ±3 semitones, 1..64 notes, preparation gaps, bounded source region,
native rate with keylock on, deadline refusal rather than late catch-up.
±3 is this experiment's policy, not a claimed hard DSP limit. No saved hotcue
edits, backing deck, controller purchase, stems or Mixxx rebuild are needed.

## Work ladder

### A. Reproduce without playback

- Read CLI help; build the existing workspace. Run the focused Python suite and
  Rust workspace checks with live opt-ins unset. Tests use synthetic fixtures,
  not a real music library. Inspect current tests before assuming names/counts.
- Verify dry-run determinism, no Mixxx connection, no file/library writes,
  absolute pitch reset and source/ownership refusal. Existing tests already cover
  much of this; preserve accumulated coverage rather than rewriting it.
- Report exact commands, compiler/runtime versions, actual failures/skips and
  whether the built executor matches the checked-out source.

Typical starting commands, after local environment discovery:

```bash
python -m unittest discover -s tests -p 'test_pitch_play.py' -v
cd core-rust
cargo fmt --all --check
cargo test --workspace
cargo clippy --workspace --all-targets -- -D warnings
cargo build --release -p clawdj-cli
```

Choose the repository's virtualenv Python if needed. These are synthetic checks;
do not set `CLAWDJ_LIVE`, launch Mixxx, start a stream or record audio to pass them.

### B. Prepare an explicit audition proposal

Identify one authorized exact original recording and a useful source cue. Read
its **current effective notes and hard restrictions**. Do not reuse an old
machine's absolute example path, a guessed lyric boundary or an unverified
0–2-second musical cue. Inspect the actual permitted attack/tail.

Return a short score table: note-on beat, gate beats, absolute semitones,
source cue/end, BPM, preparation gap and maximum lateness. Start with the
existing untransposed / 0,+1,+2,0 exercise, not a guessed famous melody. Respect
the allowed source span through the gate plus lateness margin and native guard.

The wrapper supports `--source`, `--cue-seconds`, `--source-end-seconds`, `--deck`,
`--bpm`, `--pitches`, `--gate-beats`, `--interval-beats`, `--prepare-seconds`,
`--max-late-seconds`, `--port`, `--binary`, `--dry-run` and `--live`. Check `--help`
first. Supply the current machine's verified values. Use `--pitches=-2,-1,0`
when the list begins with a minus sign.

A real-source `--dry-run` still needs that exact recording in the current
read-only library index; a missing library is not a reason to remove validation.
It should print the proposed schedule with no control connection or writes.

### C. Human-authorized short live audition and measurement

Only after explicit authorization on this machine: all decks stopped, AutoDJ
off, no mix/audition runner, chosen deck empty, correct patched control API,
conservative monitoring. The human may run the proposed wrapper command.
Authorization to write this handoff does **not** authorize playback or capture.

Separately authorized known-tone capture can measure frequency ratio, attack
latency/jitter, gate duration and pitch settling. Record device/sample-rate/
buffer configuration with measurements. Confirm the installed pitch control's
readback and audible behavior. Do not certify frequency/onset from a TCP ACK.
State measured results before proposing tolerances; no unexplained threshold
relaxation. A tone validates mechanics; listen to an actual permitted musical
cue for clicks, artifacts and musical fit as a separate step.

Verify Ctrl-C, late-note refusal and cleanup: join child first; mute/stop/eject
with source guard retained; confirm empty/stopped before removing guard and
restoring settings; never restore play=1. A persistent control outage remains a
manual stop/eject condition. Do not intentionally break a live session to test
failure handling when injected controls can exercise it safely.

### D. Integrate only after evidence

Author a verified melody/rhythm and its root/interval evidence only after a
useful cue is chosen and heard. Backing/landing, arbitrary scores, wider range,
polyphony and generic plan gestures are later product scope. Check existing
performance compiler/schema ownership before proposing a new event; arbitrary
JSON directives are not an implementation. Preserve backbeat matching,
phrase-entry rules, gentle transition faders and every approved seam.

Pitch-play Python/Rust modules are PDD-owned. Any behavior change follows the
workspace PDD playbooks, scoped intent planning and applicable approval, prompt,
independent story/negative test maintenance, scoped execution and combined diff
review. Do not broadly regenerate this brownfield repository. If the new machine
lacks the workspace playbooks/toolchain, resolve setup before claiming PDD sync.

## Deliver back

- What already worked, exact code/spec changes if any, tests and evidence paths.
- One reproducible dry-run and, only if authorized, the exact heard command and
  human verdict. Keep original identity, current source notes and cue/score
  reconstruction in the proper local state; no private paths in shared docs.
- A separate status for: control simulation, measured audio, human listening,
  reference transcription and full-mix integration. Never promote one to another.
- Update `PROGRESS.md` and `docs/HANDOFF.md`; preserve all unrequested approved
  music. No pre-rendered replacement master, DJ tags, new DSP or silent live run.

Portable optional skill: `agent/tone-play-skill/SKILL.md`. Read it by path or
install it explicitly using the target harness's supported skill mechanism.
