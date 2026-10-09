# Plan reproducibility: `50-cent-g-unit-tribute-vol-1` (2026-09-05)

Read-only review of the plan directory
`brain/data/plans/50-cent-g-unit-tribute-vol-1/` against the code changes
made since the plan was created. Nothing in the plan, the library, the
running mix or the code was modified for this review. Every fact below was
checked on disk on 2026-09-05 between 10:30 and 10:50 PDT while Ernest was
listening to this exact plan.

Purpose: the current `mix_plan.json` was built with **August 28 code** and
is being **played with September 4-5 code**. A rebuild today will not
reproduce it. This document records what the artifact is, what changed, and
what a faithful re-creation would require.

## 1. What the plan directory actually is

| Fact | Value |
|---|---|
| Plan id / slug | `c1ed2d11-1fcd-40a5-b110-b2763b872dc0` / `50-cent-g-unit-tribute-vol-1` |
| Origin | `duplicated` from `50centgunitera` (`b8f08507-2610-4209-9eba-16ca1e5d3a94`) on 2026-08-30 19:48 PDT |
| Origin plan status now | `archived` (set 2026-08-30 19:55) |
| Active plan (`plans/active.json`) | this plan, switched 2026-09-05 10:28:55 |
| `mix_plan.json` | **byte-identical copy of the origin's artifact** (SHA-256 `dff2203eee4f13e559b9b336ca9ac4f52d613629e528028f9856202328b72a86`, 719,808 bytes, mtime 2026-08-29 08:15:56) |
| Artifact stamps | still `plan_id b8f08507…` and `plan_slug 50centgunitera`; a rebuild restamps both |
| Journal | only six `open_plan` entries; the duplicate has **never been built** |

`notes.json`, `transitions.json`, `bunches.json`, `playlist.json`,
`playlist.m3u8` and `runtime.json` are identical to the origin plan.
`selection.json` and `exclusions.json` differ (see §3).

### The artifact's content

| Field | Value |
|---|---|
| version | 3 |
| tracks / segments / events | 147 / 146 / 438 |
| profile | `dj-showcase`, `order_engine: h-agent`, brief “corrected era and sampling-lineage order” |
| dj_format | `hiphop-rnb-guided` v1 (experimental, `enforcement: guided`) |
| transition techniques | smooth_blend 96, standard_blend 15, key_adjusted_blend 10, key_clash_blend 6, tempo_gap_blend 6, vocal_over_bed 5, verse_landing_blend 5, half_time_or_cut 2, echo_out_exit 1 |
| format recipe | `phrase_aligned_fallback` / `guided_fallback` on 141 of 146 transitions |
| moves | sync 137, crossfade 138, eq_dip_out_mid 116, filter_sweep_out 27, key_blend 10, censor_fill 10, stutter_fill 7, rate_nudge_in 6, vocal_over_bed 5, brake_out 2, hard_cut 2, echo_out_exit 1. **No `snare_align` moves.** |
| bodies | 141 `play_body` events carry `phase_anchor`; 44 carry `trust_ride_beats` |
| cue sources | guided_phrase_intro_downbeat 99, guided_human_downbeat 40, guided_human_landing_downbeat 5, guided_analyzed_downbeat+sanitized 2, dj_notes 1 |
| transition overrides | 8 authored events (6 agent, 2 human); one stored override (Back Down → This Is 50) is `orphaned` |
| bunches honored | 9 active ordered bunches (a tenth, Bump Heads ↔ Back Down, is disabled) |
| no `backbeat` key | this is a **legacy artifact** for the current runner |

Source revisions recorded inside the artifact match the origin plan's
journal exactly at its last `build_mix` (2026-08-28 19:06:31). The later
08:15 write on Aug 29 left content that still matches those inputs; no
journal entry explains that write.

### Where the DJ knowledge lives

All 56 note overrides in `notes.json` were written against an **empty**
library note (`global_note_at_override: ""`). A read-only query of the
Elements library confirmed `tracks.dj_notes` is empty for all 149 tracks
involved, so the plan overlay is the only copy of these notes. Directive
tokens present in the overlay: `trust_ride_beats` 56, `ride_beats` 110,
`cue_seconds` 88, `play_bpm` 36, `landing_*` 27, one `skip_from/to_seconds`
pair (G.O.D. Pt. III), one `skip_after`. None mention `snare_align`.

Library analysis rows exist for 148 of the 149 tracks in `phrases`,
`beat_phase`, `lyrics` and `chroma`.

## 2. Code then versus code now

| | Build on 2026-08-28 19:06 | Playback/build today |
|---|---|---|
| HEAD | `14a80a2` (master; branch `feat/50cent-era-arc-ear-pass` pointed at the same commit) | `9b9ead4` on `feat/snare-align-blends` |
| committed since | — | 5 commits (Sep 2-4): plan-note skip carry-over, Who Shot Ya docs, GUI 503 on unmounted collection, snare-align docs, `snare_align` move in build + runner |
| uncommitted | unknown at build time | 28 modified files (+1357/−161) and 28 untracked files: `brain/rhythm.py`, `hands/backbeat.py`, `brain/backbeat_audit.py`, `core-rust/clawdj/src/rhythm.rs`, tests, intents, stories, docs |
| untouched since 14a80a2 | | `brain/mix_profiles.py`, `brain/dj_formats.py`, `brain/onset_analysis.py`, `brain/stems.py`, `brain/verse.py` |

Any uncommitted edits present on Aug 28 evening cannot be recovered; the
Sep 2 commits were authored after the build.

## 3. Inputs have drifted from the artifact

`brain.plan_staleness.is_stale` reports `stale: true, changed_inputs:
["selection"]`. Only the selection changed; playlist, notes, bunches and
transitions still match the artifact.

- Origin selection: 147 tracks. Duplicate selection: **116 tracks**
  (re-saved 2026-08-30 20:11 and again 2026-09-05 10:29:18 while the mix
  was already running). Exclusions grew from 27 to 59.
- Removed from the selection: 33 tracks, mostly the Curtis era, the You
  Don't Know / Still Kill / Get Up / Baby By Me / Crack A Bottle / Jimmy
  Crack Corn stems, N.W.A → Straight Outta Southside, T.O.S., South Side
  Story, If You So Gangsta, Psycho.
- Added: *Don't Stop 50's Music* and *Part 2 & Bump Heads* (neither is in
  the artifact).
- Relative order of the shared tracks is preserved.
- **`playlist.json` still holds the 147 finalized tracks.** `plan_mix_build.build`
  reads the playlist, not the selection, so a Build without a fresh
  *Finalize for Mixxx* would still compose 147 tracks and ignore the 33
  exclusions.

## 4. Playing the old artifact with the new runner (what Ernest hears now)

A live run started 2026-09-05 10:28:06 PDT (`hands.run_mix_plan --plan
…/50-cent-g-unit-tribute-vol-1/mix_plan.json`, Mixxx control on 9995,
editor on 8787). The new runner treats this plan as legacy and prints
`Backbeat: legacy artifact; rebuild to enable measured entrances.`
Differences versus the Aug 28 runner:

- No measured entrance path: every transition takes the old anchor-wait →
  play → beatsync path because no event carries `backbeat` metadata.
  Crossfade duration is `blend_seconds(planned, bpm, remaining=None)`,
  i.e. the planned beats unchanged. No `brain/data/runs/backbeat-*.jsonl`
  is written for this run.
- `reset_instrument` now also sets `sync_enabled=0` on each deck at start.
- `hands/transition.wait_for_beats`: trusted bodies now read the grid beat
  index at the first counted beat and log “trusted body: observed grid beat
  N; keeping ride duration”. Ride length is unchanged; one extra control
  read happens per trusted body.
- New log lines: “crossfade: planned N beats … scheduled …” and
  “crossfade landed … executed (planned N beats)”.
- The legacy `snare_align` runner path (wait one beat, quantize off, jump)
  does not fire: the artifact has no such moves.
- `scripts/run_mix.sh` now `exec`s the runner and prints a backbeat
  summary only when the artifact has one (it does not here).

The Sep 2 `carry_library_skips` change has no effect on this plan because
the library notes are empty.

## 5. What a rebuild today would change

Assume *Finalize → Analyze & enrich missing → Build* on this plan.

1. **Phrase cues.** Build reads phrase data only from
   `brain/data/phrase_analysis.json` (`load_phrase_lookup`). That file is
   rewritten by every *Analyze & enrich* to contain only the set just
   enriched; on 2026-09-05 02:25 it was left as `{"tracks": []}`. A Build
   without a fresh Analyze on **this** plan's finalized set would find no
   phrase data, and the 99 `guided_phrase_intro_downbeat` cues plus the 2
   analyzed cues would fall back. Running Analyze first re-exports the 148
   existing `phrases` rows; the 45 human cues come from the overlay notes
   and are unaffected.
2. **Backbeat preparation.** `compose_mix_plan`/`plan_mix_build.build` now
   run `brain.rhythm.prepare_plan` on the final events: adds per-transition
   and per-segment `backbeat` metadata, a top-level `backbeat` summary,
   `source_grid` and `cue_seconds_requested` on tracks. Needs
   `core-rust/target/release/clawdj` (present, built 2026-09-05 02:20) and
   `ffmpeg` on PATH (present). Analysis failures are recorded, not fatal.
   The artifact grows roughly 50× (heavy-rotation: 105 KB → 5.6 MB).
3. **Parity nudges disabled.** Normal compositions now pass
   `legacy_parity=False`, so untrusted bodies no longer get
   `count_shift_beats` ride adjustments and no `snare_align` moves are
   emitted. The Aug 28 build could have nudged ride lengths by a beat or
   two on any of the ~97 untrusted bodies; the artifact does not mark
   which ones, so this is not recoverable from the file.
4. **Ordering.** The artifact's order came from the H Company agent with a
   non-empty brief; that call is external and not deterministic. A rebuild
   with an empty brief uses `order_engine none`; the GUI default with a
   brief is `nemoclaw`. The achieved order is recorded in the artifact's
   `profile.order_constraints` (opener `t130` = The Good Die Young, plus
   146 adjacent pairs) and `profile.order_notes`, and the 9 active bunches
   are unchanged in `bunches.json`.
5. **Identity.** `plan_id`/`plan_slug` are restamped to the duplicate.
6. Gradual-v3 policy, fade-envelope and verification live in the runner and
   apply to any prepared artifact; they do not change planned beat counts.

`hiphop-rnb-guided` v1 and `dj-showcase` are unchanged, so format recipes
and profile scaling would match.

## 6. Safety notes for this plan

- **A GUI Build on a named plan does not archive the previous artifact.**
  The archive-before-rebuild branch in `playlist_editor.start_build` only
  runs for the legacy unnamed layout (`chosen_slug is None`);
  `plan_mix_build.build` overwrites `mix_plan.json` in place via
  `write_checked`. `brain/data/archives/` has nothing newer than Jul 31.
  Copy the artifact (or the whole plan directory) before any rebuild.
- `brain.rhythm prepare --plan …` rewrites the artifact in place but does
  keep a copy under the plan's `backups/`. It would add backbeat metadata
  to this artifact without reordering; it is not required to keep playing
  it.
- The GUI refuses Build while a live mix is running.
- Do not edit `hands/`, `brain/rhythm.py` or `scripts/run_mix.sh` while
  the listen is in progress (existing house rule).
- The origin plan `50centgunitera` still holds an identical artifact and
  the original 147-track selection; it is the cleanest fallback copy.

## 7. Reproduction options

- **Keep the sound Ernest is hearing now:** keep playing the existing
  `mix_plan.json` with an explicit `--plan`, and never rebuild in place.
  Take a copy first.
- **Rebuild the same 147 tracks with today's code:** Analyze & enrich this
  plan's finalized set first (restores phrase cues), keep profile
  `dj-showcase`, format `hiphop-rnb-guided`, and expect different body
  lengths (no parity nudges), a different order unless the recorded
  adjacent chain is re-imposed, plus backbeat metadata. Compare cue and
  beat counts against the old artifact before promoting it, as was done
  for heavy-rotation on 2026-09-05.
- **Build the edited 116-track version:** Finalize (rewrites the
  playlist from the current selection and exclusions), Analyze & enrich,
  Build. This is a new mix, not a reproduction.
- **Bit-exact reproduction of the old build** is not possible: it depends
  on `14a80a2` plus unknown uncommitted edits, an Aug 28 phrase export
  that has been overwritten, and a non-deterministic external ordering
  call.

## 8. Apples-to-apples test of the new code on this mix

What Ernest hears on 2026-09-05 is the **old plan on the new runner**, and
for a legacy artifact the runner changes almost nothing (§4). To hear the
backbeat and gradual-v3 changes on the *same* tracks, order, cues, bodies
and fade lengths, prepare a copy rather than rebuilding:

```sh
# after the current run ends (never during a listen)
PLAN=brain/data/plans/50-cent-g-unit-tribute-vol-1
mkdir -p "$PLAN/candidates"
cp "$PLAN/mix_plan.json" "$PLAN/candidates/backbeat-prepared-2026-09-05.json"
.venv/bin/python -m brain.rhythm prepare --plan "$PLAN/candidates/backbeat-prepared-2026-09-05.json"
./scripts/run_mix.sh --plan "$PLAN/candidates/backbeat-prepared-2026-09-05.json"   # add --record to keep audio
```

`prepare` keeps tracks, order, cues, bodies and planned fades; it adds
measured cue-preserving entrances, live verification and a run log under
`brain/data/runs/`. It analyzes source audio with the Rust binary and
FFmpeg (CPU-heavy on 147 tracks; do it while nothing is playing). The
default `mix_plan.json` stays frozen, so the two runs are directly
comparable pair by pair. Six tracks without a `phase_anchor` in the old
artifact will report missing grids and simply keep their planned fade.

Record verdicts per transition in
[LISTENING_LOG_50_CENT_G_UNIT_TRIBUTE_VOL_1_2026-09-05.md](LISTENING_LOG_50_CENT_G_UNIT_TRIBUTE_VOL_1_2026-09-05.md).

## Related

- `docs/BACKBEAT_MATCHING.md` — what `prepare_plan` and the measured path do.
- `docs/HANDOFF.md` — gradual-v3 and the heavy-rotation candidate workflow
  that kept cues/bodies fixed while re-preparing an artifact.
- `docs/intents/request__zero_automatic_short_handoffs.md` — policy that
  now governs every fade, including this legacy artifact.
