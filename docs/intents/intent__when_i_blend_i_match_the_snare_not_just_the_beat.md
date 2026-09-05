# Intent: A blend matches the snare, not just Mixxx beat ticks

<!-- pdd-intent-id: when-i-blend-i-match-the-snare-not-just-the-beat -->

## Record

- Kind: `add`
- Scope: mix planner + Mixxx runner
- Story: `user_stories/story__when_i_blend_i_match_the_snare_not_just_the_beat.md`

## Original Request

> Always try to, for a blend or transition, match beat 'parity': not only
> the beat, but each track's snare hit. Usually 2 and 4 in 4/4, but not
> always — sometimes only 2 or only 4. Match on the snare. If the user
> asks to fix this, then fix it. Enforce it in the planner and runner,
> not only a user story. Wall to Wall → On Fire kept coming back off by
> one count after cue slides and ride_beats ±1.

## Must Stay Unchanged

- Do not slide a certified incoming `cue_seconds` one beat later to fake
  snare lock.
- `trust_ride_beats` remains a how-long lock.

## Product rule

After Mixxx `beatsync`, `snare_align` jumps the incoming deck one beat.
Incoming dj_notes may set `snare_align`. High-confidence snare-phase
mismatch may add it automatically. Weak snare reads must not.
