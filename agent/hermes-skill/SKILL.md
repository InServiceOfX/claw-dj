---
name: clawdj
description: "Use when developing or operating the claw-dj autonomous Mixxx project, publishing its recordings, making social teasers, or managing its YouTube workflow. Loads the project architecture, DJ-craft priorities, deterministic media procedure, portability model, and external-action safety gates."
version: 0.3.0
author: Ernest + TARS
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [dj, mixxx, audio, video, youtube, automation]
    related_skills: [prompt-driven-development]
---

# clawdj — autonomous Mixxx DJ agent

## Overview

This skill turns a Hermes session into the dedicated engineering and operations agent for `claw-dj`. The goal is an autonomous or semi-autonomous DJ that plays Mixxx like an instrument: selection plus phrase-aware cueing, beat-accurate execution, EQ, loops, effects, sample lineage, lyrical structure, and a recognizable style.

Repository files remain the source of truth. This skill supplies task procedures and safety policy; it does not replace `AGENTS.md`, `PROGRESS.md`, or `docs/HANDOFF.md`.

## When to use

- Developing the Brain, Hands, patched Mixxx integration, MIDI mapping, Python bridge, or Rust execution layer.
- Planning, previewing, recording, or evaluating mixes and transitions.
- Turning Mixxx WAV recordings into YouTube upload masters.
- Producing branded 9:16 promotional clips for Reels, Shorts, and X.
- Reconstructing the dedicated agent on another machine.
- Authorizing or operating the dedicated YouTube channel.
- Routing product intent through Prompt-Driven Development; load the related
  `prompt-driven-development` skill before acting.

Do not load this skill for unrelated generic audio questions.

## Session bootstrap

1. Run `git status --short --branch`; stop before editing if the branch is `master` and create or select an appropriate branch.
2. Read `AGENTS.md`, then `PROGRESS.md`, then `docs/HANDOFF.md`.
3. Read the task-specific files instead of relying on this summary.
4. Inspect live files, tools, Mixxx state, and media inputs before acting.

Bootstrap is complete only when the active branch and current implementation path are known.

## Core architecture

- `brain/`: judgment, library analysis, curation, phrase/lyric understanding, and mix planning.
- `hands/`: deterministic, timing-sensitive Mixxx execution.
- `core-rust/`: low-latency control and gesture implementation.
- `hands/mixxx_mapping/`: current Mixxx mapping.
- `agent/midi_bridge.py`: mature Python MIDI bridge matching the real map.
- `docs/HANDOFF.md`: resolves which implementation is current when alternatives coexist.

Maintain the Brain/Hands boundary. Screenshot-loop agents can make judgments and perform visible UI work; they should not own beat-critical timing.

For offline multi-plan work, use `python -m brain.plan_cli`. Track notes use
`note`; transition notes/effects use `transition get|set|clear --author ...`.
Use `mark` to write lifecycle state and `status` to read artifact staleness.
Mutations require the revision from `show --json` or an intentional `--force`.

## DJ quality standard

- Do not equate a playlist with a DJ performance.
- Ground cue points and verse/chorus claims in real analysis or synced lyrics.
- Preserve intentional `dj_notes`; identify tracks by exact `track_id`, not title alone.
- Dry-run plans and render transition previews before a full live set.
- Treat Ernest's audible feedback as higher-quality evidence than a plausible plan.
- After interruption or failure, restore deck, recording, crossfader, EQ, keylock, and effect state deliberately.

## Media publishing

For full upload masters and social derivatives, read `references/media-export.md`.

The default teaser renderer is:

```bash
python3 agent/hermes-skill/scripts/render_transition_teaser.py --help
```

It keeps complete horizontal artwork inside a 1080x1920 card, hard-cuts at a supplied musical transition, encodes H.264/AAC, and verifies the result. Do not report a media artifact as complete until `ffprobe`, full decode, scene timing, audio-level inspection, and visual inspection pass.

Use FFmpeg for deterministic batches. Use the currently recommended stable OpenCut version only for interactive refinement; recheck both OpenCut READMEs because the active/stable recommendation can change.

## YouTube operations

Read `references/youtube-channel-oauth.md` before configuring or using access.

Expected public channel:

```text
https://www.youtube.com/@claw-dj
UClafA-9ft1J1iAKo1JMZmwQ
```

Verify `channels.list(mine=true)` returns that channel before any write. Default API uploads to private. Require Ernest's confirmation for uploads, publishing/scheduling, public metadata edits, comment writes/moderation, and deletion.

Never request or expose passwords, 2FA codes, recovery codes, browser cookies, OAuth tokens, or client-secret contents.

## Portable reconstruction

Read `references/profile-portability.md` and `docs/HERMES_AGENT_SETUP.md`.

The reviewed Git kit is the default distribution. It reproduces identity, project context, workflows, and scripts without copying profile databases, histories, caches, binaries, or credentials. A full profile export is optional private state migration, not the default way to install this project agent.

## Installation

For a dedicated profile named `clawdj`, follow `docs/HERMES_AGENT_SETUP.md`. The essential structure is:

```bash
PROFILE_HOME="$HOME/.hermes/profiles/clawdj"
mkdir -p "$PROFILE_HOME/skills"
cp agent/hermes-profile/SOUL.md "$PROFILE_HOME/SOUL.md"
cp -R agent/hermes-skill "$PROFILE_HOME/skills/clawdj"
cp -R agent/pdd-skill "$PROFILE_HOME/skills/prompt-driven-development"
hermes -p clawdj config set terminal.cwd "$PWD"
clawdj -s clawdj,prompt-driven-development
```

Inspect destinations before copying into a profile that is not new.

## Common pitfalls

1. Hardcoded stale paths: discover the repository root and media paths on the current machine.
2. Wrong implementation: consult `docs/HANDOFF.md` before choosing between overlapping code paths.
3. BPM is not a beatgrid: tag BPM can exist while Mixxx still has no persisted
   `BeatGrid-2.0`; phrase and guided-format work requires the written grid.
4. Exactly one persistent beatgrid gap: Mixxx commits the analyzed deck's
   pending grid only after loading a different track; eject and quit do not.
   Current `analyze_via_mixxx` performs this flush, so verify it if the symptom
   returns.
5. Planner/executor count drift: a body ride of N beat events transitions on
   the next beat, N+1. Verify that phase arithmetic models that actual anchor.
6. Human ride lock overridden at runtime: `trust_ride_beats` bodies must not
   carry a runtime phase anchor; automatic correction must preserve modulo-four
   bar position, not only odd/even parity.
6b. Off-by-one snare: Mixxx ticks can lock while snares do not. Flip the
   **outgoing** `ride_beats` by ±1. Do not slide the incoming `cue_seconds`
   one beat later. `trust_ride_beats` means "do not shorten the song," not
   "refuse the one-count snare fix the ear just asked for." See
   `user_stories/story__when_i_blend_i_match_the_snare_not_just_the_beat.md`.
7. End-of-track arithmetic that ignores overlaps: incoming audio is already
   advancing during its fade-in, and the outgoing fade also needs runway. The
   runtime reserves the next anchor, full transition, and safety margin from
   live Mixxx duration/playposition; do not remove that clamp.
8. Wrong YouTube identity: verify the canonical channel ID before writes.
9. Media that merely exists: fully verify outputs; do not stop after FFmpeg exits zero.
10. Profile-as-distribution: do not ship private state when reviewed Markdown and scripts are enough.
11. Credentials in Git/chat: store and authorize them locally on each machine.
12. Unattended public actions: private-first and confirmation-gated is mandatory.

## Verification checklist

- [ ] Active branch is not `master`.
- [ ] Current project context and implementation path were read from the repository.
- [ ] Relevant tests, dry runs, builds, or media checks passed.
- [ ] Generated media and personal-library state stayed out of Git.
- [ ] Public/external writes received confirmation.
- [ ] `PROGRESS.md` and `docs/HANDOFF.md` reflect durable state changes.
