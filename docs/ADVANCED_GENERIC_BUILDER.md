# Measured techniques in generic Build

Build still optimizes the finalized foreground songs, honors their effective
notes and pair overrides, and produces the ordinary plan first. An optional
`advanced_mix.json` in the named plan's directory enables translation onto the
existing native-source performance clock. This is a measured-set mode: every
foreground must have compatible evidence for one common tempo. Arbitrary sets
without this evidence continue using the ordinary planner.

No recipe is invented by an LLM, no original is rewritten and no rendered file
is needed. Invalid, stale or incompatible evidence declines the upgrade and
adds an explanation to the plan's order notes. An authored performance remains
protected from generic Build; a generic-generated performance can be rebuilt.
Manually editing its performance graph or events takes it out of generic
ownership; recompiling that edited timeline does not remove this protection.
The recipe is an input revision, so editing it makes the old artifact stale.

Stage one supports same-song forward skips and backward re-entry on separate
copies, plus short-intro extension. The original foreground identity/order
stays unchanged. Native eased different-song channel-fader envelopes need at
least 24 counts to satisfy the sixteen-count linear peak-speed rule. Four-count
handoffs are restricted to copies of the same recording. Entry/exit overlaps
and invalid backbeat/pattern phase are refused. Intro loops need an observed
first-verse boundary, cannot contain a verse, and allow only two or three plays.

Stage two adds measured sample/source unison. Lineage alone is insufficient:
the sampling record needs `allow_sample_unison` without a conflicting
`no_flourish` note. Its source must be adjacent in the optimized order. The
pair must have backbeat/pitch and <=20 ms alignment evidence across the complete
overlap. Both must enter the measured sampled bar. Native source rate with
keylock off and pitch adjustment zero restores a turntable-slowed sample's
pitch; no guessed tuning is applied. An approved instrumental entry bar can
repeat one to three whole times across the gentle fade. Sample pairs allow
up to +/-16% source-rate correction; other foregrounds retain +/-8%.

Add this to the *sampling record's* source evidence (example numbers only):

```json
"sample_unison": {
  "approved": true,
  "source_track_id": "/absolute/path/to/the-original-sampled-record.wav",
  "sample_start_seconds": 32,
  "source_start_seconds": 0,
  "sample_beats": 16,
  "verified_beats": 32,
  "backbeat_verified": true,
  "alignment_error_ms": 0,
  "residual_pitch_cents": 0,
  "confidence": 0.98,
  "entry_region_instrumental": true
}
```

The pair's cue/exit timing must already match these bar starts; a model cannot
move a trusted cue to manufacture the connection. Structural sample moves
combined with another handoff/intro extension on the same pair require an
authored performance instead. Source guards apply to every sampled-bar repeat.

Stage three adds one continuous instrumental bed under one or consecutive
approved full mixes. It starts with the first foreground's entry, lasts through
the last foreground's exit, and has gentle entry/exit faders. Foreground vocals
stay in their original recordings. Low EQ is reduced on the foreground; the
bed carries bass with reduced mid/high EQ. Raw unity is 1.0. It is neither a
dry-acapella branch nor a short transition-only overlap.

Every supported foreground needs `allow_instrumental_support` in its effective
notes. A conflicting `no_instrumental_support` wins. Add a single request to
the recipe's top-level `support` list:

```json
"support": [{
  "approved": true,
  "foreground_track_ids": ["/absolute/path/to/the-full-mix.wav"],
  "track_id": "/absolute/path/to/instrumental.wav",
  "instrumental_verified": true,
  "backbeat_verified": true,
  "alignment_error_ms": 0,
  "residual_pitch_cents": 0,
  "verified_seconds": 120,
  "source_start_seconds": 0,
  "source_end_seconds": 8,
  "loop_beats": 16,
  "gain_db": -6,
  "bed_eq": [1, 0.25, 0.25],
  "foreground_eq": [0.35, 1, 1],
  "source": {
    "measured": true, "bpm": 120, "zero": 0,
    "confidence": 0.98, "pitch_residual_cents": 0,
    "duration_seconds": 300, "sha256": "REPLACE_WITH_SOURCE_SHA256"
  }
}]
```

Numbers are examples, not measurements. `verified_seconds` must cover the
whole resulting body, including repeated intro/sample bars. The loop must
match the common tempo and pattern phase exactly. Current global plus plan
notes for the instrumental are loaded at build; mandatory min/end/skips bound
its loop too. The instrumental is an independent support source, not another
finalized foreground or a duplicate playlist identity. Multiple supported
foregrounds must be consecutive so one bed covers them continuously; a second
bed, disconnected targets, acapella/full-mix misclassification, inadequate
coverage or missing alignment declines the upgrade.

Use the same **Build mix plan** button (or plan-aware CLI build) after placing
the reviewed recipe in `brain/data/plans/<slug>/advanced_mix.json`. That local
file is intentionally ignored with the rest of personal plan state. The result
shows measured techniques or its decline reason in the browser. There is no
new provider selector or playback side effect. Generic sets without a reviewed
recipe do not automatically gain these moves. Explicit DJ formats, authored
pair overrides and explicit entry/exit/tempo/pitch notes keep conventional
execution rather than silently losing their controls.

Keep the recipe, measurements and songs outside Git. Here is its schema, with
placeholder paths/hashes (replace them with actual recording evidence):

```json
{
  "version": 1,
  "approved": true,
  "tempo_bpm": 120,
  "pattern_beats": 4,
  "sources": {
    "/absolute/path/to/first-song.wav": {
      "measured": true,
      "bpm": 120,
      "zero": 0,
      "confidence": 0.98,
      "pitch_residual_cents": 0,
      "duration_seconds": 300,
      "sha256": "REPLACE_WITH_SOURCE_SHA256"
    },
    "/absolute/path/to/second-song.wav": {
      "measured": true,
      "bpm": 120,
      "zero": 0,
      "confidence": 0.98,
      "pitch_residual_cents": 0,
      "duration_seconds": 300,
      "sha256": "REPLACE_WITH_SOURCE_SHA256",
      "intro_loop": {"start_seconds": 0, "end_seconds": 8, "plays": 2}
    }
  }
}
```

`bpm` and `zero` are the independently measured source tempo and shared pattern
anchor, as in `brain.performance_measure fit` / `brain.performance_author.Grid`.
Do not substitute an arbitrary Mixxx beatgrid zero. Confidence and residual
pitch come from measurement; `approved` records review of the exact recipe,
not an invitation to guess numbers. A source hash binds it to that recording.

For intro extension, effective notes must include `allow_intro_extension` and
`observed_first_verse_start_seconds=<confirmed source seconds>`. The approved
span must cover the full incoming fade, including repeats; a loop too short
to do that declines the upgrade rather than shortening the fade.

For a forward handoff, put `skip_handoff; skip_from_seconds=A;
skip_to_seconds=B` in the effective notes, and add
`"handoff": {"from_seconds": A, "to_seconds": B, "blend_beats": 4}` to that
recording's evidence. Mandatory skips also need `mandatory_skip`; every exposed
source segment is checked against that interval. Backward handoffs use the same
recipe shape with B < A and require `allow_reentry` in the notes. A handoff and
an intro loop on the same foreground currently require a separately authored
performance instead of this automatic translation.

All recordings must have confidence >=0.9, residual pitch within 15 cents and
tempo correction within +/-8%. Explicit opener effects, tempo/pitch holds,
dramatic exits, dry-vocal layers or phase-correction moves retain their ordinary
execution. This compiler does not override them. Each source cue and the common
pattern phase must already agree; it never slides a trusted cue to make a match.

The compiled graph is validated by `shared.performance`: permitted regions,
source loops/skips, pattern phase and up to four independent decks with preload
windows. Playback uses `hands.performance_runner` and its Rust executor: original
source preflight, source guards, 80 ms drift/stop monitoring, and owned-deck/control
cleanup on completion or interruption. Latest global source limits are checked
again at Start. See [native execution](SHARED_PERFORMANCE.md).

Verification uses temporary synthetic files. A passed dry run proves scheduling,
guarding and failure behavior; audible approval still needs a short live
experiment following [the established method](LIVE_MINI_EXPERIMENTS.md).
