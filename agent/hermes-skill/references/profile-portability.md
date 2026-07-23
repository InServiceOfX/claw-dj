# Lightweight profile portability

A Hermes profile and a project skill are separate layers:

- Profile: model/provider config, credentials, state, history, memories, installed tools, and `SOUL.md`.
- Repository kit: reviewed identity, project rules, reusable procedures, and small deterministic scripts.

For another personal development Mac, prefer the repository kit documented in `docs/HERMES_AGENT_SETUP.md`.

## Minimal reconstruction

```bash
git clone git@github.com:InServiceOfX/claw-dj.git
cd claw-dj

hermes profile create clawdj \
  --no-skills \
  --description "Dedicated agent for developing and operating claw-dj: Mixxx control, DJ intelligence, media publishing, and YouTube workflows."

PROFILE_HOME="$HOME/.hermes/profiles/clawdj"
mkdir -p "$PROFILE_HOME/skills"
cp agent/hermes-profile/SOUL.md "$PROFILE_HOME/SOUL.md"
cp -R agent/hermes-skill "$PROFILE_HOME/skills/clawdj"

hermes -p clawdj config set terminal.cwd "$PWD"
hermes -p clawdj auth add openai-codex
hermes -p clawdj model
hermes -p clawdj doctor
clawdj -s clawdj
```

This is intentionally small enough to review in Git. It does not contain private conversation history, profile databases, model caches, logs, credentials, binaries, media, or music-library data.

`--no-skills` prevents the dedicated profile from seeding Hermes's full
bundled skill catalog. Omit it if the destination agent should also be a broad
general-purpose installation, or install extra skills individually later.

## What Markdown can and cannot reproduce

Markdown and small scripts can reproduce:

- identity and tone;
- mission and safety rules;
- which repository context to read;
- engineering and media workflows;
- OAuth scopes and confirmation gates;
- deterministic renderer behavior.

They cannot reproduce:

- exact nondeterministic model outputs;
- private or unrecorded memories;
- provider credentials and OAuth grants;
- application state and OS permissions;
- installed software versions;
- Mixxx databases, effect slots, controller state, or media libraries.

Use the same Hermes release, provider, model, and reasoning effort if behavioral similarity matters. Verify the machine state rather than assuming it matches.

## External workspace and data

Clone the repository separately on each machine. Transfer music/library analysis according to `docs/SETUP_NEW_MACHINE.md`; do not put it in the Hermes profile or Git.

Update the profile working directory after cloning:

```bash
hermes -p clawdj config set terminal.cwd /absolute/path/to/claw-dj
```

Authorize YouTube separately on each machine using `references/youtube-channel-oauth.md`.

## Full personal profile migration

A full export remains useful when Ernest intentionally wants history, memories, profile-local tools, and other private state:

```bash
hermes profile export clawdj -o ~/Desktop/clawdj-profile.tar.gz
shasum -a 256 ~/Desktop/clawdj-profile.tar.gz
```

On the destination:

```bash
hermes profile import ~/Downloads/clawdj-profile.tar.gz --name clawdj
hermes profile alias clawdj
hermes -p clawdj doctor
```

Named-profile exports exclude `.env` and `auth.json`, but can still include sensitive memories and history. Treat the archive as private. Do not use it as the default project distribution.

## Reasoning controls

```text
/model
/reasoning
/reasoning none|minimal|low|medium|high|xhigh
```

`/reasoning show|hide` affects display, not effort. Use medium for routine work and high for difficult engineering/research.
