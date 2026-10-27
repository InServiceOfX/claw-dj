# Pitch play: Numark / DJ K-Time reference

Research date: 2026-10-15. Initial research below predates implementation. **Follow-up: first scope approved and implemented/synthetic-tested; not live-tested.** See [runnable experiment](PITCH_PLAY_EXPERIMENT.md) and [approval/tooling record](intents/PITCH_PLAY_APPROVAL.md). Exact reference score remains unverified.

## Reference and local artifacts

- TikTok: https://www.tiktok.com/@numark_dj/video/7671346273600998686
- Caption identifies **@dj_ktime**, **Numark MixTrack Go**, and **Algoriddim djay**. Do not mistake the performance for a Serato demo.
- Archive, relative to workspace: `Data/Public/Videos/TikTok/numark-dj_7671346273600998686_dj-ktime_mixtrack-go_pitch-play.mp4`.
- Sibling directory ending `_analysis/`: `caption.md`, `source.json`, `probe.json`, `audio-original.m4a` (AAC stream copy), `audio-analysis.wav`, `audio-measurements.json`, reproducible `analyze_audio.py`, `frames/index.json`, 31 full-resolution JPGs at exact 0, 2, …, 60 seconds, and two timestamped contact sheets. `index.html` is the local viewing/listening entry.
- Original MP4 moved from Downloads, not transcoded. SHA-256 `8afb8bfb06e78889506d9301313d018a2dc550abfab3a3b942929cb04e8d6259`; 10,059,378 bytes; 60.509 s container / 60.500 s video; 576×1024, 30 fps; stereo 44.1 kHz HE-AACv2, about 32 kb/s. WAV decode has codec-padding differences; use source video timestamps as the reference clock.
- Screenshot actually resides at `Data/Public/Images/tiktokNumarkQuickBitOfPitchPlay.jpg` (directory separator was missing in the dictated path).
- Keep media outside Git. “Public” is a local directory name, not a license or authorization to republish music.

## What is established, and what is still a hypothesis

**Observed visually:** hands use the controller pads/mixer with djay on a tablet. Early views are mostly wide/over-shoulder; ~22–28 s show pad activity from the front; 30 s and 40–42 s offer useful overhead controller views; by 54–60 s the performance is settling while food arrives. The edit cuts between angles; frames are not evidence of exact continuous pad-on/note-off timing. Tablet labels and pad mode are not legible enough to reconstruct the mapping.

**Human listening description (Ernest):** Alicia Keys, *You Don't Know My Name*, a repeated descending figure, then pitches cued to suggest the characteristic melody of Beyoncé's *Upgrade U*, followed by a transition. Treat song identities and melody relationship as human-supplied working annotations, not independently fingerprinted identifications or a verified score.

**Exploratory audio measurements:** the early 0–20 s window has chroma recurrence peaks around 2.694 s and 5.378 s. Beat tracking reads ~176.87 BPM there and ~88.44 BPM at 20–32 s: a classic half/double-time ambiguity. At ~89 BPM, 2.69 s is about four quarter-note beats (**one bar** in 4/4), and 5.38 s about two bars. A full-file recurrence near 10.736 s is about four bars at that tempo. These are repeating musical-content candidates, NOT proof of a one-, two-, or four-bar engine loop. Eight bars at 89 BPM would last ~21.6 s. A descending figure inside a repeated phrase and the length of the phrase are different things. Do not settle the user's four-versus-eight-bar question by guessing from the riff length. Later beat estimates (~114–116 BPM) are also provisional because the melody/pad section can mislead a tracker; they do not establish an actual tempo change.

**Not yet verified:** exact source cue, sampled pitch/root, whether the entire descending figure or just a note/chord attack is retriggered, semitone sequence, true musical bar counts, pad gates, use of stems, precise handoff and effect settings. No direct listening-based note transcription or original-track alignment was completed in this pass. There is no meaningful spoken narrative to transcribe, and no ASR was run. Numerical analysis of the unchanged reference is not tag removal; tag contamination is a stated measurement limitation.

## The musical operation

Pitch play uses **one chosen sound as an instrument**:

1. Select a cue with a useful attack/timbre (single note, chord, vocal syllable, or short riff).
2. Each note event retriggers that same cue at a different semitone offset, usually without changing the backing tempo. Relative frequency is `2 ** (semitones / 12)`.
3. Repeated attacks plus their pitch intervals/rhythm spell a new melodic contour, teasing the incoming record before the real record lands.

A short riff can be repeatedly chopped before its tail; a single note can be mapped across pads; either can sound like a melodic instrument. Shifting an entire descending arpeggio transposes **all** its notes; it does not automatically isolate its first note. We must identify the audible source span before authoring a faithful score.

Distinguish these controls:
- **Loop**: cycles a bounded source region, normally at its existing pitch.
- **Hotcue drumming**: retriggers one/multiple positions; doesn't necessarily transpose.
- **Pitch play**: retrigger + semitone transposition of the chosen cue.
- **Pitch bend**: temporary speed nudge for beat alignment, not a melody keyboard.
- **Rate slider / turntable transposition**: changes pitch AND duration when keylock is off.
- **Stems**: separate components (vocals, drums, bass, instruments; categories depend on software). djay calls its real-time separation **Neural Mix**. Controller pads send commands to software; they do not themselves separate audio. Stems could isolate the desired timbre, but are NOT required for pitch play, and the caption's product claim does not prove stems were used in this routine.

For now, prefer original full-mix cue playback on a dedicated deck. That shifts everything audible in the cue, including drums. Don't promise isolated-instrument results from EQ or keylock. Source separation is a separate optional milestone, with bleed/artifact assessment, not an implicit dependency or a prepared-audio requirement for the live MVP.

## Mixxx: already capable, without new DSP

Strongest evidence is the local Mixxx source, revision `722eac1bced24cb743f71940e348d92e4bea47d1`, under `../mixxxes/mixxx/`:

- `src/engine/controls/keycontrol.cpp:19–29`: `pitch` = total shift from original; `pitch_adjust` = offset relative to speed/keylock baseline. Nominal knob spans are ±6 and ±3 semitones respectively, **but both explicitly allow out-of-bounds values**. Do not misread the manual's knob range as a hard ±3-semitone DSP limit. Confirm actual readback and audible range on the installed binary before enabling a larger range.
- `res/controllers/Roland_DJ-505-scripts.js:1736–1893`: **PitchPlayMode** selects a hotcue and maps eight pads to three pitch ranges. On press it sets `pitch_adjust`, then triggers `hotcue_<selected>_activate`. This is a real implementation, not merely a label. It proves the existing control vocabulary is sufficient for a monophonic prototype; it is not a gold-standard gate/cleanup implementation to copy blindly.
- `res/controllers/Denon-MC7000-scripts.js:584+`: another pitch pad mode, including cue selection and goto/play behavior.
- Counterexample: `res/controllers/Numark-NS4FX-scripts.js:1172` has a pitchplay branch that prints **not implemented yet**. Never infer support solely from a controller's pad-mode name.
- `[ChannelN],pitch_adjust` + keylock/known rate baseline + hotcue/seek/transport provide the minimum. Use absolute offsets, not repeated pitch-up presses that accumulate drift. Do NOT use `pitch` as the generic pad-mapping input; the official manual recommends `pitch_adjust`.
- No dedicated pitch-pad bank has to be visible in the skin. Pads are programmable triggers; the UI's key controls/`pitch_up` and `pitch_down` are not the same thing as a complete pitch-play mode.

**Architecture recommendation:** Mixxx owns audio/pitch DSP; claw-dj's existing Rust hands own deterministic note scheduling through the existing local control API. `core-rust/clawdj/src/control_api.rs` already exists; older sections of `MIXXX_CONTROL_SURFACE.md` saying Rust is MIDI-only are historical. `performance.rs` currently initializes `pitch_adjust` to zero and handles source timelines but does not expose this note gesture. Inspect the performance compiler/schema before adding a new event type; don't hide notes in arbitrary unsupported JSON fields or change generic plans.

**Real constraints to test before modifying Mixxx:** separate TCP writes are not proven sample-atomic; command acknowledgement is not proof the DSP has adopted the new pitch before the cue attack. Key-shift processing may have latency, smoothing and transient artifacts. One deck is monophonic: a new note/transpose affects or interrupts the old one. Overlapping notes/chords require explicit policy/extra voices; simultaneous pad presses don't make one deck polyphonic. Hotcue `activate` has different behavior when stopped/previewing vs already playing, and on an unset cue it CREATES a cue. Guard that case, pair press/release, and do not overwrite library hotcues just to experiment.

**Rebuild decision:** no Mixxx rebuild for the first milestones. Add engine/control-server batching or an internal atomic “pitch+retrigger” gesture only IF measured attack/pitch races or latency cannot be solved with safe existing controls. A Rust DSP engine outside Mixxx would duplicate routing, tempo, latency and library concerns without evidence it is necessary. Binary REA was not necessary: the relevant implementation is available as source. Proprietary djay internals were not reverse engineered.

## Sources / retrieval status

Retrieved successfully 2026-10-15:
- [Official Mixxx controls](https://manual.mixxx.org/2.5/en/chapters/appendix/mixxx_controls.html): pitch, pitch_adjust, pitch_up/down, hotcue activation/preview and saved-loop semantics. Versioned docs plus local source, not assumed UI support.
- [Algoriddim Neural Mix](https://www.algoriddim.com/neural-mix): real-time separation into beats/instruments/vocals; current product page describes AudioShake integration. Vendor claim, not an assessment of this downloaded clip.
- [djay Pro for Mac](https://www.algoriddim.com/djay-pro-mac): Neural Mix and live production context. Does not establish which djay version/platform/feature mode was active here.
- Supplied screenshot and downloaded clip are the direct reference for the specific routine.

Some guessed Numark/help article paths returned 404 and Serato support/djay PDF returned 403. No claims rely on those inaccessible pages. We did not independently verify Numark's advertised Bluetooth details, exact hardware pad shortcuts, or a proprietary pitch-play algorithm.

## Next implementation scope / approval

See [draft epic and test ladder](requirements/pitch-play.md). Request preserved verbatim once in [intake](requirements/requests/2026-10-15-pitch-play.md). Local `pdd intent plan` ran without model calls or GitHub; ID `pitch-play-original-user-request-2026-10-15-49f842d4`. Its keyword ranking picked generic plan-build first; this is NOT architectural evidence that the feature belongs there. No apply, regeneration, canonical story/contract, semantic certification, or feature implementation is claimed. Meaning-level approval comes before that consequential change.

**Durable taste rule:** exclude DJ names/shoutouts/signature drops from reference transcriptions, imitation targets, generated performances and future parsing by default. Preserve originals; don't remove legitimate sung vocals merely because they are vocals. Mark tag spans only if needed to exclude them from musical measurement; don't reproduce their wording or add a tag generator. This rule is documented intent, not yet an enforced global parser filter.
