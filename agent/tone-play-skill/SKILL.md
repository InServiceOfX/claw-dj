---
name: claw-dj-tone-play
description: Continue claw-dj's original-source monophonic pitch-play experiment using its Python validation wrapper, Rust scheduler and Mixxx DSP. Use for tone-play preparation, dry-run scores, testing or an explicitly authorized audition; not for replacing a live mix with prepared audio.
---

# claw-dj tone play

Work from a claw-dj checkout. Read its AGENTS.md, PROGRESS.md, docs/HANDOFF.md,
then **docs/TONE_PLAY_AGENT_HANDOFF.md** and docs/PITCH_PLAY_EXPERIMENT.md.
Those files contain the current code map, cross-machine setup, test ladder and
scope. This skill requires that checkout; it is not a standalone renderer.

Reuse `hands.pitch_play` for original-source/current-note validation and deck
ownership, `core-rust/clawdj/src/pitch_play.rs` for timing and native Mixxx DSP
for pitch. No new audio engine or prepared note-bank requirement. Keep dry-run
connection-free; live and capture need explicit current authorization. Never
call the internal Rust live protocol as a replacement for wrapper validation.

Start with a tested monophonic score and source-second cue. Keep absolute
semitone offsets, preparation gaps, gate plus lateness inside current hard
source limits, and first-scope ±3 semitones. Treat timestamps, root/key and
melody transcription as unverified until established. Do not invent saved cues,
sampler Scale Mode, DSP readiness, human listening approval or plan directives.

For code changes, inspect matching prompts/architecture/stories and follow
scoped PDD rules. For evaluation, separate synthetic control evidence, real
audio measurements, human audition and full-plan integration. Preserve native
source guards and existing cleanup; retain all unrequested approved seams.

Return exact artifacts/commands, actual checks and the next unresolved step.
Research source: https://www.tiktok.com/@djphilharris/video/7694719261549317379.
Its DAW/CDJ method is context, not permission to override the user's requirement
for live performance from original recordings.
