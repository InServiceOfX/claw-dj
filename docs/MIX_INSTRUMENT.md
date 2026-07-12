# Playing Mixxx as an instrument

claw-dj treats Mixxx less like a media player and more like a **two-deck
instrument**: transport, tempo, EQ, filters, crossfader, loops, and jumps are
the knobs. The Brain picks *which* songs and *what kind* of move; Hands
executes on the beat.

## Pipeline (filtered playlist → continuous mix)

```bash
# 1) curated hits already on disk (playlist.json)
# 2) enrich: sample lineage + lyrics + optional Rust chromagram
uv run python -m brain.enrich_playlist --chroma --chroma-limit 12

# 3) build a multi-song mix plan (techniques + Mixxx control map)
uv run python -m brain.build_mix_plan --tracks 8 --seconds-per-track 40

# 4) preview or perform
uv run python -m hands.run_mix_plan --dry-run
# Mixxx must be running with --control-api-port 9995
uv run python -m hands.run_mix_plan
```

## Knobs and buttons Hands can drive

| Family | Control (Mixxx) | What it's for |
| --- | --- | --- |
| Transport | `play`, cue via `playposition` | Start/stop, drop on phrase |
| Sync | `beatsync`, `keylock`, `quantize` | Beatmatch + keep pitch when rate moves |
| Levels | `volume`, `pregain`, `[Master] crossfader` | Blend decks / bus gain |
| Tempo | `rate` | Match BPM (±~8% comfortable); scratch-like wiggles |
| EQ | EqualizerRack `parameter1/2/3` (low/mid/high) | Kill bass on outgoing, carve space |
| Filter | QuickEffect `super1` | High-pass sweep to hide key clashes |
| Phrase | `beatjump_*`, `beatloop_*_toggle` | Skip to hook, loop-roll fills |
| FX (manual/extend) | EffectUnit wet/dry | Echo-out, flanger builds |

MIDI mapping (`hands/mixxx_mapping/`) already exposes play/cue/sync, crossfader,
volume, rate, and EQ for decks 1–2. The control API used by `run_mix_plan` can
touch any control the engine exposes — useful for filter, loops, and load.

## Transition techniques in the mix plan

| Technique | When | Moves |
| --- | --- | --- |
| `smooth_blend` | Close BPM + friendly key | sync, mid scoop, 16-beat crossfade |
| `sample_callback_blend` | Sample lineage or lyric hook overlap | longer fade, EQ keep shared bed |
| `chroma_matched_blend` | High chromagram similarity | longer EQ blend even if keys differ |
| `key_clash_cut` | Tempo OK, key rough | filter sweep + short cut |
| `half_time_or_cut` | Tempo far apart | rate nudge / hard cut / loop roll |
| `standard_blend` | Default | sync + mid dip + crossfade |

Optional **scratch-in** (rate oscillation) is attached when affinity is high —
same spirit as `hands/showcase_mix.py`.

## Waveform / chromagram policy

- **Full crate waveform analysis: no.** Too slow (decode × N tracks).
- **Ordered hit set (≤12–16 tracks): yes**, via Rust:
  `cargo run -p clawdj-cli -- chroma --out brain/data/chroma_similarity.json -- path1 path2 ...`
- Mixxx still owns **beatgrids** for true beatmatching after Analyze.

## Lyrics policy

- Only the **filtered hit pool** (~50 tracks), cached under `brain/data/lyrics/`.
- Source: LRCLIB (free search API). Shared tokens/bigrams score wordplay/hooks.
- Never scrape lyrics for 14k crate files.

## Sample lineage

- Curated edges in `brain/playlist_seeds/mix_lineage.json` (Wikipedia / known
  sample stories + same-artist continuum pairs for DJ call-backs).
- Prefer pairs where **both** ends exist in the local crate so the mix can
  actually play the call-back.

## Hackathon one-liner

> H agents curate researched hits from *your* library; we enrich with samples,
> lyrics, and chromagram affinity; then Hands performs a continuous set —
> playing Mixxx’s knobs like an instrument for seamless blends.
