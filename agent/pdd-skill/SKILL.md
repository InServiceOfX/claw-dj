---
name: prompt-driven-development
description: "Use when the user says 'do PDD', asks to adopt or operate Prompt-Driven Development, or gives product intent for a PDD-managed part of claw-dj. Routes ordinary intent through the local PDD fork, preserves prompt source and tests, enforces brownfield characterization and human meaning gates, and reports executable evidence."
version: 1.0.0
author: Ernest + TARS
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [pdd, prompts, intent, specifications, testing, code-generation]
    related_skills: [clawdj, test-driven-development]
---

# Prompt-Driven Development for claw-dj

## Overview

This is the Hermes adapter for doing real Prompt-Driven Development (PDD) on `claw-dj`. It does not duplicate PDD policy. The canonical agent policy is the workspace's Git-versioned `PDD.md` router and the Monoclaw playbooks it names; the executable comes from Ernest's editable PDD fork.

The operating invariant is:

```text
ordinary product intent -> reviewed meaning -> versioned .prompt source
                        -> generated implementation -> executable evidence
```

The human owns intended meaning and acceptable proof. The agent owns command selection, paths, PDD metadata, prompt syntax, story/test mechanics, synchronization, and verification.

## When to use

Load this skill when:

- Ernest says `do PDD`, `use PDD`, or asks for Prompt-Driven Development.
- A task asks to adopt PDD for a bounded part of `claw-dj`.
- A product request, correction, removal, example, or constraint affects an already PDD-managed part.
- A matching `.prompt`, `.pddrc`, `architecture.json` entry, or project instruction establishes PDD ownership.
- A PDD prompt, generated unit, story, contract, regression, synchronization, or drift check needs repair.

Do not force PDD onto unrelated conventional code. Do not treat every file in a repository containing PDD artifacts as generated output.

## Canonical sources and installed executable

From the `claw-dj` repository root, the expected workspace layout is:

```text
../../PDD.md
../Monoclaw/docs/pdd/
../PromptDrivenDevelopment/pdd/
```

Before PDD-relevant work, read in this order:

1. `../../PDD.md`
2. `../Monoclaw/docs/pdd/PDD_NATURAL_LANGUAGE_AGENT_PLAYBOOK.md`
3. `../Monoclaw/docs/pdd/PDD_WITH_ANY_AGENT_HARNESS.md`
4. `../Monoclaw/docs/pdd/PDD_AFTER_SETUP.md` for ongoing product-intent work
5. `../Monoclaw/docs/pdd/PDD_INTENT_FIRST_WORKFLOW.md` for intent ownership and approval gates
6. Installed CLI help for the exact command being considered

If this layout differs on another machine, locate the workspace router and repositories rather than silently using stale remembered instructions.

Expected executable provenance on Ernest's current machine:

```text
checkout: ../PromptDrivenDevelopment/pdd
remote:   git@github.com:InServiceOfX/pdd.git
install:  uv tool install --editable .
command:  pdd
```

Verify rather than assume:

```bash
command -v pdd
pdd --version
pdd --help
pdd <command> --help
git -C ../PromptDrivenDevelopment/pdd remote -v
git -C ../PromptDrivenDevelopment/pdd status --short --branch
```

Installed help is authoritative when it differs from Markdown.

## What `do PDD` means

If Ernest says `do PDD` with a concrete product request, begin the discovery and read-only planning workflow immediately. Do not ask him to choose a command, input form, development-unit name, prompt path, story slug, or output filename.

If he says only `do PDD` with no product intent at all:

1. Inspect the repository, branch, PDD signals, and current project context.
2. Explain whether the repository or requested area is already PDD-managed.
3. Ask only: what behavior should happen, stop happening, or change?

That is the one required product input. No magic phrase is needed after PDD ownership exists; ordinary later corrections and constraints are intent events too.

## Workflow

### 1. Discover scope and ownership

From the exact project or subproject root:

```bash
git status --short --branch
```

Read `AGENTS.md`, `PROGRESS.md`, and `docs/HANDOFF.md`. Inspect for:

- `.pddrc`
- `architecture.json`
- `prompts/` and matching `*.prompt`
- `user_stories/`
- relevant tests and generated-output mappings

Classify the target as:

- existing PDD-managed part;
- PDD project with no matching part;
- conventional brownfield part requiring characterization before adoption; or
- greenfield scope.

Discovery is complete only when the exact repository/subproject boundary, branch policy, current behavior path, and PDD ownership evidence are known.

### 2. Plan ordinary intent read-only

For a feature request, correction, removal, or adoption request, pass the user's exact words and exact scope to the planner:

```bash
pdd intent plan \
  --text "<exact user request>" \
  --project-root "<exact project or subproject root>" \
  --json
```

The planner does not call a model or write project files. Inspect its classification, candidate targets, warnings, review fields, and `intent_id`.

Present a compact review card:

```text
What I heard:
What will change:
What must stay unchanged:
Important examples:
How we will prove it:
Affected product areas:
Open decisions:
```

Planning is complete only when Ernest has approved or corrected the meaning. Never report a product change as complete after `intent plan`.

### 3. Characterize brownfield code before adoption

For an existing conventional `claw-dj` unit:

1. Choose one bounded, strong-fit unit with a stable public interface.
2. Run its existing focused tests against untouched behavior.
3. Add characterization tests for important current public behavior.
4. Add negative tests for important forbidden side effects or data loss.
5. Run those tests and retain the real output.
6. Only then may `pdd intent apply` receive `--characterized`.

The flag is an assertion backed by evidence, not permission to skip the work. Do not convert the whole codebase at once. Good first candidates are deterministic validators, adapters, data transformations, policy modules, or scripts—not beat-critical experimental algorithms with unstable interfaces.

### 4. Apply only the exact approved plan

After meaning approval, invoke apply with the exact same request, title/source, scope, and planner ID:

```bash
pdd intent apply \
  --text "<same exact user request>" \
  --project-root "<same exact scope>" \
  --approve "<intent-id>" \
  --json
```

Add only flags justified by the approved route:

- `--characterized` only after Step 3 passed;
- `--kind correct|remove|replace` and `--supersedes <prior-id>` for explicit history-preserving changes;
- `--technology` for an approved greenfield stack decision;
- `--no-story` only when independent acceptance coverage is genuinely unnecessary;
- `--no-sync` only when intentionally stopping after source work.

Apply may invoke configured models, modify files, and synchronize generated output. Recheck the working tree immediately before running it. Preserve unrelated changes.

### 5. Respect the story approval gate

If apply exits with status `awaiting_story_approval`:

1. Read the reported human story file.
2. Present its source, one-sentence outcome, affected responsibilities, contract summary, assumptions, and missing negative cases.
3. Ask Ernest to approve or correct the meaning—not its syntax.
4. If corrected, edit the human story through the supported workflow; never hand-edit the generated contract.
5. Compute the current story file's SHA-256 with a real tool.
6. Rerun the same apply command with `--approve-story <current-sha256>`.

Never pass a stale, unreviewed, or guessed hash. Story approval does not implicitly approve the fuller component prompt.

### 6. Route bugs and advanced work correctly

Use installed help before every route. The key distinction is:

- Current observable failure: reproduce it with a failing test, then use the current `pdd bug` / `pdd fix` route when its issue/source requirements are satisfied.
- New or changed intended behavior without a current symptom: use the intent front door; advanced issue-backed work may route through `pdd change` and scoped synchronization.
- Existing established PDD unit: baseline tests, then synchronize only that unit.
- Approved story needing executable regression: inspect `pdd test --help`, generate from the story, inspect the test, and run it.
- Code changed first: back-propagate durable observable behavior with the supported `pdd update` route rather than leaving source truth in code alone.

Do not choose a route from command-name similarity. Confirm current help, side effects, model use, and target scope.

### 7. Verify the complete mold

After any mutating PDD workflow:

1. Inspect every changed prompt, story, contract, test, generated file, status file, and evidence path reported by PDD.
2. Run focused repository tests, then the broader relevant suite.
3. Check deterministic prompt contracts and rule coverage where configured.
4. Run semantic/LLM story checks only when authorized and label them separately.
5. Review `git status` and `git diff`; account for every changed file.
6. Confirm important `MUST NOT` rules have executable negative tests.
7. Confirm no generated output changed without corresponding prompt ownership.

For `claw-dj`, preserve the Brain/Hands boundary and run the project's real Python, Rust, dry-run, preview, media, or live-device checks appropriate to the affected part. A PDD command exiting zero is not sufficient evidence.

## Safety and scope gates

Do not infer authorization for:

- whole-project synchronization when one part is in scope;
- `--force` or overwrite behavior;
- paid or remote model calls not implied by the requested workflow;
- GitHub issue creation/comments, commits, pushes, branches created by agentic commands, PRs, or public actions;
- changing or deleting valid existing tests;
- regenerating brownfield code before characterization;
- committing credentials, music/library data, media, OAuth state, or PDD debug/core dumps.

Preview and inspect before broad or consequential operations. Stop on disagreement between Product Intent, `.prompt` source, stories, contracts, and tests; reconcile meaning before regeneration.

## Completion report

Report these categories separately:

- Intent preserved: exact human meaning and durable request/Product Intent paths.
- Prompt source: affected product part, behavior/interface changes, and `MUST` / `MUST NOT` rules.
- Generated artifacts: every code, story, contract, test, and metadata path changed.
- Human gates: which review cards, prompts, or stories Ernest approved.
- Deterministic evidence: exact test/build/dry-run results.
- Semantic evidence: story/prompt checks, model/provider, and reported cost when available.
- Remaining uncertainty: prompt-only claims, weak text-pin tests, missing hardware/ear validation, or tooling gaps.

Completion means accepted intent is durable, the affected prompt source agrees with independent tests/stories, scoped generation has finished, and executable evidence passes.

## Common pitfalls

1. Treating `do PDD` as permission to regenerate the whole repository. Scope to one approved behavior and bounded unit.
2. Running `intent apply` immediately on conventional brownfield code. Characterize first.
3. Teaching Ernest CLI mechanics. Run the commands yourself and ask only meaning-level questions.
4. Patching generated code and stopping. Promote durable behavior into prompt source/tests and synchronize.
5. Calling every source file generated. Require matching prompt or architecture ownership.
6. Reverse-engineering the canonical story from code. Derive it independently from preserved user intent.
7. Hand-editing generated story contracts. Correct the human story/source and use supported realignment.
8. Weak evidence inflation. Semantic checks, text-pin regressions, unit tests, dry-runs, ear tests, and live Mixxx validation prove different things.
9. Copied flags drifting. Re-read installed help.
10. PDD debug snapshots entering Git. Keep `.pdd/core_dumps/` and operational state under repository policy.

## Verification checklist

- [ ] Canonical workspace and Monoclaw playbooks were read.
- [ ] Installed PDD executable and relevant command help were verified.
- [ ] Exact project/subproject scope and PDD ownership were established.
- [ ] `intent plan` used the user's exact request and remained read-only.
- [ ] Meaning-level approval preceded mutation.
- [ ] Brownfield characterization and critical negative tests preceded `--characterized`.
- [ ] Story approval used the current reviewed SHA-256 when required.
- [ ] Synchronization was limited to approved affected units.
- [ ] Prompt, story, contract, test, generated-code, and evidence diffs were inspected.
- [ ] Focused and broader relevant project checks passed.
- [ ] Unrelated work, secrets, personal data, and generated media were preserved.
