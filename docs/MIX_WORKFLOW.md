# First build, then refine the same mix

For a first pass, finalize the songs, run Analyze & enrich if any BPM is missing,
choose a mix feel and an available DJ brain, and press **Build mix plan**.
Direction is optional. With a provider selected, even a two-song set receives
an order review using the chosen feel and effective DJ notes. The model may
keep the optimizer's order; unsafe proposals or provider errors retain it with
an explanation. Optimizer-only works without a model.

The plan uses the established source exclusions, verse/phrase decisions,
backbeat matching, tempo/key compatibility, stem layering and gentle fades.
DJ showcase additionally asks the model for validated transition moves.
Existing approved measured recipes are consumed automatically; measurements
and approvals for arbitrary songs are not invented during Build. See
[measured advanced moves](ADVANCED_GENERIC_BUILDER.md). Review candidate order,
unverified blends and warnings before choosing the separate Start action.
A dry run checks execution, not how pleasant the result sounds.

## Continue with any repository-capable agent

Give Codex, Claude Code, Grok Build, Hermes or another agent this direction:

> Read AGENTS.md and docs/MIX_WORKFLOW.md. Inspect the current named mix and all
> effective DJ notes. Refine this same plan in place, preserve approved sections
> and source restrictions, and describe the changes for review. Use revision
> checks. Do not start playback. Audition uncertain musical choices in a small
> flagged live experiment before integrating them into the whole arrangement.

Run from the repository root using the project's Python environment. Read first:

```sh
python -m brain.plan_cli show --json
python -m brain.plan_cli status --json
```

`show` returns the active slug, revision, track notes, segments, constraints and
artifact. Specify `--plan <slug>` thereafter so a browser plan switch cannot
redirect the edit. Track and transition edits use the fresh `rev` and explicit
agent attribution, for example:

```sh
python -m brain.plan_cli note '<track-id>' 'ride_beats=192' --plan <slug> --author agent --base-rev <rev>
python -m brain.plan_cli transition set --from '<track-a>' --to '<track-b>' --note 'Preserve this blend' --author agent --plan <slug> --base-rev <fresh-rev>
```

Read again after each edit. A stale-revision error requires a fresh review;
avoid `--force` during collaborative editing. For a conventional or untouched
generic-generated plan, build using the desired current profile/provider:

```sh
python -m brain.plan_cli build --plan <slug> --profile mix-to-listen --provider llama-server --base-rev <fresh-rev>
```

`--brief` is optional; `--dj-format` remains available. Provider names match
the shared registry (for example `claude-cli`, `xai-api`, `hcompany-api`). Omitting
`--provider` retains the legacy optimizer-only default. This command does not
start audio. It checks the base revision before model calls and checks input
revisions again before publishing the built artifact.

For an authored `performance`, edit the existing source timeline deliberately
and compile it with `python -m brain.performance_cli --plan <slug>`. Generic
Build refuses to replace it. Read [shared performance](SHARED_PERFORMANCE.md)
and [live experiments](LIVE_MINI_EXPERIMENTS.md) before musical edits. Keep
measurement evidence and original songs out of Git; never replace live events
with finished-master playback. Source restrictions apply to every clip and loop.

Return to **Arrange → Refresh** to inspect the result and its staleness. A
provider's text review and an agent harness with repository/tools access are
different capabilities; choosing a provider does not launch a tool-using agent.
