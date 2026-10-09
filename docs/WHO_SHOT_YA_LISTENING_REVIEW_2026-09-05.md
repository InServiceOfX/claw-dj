# Who Shot Ya: skit and backbeat listening review

Ernest reports better gradual fades but one-count error on On Fire → Biggie
and unwanted spoken material around 3:30–3:50. Request:
[original feedback](intents/request__song_playback_notes_and_skit_avoidance.md).
These are findings, not a claimed audible fix. No active plan/note data,
audio or playback controls changed in this investigation.

## Skit: current note and artifact conflict with the request

Exact recording: Biggie, Ready To Die (The Remaster) [2004],
`18. Who Shot Ya.mp3`, about 319.425s, 91.6667 BPM, cue 0.4232s.
The next `06. WHO SHOT YA.mp3` is a different, 111-second 50 Cent recording,
not a duplicate suitable for same-song continuation.

- A read-only query of the exact track in
  `/Volumes/Elements/clawdj/library.sqlite3` returned empty `dj_notes`.
  August 31 documentation claiming a global skip is not true of this current
  row. Why that historical instruction is absent is not established.
- Both the heavy-rotation overlay and built track note explicitly let the
  gun-in-mouth tag sit in the overlap, and lock a 312-beat ride. That conflicts
  with the latest requirement.
- Event 11 contains no skip fields; the runner has no skip operation to
  execute. Trusted ride/phase messages are not skit-aware source deadlines.
- Earlier requested bounds were 203.5–224.5s; current estimate is 210–230s.
  Review the actual audio before saving executable region markers. Do not
  protect spoken dialogue as a verse simply to satisfy the old ride note.

Existing skip directives use a same-deck beatjump, not the proposed smooth
two-deck splice. A full next-song fade ending before the reviewed scene is
the simpler first candidate. Same-song continuation additionally requires
deck/preload planning and chain tests. Neither is newly implemented here.

## Backbeat: what the saved evidence establishes

Run log: `brain/data/runs/backbeat-20260905T081628Z-d4dd0515.jsonl`, inspected
while the run continued; header identifies gradual-v3.

- Solver used On Fire position 161.454226s, Biggie cue 0.4232s and launch delay
  0.513773s. Incoming rate was 1.0363636 (95 BPM against native 91.6667).
- Five pre-fader errors were about −41ms, median −41.037007ms. Source-onset
  comparison reported 14 matches, median 5.728607ms and p90 28.308867ms.
  Both checks rely on the same candidate percussion interpretation, not
  independent identification of a snare/clap.
- The selected sections both have cadence 2, phase about 1 beat, sourced
  from `multiband_transients`, not reviewed drum markers. A stable wrong
  alternating accent could pass this check. Misidentification is a hypothesis,
  not yet a proven root cause.
- Fade executed 32.0187 beats / 20.2223s against planned 32 / 20.2105s, with
  no shortening reason. The gradual-fade policy is active; rhythmic acceptance
  is a separate issue.
- All 45 position observations (five entrance, forty overlap) were numeric
  and labelled `measured`, despite three “local verification unavailable”
  messages. Guard.check uses that wording for incomplete/inconsistent sample
  windows too. The first overlap check has only one of three required samples;
  later roughly ±41ms samples can fail the coherence test. The message does
  not establish missing drums here and needs correction in a later isolated
  runtime change.
- End status still says `position_verified` while its verification field is
  `unverified`; that stale reason is another reporting issue.

A beat at 95 BPM is about 632ms. A −41ms residual against guessed accents
does not measure full-count error against independently identified snares.
Next: audition actual exit/entry percussion, establish reviewed hit timestamps,
and compare them at recorded positions before changing timing. Do not blindly
flip either deck or restore short handoffs.

## Notes UI versus execution

Mix now links to Arrange, where each song offers **Edit playback note…** with
multiline plan-specific Save, Cancel and confirmed Use library default.
Existing revision checks and overlays are retained. Text storage is not
arbitrary-prose execution; supported directives apply at Build. Saving does
not change already-loaded playback events.
