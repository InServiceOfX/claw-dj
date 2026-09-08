# Intent: Retain overlap backbeat parity at uncertain entrances

<!-- pdd-intent-id: retain-overlap-backbeat-parity-at-uncertain-entr-f2b17b74 -->
<!-- pdd-intent-sha256: f2b17b749a253b4dca6a096d64c0e548add6985b46097415dd7645d418eb0dc0 -->

## Record

- Intent ID: `retain-overlap-backbeat-parity-at-uncertain-entr-f2b17b74`
- Kind: `add`
- Supersedes: none
- Approval ID: `retain-overlap-backbeat-parity-at-uncertain-entr-f2b17b74`
- Source kind: `file`
- Source reference: `docs/intents/request__jealous_backbeat_parity.md`
- Request SHA-256: `f2b17b749a253b4dca6a096d64c0e548add6985b46097415dd7645d418eb0dc0`
- Project scope: `repository`
- Adoption scenario: `existing_pdd_change`

- Technology: `rust`

## Original Request

> # Request: Put It On Me → Jealous is one count off
>
> Ernest, 2026-09-05, while listening to the existing run:
>
> ```text
> [61/110] transition
>   smooth_blend: Ja Rule — Put It On Me → Nick Jonas — Jealous
>   moves: ['sync', 'eq_dip_out_mid', 'crossfade', 'eq_restore']
>   anchoring on [Channel1] beat (93.19 BPM)
>   backbeat: unverified — weak or inconsistent local snare/clap evidence; keeping planned gradual blend
>   crossfade: planned 32 beats (20.6s); scheduled 32.0 beats (20.6s)
>   backbeat: sustained measured backbeat mismatch during overlap; keeping planned gradual blend (needs review)
>   crossfade landed -> deck 2: 32.0 beats / 20.6s executed (planned 32 beats)
> is still off by 1 count, match backbeat please i.e. beat parity
> ```
>
> Accepted implementation meaning: resolve the entrance using reliable local
> backbeat evidence within the intended overlap, even if the first section is
> uncertain. Preserve cue, full32-beat fade and current playing process. Build
> and test a separate Rust candidate, replay recorded positions, then offer an
> explicit next-run candidate. Do not replace the binary used by the current
> run. No blind jumps, cue shifts, confidence inflation, automatic short
> handoffs, or claims of audible success from numerical tests.

## Must Stay Unchanged

- Do not replace the binary used by the current

## Examples

- None stated.

## Candidate Product Areas

- The single plan-aware entry to mix composition, callable from both the GUI and the CLI so the two cannot produce different artifacts.
- The riskiest module in the feature: the only one that changes behaviour inside working, ear-tested ordering code.
