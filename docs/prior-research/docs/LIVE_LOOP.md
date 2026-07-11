# Live loop: how the human + agent + Mixxx mix together

## Operating modes

1. **Pre-show planning** — chat-only. Agent reads library DB, proposes a
   setlist. No MIDI sent. Output is a JSON timeline.
2. **Live with autopilot** — agent executes the timeline, deviating when the
   human steers ("speed up", "drop something darker").
3. **Live with co-pilot (default)** — agent suggests next moves, human
   confirms, executes, or overrides. Default safety setting.
4. **Manual** — agent shuts up unless asked.

User picks via `clawdj live --mode copilot` or in chat: "switch to autopilot".

## Real-time chat ↔ harness

We do NOT need realtime audio streaming between Ernest and the agent — the
agent isn't *listening* live (yet). Instead:

- Ernest chats text in his usual OpenClaw session.
- The OpenClaw main agent (Grimlock) interprets intent, calls
  `clawdj-core cmd '...'` to schedule the next move.
- `clawdj-core` runs as a long-lived background process started via
  `clawdj live`. It owns the MIDI bridge and exposes a Unix socket
  (`/tmp/clawdj.sock`) for command JSON in and event JSON out.
- A second OpenClaw cron/heartbeat tails events from the socket and lets
  Grimlock react to state ("track ending in 24s — propose transition").

## Beat-locked scheduling

The agent's instructions are *intent at the bar/beat level*, never raw seconds:

- "At the next downbeat, swap kick patterns"
- "On bar 16 of the breakdown, cut deck A's lows for 2 beats then bring in B"
- "Loop the acapella from 1:30–1:45 of track X over the verse of track Y"

`clawdj-core` translates intent → a sequence of (target_beat, midi_msg) pairs
and posts them to a tiny scheduler thread. The scheduler watches Mixxx's
`[Channel1].beat_active` (via the MIDI feedback bus) and fires each message
slightly before the target beat (compensating for ~5 ms of MIDI/IPC latency
that we measure once at startup).

For sample-accurate ops (EQ-kill, scratch, beat-loop start), the message we
send is a *recipe trigger* (note 16..31 on channel 16). The recipe runs
**inside** Mixxx's QJSEngine using `engine.beginTimer(0, ...)` against the
sample clock, so the actual EQ-cut happens with sub-millisecond accuracy.

## Pre-computed transition recipes

Per track-pair `(A, B)` we precompute:

- BPM delta and required `rate` change for each deck so they sync at the
  transition midpoint.
- Camelot compatibility flag.
- Best transition windows: pairs of `(end-of-A section, start-of-B section)`
  where the energy curves match. E.g. `A.outro` → `B.intro`,
  `A.breakdown_end` → `B.drop_start`, `A.acapella` → `B.verse`.
- For each window, a recommended "cut shape": equal-power crossfade /
  bass-swap / cut-on-1 / acapella-bridge / loop-roll.

When the agent picks a transition, this is already a lookup, not a computation.

## Lyric-aware transitions

If A has a lyric line ending precisely on bar 32 beat 1 (a "punch-out") and B
has a lyric *answer* at bar 0 beat 1, we mark that as a
`lyric_punch_transition`. The agent loves these for hip-hop sets.

## Failure & override

- Human types "STOP" / "kill it" / "fade out" → core sends
  `[Master].headMix` etc. and halts the queue.
- Mixxx crash → core notices socket close, queues nothing, alerts in chat.
- Track misload (wrong file, can't decode) → fall back to next item, log.
- Watchdog: if no `beat_active` events for 4 s while a deck is supposedly
  playing, assume desync; re-emit play state.

## Telemetry / set replay

Every fired event is appended to `~/.local/share/clawdj/sets/<timestamp>.jsonl`.
Replaying a set = feeding the file back through the core. Useful for debugging
and for training future planners.

## Permissions / safety

- `clawdj live` only runs after `clawdj setup` confirms (a) virtual MIDI
  port is wired up, (b) Mixxx's controller preferences include our mapping,
  (c) audio output device is set as expected.
- The Rust core never deletes audio files; the analyzer never modifies them.
- All paths read from config; no hardcoded music dirs in commits.
