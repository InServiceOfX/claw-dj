# Continue refining the current mix with my preferred agent

As an experienced DJ, I want my preferred AI agent to inspect and refine the
current named mix plan, so I can improve individual transitions and arrangements
while preserving approved work and musical safeguards.

Accepted by Ernest on 2026-10-06 in
docs/intents/intent__one-shot-mixes-and-agent-refinement-of-the-curre-3dc013eb.md.

Acceptance:

- Codex, Claude Code, Grok Build, Hermes or another repository-capable harness
  can use the same plan-aware CLI/API without a special managed agent runtime.
- Inspect the current named plan, artifact, global plus plan DJ notes, source
  restrictions, overrides and revision before editing. Continue that plan in
  place; do not create a parallel mix or overwrite unrelated approved sections.
- Track notes, transition edits and order constraints retain author attribution
  and revision checks. An optional build base revision rejects stale work before
  model calls or writes; existing build callers remain compatible.
- CLI Build exposes the same provider and optional direction as GUI Build.
  Explicit profile/format choices remain available, and optimizer-only stays the
  default for legacy CLI calls. No new provider setting or credential store.
- Authored performances are refined through the existing performance compiler;
  generic Build must preserve its refusal to replace them, including manually
  edited generic-generated performances. Validate source regions and native
  events, and audition a small uncertain passage before revising a whole mix.
- Refresh in Arrange shows the updated plan, notes, transitions and staleness.
  Editing/building/compiling does not start playback or change source recordings.

<!-- pdd-story-prompts: prompts/brain/plan_cli_Python.prompt prompts/brain/plan_mix_build_Python.prompt prompts/brain/dj_brain_workflow_Python.prompt -->
