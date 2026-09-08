# Handoff / continuation notes

## Current: 50 Cent / G-Unit tribute plan reproducibility (2026-09-05)

`brain/data/plans/50-cent-g-unit-tribute-vol-1/mix_plan.json` (active plan,
being listened to on 2026-09-05) is the unchanged Aug 28 artifact copied from
the archived `50centgunitera` plan: 147 tracks, `dj-showcase` +
`hiphop-rnb-guided`, H-agent order, no `backbeat` metadata, no `snare_align`
moves. The runner treats it as a legacy artifact (planned fades unchanged,
no measured entrances, no run log). Its selection has since shrunk to 116
tracks but `playlist.json` still has 147, so Build without Finalize would
still compose 147. A rebuild today would differ: `prepare_plan` backbeat
metadata, no parity ride nudges, different ordering engine result, and no
phrase cues unless Analyze & enrich runs first (the shared phrase export is
empty). Named-plan Build overwrites the artifact without archiving. Full
review and reproduction options:
[PLAN_REPRODUCIBILITY_50_CENT_G_UNIT_TRIBUTE_VOL_1_2026-09-05.md](PLAN_REPRODUCIBILITY_50_CENT_G_UNIT_TRIBUTE_VOL_1_2026-09-05.md).
Nothing in the plan, code or Mixxx was changed for this review.

## Current: listening corrections, notes and review candidate (2026-09-05)

Ernest continued the gradual-v3 listen: fades improved, several backbeats
still one count off. Keep ZERO automatic evidence-triggered short handoffs.
Independent reviewer challenged both UI and Rust changes; blockers fixed and
re-reviewed. No commit/push/PR or live Mixxx commands.

- Added multiline **Edit playback note…** to Arrange, linked from Mix.
  Existing plan-only revision-checked API; Save/Cancel/confirmed library-default
  restoration. Forms bind to rendered plan, late snapshots cannot paint the
  wrong plan, drafts survive other saves/Arrange refreshes/in-app switches,
  stale edits never retry and browser navigation warns about unsaved drafts.
  Fixed pre-existing populated-bunch rendering ReferenceError so the actual
  three-bunch plan can reach the editor. Browser refresh loads these static
  changes; no editor restart needed for this UI-only change.
- Added song-note story; expanded opening-skit story to middle/ending skits,
  reviewed regions, full fades ending BEFORE the scene, and optional same-song
  two-deck continuation. That new splice/automatic skit identification is NOT
  implemented. Biggie's active global note is empty and the plan overlay still
  permits the unwanted spoken tag; event11 has no skip. Approximate210–230s
  differs from historical203.5–224.5s. Do not invent reviewed bounds or claim
  a saved sentence executes itself. See `WHO_SHOT_YA_LISTENING_REVIEW_2026-09-05.md`.
- Rust `rhythm::align` now searches for reliable later evidence INSIDE the
  planned overlap when the entrance is weak/missing. Require three matching
  hits, compatible cadence, enough full-fade bed and no contradictory confident
  selected interval. Exact window-boundary/center-midpoint partition closes
  the reviewer's10ms-conflict case. Account for outgoing audio during launch
  wait. Keep `uncertain`, identify the limited evidence window; no cue jumps,
  threshold lowering or fade changes. Python execution code was not changed.
- Ja→Jealous recorded-position replay: old grid fallback gave619ms mismatch;
  new delay1.152042s versus0.510574s gives median−22.392ms/max33.982ms over10
  counterfactual numeric readings. Not audible acceptance. OnFire→Biggie,
  Instrumental→Part2, Superwoman→Heartbeat Club and CaughtUp→Fastlove remain
  open. Details: `OVERLAP_PARITY_REVIEW_2026-09-05.md`.
- Built/tested separate Rust target while Ernest listened. Installed normal
  `core-rust/target/release/clawdj` only after log `run_end` and approved read-only
  process check found no mix runner. No stop/restart or wrapper edits this turn.
- Jadakiss Who Shot Ya moved24→7 immediately AFTER K.Dot (still6) in next-build
  selection/playlist. Expanded only this plan's opening bunch8→9; preserved
  all original members' relative order and all36 tracks. All10 overrides kept;
  K.Dot→Aaliyah now orphaned, not deleted. Shared library bunch/DB unchanged.

### Try the checked candidate, not the old default artifact

```sh
./scripts/run_mix.sh --plan brain/data/plans/heavy-rotation-vol-1/candidates/listening-fix-2026-09-05.json
```

Optional `--record`. This is a review candidate, not a claim all backbeats are
fixed. 36 tracks/110 events; requested order, every old cue/body beat count and
existing-pair fade length preserved. Stunt Instrumental's source grid restored
without moving139.27s cue. New K.Dot→Jadakiss→Aaliyah pairs predict ready;
overall7 ready/26 uncertain/2 separate, no analysis failures. It does NOT remove
Biggie's skit. Candidate-only supported cue/ride locks freeze the prior listen's
choices; plan/global note storage unchanged. Provenance identifies those locks.

Current `mix_plan.json` is still SHA1826e5e2ddb51079bd23e4a48d5a1a4605183ae98fb0c4554efbb9550678263d;
plain `run_mix.sh` still uses old order/grid metadata (with updated Rust live
solver). Source inputs are now stale from Jadakiss move. Do not promote the
rejected `candidates/ordered-backbeat-review-2026-09-05.json`: normal recomposition
changed24 unrelated cues. Earlier `backbeat-grid-2026-09-05.json` is old order too.
The checked listening candidate is SHAcd4f752750343e159f9116ae7e1d8c5a6d9e659a5019c3d60b8fc01822fa9504.
Standard Build may recalculate unfrozen cues; do not silently claim its output
equals the pinned listening candidate. Candidate bunch provenance uses the
plan-local activated members; normal `decorate()` still looks up shared bunch
members for its `honored` label (known reporting gap, ordering uses local list).

Validation:254 scoped Python tests (one sandbox-skipped HTTP case separately
passed with temporary loopback permission),38 Rust unit tests/workspace checks,
Clippy/fmt, Node behavior/parsing, Bash syntax, diff checks and full110-event
wrapper dry-run. Live-MIDI test is gated and did not open a port. PDD recorded
notes and overlap-parity intents; model-stage prompt regeneration failed absent
credentials/network, so source prompts/stories/tests were manually updated via
the documented fallback. Strict structural checks are not semantic-model review.

For the two latest unresolved pairs, short A/B source-audio review clips are at
`brain/data/previews/backbeat-count-ab-2026-09-05/index.html`:01/02 are
Superwoman→Heartbeat Club,03/04 CaughtUp→Fastlove. A reconstructs the first
observed relative deck positions; B delays that same incoming cue one count.
These are hypotheses for Ernest to compare, NOT installed runtime corrections
or independently labelled snare hits. EQ/filter/Fastlove key bridge are not
rendered; both versions keep the full fade. Files are decoded/probed and
rendered with6dB headroom. Review metadata includes source positions and gain.
Ask which count matches before encoding a reviewed pair-local constraint;
never turn the A/B generation into a blind every-run beat jump.

## Current: zero automatic short handoffs — gradual-v3 (2026-09-04)

Ernest rejected the evidence-failure → two-beat fallback as an audible
regression throughout heavy-rotation-vol-1. He approved implementation and
requested an independent agent review. His final correction requires **zero
automatic evidence-triggered short handoffs per mix**, not an allowance of
one. The briefly proposed eight-beat mismatch recovery was also removed.
Source: `docs/intents/request__zero_automatic_short_handoffs.md` (supersedes
`request__implement_gradual_blend_recovery.md`). Do not reinstate either policy.

Implemented and reviewed:

- Build/live share a duration policy that takes planned time and physical
  remaining audio, not evidence confidence. Weak/missing/noisy/lost evidence
  AND confirmed mismatch keep the planned gradual fade. Mismatch is reported
  honestly, never called aligned. Explicit DJ cuts remain separate recipes.
- Multi-sample muted entrance checks retain the last cue-preserving timed
  launch when inconclusive. Rust distinguishes weak evidence from confident
  incompatibility and supplies best-effort grid timing without claiming
  backbeat readiness. Half/double-time native BPMs alone are not mismatch.
- Continuous monotonic envelope; only corroborated actual exhausted/stopped
  outgoing audio can constrain duration. Reviewer found that one stale
  stopped/near-EOF read could rush the earlier implementation; corrected and
  tested .995/.999/1 readings in both directions. Do not confuse true audio
  limits (e.g. 71-second 2 Bricks cued at 38.38s) with weak percussion evidence.
- Log planned/scheduled/executed beats and seconds plus verification and
  shortening reasons. Old two-/eight-beat metadata cannot override live v3.
  Previews reject stale v1/v2 timing; Build advances nominal positions even
  when DSP failed but source timing is available. Separate vocal/cut recipe
  preview equivalence is not expanded by this change.
- User reported `run_mix.sh: line 174: unexpected EOF while looking for
  matching '"'` after `mix plan complete`. Current script passes `bash -n`;
  likely caused by our in-place wrapper edits while Bash waited on old Python.
  Final runner commands now use `exec` so Bash cannot resume reading the
  edited file afterward. A fake-runner test changes the wrapper during both
  live/dry-run branches and verifies clean completion, with no Mixxx access.

Validation: 252 scoped Python tests passed (one sandbox-skipped ephemeral
HTTP test rerun successfully with permission), 33 Rust unit tests, Clippy/fmt,
Python/inline-JavaScript/Bash syntax and actual wrapper dry-run10. The Rust
live-MIDI test returns without opening a port unless explicitly enabled;
no live MIDI test is claimed. The independent agent passed final code review,
35 backbeat/fade/wrapper tests including a 35-transition zero-handoff chain,
and 12 held-out 85/94/169-BPM simulations (both directions, uncertain and
incompatible solver outcomes). These checks are not audible acceptance.

PDD recorded both approved intent corrections. Automatic model-stage updates
again failed unavailable provider credentials/network; the scoped manual
story/prompt/code fallback is explicit, not successful model regeneration.
Stories, prompt, agent rules and current architecture reflect final v3.
No commit/push/PR. Preserve the extensive pre-existing dirty worktree.

**Next listen:** `./scripts/run_mix.sh` or `--record`. Look for
`Crossfade policy: gradual-v3`. Runtime fixes need no active-plan rebuild.
No active plan/order/cues, library database or running Mixxx session were
changed in this correction. An old CLI process keeps old Python until the
user restarts; do not edit playback code/wrapper during their next listen.
For new GUI Build behavior reload the editor at a safe idle point; refreshing
the browser alone cannot reload Python. Old rendered previews remain old
until regenerated. The user was told the checks passed and could restart.
Still awaiting listening acceptance for fader curve, EQ, groove and backbeats.

## Historical: fades too fast; story started (2026-09-04)

Ernest ran the mix and reports backbeat matching seems fine, but many
crossfades are too fast. Added
`user_stories/story__when_i_blend_tracks_the_crossfader_moves_gradually_and_seamlessly.md`
from his exact feedback in
`docs/intents/request__gradual_seamless_crossfader_blends.md`.
Ordinary blends should be gradual and seamless; deliberate DJ-performance cuts
are exceptions. He found On Fire → Biggie's 32-beat fade acceptable and is
open to longer blends when musical material supports them.

Cause of the supplied abrupt Wall → On Fire example is visible in the log
and code: `hands/backbeat.launch` did not verify the muted entrance;
`hands/run_mix_plan.perform_transition` then clamps the fade to
`fallback_beats=2` (~1.28 seconds at 94 BPM). The other transition was
position-verified (+15ms) and retained 32 beats (~20.21 seconds at 95 BPM).
The generic “could not be verified” message does not establish whether timing
was wrong or observation was unavailable; this turn did not diagnose the
underlying verification failure. Do not infer it was a false alarm from
the listener report alone, or treat “bass swap (gradual)” as proof of a slow fade.

Documentation/story only: no runtime, tests, prompts, active plan or Mixxx
were changed. No automated contract/regression generation or semantic
validation was requested/performed. Read-only PDD intent planning was used;
manual story drafting stays within the explicit request. Before implementing,
reconcile this feedback with the earlier blanket-short-handoff prompt contract
and define/test recovery for inconclusive checks separately from known drift
or an actual end-of-track emergency. Do not just remove verification or
globally force every blend to 64 beats. Live fader/audio acceptance is pending.

## Analyze & enrich backbeat wiring (2026-09-04 follow-up)

Ernest explicitly approved moving reusable analysis earlier in the workflow.
`brain/enrich_set.py` now calls shared `brain.rhythm.analyze_track` after
phrases, for missing/stale finalized tracks only. No new DSP implementation
was needed: this uses the already-built Rust multiband/section analyzer.
Build remains the pair/cue-specific step and fills missing evidence if Analyze
was skipped; playback retains actual-position/rate verification. Legacy
`beat_phase` stays compatible but is not proof of the new cached analysis.

`brain/rhythm.py` publishes lightweight per-file/grid cache references.
Read-only UI polling uses metadata, tool fingerprints and annotations, never
audio hashing/decoding or DSP. Build still checks the full audio content hash.
Changed audio/grid/tools/markers or missing/corrupt caches are gaps; uncertain
but successfully analyzed sections are cached, not endlessly retried. The UI
shows analyzed, missing/stale and uncertain-section counts separately from
built-transition readiness. CLI supports `--skip-backbeat`; `--skip-bpm`
does not discover/control Mixxx just to run offline enrichment.

Verified the new local stage on the 36 finalized heavy-rotation tracks using
a read-only connection to the external library: 36 cached, no errors, 27
tracks with at least one uncertain section. The built plan is byte-for-byte
unchanged. Did not run lyric fetches, schema writes, reorder/rebuild the plan,
or control Mixxx. Restarted only the idle editor (8787, control port 9995),
and verified `/api/mix` reports 36 analyzed / 0 missing-stale plus the existing
32/36 fully enriched (four lyric gaps). This does not change its 7-ready /
26-fallback / 2-separate-recipe plan prediction or prove audible acceptance.

Validation: 232 scoped Python tests passed, with the sandbox-skipped loopback
HTTP test rerun successfully under permission; 15 new enrichment/cache/action
tests include offline GUI Analyze, cue preservation and Build cache reuse.
JavaScript syntax, diff checks and strict PDD structural contracts passed.
Approved intent: `docs/intents/request__backbeat_analysis_during_enrichment.md`.
Model-driven PDD apply again stopped at unavailable provider credentials;
recorded intent succeeded and scoped manual story/prompt/code edits followed.
No successful model regeneration/semantic validation is claimed. No commit,
push or PR; preserve the pre-existing worktree. Live listening remains next.

## Backbeat implementation (2026-09-04 — supersedes blind-jump workaround)

Backbeat = the snare/clap accent. The amended story and
`prompts/brain/plan_mix_build_Python.prompt` require preparation from the first
transition in every build/profile/format. Rust `rhythm.rs` owns multiband
onset/section analysis and alignment. `brain/rhythm.py` owns cache, reviewed
and optional independent evidence, final-event preparation and artifact
upgrade; `hands/backbeat.py` owns muted launches, live position checks and
logs. No post-launch beatsync or automatic audible-deck jumps in measured
transitions. At this historical stage missing evidence used a two-beat
handoff; gradual-v3 above supersedes that regression. The legacy direct
`build_plan` / old-artifact path remains compatible; normal compositions
disable parity nudges and legacy snare moves.

Current `heavy-rotation-vol-1` was upgraded without changing its 36-track
order, cues, bodies or tempo choices; the previous artifact is backed up
under its `backups/`. First two blends pass offline onset comparison (about
5ms median each), but the full plan is conservative: 7 ready, 26 fallback,
2 separate recipes. Opening audio previews and the full timing report are
under `brain/data/previews/heavy-rotation-vol-1-backbeat/`. No live playback
or ear acceptance was performed. Do not describe all transitions as fixed.

See [BACKBEAT_MATCHING.md](BACKBEAT_MATCHING.md) for commands, controls,
confidence limits, reviewed markers, optional model adapters and evidence.
PDD recorded the exact approved intent but model-driven architecture/apply
failed because configured credentials/network were unavailable. Scoped
direct implementation used the documented fallback. Deterministic contract
checking passed with zero warnings/errors; this is not successful model
regeneration or semantic validation. Keep future generated changes aligned
with the amended prompt and story.

Verification: 209 focused Python tests passed using a temporary isolated
collection registry/index (never schema-write the real removable library
from tests); 31 Rust unit tests plus one integration test passed. Cargo fmt,
Clippy `-D warnings`, Python compilation, inline JavaScript parsing and
`git diff --check` passed. The opening 10 events dry-run without Mixxx.
The idle editor was restarted on 8787, preserving its control port 9995;
GET `/api/mix` reports ready/non-stale and includes the backbeat counts.
Mixxx was left running untouched; no mix playback was started. No commit,
push or PR was made; unrelated pre-existing worktree edits were preserved.
Read-only checks against the existing Mixxx control API confirmed `file_bpm`,
`rate_ratio`, duration, playposition and sync/quantize controls are available;
both decks were stopped and position roundtrips were approximately 0.1ms.
This confirms control availability, not live launch or audio verification.

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

## Who Shot Ya variations (2026-08-31)

Active named plan: `notorious-big-who-shot-ya-variations`. Editorial
lock, not a planner rewrite: Notorious B.I.G. album *Who Shot Ya*
(Ready to Die remaster) opens from 0:00, skips the gun-in-mouth /
victim-squeal skit (`skip_from_seconds=203.5; skip_to_seconds=224.5`,
also in global `dj_notes` for every mix), and blends out on the
chorus. VLS instrumental is not a solo song (`ride_beats=0`) — a
32-beat gentle blend into DMX so beat and vocal play together. Club
Mix sits after the interpolators, not after the album. Rebuild with
`--profile mix-to-listen`.

## Anthology and short-form program (2026-08-02)

The long-running product direction is now explicit in
`docs/ANTHOLOGY_AND_SHORT_FORM_PROGRAM.md`. Named multi-plan workspaces are not
only convenient parallel sets: they are the working surface for definitive,
living anthologies in mix form. The initial slate covers the early
Chronic/Doggystyle/Dogg Pound West Coast era, an expanded *2001* sample-lineage
mix, conscious rap, Wu-Tang and its East Coast orbit, Biggie/Shyne, East Coast
jazz-informed hip-hop, the Shiny Suit era, and a researched Drake-season arc.
The standard is an editorial and performed musical argument—lineage, lyrics,
chapters, phrase-aware transitions, cueing, EQ, loops, effects, and human ear
review—not a chronological playlist with automatic crossfades.

Promotion is part of the same lifecycle. Agents are expected to help research
current TikTok/Reels/Shorts conventions and comparable music/DJ performance,
mine recordings for attention-earning transitions and historical revelations,
direct reviewed tools such as OpenCut or Hyperframes where useful, and keep
FFmpeg-based rendering and verification as the deterministic backbone. View
count is the easiest reach measure, not a complete quality measure; compare
retention/completion, rewatches, shares, saves, follows, and anthology
click-through when those metrics are available. Keep variants attributable,
do not infer a universal viral formula from one post, keep generated media out
of Git, and confirmation-gate uploads and all publication.

This is portfolio-level strategy, so it lives in normal repository Markdown
and is linked from `AGENTS.md`. Each anthology itself lives in a named plan.
Future bounded automation—such as cue-sheet clip extraction, campaign
manifests, or metrics ingestion—belongs in the affected PDD `.prompt` and tests
when its observable behavior is concrete; a user story is selective acceptance
coverage, not a substitute for that prompt.

## Mix runner count/EOF invariants (2026-08-03)

`brain/build_mix_plan.py` phase correction must model the executor's actual
anchor: after N `play_body` beat events, `perform_transition` waits for the next
beat, so the anchor is N+1. `hands/run_mix_plan.py` treats remaining audio as a
hard runtime constraint: a body ride reserves the next anchor, the complete
outgoing transition, and four safety beats using live Mixxx duration and
playposition. A clamp preserves the requested mod-4 count. If a stale artifact
still reaches a stopped outgoing deck, transition execution starts the cued
incoming deck and moves the crossfader instead of aborting the whole set.

Listener-locked `trust_ride_beats` values block planner auto-nudges of ride
length, but the trusted count still defines a planned `phase_anchor` so runtime
can absorb preload/settle jitter without abandoning the 1-2-3-4 target.
Historical artifacts used a separate `snare_align=±1` jump after beatsync.
This is superseded by the measured backbeat implementation above. One beat
forward on either side flips the same relative parity for a two-beat cycle;
changing “direction” alone is not a diagnosis. Do not add those moves to new
compositions or treat a trusted ride length as proof of phase alignment.
Transition beat overrides must enter `build_plan` before previous-fade math;
post-build event patching alone left anchors assuming the default fade while
the runner executed longer human blends (one-count lineage defects on
2026-08-04). For energy holds after a true-synced blend, prefer `settle_bpm`
over midpoint `play_bpm` / `incoming_bpm_target`.

Variable loading and rate-settle time can still make an automatic body's first
counted edge differ from cue arithmetic. Automatic and trusted events therefore
retain a `phase_anchor` targeting the complete modulo-four bar position.

The active `imported-working-mix` build following the latest ear pass keeps
Tell Me at 192 and Keni Burke at 80 with phase anchors, ANL/SO/ATWG at
279/103/111 with anchors 280/168/176 after 64-beat override-aware previous-fade
math, and Around→Tell Me as settle_bpm=96.5 with no incoming_bpm_target. Camp
Lo instrumental remains on beat 101 (`73.237s`). The plan reports current with
56 events; live listening remains the acceptance gate.

## Current-path ordering and flexible control port (2026-07-31)

The recurring “Analyze always leaves exactly one track without a beatgrid” gap
had two reinforcing causes. `brain.enrich_set.status()` correctly treated a
positive tag-derived BPM as enough for ordinary planning, but `run_enrich()`
then used that same status to decide whether to invoke Mixxx—even when phrase
analysis proved no persisted Mixxx `BeatGrid-2.0` existed. Separately, Mixxx
does not commit the final analyzed deck's grid on eject or quit; measured
behavior requires loading a different track. `run_enrich()` now adds
phrase-missing tracks with absent Mixxx grids to its muted-deck analysis
targets regardless of tag BPM, and `brain.analyze_via_mixxx.analyze_tracks()`
performs and verifies a different-track flush after the final successful
target. Regression coverage is in `tests/test_enrich_set.py` and
`tests/test_analyze_via_mixxx.py`.

The standalone runner now follows the active named plan selected in the GUI.
Before 2026-08-02, running `uv run python ./hands/run_mix_plan.py --record`
without `--plan` always opened the legacy `brain/data/mix_plan.json`; this could
record a completely different historical set even though the browser showed a
current named plan. `hands.run_mix_plan.default_plan_path()` now delegates to
`brain.plan_paths.resolve()`, preserving legacy fallback only for an actual
legacy workspace. An explicit `--plan` remains available for archived or
non-active artifacts. If named plans exist but none is active, the runner stops
with a selection/build instruction instead of guessing.

## Multi-plan foundation implementation (2026-07-31)

Architecture entries 1–31 are now materialized under `brain/plan_*.py`,
`brain/api_router.py`, and `brain/api/`, plus `bunch_store.py`,
`transition_overrides.py`, and `order_constraints.py`.
Plans live at `brain/data/plans/<frozen-slug>/`; `active.json` is only a pointer
and listing is always a directory scan. Writes use content-hash optimistic
concurrency and atomic same-directory replacement. Global `tracks.dj_notes`
remain untouched beneath sparse per-plan overrides. Library bunches may overlap,
but enabled bunches in one plan must be disjoint and retain exact internal
order. `plan_mix_build` writes version-3 artifacts with plan/source provenance,
transition attribution, bunch evidence, and the effective Mixxx port; v2 remains
readable. `python -m brain.plan_migration` promotes legacy singleton files
without removing them and is guarded for repeat runs. The stdlib server now
registers plan APIs without changing legacy endpoints; mutations use composite
revision guards and Arrange is one disk-consistent snapshot. `brain.plan_cli`
is the offline agent contract: `note` is track-scoped,
`transition get|set|clear` is transition-scoped, `mark` writes lifecycle, and
`status` reads staleness. Plan-scoped build/start/enrich/refresh retain the
effective Mixxx port. Browser modules 32–35 are now implemented as vanilla ES
modules under `brain/web/`. `plan_client.js` owns revision threading,
structured conflicts, and the one-shot Arrange read; `plan_picker.js` keeps
frozen slugs internal while switching colloquial names above the workflow tabs;
`arrange.js` adds accessible order/bunch/track/journal controls; and
`transition_editor.js` owns sparse human overrides and explicit clearing.
`playlist.html` retains its Curate and Create code and exposes only a refresh
hook after plan switches. The browser never chooses or submits a Mixxx port.
`tests/test_plan_frontend.py` starts a temporary loopback editor server and
verifies HTML, JavaScript MIME responses, and real plan/Arrange GETs; the
top-level suite is 211/211.

## Per-volume music collections (2026-08-06)

The local playlist editor can now switch between independent music volumes
without restarting. `brain/collection_registry.py` keeps a versioned atomic
registry at gitignored `brain/data/collections.json`; it records collection
identity, mount/data/database paths, and the last-used active pointer. The
pointer is deliberately machine-local. The portable identity marker remains
on the collection at `<data-dir>/collection.json`. Startup reads the last-used
choice without prompting, scanning volumes, or creating a replacement
database. If that active volume/database is missing, access fails visibly and
does not fall back to another collection.

`brain.library_index.current_index_path()` is the sole default resolution
boundary. An explicit SQLite path still has absolute precedence for tests,
migrations and portable import/export. An omitted path resolves the active
collection at call time, so a running `PlaylistApp`, enrichment workflow,
DJ-note writer, bunch store, and plan hydration follow an explicit switch.
`brain.scan_library.incremental_scan()` freezes that resolved path once at
scan start; a later switch cannot redirect the in-flight scan, and legacy
crate bootstrap data is never imported into a per-volume database.

The shared lifecycle in `brain.collection` creates or reuses the collection
marker and SQLite, initializes only schema and chosen roots, preserves a
pre-existing local `brain/data/library.sqlite3` as the switchable “Legacy
local library,” and does not scan unless explicitly requested. Its path-only
estimate opens no tags and performs no external calls. CLI and GUI both use
this lifecycle:

```bash
uv run python -m brain.collection list
uv run python -m brain.collection status
uv run python -m brain.collection new /path/to/volume \
  --root /path/to/volume/Music --name "Collection name"
uv run python -m brain.collection new /path/to/volume \
  --root /path/to/volume/Music --scan
uv run python -m brain.collection use <collection-id>
```

On `#curate`, the collection panel lists known/mounted state and keeps the old
Add music folder / Check for new music controls scoped to the active database.
Starting a collection first gets `/api/collections` estimate results, shows
the count/time estimate, and requires browser confirmation. Clearing “Scan
after creating” registers and activates without scanning. A confirmed initial
scan is ordinary local Mutagen metadata ingest only: no lyrics, chroma, Mixxx,
playback or network enrichment is triggered.

The two approved PDD amendments are implemented in the working brownfield
application and the multi-plan graph is now wired through the local server and
offline CLI. `brain.build_mix_plan.compose_mix_plan` always runs the deterministic
mix graph, even with no model or an empty brief. Optional NemoClaw/H Company
responses are constraint interpretation only, invalid/failed responses preserve
the full pool and fall back locally, and H planning uses a non-desktop agent
(cloud web env in text mode — the platform rejects `environments=[]` unless
the agent is a pure orchestrator with subagents) rather than
`brain.agent.Brain` or a local desktop bridge. The playlist editor dry-run now
lists the complete candidate playback order before Start mix.

Port 9995 is now preferred rather than required. `hands.mixxx_control` discovers
only the preferred port and TCP listeners owned by detected Mixxx processes,
then requires the patched JSON `ping` response. `scripts/start.sh` reuses a
validated non-default listener, reports running-Mixxx/no-control-API distinctly,
and passes one effective port into playlist-editor server state. Analyze &
enrich, plan metadata, Start mix, `scripts/run_mix.sh`, and the live runner reuse
that value; explicit overrides remain highest priority. Browser requests no
longer contain their own 9995 default.

## Portable Hermes agent and publishing state (2026-07-23)

The dedicated `clawdj` Hermes agent is now reproducible from a small reviewed
Git kit instead of a full personal-profile export:

- `AGENTS.md` — canonical cross-agent repository rules;
- `agent/hermes-profile/SOUL.md` — TARS/clawdj identity template;
- `agent/hermes-skill/SKILL.md` plus `references/` — operational workflows;
- `agent/pdd-skill/SKILL.md` — PDD intent, brownfield-adoption, approval, and
  evidence workflow backed by the workspace's canonical Monoclaw policy;
- `agent/hermes-skill/scripts/` — deterministic 9:16 teaser rendering;
- `docs/HERMES_AGENT_SETUP.md` — exact new-Mac bootstrap.

This intentionally excludes Hermes history/state databases, caches, logs,
binaries, credentials, personal media, and Mixxx application state. Those are
machine-local and must be installed, transferred, or reauthorized separately.

PDD integration is workflow-ready but does not declare the entire brownfield
repository generated. The workspace router is `../../PDD.md`; canonical policy
is in `../Monoclaw/docs/pdd/`; the executable is the editable fork at
`../PromptDrivenDevelopment/pdd` (remote `InServiceOfX/pdd`). The first
read-only planner classified this repository as conventional brownfield; the
now-characterized multi-plan subsystem is the bounded adopted slice. Its 37
architecture entries have matching `.prompt` sources under `prompts/`, including
dedicated runtime prompts for Mixxx discovery and `scripts/start.sh`, and
`pdd contracts check prompts/ --stories user_stories/` is clean. The current
211-test implementation is the reviewed baseline. Future changes still require
exact intent planning, meaning approval, focused negative tests, and reviewed
sync output. Saying “do PDD” loads this procedure; it is not permission for
whole-project regeneration.

YouTube OAuth is still open work. Ernest is creating the Google Cloud project
and Desktop OAuth client for `https://www.youtube.com/@claw-dj`. Continue from
`agent/hermes-skill/references/youtube-channel-oauth.md`; the currently verified
channel ID is `UClafA-9ft1J1iAKo1JMZmwQ`. The first API upload must be private,
and publication or other public writes require explicit confirmation.

### Synced-lyric timelines (2026-07-13, `brain/lyric_timeline.py`)

First slice of the post-hackathon arc is live. `brain/lyrics.py` now keeps
LRCLIB's `syncedLyrics` (raw LRC with per-line `[mm:ss.xx]` timestamps —
it used to strip them). `brain/lyric_timeline.py` parses the LRC, detects
chorus vs verse by line repetition (choruses recur near-verbatim; ≥3-word
lines repeating ≥2×), splits segments on ≥12s silent gaps (instrumental
breaks), and snaps each vocal onset to the nearest beatgrid bar (4 beats)
via Mixxx's BeatGrid-2.0. Persisted in `lyric_timelines`
(track_id, lrc, segments JSON); wired into `enrich_set` as the `timeline`
step (check-before-fetch; no-synced tracks get an empty row so they aren't
refetched every run). CLI: `uv run python -m brain.lyric_timeline`
(finalized set) / `--show <path substring>` to print a track's map.

Real coverage on the current 24-track set: **17 with full verse/chorus
maps, 7 without synced lyrics on LRCLIB** (fallback plan: whisperX forced
alignment against the plain lyrics, offline). Quality check — 21 Questions
decomposed exactly right: 3 choruses ("Girl, it's easy to love me now") at
32.7/94.6/156.6s, verse onsets at 53.2/115.0s, all bar-snapped with beat
indices. **Verse tour is built and live-validated (2026-07-13,
`brain/build_verse_tour.py`).** Same track loaded on decks 1+2, on-beat
`hard_cut` slams verse→verse, every chorus skipped, freed deck re-cued to
the verse after next. Emits the standard plan schema — `hands.run_mix_plan
--plan brain/data/verse_tour_plan.json` runs it unchanged (only runner
tweak: `wait_for_beats` timeout now scales with ride length, since full
verses outlast the old fixed 90s at slow tempos). Live run: 21 Questions,
3 verses (beats 4/80/176 at 93.1 BPM), both cuts anchored clean, stop_all.
No `sync` in verse cuts on purpose — beatsync's phase-pull would fight the
lyric cue; quantize keeps the slam on grid. Jay-Z "Watcher 2" (Ernest's
target example: Jay/Dre/Rakim verses back to back) is NOT on the drive —
only Dre's "The Watcher"; when the file lands, it's
`uv run python -m brain.build_verse_tour --track "Watcher 2"` after
Mixxx analysis + `brain.lyric_timeline`.

**DB portability Mac→Mac (asked 2026-07-13):** copy
`brain/data/library.sqlite3` into the other clone's `brain/data/` (keep a
backup copy on the USB itself so it travels); macOS mounts the stick at
the same `/Volumes/USB322FD` path so absolute track_ids resolve unchanged
(check `ls /Volumes` for a name collision → "USB322FD 1" breaks paths).
Then one incremental scan regenerates crate/catalog in seconds. Mixxx
beatgrids do NOT travel (they're in that machine's mixxxdb.sqlite) —
import + analyze the finalized set there once; `enrich_set --status`
shows exactly what's missing.

**Hackathon outcome (2026-07-13): FINALIST** — no top-3/NVIDIA prize (PVLA
won). Goal 2 is now the project. NemoClaw/H-agent engines stay while the
free credits last, but are no longer required. Focus per Ernest:
**transitions and mix quality** (songs are already chosen). Agreed next
arc: keep LRCLIB *synced* lyrics (the fetcher strips timestamps today) →
chorus/verse detection from line repetition, snapped to beatgrids →
"verse tour" plan technique (same track on both decks, cut verse-to-verse,
skip choruses; test case: Jay-Z "Watcher 2" — Dre/Jay/Rakim verses back to
back) → offline transition-preview rendering → generic OpenAI-compatible
LLM engine (covers xAI + local models + hermes with one client) → Rust
(core-rust) gesture executor for sub-beat cuts/juggles. Database stays
SQLite; cross-machine portability = relative-path identity + per-machine
roots (optionally ship the sqlite file on the USB), not PostgreSQL.

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
| `brain/playlist_editor.py` | Local browser UI for searching the crate, enabling/disabling tracks, applying the researched R&B/West Coast hit seed, exporting a Mixxx playlist without dropping BPM/key metadata, "Ask the DJ brain", post-finalize **Create the mix** (profile + brief → plan → confirmed live start), and **in-tab preview** via native `<audio>` + `GET /api/preview` (not Mixxx) |
| `brain/mix_profiles.py` | Named mix-feel presets + free-text brief → profile overrides |
| `brain/dj_formats.py` | Versioned expert transition grammars, strict phrase requirements, and format provenance |
| `brain/mix_order_brief.py` | Free-text order intent → agent constraints → greedy + forced adjacency/regions |
| `brain/build_mix_plan.py` | Continuous mix plan builder; `compose_mix_plan` / `plan_summary` shared by CLI and editor |
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
that find new music rebuild `new_music_agent.json` automatically.

**"Create the mix" is page 2 of the playlist editor (2026-07-12).** Hash
routes: `#curate` (crate / enabled set) and `#mix` (create the mix).
**Finalize for Mixxx** writes `playlist.json` and **navigates to `#mix`**,
which always reloads the finalized snapshot (track list + BPM/key status).
A **stale-plan banner** appears when the dry-run no longer matches the
finalized analyzed set (e.g. you added Many Man); Start mix is disabled
until rebuild. Tracks missing BPM/key show in red and are skipped by the
plan builder until Mixxx-analyzed (sync crate afterward).

**Suggest blends** always returns a `message` (set already blends well /
weak links / unanalyzed in set / no candidates) and the UI scrolls to the
brain picks panel so results aren't silent.

**Analyze & enrich from the mix page (2026-07-12):** GUI Mixxx Analyze
often leaves `library.bpm=0` / empty key (verified on Many Man (Wish
Death)) and never reaches claw-dj until something writes the crate. The
mix page now has **Sync from Mixxx** (pull bpm>0 from mixxxdb → index +
crate + re-export playlist.json), **Analyze & enrich missing** (muted-deck
control-API analysis via `brain.enrich_set` → lyrics/chroma/phrases, then
re-export so Build mix plan sees the new BPM/key), and **Refresh list**.
No Holo/GUI agent required when the patched Mixxx control API is up on
9995. Endpoints: POST `/api/mix/sync`, `/api/mix/enrich`, `/api/mix/refresh`.

**Rename + mix graph opener (2026-07-12):** File rename to `Many Men…mp3`
left ID3 as "Many Man"; path was already new. Mix page **Rescan titles/paths**
re-reads tags and prefers filename when it fixes man→men-style typos.
**Shuffle opener** re-runs `greedy_mix_order` from a random (or chosen)
start so the blend graph unfolds differently while keeping adjacent pairs
mixable; then rebuild the plan.

**BPM control-API vs Mixxx DB lag (Many Man case, 2026-07-12):** muted-deck
analysis printed `mixxx bpm: 97.14` but mixxxdb stayed `bpm=0` / no beatgrid
even after 45s + re-sync — so claw-dj stayed empty. Fix: `analyze_via_mixxx`
now **returns live API bpm/key** and `apply_analysis` writes them straight
into `library.sqlite3` + crate (do not wait on Mixxx flush for plan
eligibility). Phrases still need a Mixxx beatgrid blob (may lag or need a
later re-enrich). **Lyrics typo:** ID3/filename "Many Man (Wish Death)" is
wrong chart title; LRCLIB only hits **Many Men** — `lyrics.title_search_variants`
retries that correction without renaming the file.

Profile presets + free-text brief + order engine → `compose_mix_plan` →
dry-run → **Start mix** (double confirm + Mixxx ping). Endpoints: GET
`/api/mix` (includes `finalized`, `plan_stale`), POST `/api/mix/build`,
POST `/api/mix/start`.

**Order briefs are real now (not just feel keywords).** Example that used
to be ignored: *"mix Parce Que Tu Crois next to What's The Difference in
the first half"*. Flow: NemoClaw or H-agent returns structured
**constraints** (adjacent pairs, region windows, optional `use_only`
subset, optional opener) → local mix-graph greedy tour + forced
adjacency/region placement (`brain/mix_order_brief.py`) → plan events.
Agent never invents tracks; unknown ids are dropped. Provenance stores
`order_engine`, `order_notes`, and the constraint object. Feel keywords
still go through `mix_profiles.apply_brief` in parallel. Empty brief
skips the agent. Agent turns can take 1–7 min (same as Ask the DJ brain).

### Mix profiles (2026-07-12, `brain/mix_profiles.py`)

Architecture decision (Ernest asked "should run_mix_plan be very
configurable?"): **configure the plan BUILDER, keep the plan format and
runner deliberately boring.** The plan stays a declarative event list;
every feel knob lives in a `MixProfile` (ride-phrase pattern, transition
scale, flourish density, intro-entry rate) behind named presets:
`dj-showcase` (default; today's tuned values), `club-set`, `warm-up`.
`build_mix_plan --profile <name> --mix-brief "<free text>"
--order-engine nemoclaw|h-agent|none` — the brief maps onto (1) feel
overrides via keyword pass and (2) order constraints via the chosen
engine. Every adjustment is named in the plan's `profile` provenance
block. Gotcha fixed: negation keywords ("no tricks") must be checked
exclusively before positives ("tricks"). Only knobs validated by real
runs get added — grow one at a time.

### DJ formats (2026-07-24, `brain/dj_formats.py`)

DJ formats are a second, independent planning axis:

- **mix profile** = feel/pacing/performance density;
- **DJ format** = allowed transition grammar and hard phrase rules.

The first format, `hiphop-rnb-8bar`, records advice Ernest obtained from a
practicing hip-hop/R&B DJ. The canonical, human-readable source is
`docs/dj-formats/HIP_HOP_RNB_8_BAR.md`; the typed registry is
`brain/dj_formats.py`. It can be paired with any existing profile in the
`#mix` UI or CLI:

```bash
uv run python -m brain.build_mix_plan \
  --profile club-set \
  --dj-format hiphop-rnb-8bar
```

This format is strict and optional: the default is `--dj-format none`.
Incoming cues and outgoing chorus/hook anchors must
resolve to beat 1 of a four-beat bar, its intro/chorus phrase is 8 bars
(32 beats), and missing evidence raises a build error. `chorus_to_intro`
can use beatgrid + lyric-timeline evidence. `acapella_hook_swap` requires
human `hook_acapella_seconds`; lyrics alone cannot prove “no music.”
`intro_loop_under_entry` jumps the outgoing deck to its verified intro,
engages `beatloop_32_activate`, starts the incoming deck on beat 1, and
hands off over the loop. Format-specific annotations live in persistent
`dj_notes`; the full vocabulary is in the spec.

The separate `hiphop-rnb-guided` format is the practical library-scale
option. It keeps the expert's universal “everything enters on the 1” rule
hard, uses the strict recipe when intro+chorus evidence is actually present,
and otherwise retains a tempo-safe ordinary technique at analyzed downbeats.
Every transition carries `format_compliance=expert_recipe` or
`format_compliance=guided_fallback`; a fallback also records its reason and
is never presented as expert-certified. Its spec is
`docs/dj-formats/HIP_HOP_RNB_GUIDED.md`.

The 2026-07-24 15-track playlist builds in guided mode and dry-runs 47 events
with all 14 transitions honestly labeled as guided fallbacks. Party And
Bullshit initially lacked a persisted beatgrid; loading it and then a second
track through `brain.analyze_via_mixxx --apply`, followed by
`brain.enrich_set`, produced its phrase and beat-phase rows. The strict mode
still correctly stops on Ten Crack Commandments because that album recording
does not have a provable conventional 8-bar incoming intro. CLI structural
failures are now concise `mix plan build stopped: …` messages rather than
tracebacks.

A four-track strict proving set (Who Shot Ya → Give It To Me - Remix → Young
Wild And Free → I Love The Dough) and six exact 32-beat audition clips are
described in `docs/dj-formats/STRICT_PILOT_2026-07-24.md`. The local ignored
playlist is `brain/data/strict_pilot_playlist.json`; clips are under
`brain/data/strict_pilot_auditions/`. The proposed annotations were tested
only in a temporary simulation: they build three 32-beat
`dj_format_chorus_to_intro` transitions and dry-run 14 events. Do not persist
those annotations until Ernest confirms each clip by ear.

When adding another expert recommendation, add another spec under
`docs/dj-formats/` and a separate registry entry. Do not overload the three
mix-feel profiles or weaken an existing strict format with silent fallback.

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

## Key-adjusted blends (2026-07-14, `feat/post-hackathon-direction`)

`brain.build_mix_plan.pick_technique` now turns close-BPM key clashes into
`key_adjusted_blend` when the incoming key can reach a same, relative, or
Camelot-neighbor key with a bounded ±1–2-semitone move. The plan records
`pitch_adjust_semitones` and `pitch_adjust_target`; no key metadata means no
guessed shift and falls back to the filtered `key_clash_blend` recipe.

`hands.run_mix_plan` applies Mixxx `[ChannelN],pitch_adjust` before the
incoming deck starts, holds it through the first half of the overlap, then
smoothly returns to native key as the outgoing deck disappears. Instrument
reset and every deck load zero stale pitch adjustment defensively. Unit tests
cover planner selection, bounded harmonic targets, runner apply/restore, and
rejection of shifts beyond the plan's ±2-semitone safety limit. Audible live
validation is still pending.

Do **not** infer that verse-tour cuts should now use `beatsync_phase`: the tour
was live-validated without sync because phase-pull can move its lyric-aligned
cue. Phase-only alignment remains a separate A/B experiment for ordinary hard
cuts before it becomes planner vocabulary.

## Mix-brief -> dj_notes edits, and set recording (2026-07-15)

A detailed by-hand DJ-craft editing pass on 2026-07-14 (verse landings, cue
timing, reordering — see PROGRESS.md) motivated building the pipeline it had
been standing in for: `brain/mix_directives.py`. Given a free-text brief and
the current finalized track order, it asks an LLM (reusing
`pick_candidates.py`'s engine functions) for structured
`{notes: {id: dj_notes}, reorder: [id,...] | null}` edits, grounding any
brief-mentioned track in its real raw synced lyrics (`lyric_timelines` table)
rather than letting the model guess a timestamp. IDs in the prompt/response
are short synthetic ones (`t000`-style), never real paths — so a hallucinated
or wrong-file-copy path structurally cannot reach the write path. A reorder
must be an exact permutation of the current set or it's rejected outright.
Dry-run by default; `--apply` (or the web UI's "Apply these edits" button)
writes dj_notes into `library.sqlite3` and patches `playlist.json`'s rows in
place directly — **not** a `load_crate()`/`export_playlist()` round trip,
because `crate.json` is only refreshed on scan/analyze/sync and would serve
stale dj_notes back into playlist.json otherwise. Wired into the web UI
(`playlist_editor.py`: `ask_directives`/`apply_directives`, background-thread
pattern matching `ask_brain`; `playlist.html`: "Interpret as DJ notes…"
button right before "Build mix plan", reusing the `#mix-brief` textbox).

Real end-to-end test against the live 28-track set (nemoclaw engine) both
validated the pipeline (correctly grounded a verse-landing ask in actual
lyrics) and demonstrated why the dry-run/confirm step is load-bearing: asked
not to touch one track's BPM, the model added a `play_bpm` directive anyway.
Nothing gets written without a human looking at the diff first — by design,
not as a stopgap.

Separately, `hands/run_mix_plan.py` gained `--record`, toggling Mixxx's
`[Recording]` control group (`toggle_recording`/`status`, confirmed against
the patched fork's `recording/defs_recording.h`) around the plan run inside
a `try/finally`, and never touching a recording that was already running.
Current build has no mp3 encoder (`docs/BUILD_MIXXX.md`'s macOS recipe omits
`-DFFMPEG=ON`), so this records WAV; convert with `ffmpeg` after, or rebuild
with FFMPEG support for native mp3.
