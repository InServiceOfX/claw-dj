# claw-dj Mixxx controller mapping

Mixxx controller mappings live in `~/.mixxx/controllers/` and consist of:

- `claw-dj.midi.xml` — maps MIDI CC/note numbers to Mixxx controls
  (`[Channel1]hotcue_1_activate`, `[Channel1]beatjump_4_forward`, etc.)
- `claw-dj-scripts.js` — optional JS for anything the XML mapping can't
  express directly

Not written yet — needs a real Mixxx install to iterate against. Do this
early on hackathon day: create a virtual MIDI port (`IAC Driver` on macOS,
`aconnect`/`snd-virmidi` on Linux), point Mixxx's Controller preferences at
it, and confirm `hands/midi_engine.py`'s note/CC numbers actually move decks
before building anything on top.

Reference: https://mixxx.org/wiki/doku.php/midi_scripting
