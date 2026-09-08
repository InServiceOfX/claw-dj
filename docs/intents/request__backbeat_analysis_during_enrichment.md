# Backbeat analysis during enrichment — 2026-09-04

## Original request

> oh btw, can we do this multiband percussion analysis, section local rhythm detection, and cue-preserving entrance timing when we do an "Analyze tracks", in http://127.0.0.1:8787/#mix with the button, or when? Finalized set
> 36 tracks · 36 with BPM/key · BPM/key ready for plan build
> 32/36 fully enriched · missing bpm/key 0, lyrics 4, chroma 0, phrases 0, beat_phase 0
> ← Back to curate
> Refresh list
> Rescan titles/paths
> Sync from Mixxx
> Analyze & enrich missing

> or when should we do all those implementation adds youj just did?

## Approved recommendation

Analyze & enrich missing prepares reusable per-track multiband percussion
and section-local rhythm evidence. Build reuses it and fills missing/stale
analysis, then computes pair/section/cue-dependent entrances. Playback still
verifies actual positions and rates before/during overlap. No analysis-only
action may build/reorder a mix, move cues, or start playback. Distinguish
cached analysis from confidence and blend readiness in the enrichment UI.

## Approval

> Ok great, you implemented your recommendation already right? if not then go ahead

Scope: existing enrichment workflow, shared rhythm cache, status/UI, tests
and existing backbeat/finalized-set stories. No Rust DSP changes required.
