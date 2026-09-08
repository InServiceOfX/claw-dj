# Implement gradual blend recovery

## Original approval

So should we go ahead with the "next implementation" you mentioned?

## Approved context

Ernest approves implementing the next step described after
`request__gradual_seamless_crossfader_blends.md`: distinguish unavailable or
inconclusive verification from confirmed misalignment while preserving smooth
transitions. The independent story is
`user_stories/story__when_i_blend_tracks_the_crossfader_moves_gradually_and_seamlessly.md`.

## Scoped implementation interpretation

- Keep the planned musical blend duration under inconclusive/weak evidence;
  report it as unverified, never as confirmed backbeat alignment.
- Use repeated muted-entrance observations rather than a single threshold
  sample. Preserve the last timed entrance instead of resetting it solely
  because verification is inconclusive.
- Distinguish sustained measurable mismatch and incompatible rhythm from
  missing/weak observation. For confirmed mismatch use a gradual recovery of
  at most eight beats, never lengthening an already shorter remaining fade.
- Reserve faster emergency completion for actual remaining-audio/transport
  constraints, with explicit reasons. Continue monitoring unverified blends.
- Preserve cues, intentional tempo holds, requested DJ cuts and planned phrase
  lengths. No blanket longer-duration override and no audible beat jumps.
- Share policy between Build predictions and runtime, including old artifacts
  with legacy fallback_beats=2. Report planned/effective/actual fade timing.
- Add independent regressions and update the affected prompt/story/docs.
  Do not control Mixxx, restart a running mix or rewrite the active plan.
