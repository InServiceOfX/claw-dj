# claw-dj Mixxx controller mapping

Ported 2026-07-11 from prior work (Monoclaw `Projects/clawdj/mixxx-mapping/`,
2026-04-25 through 2026-07-08) — see
[`docs/prior-research/`](../../docs/prior-research/) for full provenance.
This mapping was designed and code-reviewed but **never validated against a
live Mixxx session** before today; that's the next real step here.

- `clawdj.midi.xml` — maps MIDI note/CC numbers (all on **channel 16**,
  reserved for clawdj-core ⇄ Mixxx) to Mixxx controls: transport
  (load/play/pause/cue/sync per deck), crossfader, per-deck volume/rate/EQ.
  Full note/CC map is documented in the file's own header comment.
- `clawdj.scripts.js` — the JS half of the mapping (Mixxx 2.4+ runs this in
  QJSEngine). Handles the note-triggered actions and the `__clawdj_queue`
  track-loading trick (see `docs/prior-research/docs/MIXXX_INTEGRATION.md`
  for why Mixxx has no scriptable "load by path" and this workaround exists).
- `install-mapping-macos.sh` — copies both files into Mixxx's macOS App
  Store sandbox controllers dir
  (`~/Library/Containers/org.mixxx.mixxx/.../Mixxx/controllers/`). Run it,
  then in Mixxx: **Preferences → Controllers → "IAC Driver clawdj" → Enabled
  → Load Mapping → "clawdj" → Apply.** Requires the `IAC Driver` bus named
  `clawdj` to exist first (Audio MIDI Setup → MIDI Studio → IAC Driver →
  online, or let `midir`/`python-rtmidi` create it programmatically).

## Status

Installed on this machine already (a stray copy was found already present
in Mixxx's controllers dir, dated April — this is that same mapping, now
tracked in git here instead of only living on one machine). **Not yet
confirmed live**: enabling it in Mixxx Preferences and sending a real MIDI
message to trigger a deck action is still an open TODO — see
`docs/HANDOFF.md` at the repo root for current status.

`hands/midi_engine.py` predates this port and used a different, made-up
note/CC map — needs reconciling against the note/CC map actually documented
here before relying on it.
