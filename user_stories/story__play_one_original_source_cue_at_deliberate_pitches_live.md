<!-- pdd-story-prompts: prompts/hands/pitch_play_Python.prompt, prompts/core/pitch_play_Rust.prompt -->
<!-- pdd-story-status: first-scope-approved-2026-10-15; live-listening-not-yet-evaluated -->
<!-- pdd-story-intent: docs/intents/PITCH_PLAY_APPROVAL.md -->

# Play one original-source cue at deliberate pitches live

## Story

As a DJ, I can retrigger one chosen cue from an original recording at deliberate
pitches and rhythms in live Mixxx, first as a simple monophonic experiment,
so I can build toward playing a recognizable melody and transitioning into its
record without replacing the performance with a finished render.

## Acceptance

1. I can inspect the source cue, pitches, note timing and gates before anything
   connects or plays. Playback requires an explicit live choice.
2. The first experiment uses one reserved, empty deck with existing Mixxx pitch
   DSP, not a new audio engine. It refuses to take over a playing mix. It does
   not require buying a controller or modifying saved library cues.
3. Each trigger starts at the chosen allowed source cue. Its semitone offset
   is intentional and repeatable; pitch changes do not change playback tempo.
   Start with repeated untransposed notes and a small simple pitch phrase.
4. The experiment refuses impossible/overlapping notes and invalid source
   regions. Current mandatory song exclusions apply to every attack and tail.
5. Notes do not accumulate timing or pitch-offset drift. A delayed scheduler
   aborts rather than rushing through a queue of missed notes.
6. Stop, error or Ctrl-C stops the owned voice and restores touched controls;
   it never resumes an earlier playing transport position. If the connection
   remains broken, it reports the failure rather than claiming successful
   cleanup or opening an unverified voice.
7. No tag/shoutout/signature drop is transcribed or generated as part of this
   technique. Legitimate song vocals remain allowed.
8. Automated checks establish scheduling and safety behavior, then I audition
   the simple live phrase before we claim it sounds right or reconstruct the
   Alicia Keys / Beyoncé example. Stems, polyphony and backing/handoff are later
   steps, not requirements for this first experiment.

## Independent source

Ernest's original request in
`docs/requirements/requests/2026-10-15-pitch-play.md`, the preceding proposed
first-build summary, and his reply **“approve first scope I approve”**.
Manually authored from that intent; not an automatically generated PDD contract.
