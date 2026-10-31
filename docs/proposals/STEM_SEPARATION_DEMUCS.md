# Proposal: stems from full mixes (Demucs) — not built

Status: **proposal only** (Ernest, 2026-10-31: "Propose it, don't build it yet").

## Why

Many songs have no acapella or instrumental in the library. A source
separator can split a full mix into vocals and accompaniment. Those two files
would then use the same Stems page and live layer as a real acapella or
instrumental.

## Shape

1. **Offline only, opt-in, one track at a time.** Run it from the Stems page
   ("make stems for this track") or the CLI. Never in bulk by default, and
   never while Ernest is streaming. Separation uses heavy CPU/GPU; the time per
   song on this Mac is not measured yet.
2. **Outputs.** Write the files next to the library data, not into the music
   folders: `<collection data>/stems/<track hash>/vocals.flac` and
   `no_vocals.flac`. Add them to the library index as derived tracks with
   `track_kind=vocals_only|instrumental_only` and `derived_from=<track_id>`.
   The original is never modified.
3. **Timing for free.** A separated vocal is sample-aligned with its source,
   so the cross-correlation step is exact (offset 0). The full mix's measured
   snare timing applies directly.
4. **Labeling.** Rows show "separated" so a real studio acapella stays
   distinguishable. Separation artifacts (bleed, a watery high end) are
   expected; Ernest's ear decides whether a separated stem is usable.
5. **Dependencies.** `demucs` (MIT) pulls in PyTorch. Keep it an optional
   extra (`uv sync --extra stems`) so the base install stays light.

## Open questions for Ernest

- Separate on demand only, or pre-separate a chosen set before a stream?
- FLAC (lossless, larger) or 320 kbps MP3 for derived stems?
- Is a separated "instrumental" of a full mix acceptable as a bed, or only
  separated vocals?
