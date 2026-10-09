# Request: Put It On Me → Jealous is one count off

Ernest, 2026-09-05, while listening to the existing run:

```text
[61/110] transition
  smooth_blend: Ja Rule — Put It On Me → Nick Jonas — Jealous
  moves: ['sync', 'eq_dip_out_mid', 'crossfade', 'eq_restore']
  anchoring on [Channel1] beat (93.19 BPM)
  backbeat: unverified — weak or inconsistent local snare/clap evidence; keeping planned gradual blend
  crossfade: planned 32 beats (20.6s); scheduled 32.0 beats (20.6s)
  backbeat: sustained measured backbeat mismatch during overlap; keeping planned gradual blend (needs review)
  crossfade landed -> deck 2: 32.0 beats / 20.6s executed (planned 32 beats)
is still off by 1 count, match backbeat please i.e. beat parity
```

Accepted implementation meaning: resolve the entrance using reliable local
backbeat evidence within the intended overlap, even if the first section is
uncertain. Preserve cue, full32-beat fade and current playing process. Build
and test a separate Rust candidate, replay recorded positions, then offer an
explicit next-run candidate. Do not replace the binary used by the current
run. No blind jumps, cue shifts, confidence inflation, automatic short
handoffs, or claims of audible success from numerical tests.
