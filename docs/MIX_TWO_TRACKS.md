# Mix Two Tracks In Mixxx Right Now

This is the shortest attended path for a live two-track transition using the
existing `clawdj` bridge.

## Preconditions

- Mixxx is open.
- The `clawdj` controller mapping is enabled on the `clawdj` / `IAC Driver clawdj`
  MIDI port in Mixxx Preferences.
- Two tracks are already loaded in Mixxx, one on each deck.
- The outgoing deck is **not** parked at end-of-track; if it is, send `cue`
  before `play`.

## 1. Verify the MIDI bridge from a normal host terminal

From `core-rust/`:

```bash
cargo run -p clawdj-cli -- setup
```

Expected: at least one input/output port whose name contains `clawdj`, and
`clawdj present: true`.

If you instead get `failed to initialize MIDI input`, the shell you're using
does not currently have a usable MIDI backend/port. Fix that first in the
host session where Mixxx can see the virtual port.

## 2. Put deck 1 live and deck 2 ready

If deck 1 is the outgoing deck:

```bash
cargo run -p clawdj-cli -- cmd '{"op":"cue","deck":1}'
cargo run -p clawdj-cli -- cmd '{"op":"volume","deck":1,"value":127}'
cargo run -p clawdj-cli -- cmd '{"op":"volume","deck":2,"value":127}'
cargo run -p clawdj-cli -- cmd '{"op":"crossfade","value":0}'
cargo run -p clawdj-cli -- cmd '{"op":"play","deck":1}'
```

Optional sanity check:

```bash
cargo run -p clawdj-cli -- monitor --seconds 8
```

You want beat ticks arriving from deck 1 before attempting a transition.

## 3. Transition from deck 1 to deck 2

```bash
cargo run -p clawdj-cli -- transition --from 1 --to 2 --beats 16
```

What it does:

- measures deck 1's live BPM from Mixxx's beat feedback
- starts deck 2 on a beat
- beat-syncs deck 2
- crossfades over 16 beats
- pauses deck 1 at the end

Use `--beats 8` for a faster cut or `--beats 32` for a longer fade.

## Reverse direction

To go from deck 2 back to deck 1:

```bash
cargo run -p clawdj-cli -- cmd '{"op":"cue","deck":2}'
cargo run -p clawdj-cli -- cmd '{"op":"crossfade","value":127}'
cargo run -p clawdj-cli -- cmd '{"op":"play","deck":2}'
cargo run -p clawdj-cli -- transition --from 2 --to 1 --beats 16
```

## Known gotchas

- No beat ticks means no measured BPM; the transition command needs live
  feedback from the outgoing deck.
- A deck at end-of-track may accept `play` but emit no beats. Send `cue`
  first.
- The older `demo-*` subcommands are canned demos. For a real live mix, use
  `monitor` and `transition`.
