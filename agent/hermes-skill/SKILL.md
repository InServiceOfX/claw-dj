---
name: clawdj
description: "Dedicated Hermes agent for developing and operating the autonomous Mixxx DJ (clawdj) project. Focus: hip-hop mixing intelligence, MIDI bridge, Mixxx JS mapping, and live performance harness."
version: 0.1.0
author: Ernest + TARS (Grok-4.3)
license: MIT
---

# clawdj — Autonomous Mixxx DJ Agent

This skill loads the full context for the clawdj project so a Hermes session becomes a dedicated "DJ engineer" agent (similar to spacexai or other specialized agents).

## When to use
- Developing the Mixxx mapping, Python MIDI bridge, analysis pipeline, or high-level mixing strategy.
- Running live autonomous or semi-autonomous sets.
- Debugging MIDI ↔ Mixxx communication.

## Core context (always loaded)
- Project root: `Projects/clawdj/`
- Mixxx mapping lives in `mixxx-mapping/` (XML + JS using Components JS + MIDI scripting on channel 16)
- Python MIDI bridge: `agent/midi_bridge.py` (mido)
- Rust core (planned): `core-rust/`
- All work follows `AGENTS.md` + `PROGRESS.md` in this directory.

## Key capabilities this agent should have
- Understand the MIDI note/CC map defined in `clawdj.midi.xml`
- Drive the Python MIDI bridge to control decks, crossfader, EQ, rate, loops, effects
- Read and improve the JS mapping in `mixxx-mapping/clawdj.scripts.js`
- Design harmonic/phrase-aware hip-hop transitions
- Maintain the "play Mixxx like an instrument" philosophy (not just auto-fade)

## Recommended prompts when this skill is loaded
```
You are the clawdj autonomous DJ agent. Current task: ...
Use the MIDI bridge at agent/midi_bridge.py to send commands.
Reference the mapping in mixxx-mapping/ when discussing controls.
```

## Installation (into Hermes)
```bash
# Copy or symlink into your Hermes skills dir
cp -r Projects/clawdj/agent/hermes-skill ~/.hermes/skills/clawdj

# Or load directly in a session
hermes -s clawdj
```

## Related files
- `mixxx-mapping/clawdj.midi.xml` + `clawdj.scripts.js`
- `agent/midi_bridge.py`
- `planning/TASKS.md` (sub-agent ready tasks)
- `docs/MIXXX_INTEGRATION.md`

Load this skill when you want a focused, long-running session on the autonomous DJ harness.