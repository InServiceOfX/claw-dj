# Local branch audit — 2026-10-30

Compared all21 local branches with freshly fetched `origin/master` and local
`master`, both at `2cbbe7c`. Reviewed ancestry, patch equivalence and unmatched
changes; tested the two substantial unmerged candidates in isolated Git archive
snapshots. Current runtime fix is committed as `5b19d79`. No branch was rebased,
merged, deleted or pushed. Merge simulations wrote temporary Git tree objects
without changing refs or the worktree. Remote-only branches were outside scope.

## Keep and integrate

| Branch | Finding | Recommendation |
| --- | --- | --- |
| `fix/three-rnb-backbeats-2026-10-29` | Original cues, strict source-clock starts, human-approved235 delay, deadline scheduling, cleanup and regression coverage.456 isolated tests pass. | Keep. Review/merge this current work after the corrected109 start is heard live. Current plan/approvals remain unchanged. |
| `fix/scan-stops-check-again` | `8eaa835` adds dead-editor scan recovery, PID tracking/schema migration and Curate progress/log UI. Missing from master.7 targeted tests pass. | Best next rebase/merge candidate. Simulated merge conflicts only in `PROGRESS.md` and `docs/HANDOFF.md`; code merges automatically. Re-run modern collection/scan checks after integration. Preserve conservative handling of old scan rows with no PID. |
| `feat/snare-align-blends` | `1ec2b94` adds a Rust multiband rhythm analyzer/solver, cache/enrichment, annotations, telemetry and gradual-fade runtime. `5b6ebd7` adds plan-scoped playback-note editing in Arrange. These modules/UI are absent from master. | Retain for staged integration. Port the note editor separately, then analyzer/cache work. Reconcile runtime timing and safety before a whole-branch merge. |

Rhythm branch validation:39 Rust workspace tests,50 Python backbeat/enrichment/
gradual-blend tests and the Node playback-note behavioral checks pass on its
own snapshot. Built its CLI offline, using at most2 compiler workers. No actual
Mixxx playback, library writes, model downloads or OBS configuration changes.

Passing branch tests do not establish compatibility with today's master:

- Simulated merge has15 conflicting files across runner, builder, Arrange,
  scripts, prompts, stories and documentation.
- Its runtime reads the15Hz `playposition` clock and uses a60ms default timing
  threshold. Its policy can continue a gradual fade while reporting mismatch.
  Preserve the current timestamped clock, deadline scheduling,30ms gate and
  explicit human-approved launch target when integrating it. Do not silently
  replace these with that older policy.
- Its2 commits are substantial independent feature work, not merely old commit
  hashes for functionality already present. Do not delete this branch.

## Already merged: recommend deleting the local branch pointers

Each is an ancestor of `master`; ordinary `git branch -d` applies. Keep `master`
and the current fix branch. No remote deletion is implied.

| Branch | Tip |
| --- | --- |
| `chore/pdd-agent-workflow` | `502c762` |
| `docs/marketing-media-and-veltria` | `87a554d` |
| `docs/portable-hermes-clawdj` | `d3cf70e` |
| `docs/social-channel-links` | `e9486b6` |
| `feat/build-review-mix-sheet` | `9dd5a22` |
| `feat/dj-transition-refinements` | `b890aa5` |
| `feat/hip-hop-anthology-review-2026-10-27` | `2cbbe7c` |
| `feat/load-new-music-collection` | `0897588` |
| `feat/mix-stem-layers-and-phrase-locks` | `14a80a2` |
| `feat/preview-track-in-browser` | `2f42173` |
| `feat/review-backbeat-audition` | `2cbbe7c` |
| `feat/shared-dj-brain-providers` | `b93ed52` |

The anthology and audition pointers currently equal master exactly. Private mix
artifacts/recordings live outside tracked Git history; deleting these branch
pointers would not delete those files or replace their dedicated backups.

## Superseded without ancestry: recommend deletion after reviewing this evidence

These are not all eligible for ordinary `-d`. Do not bulk-force-delete them
based only on their age or an unmatched-commit count.

| Branch | Evidence |
| --- | --- |
| `feat/50cent-era-arc-ear-pass` | Both branch-only commits are patch-equivalent to master; `git cherry master BRANCH` has no `+` entries. |
| `feat/build-mix-plan-refactor` | The3 rewritten commits map to master `83b607c`, `e5b5cf1`, `5d41693`. Main provider/optimizer/refinement modules and showcase code/tests match their counterparts; later master extends the builder. Re-merging the September versions adds no missing feature. |
| `backup/build-review-mix-sheet-pre-rebase-a8b19b9` | The OBS implementation, prompts and tests match the merged `9dd5a22` branch. Remaining tree differences concern missing duration-estimate files and old script/docs state; the backup offers no extra OBS capability. |
| `docs/nemoclaw-hai-install` | Sole unmatched commit `37dd937` documents old HAI CLI/NemoClaw installation. Current DJ-brain workflow has moved away from NemoClaw. No complete missing product feature to merge. |
| `fix/nemoclaw-hermes-sandbox-name` |3 obsolete sandbox-name commits, plus whole-library default and candidate-count cap already implemented in current GUI/`pick_candidates.py`. Reintroducing the removed provider is inappropriate. |

Recommended order: live-check/current fix review, integrate stopped-scan
recovery, port Arrange playback-note editing, then evaluate rhythm analysis
and runtime integration separately. Keep the heard R&B artifact frozen during
these source integrations.

## Reproducing the audit

`git merge-base --is-ancestor BRANCH master`, `git cherry master BRANCH`,
targeted commit/file comparisons and
`git merge-tree --write-tree --name-only master BRANCH` provided the history
and conflict evidence. Branch tests ran from extracted snapshots, without
checking out or changing the user's branches. Raw per-branch ancestry and
commit details are retained privately in
`Data/claw-dj-reviews/local-branch-audit-2026-10-30.json` under the workspace.
