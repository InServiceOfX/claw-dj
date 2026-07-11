# claw-dj: two-layer architecture

## Why two layers

H Company's computer-use agent runs a screenshot → vision model → click/type/scroll
loop. That loop has multi-second latency per action — great for "find and add this
to cart," wrong for triggering a hotcue on the beat. So the DJ is split into two
processes that never share a clock:

- **Brain** (`brain/`) — the H Company agent. Slow, deliberative, visible on
  screen. Owns judgment calls: what to play next, when to transition, how to react
  to a request. Drives Mixxx's actual GUI for anything that isn't time-critical.
- **Hands** (`hands/`) — a deterministic Python process. Fast, dumb, invisible.
  Owns beat-accurate execution: hotcues, loops, beatjump, crossfader ramps. Talks
  to Mixxx over MIDI, not the screen.

Brain sends Hands structured commands (`shared/commands.py`); Hands never waits on
a vision model to hit a beat.

## Brain — H Company agent

Responsibilities:
- Browse/search the local track library in Mixxx's GUI, drag tracks to a deck
- React to input (chat request / crowd-energy signal / vibe description) by
  picking the next track from library metadata (BPM, key, energy, genre)
- Decide transition style (blend / cut / beat-juggle / scratch-in) and hand that
  decision to Hands as a command
- Toggle non-time-critical GUI state: FX panel, filters, browser view

Built on `hai-agents` (H Company SDK). This is the part that's actually on screen
during the demo — judges need to see it act, not just emit JSON.

## Hands — deterministic execution engine

Responsibilities:
- Read BPM / beatgrid for the loaded track (`hands/beatgrid.py`, from Mixxx's
  `mixxxdb.sqlite` — Mixxx already analyzes this on import, no need to redo it)
- Compute beat-accurate timestamps for the next N bars
- Execute commands from Brain by sending MIDI (`hands/midi_engine.py` via
  `python-rtmidi`) to a custom Mixxx controller mapping
  (`hands/mixxx_mapping/claw-dj.midi.xml` + `.js`) that maps MIDI CC/notes to
  Mixxx's hotcue/loop/beatjump/crossfader controls

No vision model in this path. Timing comes from Mixxx's own beatgrid data plus a
local scheduler, not from screenshots.

## Command schema (Brain → Hands)

Defined in `shared/commands.py`. Rough shape:

```
LoadTrack(deck, track_id)
SetHotcue(deck, slot, position_beats)
TriggerHotcue(deck, slot)
Loop(deck, beats, action=in|out|toggle)
BeatJump(deck, beats)
Crossfade(from_deck, to_deck, duration_ms, curve=linear|scurve)
```

Brain never sends raw MIDI or touches timing math — it only expresses intent.

## Hackathon MVP cut-list

48 hours. Cut in this order if behind:

1. **Cut first:** scratch-effect emulation, key-matching, multi-genre library —
   ship with one curated hip-hop crate, BPM-matched, pre-tagged energy levels
2. **Cut second:** live crowd-energy sensing (mic input) — fall back to a chat
   input or a hardcoded request queue for the demo
3. **Keep:** the Brain visibly driving Mixxx's GUI on screen (this is the part
   judges score on Track/Demo alignment)
4. **Keep:** Hands doing at least one real beat-juggle or on-beat hotcue trigger
   via MIDI, audibly in sync — this is the "useful/technical" proof point
5. **Never cut:** the Brain/Hands boundary itself — it's the whole pitch

## Judging-criteria mapping

- **Technicality** — real MIDI timing engine, not just LLM-clicks-mouse
- **Creativity** — explicit two-speed-agent split (judgment vs. reflexes)
- **Usefulness** — reusable pattern for any "agent controls a real-time app"
  problem, not DJ-specific
- **Demo** — Brain's GUI actions are visible; Hands' output is audible and on-beat
- **Track/sponsor alignment** — H Company agent does real click/type/scroll work,
  it's just scoped to what it's actually good at
