# Worktree review — 2026-10-26

Ernest requested review and commits of the accumulated work on
`feat/review-backbeat-audition`, starting at `3e4d2ea`. All 54 original dirty
or untracked source files are relevant. Three test files were updated during
this audit. No original file was discarded or hidden with a new ignore rule.
Generated recordings, videos, source footage and personal plans remain outside
Git. `.env` remains ignored and untracked; `.env.example` remains tracked.

## Decisions and limits

- The no-abrupt-cutoff story is implemented: automatic hard cuts are replaced,
  model choreography cannot request abrupt exits, and runner/audition refuse
  unreasoned abrupt exits. A deliberate human exception carries its reason.
- Backbeat changes distinguish measured evidence from ambiguous count shifts.
  Human-certified rides/cues remain authoritative. Optional strict cue readback
  is expressed in `cue_tolerance_ms`; existing plans retain legacy defaults.
- Pitch play is a complete **approved first-scope experiment**, isolated behind
  explicit live opt-in. Dry-run/control/scheduler tests pass. It is not integrated
  into generic Build and has no new live listening or pitch-accuracy verdict.
  A full Alicia Keys/Beyoncé reconstruction remains future work. The first-scope
  approval and the historical PDD tooling timeout remain explicit in its docs;
  structural prompt checks are not semantic certification.
- Popup additions are sourced **provisional** records (`verified: false`), not
  newly fact-checked claims or Ernest-authored commentary.
- The demo kit is a reusable authoring tool with synthetic music and explicit
  recording/import steps. Its script no longer promises a plan “in seconds” or
  automatic learning that preserves every audition in every future mix.
- Dated listening logs are history. Later accepted placements supersede earlier
  rejected/unheard candidates; checking those files in does not approve them.

## File-by-file disposition

Every row is retained and committed in its relevant group. “New” means an
originally untracked source file; none is generated personal media.

| File | Review / reason to retain |
| --- | --- |
| `.pddrc` | Registers the bounded pitch-play Python/Rust dev units. |
| `architecture.json` | Declares matching pitch-play ownership and dependencies. |
| `PROGRESS.md` | Preserves dated current-plan, listening and production context. |
| `brain/build_mix_plan.py` | Gentle exits, evidence-gated count shifts, double-time blend reads. |
| `brain/library_index.py` | Schema for cached real-beat window measurements. |
| `brain/onset_analysis.py` | Double-time measurements and ambiguity/confidence decisions. |
| `brain/popup_facts.json` | Sourced, explicitly unverified music-fact candidates. |
| `brain/showcase_moves.py` | Removes automatic abrupt model-selected exits. |
| `brain/web/arrange.js` | Displays a structured profile's name instead of `[object Object]`. |
| `core-rust/clawdj-cli/src/main.rs` | Explicit pitch-play subcommand and dry-run/live protocol. |
| `core-rust/clawdj/src/lib.rs` | Exports the new bounded pitch-play module. |
| `core-rust/clawdj/src/pitch_play.rs` (new) | Monophonic absolute-clock scheduler, guard/readback and cleanup. |
| `core-rust/clawdj-cli/tests/pitch_play.rs` (new) | Subprocess dry-run, invalid live score and strict-input coverage. |
| `docs/DJ_TRANSITIONS_PLAYBOOK.md` | Aligns musical guidance with no unrequested abrupt exits. |
| `docs/HANDOFF.md` | Durable operational history and known gaps. |
| `docs/LIVE_MIX_LESSONS.md` | Records heard count-alignment and pairing lessons. |
| `docs/PRODUCT_INTENT.md` | Accepted gentle-exit and bounded pitch-play intent. |
| `docs/PITCH_PLAY_EXPERIMENT.md` (new) | Reproducible commands, explicit limitations and next listening step. |
| `docs/PITCH_PLAY_RESEARCH.md` (new) | Supporting technique/control research. |
| `docs/intents/PITCH_PLAY_APPROVAL.md` (new) | Exact first-scope approval and tooling evidence. |
| `docs/intents/intent__no-abrupt-cut-offs-echo-cut-and-brake-exits-only-22291d42.md` (new) | Accepted human intent behind the cutoff safeguards. |
| `docs/intents/intent__pitch-play-original-user-request-2026-10-15-49f842d4.md` (new) | Original pitch-play intent, independent of implementation. |
| `docs/marketing/DEMO_SHORT.md` (new) | Reusable demo workflow, truthful script and recording choices. |
| `docs/requirements/backbeat-start-safety.md` (new) | Alignment and cue-start safety requirements. |
| `docs/requirements/pitch-play.md` (new) | Approved first-scope pitch-play requirements. |
| `docs/requirements/requests/2026-10-15-pitch-play.md` (new) | Preserves the original musical request. |
| `docs/transition-log-2026-10-15.md` (new) | Dated audition observations and verdicts, not current universal recipes. |
| `hands/audition_transition.py` | Shares abrupt-exit refusal and strict cue validation with the runner. |
| `hands/run_mix_plan.py` | Exit guards, optional cue precision, nudge readback, center hold and outgoing level controls. |
| `hands/pitch_play.py` (new) | Original-source validation, ownership, guarded setup and fail-closed cleanup. |
| `prompts/brain/plan_mix_build_Python.prompt` | Source contract for planner exit/alignment behavior. |
| `prompts/brain/showcase_moves_Python.prompt` | Source contract withholding automatic abrupt exits. |
| `prompts/hands/audition_transition_Python.prompt` | Source contract for audition safety. |
| `prompts/hands/live_kit_Python.prompt` | Source contract for runner guards and authored controls. |
| `prompts/core/pitch_play_Rust.prompt` (new) | Scheduler/guard contract. |
| `prompts/hands/pitch_play_Python.prompt` (new) | Source-validation/session contract. |
| `scripts/demo/demo_kit.py` (new) | Reusable recording/import/assembly CLI, no import-time playback. |
| `scripts/demo/demo_music.py` (new) | Original synthetic demo music and fixture generation. |
| `scripts/demo/storyboard.json` (new) | Reusable timing, captions and honest narration. |
| `tests/test_audition_transition.py` | Audition refuses unreasoned abrupt exits. |
| `tests/test_blend_window.py` | Blend-window fixtures distinguish trusted musical evidence. |
| `tests/test_mix_plan.py` | Planner cutoff policy and explicit deliberate exceptions. |
| `tests/test_mix_runner.py` | Strict cue failure, cleanup and settled nudge readback regressions. |
| `tests/test_onset_analysis.py` | Confidence/ambiguous bar-count regression coverage. |
| `tests/test_showcase_moves.py` | Model choreography cannot select abrupt exits. |
| `tests/test_alignment_safety.py` (new) | Refuses guessed count shifts under weak/ambiguous evidence. |
| `tests/test_center_hold.py` (new) | Authored center hold and outgoing-volume behavior. |
| `tests/test_double_time_grid.py` (new) | Real-beat mapping and trusted-cue preservation. |
| `tests/test_pitch_play.py` (new) | Source restrictions, dry-run, session ownership and cleanup. |
| `user_stories/story__blend_with_gentle_faders_never_fast.md` | Aligns transition policy and deliberate articulation exceptions. |
| `user_stories/story__when_i_blend_i_match_the_snare_not_just_the_beat.md` | Evidence and ambiguous-count safeguards in user terms. |
| `user_stories/story__do_not_turn_uncertain_backbeats_into_guessed_count_shifts.md` (new) | Explicit accepted negative behavior. |
| `user_stories/story__never_end_a_song_with_an_abrupt_cut_off.md` (new) | Accepted human rule and observable enforcement. |
| `user_stories/story__play_one_original_source_cue_at_deliberate_pitches_live.md` (new) | First-scope story; live listening explicitly pending. |
| `tests/run_dj_workflow_checks.py` (audit update) | Adds eight relevant suites to the existing isolated workflow runner. |
| `tests/test_collection.py` (audit update) | Invalidates the fixture's schema cache after it manually recreates an old schema. |
| `tests/test_performance.py` (audit update) | Uses real plan paths for revision-aware refusal; explicitly skips optional libsoxr decode test when unavailable. |

## Verification

- Full isolated Python suite: **681 tests, OK, one skipped**. The optional
  decoder/export test needs an FFmpeg build with libsoxr; this machine lacks it.
  Production resampling behavior was not changed to make that test pass.
- Expanded `python tests/run_dj_workflow_checks.py`: **419 tests pass**.
  Temporary empty libraries protect the mounted personal library; local HTTP
  test fixtures run with loopback access. No Mixxx playback is part of these tests.
- Rust: **46 tests pass**, `cargo fmt --all -- --check` and
  `cargo clippy --offline --workspace --all-targets -- -D warnings` pass.
- Six modified/new managed prompts: strict deterministic contract checks report
  **zero errors and zero warnings**. No broad PDD synchronization/regeneration.
- Demo CLI help/import checks and JSON parsing pass. No demo recording triggered.
- `git diff --check` and credential-pattern scan pass. The scan reports filenames
  and line numbers only; no secret values are printed or added to Git.

Private R&B media delivery is documented in the latest PROGRESS/HANDOFF entry.
Its recordings, downloaded artist footage, credits, manifests, reconstruction
scripts and finished MP4s remain in the private production directory outside
the checkout. Committing source does not alter a saved plan or waveform.
