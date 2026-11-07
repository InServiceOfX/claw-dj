# Phil Harris: tone play preparation

Source: https://www.tiktok.com/@djphilharris/video/7694719261549317379

The six-video research batch in public repository `InServiceOfX/claw-work`,
merged at `61aeedf`, contains the original notes and cleaned auto-captions under
`research/tiktok-skill-research-2026-11-05/`. Its four selected screenshots now
live here in [screenshots/djphilharris/](screenshots/djphilharris/README.md),
with the source, capture timecodes and preservation hashes. They were moved,
not re-encoded; the screenshot copies were removed from claw-work's current tree.
This note is a portable synthesis; no other checkout or media download is
required to understand the implementation handoff.

## What was shown

Phil explains playing a melody from one pitched sample. He shows two methods:

1. In Ableton Live, duplicate an isolated sound, transpose each copy, space the
   notes, export one file and set CDJ hot cues at their onsets.
2. Load a sample into a Pioneer DJS-1000 and use its Scale Mode to map notes to
   pads.

This is preparation for tone play, not a demonstration of Mixxx or a continuous
two-track transition. The clip does not establish a particular song identity,
note score, key, EQ recipe, Mixxx sampler mode or sample-accurate live API.
The archive has auto-captions and inspected stills; it does not supply a verified
musical transcription or a fresh human audition of our implementation.

## What transfers to claw-dj

The useful abstraction is **one cue + absolute semitone offsets + note rhythm**.
Relative frequency is `2^(semitones/12)`. Resampling changes duration as well as
pitch; native key shift can separate pitch from playback rate. One deck is one
monophonic voice. Pitch readback alone does not establish DSP settling before
the attack.

The current repository already implements a bounded original-source experiment:
`hands/pitch_play.py` -> `core-rust/clawdj/src/pitch_play.rs` -> Mixxx pitch DSP.
It is not necessary to build another Rust audio engine, buy a hardware sampler,
or pre-render music to start evaluating it.

**The user's live-performance requirement takes precedence over the video's
pre-produced method.** Do not substitute a prepared note bank/master for the
original-source performance. Any later offline preview is optional and separate.
Do not infer that Mixxx lacks pitch play merely because it lacks this exact
Pioneer pad UI: the existing research identifies controller implementations.

Next-agent entry point: [TONE_PLAY_AGENT_HANDOFF.md](../TONE_PLAY_AGENT_HANDOFF.md).
