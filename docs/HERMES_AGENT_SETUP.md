# Lightweight clawdj Hermes setup on a new Mac

This is the preferred portable setup for a second personal machine. It recreates the clawdj agent's identity, repository context, and repeatable procedures from small reviewed files in Git instead of copying a full Hermes profile archive.

## What this reproduces

- TARS/clawdj identity and operating posture.
- The project mission, architecture, branch rules, and safety policy.
- The Mixxx engineering workflow recorded in this repository.
- The verified WAV-to-video and 9:16 teaser procedure.
- The YouTube OAuth scope and confirmation policy.
- A small deterministic social-teaser renderer.

## What it deliberately does not reproduce

- Model-provider credentials or OAuth tokens.
- Google passwords, browser sessions, or YouTube refresh tokens.
- Hermes conversation history, `state.db`, caches, logs, or bundled binaries.
- Personal memory that is unrelated to this project.
- Mixxx GUI preferences, effect-slot state, its database, or macOS permissions.
- Music, stems, recordings, rendered videos, or the derived `brain/data/` library.
- Bit-for-bit model behavior. Use the same Hermes version, provider, model, and reasoning effort for the closest behavior, but generation remains nondeterministic.

This distinction is why the Git kit is small and safe while a full profile export can be many megabytes.

## 1. Install prerequisites

Install Hermes from the current official instructions:

<https://hermes-agent.nousresearch.com/docs>

Install repository tooling:

```bash
brew install uv ffmpeg
xcode-select --install   # only if `swift --version` is unavailable
```

`ffmpeg`/`ffprobe` render and verify media. Swift/AppKit renders branded PNG cards on macOS without Pillow, ImageMagick, or an FFmpeg `drawtext` build.

The full live-DJ environment has additional prerequisites, especially the patched Mixxx build. Follow `docs/SETUP_NEW_MACHINE.md` and `docs/BUILD_MIXXX.md` after the agent bootstrap.

## 2. Clone and install claw-dj

```bash
git clone git@github.com:InServiceOfX/claw-dj.git
cd claw-dj
uv sync
```

If testing a documentation branch before it is merged, switch to that branch explicitly. Normal fresh installs should use the reviewed default branch.

## 3. Create the isolated Hermes profile

```bash
hermes profile create clawdj \
  --no-skills \
  --description "Dedicated agent for developing and operating claw-dj: Mixxx control, DJ intelligence, media publishing, and YouTube workflows."
```

`--no-skills` opts this profile out of seeding Hermes's full bundled skill
catalog. That keeps the dedicated profile minimal; install additional skills
later only when the workflow needs them. Omit the flag if the second agent is
intended to be a broad general-purpose Hermes installation as well as clawdj.

Profile creation normally creates the `clawdj` shell alias. If it does not:

```bash
hermes profile alias clawdj
```

Set the repository as the working directory:

```bash
hermes -p clawdj config set terminal.cwd "$PWD"
```

## 4. Install the identity and skill

Use a copy for isolation or a symlink for automatic updates after `git pull`.

### Copy option

Run only in a newly created profile where the destinations do not already exist:

```bash
PROFILE_HOME="$HOME/.hermes/profiles/clawdj"
mkdir -p "$PROFILE_HOME/skills"
cp agent/hermes-profile/SOUL.md "$PROFILE_HOME/SOUL.md"
cp -R agent/hermes-skill "$PROFILE_HOME/skills/clawdj"
```

### Symlink option

This keeps the installed identity and skill tied to the checked-out repository:

```bash
PROFILE_HOME="$HOME/.hermes/profiles/clawdj"
mkdir -p "$PROFILE_HOME/skills"
ln -s "$PWD/agent/hermes-profile/SOUL.md" "$PROFILE_HOME/SOUL.md"
ln -s "$PWD/agent/hermes-skill" "$PROFILE_HOME/skills/clawdj"
```

Before using either recipe on a non-fresh profile, inspect the destinations. Do not overwrite an existing `SOUL.md` or skill without reviewing it.

## 5. Authenticate the model provider locally

Provider credentials are machine-local and must not enter Git. For the current OpenAI Codex OAuth provider:

```bash
hermes -p clawdj auth add openai-codex
hermes -p clawdj model
```

Choose the intended provider/model in the interactive picker. If you use another provider, follow its current Hermes documentation rather than copying a credential file from the first Mac.

Reasoning and model selection are separate:

```text
/model
/reasoning medium
/reasoning high
```

Use `medium` for routine operation and `high` for difficult engineering, debugging, or research.

## 6. Verify the reconstructed agent

```bash
hermes profile show clawdj
hermes -p clawdj doctor
clawdj -s clawdj
```

Inside the session, ask:

```text
Summarize the claw-dj mission, the brain/hands architecture, the Git branch policy, the social-teaser verification gates, and the YouTube publishing confirmation policy. Cite the repository files you used.
```

A successful response should cite `AGENTS.md`, `PROGRESS.md`, `docs/HANDOFF.md`, and the `clawdj` skill. It should say that DJing is more than playlist selection, that timing-sensitive work belongs in Hands, and that API uploads default to private.

## 7. Media smoke test

Confirm tools:

```bash
ffmpeg -version
ffprobe -version
swift --version
python3 agent/hermes-skill/scripts/render_transition_teaser.py --help
```

For a real render, follow `agent/hermes-skill/references/media-export.md`. Keep WAV, artwork, cards, and rendered clips outside the repository.

## 8. Recreate external integrations separately

- YouTube: follow `agent/hermes-skill/references/youtube-channel-oauth.md`; authorize through Google's browser consent flow on each machine.
- Mixxx/library: follow `docs/SETUP_NEW_MACHINE.md`.
- macOS computer control: grant Accessibility and Screen Recording only when a task requires them.
- Social accounts: authorize each official API/CLI separately; do not transfer browser cookies.

## Updating the portable agent

After repository changes:

```bash
git pull
```

A symlink installation sees updated skill/profile files immediately in the next Hermes session. A copied installation must be reviewed and recopied manually.

## When a full profile export is still appropriate

Use `hermes profile export` only when you intentionally want private history, memories, profile-local tools, and other state to migrate together. Treat that archive as sensitive. For a reproducible project agent, this Git-based kit should be the default.
