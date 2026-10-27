# Draft epic: play a cue as a melodic instrument in live Mixxx

**Status: first bounded monophonic experiment approved by Ernest (2026-10-15), implemented and synthetic-tested; later epic stages remain proposed. No live listening/audio evaluation yet.** See [experiment and evidence](../PITCH_PLAY_EXPERIMENT.md), [approval](../intents/PITCH_PLAY_APPROVAL.md), and the first-scope acceptance story in `user_stories/story__play_one_original_source_cue_at_deliberate_pitches_live.md`.

Independent source: [Ernest's original request](requests/2026-10-15-pitch-play.md).
Reference/implementation evidence belongs separately in [research](../PITCH_PLAY_RESEARCH.md).

## User outcome

As a DJ, I want claw-dj to retrigger a chosen cue at deliberate pitches and rhythms, so I can tease a recognizable melody and then land smoothly in the next song, live in Mixxx from original recordings.

## Boundaries

- Start monophonically, one selected cue and one explicitly reserved deck. No controller purchase or visible pitch-pad UI required.
- Keep backing tempo stable while changing note pitch; distinguish this from intentional turntable-style rate changes.
- Original source performance, not playback of a pre-rendered pitch-play master.
- No DJ tags, shoutouts, vocal signatures or tag-generation feature. Legitimate song vocals remain allowed.
- Source exclusions always win, including over notes/tails/loops. No destructive library cue edits, stolen decks, hidden live playback, or filesystem media writes in a dry run.
- Stop/error/Ctrl-C releases held controls, silences/stops the owned test voice safely, and restores every touched control. Never blindly restore `play=1` on a stale position.
- Preserve the gentle-fader and backbeat rules. Cue gate cuts are intentional instrument articulation, not permission to rush a track transition's faders.

## Small-to-large ladder

### 0. Reference and score (this research pass is partial)
Archive reference + caption + audio + timestamped frames; distinguish observed facts, user listening annotations and inference. Later identify a clean original source cue, fundamental/reference pitch, usable tail, exact note rhythm and semitone intervals; audition rather than hallucinate a transcription. Measure 4/8-bar candidates with a real musical downbeat. Existing accepted one-bar-loop story remains independent and unchanged.

### 1. One cue, one pitch (first executable experiment)
Given an explicitly supplied/validated source and cue, run a few untransposed attacks, then e.g. `0, +1, +2, 0` semitones at a slow fixed beat interval. This synthetic interval exercise is NOT a transcription of the TikTok. Expose cue, note/gate duration, pitch baseline and tempo as reviewable parameters. Dry-run prints source-time cue, note-on/off times, semitones and intended control changes with no connection or writes. Live execution requires an explicit opt-in and idle/owned deck; reject unset or loop-type cues unless explicitly supported. First narrow pitch range: ±3 semitones by default; expand only after capability/readback/audio checks.

### 2. Deterministic monophonic note phrase
A score expresses relative beat position, pitch in semitones, cue identity and gate duration. Absolute monotonic deadlines avoid accumulating sleeps; define late-note behavior (refuse/abort rather than burst stale attacks). Same-cue repeats, rests, finite ends and repeated pitches work. Reject nonfinite values, invalid source positions, negative durations, overlapping notes on the same voice and ambiguous cue types. Save/restore baseline keylock, pitch, rate, quantize, sync, routing, faders and any transport/cue state actually touched. This is a gesture extension of the original-source performance, not a replacement plan architecture.

### 3. Background + source melody + incoming record
Reserve a voice for pitch play while an independent original-source bed continues. Respect deck occupancy, measured downbeats, backbeat and incoming source boundaries. Repeat a short figure only as authored, count passes explicitly, then hand off on a reviewed downbeat without dead air. Preserve the existing taste default of a few repeats; do not hard-code eight bars or unlimited looping from this one reference.

### 4. Reference reconstruction and optional sophistication
Use reviewed Alicia Keys/Beyoncé source identities, cue and interval/rhythm score for an A/B comparison with the saved reference (excluding tags). Evaluate source timbre, pitch, attack, timing, tail, handoff and musical recognizability—not waveform equality with compressed TikTok audio. Later: controller/UI pad bank, optional stem-isolated voice and explicit polyphony. Keep those independent, not MVP blockers.

## Testing / evidence required before claiming success

1. **Pure score tests:** beat→seconds math at several tempos, repeated note/offset reset, semitone ratio, note-off ordering, invalid/overlapping/NaN input, boundary-clipped tails, reproducible dry-run.
2. **Fake control transport:** no writes/connections on dry-run; refusing occupied deck/missing cue causes zero mutations; offsets are absolute; press/release pairs; restore after success, error, disconnect and cancellation; source exclusions and library cue metadata preserved. Test stopped preview vs playing behavior explicitly.
3. **Deterministic scheduler tests:** injected clock, absolute deadlines, no cumulative drift, bounded/rejected lateness; no catch-up note bursts.
4. **Real Mixxx synthetic audio test (human-gated):** known pitched tone with an attack, captured via a test output route. Verify frequency ratios, cue-position accuracy, gate and inter-onset timing, repeatability, no BPM drift, no stuck voice/clipping. Define timing tolerances from actual buffer size, measured round trip and capture alignment, not an invented universal sample-accuracy guarantee. Measure whether pitch settles before the first attack.
5. **Human listening:** first listen to the simple phrase, then the original-song cue, then the staged reference reconstruction. Ernest approves musical resemblance. Synthetic unit tests alone cannot establish a good-sounding routine.

First-scope implementation now has 18 Python, 8 Rust unit and 3 Rust CLI tests, plus broader regression checks; see the experiment document for exact results and unrelated broader-suite failures. This is control/scheduler evidence, not measured audio or listening acceptance. Human-approved scope is the bounded original-source monophonic experiment only; stems, polyphony, backing/handoff integration, reference reconstruction and a Mixxx rebuild remain later decisions.
