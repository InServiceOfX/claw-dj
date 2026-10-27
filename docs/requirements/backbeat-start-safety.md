# Backbeat/count decisions and strict cue verification — 2026-10-23

## Accepted request and authorization

Source: Ernest's Desktop transition logs dated October 17, 20 and 22, followed
by these explicit messages:

> back up , skip audition, just build tghe plan please

> just go ahead and implement the .py changes as well and we'll test after the fact later when i'm back

> i'm just gonna run the current mix; we'll do the audtion testing later, just implement the change already it's ok

Keep Maxwell Sumthin' Sumthin' -> The Urban Theme together. Preserve existing
approved musical recipes, do not invent a millisecond nudge or listening
approval, and do not interrupt the current run. The authorization waives a
live audition before implementation/preparation, not truthfulness about sound.

## Contract

- BG1: An ambiguous count choice must not automatically become a whole-beat
  ride adjustment, cue displacement, or inferred snare_align jump. This applies
  to ordinary and mixed double-time grids. Keep count1_verified=false; distinguish
  unresolved bar position from a measured snare parity.
- BG2: Weak reads must not trigger a guessed whole-beat ride correction. Explicit
  existing human snare_align directives and trusted recipes remain authoritative.
- BG3: A new load may explicitly request cue_tolerance_ms in (0,250], finite and
  not boolean. Omitted/None retains legacy playback behavior and call arguments.
- BG4: Strict verification requires a stopped deck, temporarily disables
  quantize, verifies the source position holds, restores quantize on success or
  failure, and checks again after engine settlement. A 600 ms miss cannot be
  called verified under a 20 ms tolerance. Invalid tolerances are rejected before
  a full-run or audition connection. No guessed beat jump or nudge is substituted.
- BG5: A strict cue failure does not start the incoming deck. The full runner
  stops/neutralizes both decks; audition cleanup remains mandatory. Persistent
  loss of the control connection cannot guarantee a successful stop.
- BG6: An actively running plan and its inputs are not replaced. Prepare a full
  candidate separately, preserving all original recordings, approved cues,
  source fade anchors, transitions, exclusions and skip handoffs outside the
  explicitly changed entry. No generic rebuild, playback or render is required.

The runtime runner/onset helpers are conventional dependencies, not newly
adopted generated dev units. Managed source requirements were updated in
prompts/brain/plan_mix_build_Python.prompt and
prompts/hands/audition_transition_Python.prompt. Deterministic PDD intent planning
ran with ID safe-backbeat-decisions-and-verified-cue-starts--ae7843fe; no model
apply/sync, generated story contract or semantic certification is claimed.

## Findings and limits

The legacy count helper assumes grid beat0 is count1; when the snare parities
conflict, +/-1 can both satisfy parity. The planner now withholds that ambiguous
choice instead of merely labelling a guess while executing it. The legacy pure
math helpers remain available unchanged; the planner gates their application.
This is not a new reliable musical downbeat detector. Even an unambiguous
snare/grid result is not independent proof of count1.

Legacy cue verification accepts about one second of error. An in-memory
reproduction accepted 9.7274s requested / 10.3274s observed as verified.
New strict verification fixes that contract for explicitly opted-in loads,
without retroactively changing approved starts (e.g. Say I requested0.000s,
observed about0.37s in the accepted audition). The exact engine behavior of a
new strict file-head start remains to be tested live, including after beatsync.

## Implementation and evidence

- brain/build_mix_plan.py: withhold ambiguous ordinary/double-time and weak-read
  whole-beat corrections; do not reintroduce them as inferred snare_align.
- hands/run_mix_plan.py: opt-in strict cueing, event propagation, preflight and
  fail-closed cleanup; default legacy behavior retained.
- hands/audition_transition.py: validate and forward the explicit load tolerance.
- tests/test_alignment_safety.py: new fake-control regressions. Existing valid
  tests were retained. Baseline105 tests passed; seven selected suites now pass
  211 tests. The new tests failed on the pre-fix implementation.
- Existing Q verification: all eight recent approved seam control sequences still
  match their heard miniatures, and the full812-event fake-control run passes.

Backup before edits:
Data/claw-dj-backups/rnb-cooldown-mix-vol-02/build-R-2026-10-23_081400/
(plan/state/journal snapshots plus copies of the already-dirty source files).

Full UNHEARD candidate:
Data/claw-dj-candidates/rnb-cooldown-mix-vol-02/mix_plan.10-23-R-maxwell-file-head.json
SHA256 48c65efe0acb0dc22b23473362068f085727f63cad5c5d9c44fa3619bc9593c4.
Only two execution events differ from Q: The Urban Theme preload requests0.000s
with strict20ms verification; its own body183->199 compensates the16-grid-beat
earlier entry and retains outgoing source139.254464s/grid232 into Marvin Gaye.
All269 transition events and all31 active saved pair audition recipes remain
unchanged. Full dry-run and fake-control simulation pass. Active Q and all plan
inputs remain unchanged because Ernest started the current full mix. Pending
note/order intent is saved beside the candidate, NOT marked human-approved or
installed. Apply plan-only notes/lock and current revisions after the stream if
this candidate is promoted. Do not blindly run an old installer.
