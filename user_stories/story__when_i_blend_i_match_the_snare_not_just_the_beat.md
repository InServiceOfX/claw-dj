<!-- pdd-story-status: amended-from-approved-intent-2026-09-04 -->
<!-- pdd-story-areas: rhythm, backbeat, build_mix_plan, run_mix_plan, mix_directives, plan_notes -->
<!-- pdd-story-prompts: prompts/brain/plan_mix_build_Python.prompt -->
<!-- pdd-story-dev-units: plan_mix_build_Python.prompt -->

# User Story: Every built mix aligns the backbeat from its first transition

## Story

As a DJ, when I build Club set, Mix to listen, or an expert DJ format,
I want overlapping tracks to match their audible backbeats from the first
transition and through the whole set, while preserving the intended cues,
verses, musical phrasing, and groove.

**Backbeat** is what Ernest has been calling the **snare** or **clap**:
the rhythmic accents often on counts **2 and 4** in 4/4. Continue to accept
"match the snare/clap", "off by one", and "beat parity" as descriptions of
this goal, and gently use the term backbeat in responses and the UI.
Beatmatching, backbeat alignment, downbeat alignment (beat 1), and phrase
matching are distinct. A grid's first tick is not automatically musical 1.

Feedback that a blend is off calls for diagnosis and measured correction,
not an unconditional one-beat flip. The ear remains the final acceptance
oracle; analyzer agreement or a successful control write is not audible proof.

## Acceptance criteria (observable)

1. **Analyze prepares tracks; Build prepares alignment.** Analyze & enrich
   missing performs Rust multiband percussion and section-local rhythm
   analysis once per current source/grid/analyzer/annotation identity for the
   finalized set. The status distinguishes cached analysis, missing/stale
   inputs, and tracks with uncertain sections; legacy `beat_phase` is not
   proof of new analysis. Status polling performs no audio decoding or DSP.
   GUI and CLI builds reuse that cache, fill missing/stale evidence if Analyze
   was skipped, and include local rhythm
   evidence and a backbeat decision for every transition, independent of
   profile, format, ordering engine, or legacy snare notes. Missing or weak
   evidence is visible in the build summary. Pair/section/cue-specific entrance
   decisions belong to Build; actual-position/rate verification belongs to
   playback. Cached uncertain sections are not repeatedly analyzed or called
   ready blends. Analyzing rhythm and building never start playback.
2. **Measure the actual sections.** Retain individual transient timestamps,
   cadence, timing offsets, section bounds, confidence, and provenance.
   Distinguish 2-and-4, one accent per bar, half-time, fills, missing drums,
   and ambiguous patterns. A high-frequency transient alone is not proof
   of a snare. Cache identity includes audio, grid, analyzer, and annotations.
3. **Preserve cues and choose the entrance.** Use actual source positions
   and playback rates to choose a matching launch moment. Complete alignment
   checks before opening the fader. Never jump the audible outgoing deck as
   an automatic backbeat correction. An already-aligned pair needs no flip.
4. **Maintain the relationship.** Observe both decks during the overlap.
   Preload delay, rate settling, end-of-track clamps, prior transitions,
   beat jumps, and trusted ride lengths must not invalidate the next entrance.
   Separate a trusted duration from measuring live phase. Lost confidence
   does not prove drift: retain the planned gradual fade. Repeated coherent
   mismatch is reported honestly but also retains the planned fade: zero
   automatic evidence-triggered short handoffs per mix. Corroborated real
   remaining audio may still limit duration. Restore temporary deck
   settings afterward; do not repeatedly restart recovery or rush to an edge.
5. **Represent uncertainty honestly.** Low-confidence sections use an
   explicit unverified best-effort blend at the planned duration, without
   declaring the backbeats matched. Never default to a two-beat handoff for
   weak/missing evidence. Reviewed
   source-time backbeat/downbeat markers can resolve an ambiguous section
   and be reused with other neighboring songs. Do not silently assume 1.
6. **Verify audio and the complete chain.** Provide listenable previews,
   onset comparisons, and live position/error logs. Test controlled audio
   with known drum timing and repeated three-track execution under different
   preload delays. Record predicted, position-verified, and ear-verified
   evidence separately. A live listen is required before claiming the
   original audible complaint is resolved.
7. **Opening regression.** Wall to Wall → On Fire → Who Shot Ya preserves
   the certified cues near 0.4763 / 0.2922 / 0.4232 seconds. Check both
   transitions as one sequence. Historical `snare_align=±1` notes remain
   inspectable but must not add blind jumps to the new measured entrance.
8. **Position agreement is not percussion identification.** Ernest's
   September 5 On Fire → Who Shot Ya listen reports a one-count error despite
   “positions verified (−41 ms median).” This is a failed audible acceptance
   case, not disproved by the log. Check candidate-hit identity in the actual
   exit/entry sections and launch timing before correcting. Distinguish
   unavailable measurements from incomplete observation windows or
   inconsistent samples. Preserve the improved 32-beat gradual fade.
9. **No grid gaps hidden by preserved cues.** Stunt 101 → Stunt 101
   (Instrumental) → Part 2 & Bump Heads was reported one count off at both
   entrances while the older artifact lacked the instrumental's source grid.
   Preserve the requested 139.27s cue separately from its measured grid.
   Repair missing evidence before considering a different neighbor; maintain
   the requested 32-/24-beat fades and validate both transitions as a chain.
10. **Do not discard usable parity at a weak entrance.** Put It On Me →
    Jealous retained32 beats yet selected the wrong alternating count when
    its first outgoing window was weak. Reliable backbeats later INSIDE the
    actual overlap may time the entrance, with at least three corresponding
    hits and no contradictory confident selected window. Account for outgoing
    audio during the launch wait. Keep the uncertain entrance explicitly
    unverified, name the limited evidence window, preserve the cue/full fade,
    and recompute from variable live anchors rather than blindly adding one
    beat. No evidence outside the blend may certify it.
11. **Remaining listening failures stay open.** Superwoman pt.2 → Heartbeat
    (Club), Caught Up → Fastlove, and the earlier On Fire → Biggie complaint
    require their own percussion/section checks; one corrected pair does not
    close them. Preserve32/24/32-beat fades respectively, including Fastlove's
    deliberate −2-semitone key bridge.

## Must not

- Do not equate identical BPM, generic grid ticks, or heuristic confidence
  with matched audible backbeats.
- Do not force every song into alternating 2-and-4 or infer downbeat from
  file start. Preserve intentional swing/late hits; reject incompatible grooves.
- Do not change a certified cue, rewrite human markers, or apply blind jumps.
- Do not reuse stale or distant-section evidence as though it were current.
- Do not claim live or ear verification from synthetic tests or previews.

## Source

Amended 2026-09-04 from Ernest's explicit approval to implement all four
recommendations, prefer Rust, accept "snare/clap" as backbeat terminology,
and enforce matching from Build in Club set and Mix to listen. Request:
`docs/intents/request__backbeat_matching_from_build.md`.
This supersedes the earlier one-beat-flip implementation prescriptions.
Amended again from `docs/intents/request__backbeat_analysis_during_enrichment.md`:
Ernest approved connecting this reusable analysis to Analyze & enrich missing,
retaining Build's safety net and live verification.
Corrected from `docs/intents/request__implement_gradual_blend_recovery.md`:
smooth transfer and backbeat matching are separate acceptance requirements.
The blanket short-handoff policy was an audible regression and is superseded
by the [gradual-blend story](story__when_i_blend_tracks_the_crossfader_moves_gradually_and_seamlessly.md).
`docs/intents/request__zero_automatic_short_handoffs.md` further rejects
automatic shortening even for measured mismatch; keep measuring and report it,
but do not break the mix's continuity to hide an alignment problem.

Ernest, 2026-09-03, hearing heavy-rotation-vol-1 *Wall to Wall* → *On
Fire* and *On Fire* → Biggie *Who Shot Ya*:

> Always try to, for a blend or transition, match beat 'parity': not
> only the beat, but each track's snare hit. Usually 2 and 4 in 4/4,
> but not always — sometimes only 2 or only 4. Match on the snare. If
> the user asks to fix this, then fix it.
