# Repair Stunt 101 backbeat evidence

Received 2026-09-05 while Ernest listens to gradual-v3.

## Original request (verbatim)

[34/110] transition
  smooth_blend: G-Unit — Stunt 101 → G-Unit — Stunt 101 (Instrumental)
  moves: ['sync', 'eq_dip_out_mid', 'crossfade', 'eq_restore']
  notes: Near-identical tempo + friendly key — long crossfade with light EQ.
  anchoring on [Channel2] beat (95.92 BPM)
  backbeat: unverified — missing analyzed source beatgrid; keeping planned gradual blend
  crossfade: planned 32 beats (20.0s); scheduled 32.0 beats (20.0s)
  bass swap (gradual)
  crossfade landed -> deck 1: 32.0 beats / 20.0s executed (planned 32 beats)
  preload next into freed deck 2
[load] deck 2: 16 - Part 2 & Bump Heads.mp3  (223s, 87.15 BPM, cue 44.19s verified at 44.19s)
 this is off by 1 count for the backbeat matching, i.e. the beat parity, likewise fix this transition: [37/110] transition
  standard_blend: G-Unit — Stunt 101 (Instrumental) → G-Unit — Part 2 & Bump Heads
  moves: ['sync', 'eq_dip_out_mid', 'crossfade', 'eq_restore']
  notes: Default instrument path: sync, mid scoop, longer crossfade.
  anchoring on [Channel1] beat (95.92 BPM)
  backbeat: unverified — missing analyzed source beatgrid; keeping planned gradual blend
  crossfade: planned 24 beats (15.0s); scheduled 24.0 beats (15.0s)
  bass swap (gradual)
  crossfade landed -> deck 2: 24.0 beats / 15.0s executed (planned 24 beats)
  rate settled to native tempo on deck 2
  preload next into freed deck 1
[ probably just off by 1 beat, but it's not blending well. or just match it with another song in the playlist that better blends together.

## Bounded repair

Use the existing analyzed source grid for the exact instrumental recording,
stored independently of its 139.27s cue. Prepare an offline candidate artifact
with fresh pair/section evidence and unchanged tracks/order/cues/bodies/tempo
directives and fade lengths. Do not switch the active plan or touch Mixxx.
Do not infer a correction direction from “one count” alone. If evidence is
still uncertain, report that and review the audio rather than promising
matching from the repaired metadata. A different neighbor is an authorized
alternative, not a reason to reorder before checking the concrete grid gap.
