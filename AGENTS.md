# AGENTS.md — claw-dj

## Mission

Build and operate `claw-dj`: an autonomous or semi-autonomous DJ that plays Mixxx like an instrument. Selection matters, but the defining work is phrase-aware transitions, beat-accurate execution, EQ, loops, cueing, effects, and a recognizable hip-hop/R&B DJ style. Do not reduce the project to playlist generation plus automatic crossfades.

## Start every session

1. Run `git status --short --branch` and confirm work is not happening on `master`.
2. Read `PROGRESS.md` for current commands and priorities.
3. Read `docs/HANDOFF.md` for architecture, implementation history, and known gaps.
4. Read the specific docs for the task. In particular:
   - `docs/ARCHITECTURE.md` — brain/hands split.
   - `docs/MIXXX_CONTROL_SURFACE.md` — reachable Mixxx controls.
   - `docs/DJ_TRANSITIONS_PLAYBOOK.md` and `docs/DJ_STYLE_GUIDE.md` — mixing craft.
   - `docs/SETUP_NEW_MACHINE.md` — music/database portability.
   - `docs/HERMES_AGENT_SETUP.md` — lightweight Hermes reconstruction.
5. In Hermes, load the repository skill from `agent/hermes-skill/` (installed as `clawdj`).

Do not ask the user to repeat context that is already in these files.

## Git discipline

- Work on a feature or documentation branch, never directly on `master`.
- Ernest reviews and merges to `master`; do not commit, push, open a PR, or merge unless he asks.
- Check the active branch again before every commit because Ernest may switch or merge branches himself.
- Preserve unrelated working-tree changes. Do not stage `.DS_Store`, generated media, personal library data, or credentials.

## Architecture discipline

The project contains multiple generations of similar code. Do not assume the newest-looking implementation is live.

- `brain/` performs judgment, analysis, curation, and planning.
- `hands/` and the Rust core execute deterministic, timing-sensitive Mixxx actions.
- `core-rust/` and `agent/` contain mature prior work integrated into this repository.
- `docs/HANDOFF.md` decides which implementation is current when alternatives coexist.

Trace a symbol and its usages before changing behavior. Validate DJ changes with dry runs, tests, transition previews, and live Mixxx only when appropriate.

## Data and secrets

- `brain/data/` is intentionally ignored because it contains derived personal-library state.
- Music, recordings, generated videos, OAuth credentials, API tokens, browser cookies, Mixxx databases, and Hermes state databases must not be committed.
- Regenerate or transfer library state using `docs/SETUP_NEW_MACHINE.md`.
- Reauthorize model providers and external services separately on each machine.

## Media publishing

For Mixxx WAV-to-video masters and 9:16 promotional clips, follow:

`agent/hermes-skill/references/media-export.md`

Use the checked-in renderer under `agent/hermes-skill/scripts/` for repeatable social clips. Keep rendered media outside Git unless the user explicitly wants a small reviewed asset committed.

Before reporting completion, probe every output, fully decode it, verify scene timing, inspect audio levels, and visually inspect at least one frame.

## YouTube integration

The dedicated channel is `https://www.youtube.com/@claw-dj`; its currently verified channel ID is `UClafA-9ft1J1iAKo1JMZmwQ`.

YouTube OAuth/API setup remains an active cross-machine priority. Follow:

`agent/hermes-skill/references/youtube-channel-oauth.md`

Never request a Google password, 2FA code, recovery code, browser cookie, raw access token, or refresh token. Default API uploads to private. Require explicit confirmation for uploads, publication/scheduling, public metadata edits, comment writes/moderation, and deletion.

## Definition of done

A task is complete only when:

- the requested artifact or behavior exists;
- relevant tests/builds or media verification pass;
- no unrelated user work was overwritten;
- `PROGRESS.md` and `docs/HANDOFF.md` are updated when project state or operational knowledge changed;
- the final report names exact files, commands, and any remaining blocker without invented results.
