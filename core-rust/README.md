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
