# Request: gradual, seamless crossfader blends

- Received: 2026-09-04
- Change kind: correction / listening feedback / constraint
- Scope authorized now: create or start a user story; document the observed
  regression. No playback-code, active-plan or Mixxx changes in this turn.
- Status: request captured; story drafted for review; implementation pending.

## Original request

I think the "beat parity" or backbeat matching is fine now but I'm noticed on this and many other transitions I listened to after you modified that you moving the crossfader is TOO FAST. It should be a user story (please make or at least start a user story): The crossfader should be moved at an appropriate slow pace because we want to blend two tracks almost or perfectly seamlessly; the beats should blend, the backbeats should blend and the transition should smooth blend on track into the other. We should in general avoid sudden crossfader switch over, except for "DJ tracks". I saw that in this transition now:

```text
[7/110] transition
  smooth_blend: Chris Brown — Wall to Wall → Lloyd Banks — On Fire (Feat. 50 Cent)
  moves: ['sync', 'eq_dip_out_mid', 'crossfade', 'eq_restore']
  notes: Near-identical tempo + friendly key — long crossfade with light EQ.
  anchoring on [Channel1] beat (94.00 BPM)
  backbeat: short handoff — entrance timing could not be verified
  bass swap (gradual)
  2-beat landing -> deck 2
  rate settled to native tempo on deck 2
  preload next into freed deck 1
[load] deck 1: 18. Who Shot Ya.mp3  (319s, 91.67 BPM, cue 0.42s verified at 0.42s)
```

this transition was good with backbeat matching and ok with the smooth crossfader transition, but be ok with even taking longer to make that cross fader blend:

```text
[10/110] transition
  smooth_blend: Lloyd Banks — On Fire (Feat. 50 Cent) → The Notorious B.I.G. — Who Shot Ya
  moves: ['sync', 'eq_dip_out_mid', 'crossfade', 'eq_restore']
  notes: Near-identical tempo + friendly key — long crossfade with light EQ.
  anchoring on [Channel2] beat (95.00 BPM)
  backbeat: positions verified (+15 ms); opening blend
  bass swap (gradual)
  32-beat landing -> deck 1
  rate settled to native tempo on deck 1
  preload next into freed deck 2
[load] deck 2: 06. WHO SHOT YA.mp3  (111s, 93.00 BPM, cue 0.44s verified at 0.44s)
```

## Interpretation for story review

Preserve the improved perceived backbeat matching while making ordinary blends
gradual and seamless. A planned smooth blend should not routinely become an
abrupt cut merely because automatic verification is inconclusive. Longer than
the acceptable 32-beat example is welcome when the musical material permits;
no universal duration was requested. "DJ tracks" is provisionally interpreted
as intentionally designated cut/scratch/beat-drop/showcase passages, not a
title or artist containing the text "DJ". Exact exception controls and the
unverified-entrance recovery policy remain implementation design decisions.

Story: `user_stories/story__when_i_blend_tracks_the_crossfader_moves_gradually_and_seamlessly.md`.
