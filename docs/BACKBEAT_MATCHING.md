# Backbeat matching

Backbeat is the snare/clap accent Ernest previously called “the snare” or
“beat back,” usually on 2 and 4 in 4/4. It is not the same thing as a
downbeat (1), a generic beatgrid tick, or a phrase boundary.

## What runs automatically

The work is split across the normal workflow:

1. **Analyze & enrich missing** prepares reusable multiband percussion and
   section-local rhythm evidence for the finalized tracks, after phrases
   provide source beatgrids. This new step uses local audio, not Mixxx deck
   control. The existing BPM/grid step may still need a muted Mixxx deck.
2. **Build mix plan** reuses that evidence, or fills missing/stale cache
   entries if Analyze was skipped. After final order, cues and transition
   overrides, it computes pair-specific, cue-preserving entrance timing.
   This applies to Club set, Mix to listen and every DJ format.
3. **Playback** solves again from actual source positions/rates and verifies
   the muted entrance and continuing overlap. Build predictions alone are
   not proof of live alignment.

No extra note is required. Old `snare_align=±1` notes remain in the notes/history, but new
builds do not emit their blind jumps or parity-based ride nudges.

- Rust decodes through local FFmpeg, computes spectral flux in five bands,
  suppresses hat-only evidence, normalizes locally, and retains individual
  transient timestamps. Overlapping 32-beat windows estimate cadence,
  microtiming, coverage and agreement; they are not instrument probabilities.
- Rust solves a positive launch delay from both source positions and actual
  rates, preserving the incoming cue. It checks one dominant hit per cycle,
  coverage and section consistency across the intended overlap. Compatible
  independently verified downbeats additionally constrain bar phase.
- Python owns the existing Mixxx connection. Incoming audio remains muted
  during launch verification; tempo-only sync does not resnap beat phase.
  The runner uses `file_bpm`, `rate_ratio`, duration and playposition, rejects
  stale audio/changed tempo grids, and checks positions before the fade and
  every half second during it. It does not jump the audible deck or snap
  the incoming deck to a nominal landing afterward.
- **Weak, missing, noisy or lost evidence keeps the planned gradual blend**,
  explicitly unverified. This includes filter-sweep/key-clash blends. A short
  muted observation window handles noisy reads; an inconclusive result keeps
  the last timed entrance rather than restarting at an arbitrary beat.
- Confirmed mismatch (coherent repeated timing errors or confident rhythm
  incompatibility) is reported honestly but **also keeps the planned fade**.
  Default to zero automatic evidence-triggered short handoffs per mix, not a
  quota of one to spend. Real exhausted/stopped outgoing audio is a physical
  limit; sudden stopped/near-EOF readings require corroboration before
  shortening. One stale read cannot slam the fader. A gradual fade with a
  mismatch warning is not a claim that the rhythmic clash is resolved.
- Logs report planned and executed duration, verification and exception
  reasons. Intentional DJ cuts stay intentional. Settings are restored,
  including on interruption. Trusted rides still allow phase observation.

This gradual-v3 policy corrects an audible regression: the previous blanket
two-beat fallback destroyed ordinary blends when analysis was uncertain.
Existing two-/eight-beat fallback metadata no longer controls live fades.
Native half/double-time BPMs alone do not prove incompatible backbeats.

Evidence claims remain conservative. Repeating rhythms, drumless intros,
busy vocals, unusual drums, dynamic grids, half/double-time interpretations
and highly syncopated sections can remain unresolved. A missing drum hit is
not filled with an invented timestamp. Source clips longer than 30 minutes
are analyzed only through minute 30; later sections cannot be certified.

## Build and try

September5 listening follow-up: a weak entrance can now use repeated reliable
hits later **inside the planned overlap** to select the correct alternating
count, while remaining explicitly unverified. No confidence threshold was
lowered and no fade is shortened. Source positions are solved afresh; there
is no unconditional one-beat correction. Ja→Jealous's recorded-position replay
improves from about619ms to22ms median residual, but other reported pairs still
need review. Current checked candidate and exact command are in
[HANDOFF.md](HANDOFF.md); it includes Jadakiss after K.Dot and preserves existing
cues/body lengths. See [the evidence review](OVERLAP_PARITY_REVIEW_2026-09-05.md).

One-time/current Rust build (FFmpeg must be on PATH):

```sh
cd core-rust
cargo build --release
cd ..
```

Then use **Analyze & enrich missing → Build mix plan → Start mix**. The
finalized-set status shows how many tracks have cached backbeat analysis,
how many are missing/stale, and how many contain uncertain sections. A track
can be fully analyzed but still need live verification in a particular blend.
Uncertain sections do not cause repeated analysis on every click. Legacy
`beat_phase` is reported separately and does not count as this new cache.
Status refreshes only inspect cache references, file metadata and tool/marker
identity; they never hash/decode audio or run DSP. Build additionally verifies
the full audio content hash before cache reuse.

For the gradual-fade correction alone, an existing prepared plan does **not**
need rebuilding or re-analysis. Stop the old CLI with Ctrl-C when ready, then
run `./scripts/run_mix.sh` (optionally `--record`). Look for
`Crossfade policy: gradual-v3`. A running Python process retains the old code;
editing files does not repair its remaining transitions. The implementation
did not stop/restart the user's mix or change the current plan/cues.

Restart an already-running
playlist editor after updating Python code; merely refreshing the browser
does not reload server modules. `scripts/stop.sh` stops only the editor,
then `scripts/start.sh` reuses an available Mixxx instance.

For just the new local rhythm step with existing phrase grids (no Mixxx
control or lyric fetch), the CLI also supports:

```sh
.venv/bin/python -m brain.enrich_set \
  --playlist brain/data/plans/heavy-rotation-vol-1/playlist.json \
  --skip-bpm --skip-lyrics --skip-chroma --skip-phrases \
  --skip-timelines --skip-beat-phase
```

`--skip-backbeat` explicitly opts out of this enrichment step; Build still
prepares missing rhythm evidence. Missing grids/decoders remain reported gaps.

To prepare an existing artifact **without reordering or recomposing it**:

```sh
.venv/bin/python -m brain.rhythm prepare \
  --plan brain/data/plans/heavy-rotation-vol-1/mix_plan.json
```

This retains a unique backup under the plan's `backups/`, then performs a
revision-checked atomic write. Tracks, cues, bodies and tempo directives
remain intact; alignment metadata and superseded legacy moves change.

Old cached preview timing from fade policies v1/v2 is rejected on re-render: run
the preparation command above first if you want updated source previews.
This is separate from loading the live runtime fix. Historical rendered audio
also remains old until regenerated. Preview timings are nominal predictions,
not a guarantee that live observations/transport delays will match.

Render opening previews and inspect every transition's timing/status:

```sh
.venv/bin/python -m brain.backbeat_audit \
  --plan brain/data/plans/heavy-rotation-vol-1/mix_plan.json \
  --out-dir brain/data/previews/heavy-rotation-vol-1-backbeat \
  --render-limit 3
open brain/data/previews/heavy-rotation-vol-1-backbeat/index.html
./scripts/run_mix.sh --record
```

The current September 4 artifact has 36 tracks / 110 events / 35 transitions:
7 predicted-ready, 26 needing verification, 2 non-applicable recipes. Those
26 are **not** automatic short handoffs under gradual-v3. The first two
transitions are ready: Wall → On Fire median/p90 hit error approximately
5/21 ms, and On Fire → Biggie approximately 5/26 ms. Certified cues remain
0.4763 / 0.2922 / 0.4232 seconds. These numbers describe predicted source
audio timing, **not a successful live listening test**. Stunt 101
(Instrumental) lacks a source grid in this older artifact; new compositions
retain grids even for deliberately off-grid cues.

## Reviewed and independent evidence

Caches live in ignored `brain/data/rhythm/`, keyed by audio SHA-256,
size/mtime, BPM/first beat, analyzer source and binary, and annotations.
Editing audio, the grid or annotations invalidates matching cache entries on
the next Analyze or Build. Old Build caches are reusable: the first Analyze
adds lightweight status references without repeating the DSP.

A reviewed backbeat timestamp is the **actual audible hit in source audio**,
not a correction direction. Specify a region over which its cadence holds:

```sh
.venv/bin/python -m brain.rhythm annotate /path/to/song.mp3 \
  --start 0 --end 32 --backbeat 0.5 --cadence 2 --author ernest
```

Use the song's real timestamps, not these illustrative numbers. `--downbeat`
optionally records a reviewed musical-1 timestamp; omit it when unknown.
Markers do not move the cue and do not bypass the overlap's actual-hit check.
Rebuild after changing evidence.

An optional independent [Beat This! backend](https://github.com/CPJKU/beat_this)
can add beat/downbeat evidence using an **explicit existing local checkpoint**:

```sh
.venv/bin/python -m brain.rhythm model /path/to/song.mp3 \
  --checkpoint /path/to/local-checkpoint.ckpt
```

Install the upstream project's supported environment separately if needed;
it is not part of the default dependency set and was not installed or
benchmarked for this implementation. This command never intentionally
downloads a checkpoint. Model beat-grid disagreement lowers confidence;
repeated consistent downbeats can supply local bar phase. Generic beats are
never treated as snare timestamps.

An independent drum transcription or human-curated onset list can be imported:

```sh
.venv/bin/python -m brain.rhythm import-drums /path/to/song.mp3 \
  --evidence /path/to/snare-onsets.json --source 'model/checkpoint or reviewer'
```

JSON format:

```json
{"instrument":"snare","onsets":[{"seconds":0.5,"strength":1.0}]}
```

Supply the complete relevant onset sequence, not just this one-hit example.
Rust refits sections from those hits. Provenance is retained. No separation
or transcription model is silently chosen/downloaded; check a model's
license and its performance on the actual electronic/hip-hop drums first.

## Evidence and tests

Live runs write `brain/data/runs/backbeat-*.jsonl`: source IDs, entrance
decisions, timed positions/rates, signed errors, verification and fallback
events. Add `--telemetry PATH` to the audit command for a position-log summary.
The report separates prediction from observed transport timing. A recorder
or a live ear pass is still required for audible acceptance; the detector is
not a real-time microphone/snare recognizer.

`tests/test_backbeat.py` uses the real Rust solver with a simulated transport:
three-track chains, variable delays, pre-fader gating, cue preservation,
lost confidence, drift, stale grids, high latency, timeouts, restored controls,
cache/annotation invalidation and trusted-body observation. Rust tests include
synthetic PCM with loud hats/kicks/snare, silence, half-time, beat-2 vs beat-4,
microtiming, ghost hits and reviewed bar phase. Tests never start Mixxx.
`tests/test_backbeat_enrichment.py` covers the Analyze/Build cache boundary,
stale and corrupt caches, uncertain-but-analyzed status, read-only polling,
same-run phrase enrichment, offline operation and reported analyzer failures.
