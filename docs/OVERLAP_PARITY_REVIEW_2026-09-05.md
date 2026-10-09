# Listening review: weak entrance must not discard backbeat parity

Source: [Put It On Me → Jealous request](intents/request__jealous_backbeat_parity.md).
Related: [Stunt101 chain](intents/request__stunt_101_backbeat_repair.md),
[Who Shot Ya notes/skit](WHO_SHOT_YA_LISTENING_REVIEW_2026-09-05.md),
[Jadakiss next-build order](intents/request__jadakiss_who_shot_ya_next_to_k_dot.md).

## Measured failure and correction

Run `backbeat-20260905T081628Z-d4dd0515.jsonl`, event61:

- Ja Rule source81.390827s, Jealous cue43.4793s, rates1/1.00199245.
- Ja's entrance section confidence0.4017 was below0.45; Jealous's was0.9157.
  The old solver returned a one-grid-beat cycle0.643878s and delay0.510574s,
  discarding their alternating accent relationship.
- The last nine overlap observations measured607–619ms, median619.141ms.
  Executed32.0022beats/20.6055s, without shortening. This supports the
  listener's full-count report, independently of fade duration.
- New Rust solver finds three corresponding hits in the last4.1852seconds
  of the intended overlap (starting16.4189seconds after entrance). Their
  median/p90 source-hit errors are6.203/8.893ms. It computes delay1.152042s,
  retaining a two-count cycle1.287757s so a late control read cannot turn
  the retry onto the opposite count.
- Counterfactual replay of recorded positions with that changed entrance
  yields ten numeric observations, median−22.392ms, maximum absolute33.982ms.
  This is a replay, NOT a new live recording or audible acceptance.

The initial synthetic passing implementation did not correct this real case:
it forgot outgoing audio advancing during the grid wait, leaving fewer than
three usable hits in its search. Corrected before handoff and covered by a
narrow-suffix regression. The independent reviewer also found a very brief
contradictory window between window-center boundaries; the solver now checks
exact selected intervals, not a coarse time sample.

## Implementation boundaries

`core-rust/clawdj/src/rhythm.rs` retains the existing complete-overlap
classifier. Only uncertain/missing entrance evidence triggers a bounded
search for a reliable suffix inside the planned overlap. Require three real
corresponding onsets, compatible cadence, full-fade source headroom and no
contradictory confident interval. Keep `status=uncertain`, report the evidence
window and do not inflate confidence or mark a weak entrance verified.
No cue movement, deck jumps, fader changes or new short-handoff policy.

Development/tests used a separate Rust target/binary so the existing live
process kept the old solver. Installation waited until the log had `run_end`
and a read-only process check found no active mix runner.

## What this does not yet fix

- **On Fire → Biggie:** unchanged numerical decision; the ear-reported
  one-count error despite−41ms verification remains unresolved. Candidate
  percussion identity requires review, not a forced jump.
- **Stunt101 → Instrumental:** old artifact omitted the instrumental grid;
  a separate grid-repair candidate restored95.9167BPM/firstbeat0.374853s while
  preserving139.27s cue. The first pair predicts ready; the following
  Instrumental → Part2&BumpHeads still has weak evidence. No audible pass.
- **Superwoman → Heartbeat Club (event67):** old entrance used a0.489136s
  grid delay. All39 overlap readings were nonnumeric; later sections had
  incompatible fitted cadence. Do not label that a measured619ms error or
  borrow Jealous's correction. Full32-beat fade retained.
- **Caught Up → Fastlove (event79):** old entrance confidence0.1884;
  all29 readings nonnumeric, grid delay0.539653s. No qualifying reliable
  suffix found. Full24-beat key-adjusted blend retained. User reports one
  count off; audio/markers still need review.
- **Biggie skit:** editable notes and an expanded skit story are implemented,
  not a certified3:30–3:50 removal or seamless two-deck same-song splice.

Tests and source-position replays do not replace listening to these pairs.

## A/B review for the two latest reports

Open `brain/data/previews/backbeat-count-ab-2026-09-05/index.html`.
Clips01/02 compare Superwoman→Heartbeat Club;03/04 compare CaughtUp→Fastlove.
A reconstructs relative source positions from the first overlap observation.
B delays the incoming entrance by one outgoing count, preserving the cue and
full fade. It is a listening hypothesis, not an installed fix or a claim that
these timestamps identify snares. EQ/filter/Fastlove's key bridge are absent.
Four files are fully decoded, duration-probed and rendered with6dB headroom;
`review.json` retains the exact specs. Listener choice should inform reviewed
pair-local timing, not an unconditional jump that flips with the next anchor.
