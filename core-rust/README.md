# clawdj core-rust

Rust workspace for the `clawdj` library and `clawdj` CLI.

## Requirements

- Rust 1.85 or newer
- macOS CoreMIDI or Linux ALSA for live MIDI probing

## Build

```bash
cd Projects/clawdj/core-rust
cargo build --workspace
```

## Test

```bash
cd Projects/clawdj/core-rust
cargo test --workspace
```

Live MIDI integration test:

```bash
cd Projects/clawdj/core-rust
CLAWDJ_LIVE=1 cargo test -p clawdj --test live_midi -- --nocapture
```

## Lint and Format

```bash
cd Projects/clawdj/core-rust
cargo fmt --all
cargo clippy --workspace --all-targets -- -D warnings
```

## CLI

```bash
cargo run -p clawdj-cli -- setup
cargo run -p clawdj-cli -- load 1 42
cargo run -p clawdj-cli -- cmd '{"op":"play","deck":1}'
cargo run -p clawdj-cli -- queue init
```

## Offline backbeat analysis

FFmpeg must be installed on PATH. These commands only read local audio/JSON;
they never connect to Mixxx:

```sh
cargo run --release -p clawdj-cli -- rhythm analyze /path/to/song.mp3 --bpm 94 --first-beat 0.48
# AlignmentRequest JSON on stdin:
cargo run --release -p clawdj-cli -- rhythm align
# Rhythm JSON with independently supplied snare/clap onsets on stdin:
cargo run --release -p clawdj-cli -- rhythm refit
```

`clawdj/src/rhythm.rs` owns multiband transient extraction, section-local
cadence/microtiming, overlap checks and cue-preserving launch decisions.
The existing Python runner owns transport and verifies actual positions.
See [Backbeat matching](../docs/BACKBEAT_MATCHING.md) for build integration,
cache identity, reviewed markers, previews and live verification limits.
