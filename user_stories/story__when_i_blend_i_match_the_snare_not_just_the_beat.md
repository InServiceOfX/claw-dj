<!-- pdd-story-status: drafted-2026-09-03 -->
<!-- pdd-story-areas: onset_analysis, build_mix_plan, run_mix_plan, mix_directives, plan_notes -->
<!-- pdd-story-prompts: prompts/brain/plan_mix_build_Python.prompt -->
<!-- pdd-story-dev-units: plan_mix_build_Python.prompt -->

# User Story: A blend matches the snare, not just the beatgrid

## Story

As a DJ, when two tracks blend I need more than Mixxx **beat-matching**.
The ticks can lock and the mix still feel one count off, because one
track’s kick is sitting on the other track’s snare.

**Beat parity** here means: the snares hit together. In 4/4 that is
usually counts **2 and 4**. Not every record has a snare on both; some
only accent 2, or only 4, or put the backbeat on the other side of the
grid. The rule is still: **match the snare you can hear**, not an assumed
1-2-3-4 on the beatgrid.

If I say a transition is “off by one,” “off by parity,” or “match the
snare,” that is an order to **flip one count on that blend** and rebuild.
Do not report it fixed until the next live listen confirms the snares
lock.

## Acceptance criteria (observable)

1. **Ticks are not enough.** A `smooth_blend` / `sync` that only lines up
   Mixxx `beat_active` edges is incomplete. The planned landing must also
   put each track’s snare (measured backbeat, usually 2 and 4) on the
   same counts.
2. **Measure the snare, do not assume 2 and 4.** Use the cached
   waveform/onset snare phase (`beat_phase.snare_parity`) when confidence
   is usable. If a record only has a snare on 2, or only on 4, match
   *that* hit. Weak/coin-flip snare reads stay on bar-count alignment
   only — they must not drive a one-beat nudge.
3. **The one-count fix is the outgoing ride, ±1 beat.** Flip
   `ride_beats` on the **outgoing** track (308→309 or 308→307). That is
   the same musical ride plus or minus one count. Do **not** move the
   incoming song’s musical cue by one beat to fake a snare lock — that
   changes where the record starts and throws the *next* blend.
4. **Human “fix the snare” overrides a locked ride.** `trust_ride_beats`
   means “do not shorten this song.” It does **not** mean “refuse the
   one-count snare flip I just asked for.” After that ask, the note
   still keeps the body length and records `ride_beats` as the flipped
   count (`trust_ride_beats` remains). Runtime must actually play that
   count; it must not bar-guard the snare flip back.
5. **Ear is the oracle.** Analyzer agreement is not proof. If the live
   mix is still one count off, flip again (or revert a bad cue hack)
   rather than explaining that the math already matched.
6. **Example (heavy-rotation-vol-1, 2026-09-02/03).**
   Chris Brown *Wall to Wall* → Lloyd Banks *On Fire (Feat. 50 Cent)*:
   beats locked, snares did not. An agent moved On Fire’s cue 0.29→0.92
   (one beat later) and kept 308/180. Live listen: still off by one, and
   On Fire → Biggie *Who Shot Ya* was then off by one as well. The fix
   is restore On Fire’s downbeat cue and flip the outgoing counts
   (Wall 308→309, On Fire 180→181).

## Must not

- Do not treat Mixxx beatsync / identical BPM as snare-matched.
- Do not assume every hip-hop/R&B grid has snares on both 2 and 4.
- Do not “fix” parity by sliding the incoming `cue_seconds` one beat
  later when the human certified that cue.
- Do not leave `trust_ride_beats` blocking a requested one-count snare
  flip.
- Do not claim the blend is fixed without a live listen, or after only
  changing prose in the note.

## Source

Ernest, 2026-09-03, hearing heavy-rotation-vol-1 *Wall to Wall* → *On
Fire* and *On Fire* → Biggie *Who Shot Ya*:

> Always try to, for a blend or transition, match beat 'parity': not
> only the beat, but each track's snare hit. Usually 2 and 4 in 4/4,
> but not always — sometimes only 2 or only 4. Match on the snare. If
> the user asks to fix this, then fix it.
