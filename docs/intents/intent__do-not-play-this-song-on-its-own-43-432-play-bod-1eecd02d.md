# Intent: Do not play a vocals-only track on its own

<!-- pdd-intent-id: do-not-play-this-song-on-its-own-43-432-play-bod-1eecd02d -->
<!-- pdd-intent-sha256: 1eecd02d2f32e9085fcee1c4019d25482c412c3b812a6e170d85826d5af07761 -->

## Record

- Intent ID: `do-not-play-this-song-on-its-own-43-432-play-bod-1eecd02d`
- Kind: `correct` (tightens the 2026-08-19 stem-layering story)
- Source: inline chat 2026-08-28 after hearing Get Up (Acapella) ride 32 dry beats
- Request SHA-256: `1eecd02d2f32e9085fcee1c4019d25482c412c3b812a6e170d85826d5af07761`
- Planner top target: `prompts/brain/plan_mix_build_Python.prompt` / `brain/plan_mix_build.py`
- Also: new Rust tool `clawdj stems classify|pair` (`core-rust/clawdj/src/stems.rs`)

## Meaning

- Get Up (Acapella) must not play as a sequential `play_body`, including 32 beats.
- Almost always: vocals-only / acapella plays **at the same time** as an
  instrumental-only track or a cued, repeated instrumental section of a
  full song. Two decks, not a mix transition. The bed stays live.
- Canonical accepted pair: Get Up (Acapella) over Outta Control
  Instrumental (96-beat layer after a short instrumental intro).
- The agent may pick the initial pair from any vocals-only and any
  instrumental (or instrumental section) in context, then iterate by
  swapping either stem.
- `showcase_acapella` is the only sequential exception and is **very
  rare**. Banks On Fire/Warrior / Baby By Me is not that exception.

## Story

`user_stories/story__when_i_add_vocals_only_and_instrumental_only_tracks_i_layer_them_i_do_not_play_the_acapella_in_full.md`
