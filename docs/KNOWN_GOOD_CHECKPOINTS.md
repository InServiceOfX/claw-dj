# Known-good checkpoints

Mixes Ernest listened to and liked, and the git tag of the code that built
them. Later commits may experiment freely; these are the "this sounded right"
points to come back to.

## `mix-to-listen-baseline-v1` (commit `b93ed52`, 2026-10-08)

`b93ed52` is also `master` (fast-forwarded and pushed 2026-10-08). The tag
itself is pushed only when `git push origin mix-to-listen-baseline-v1` runs.

The long continuous listen: most of each song's body played, gentle 32-beat
blends, verses respected. Built with **Mix to listen**, DJ brain
**Optimizer only** (no model needed), on the R&B cooldown set (68 songs).
The same code also built the 78-song R&B cooldown mix Ernest enjoyed later
the same day (Claude's review was rejected there, so that order was the
optimizer's too).

What the code at this tag does:
- whole-set optimizer order (best blends, snare-checkable pairs preferred);
- Mix to listen rides most of each song from its intro and blends out on a
  chorus / after a verse / in an instrumental part;
- direction words ("smooth", "long blend", …) no longer change Mix to listen
  blend length;
- DJ notes win in every Mix feel.

Plan files are not in git (`brain/data/` is ignored). The 68-song plan is
archived locally at
`brain/data/archives/2026-10-08_082758_-0700_rnb-cooldown-baseline/`.

## Going back to a checkpoint

History is never rewritten; going back is just another commit.

- **Try the old code without changing anything:**
  `git switch -c try-baseline mix-to-listen-baseline-v1`
- **Rewind the working branch to the checkpoint as a new commit** (keeps all
  later history, so nothing is lost):
  ```bash
  git restore --source mix-to-listen-baseline-v1 --staged --worktree -- .
  git commit -m "Rewind code to mix-to-listen-baseline-v1"
  ```
  To rewind only part of the code, name the files or folders instead of `.`.
- **Undo specific later commits** (also a new commit): `git revert <commit>`.

After any rewind, restart the playlist editor so it loads the code, then
rebuild the plan. A rebuild of the same set with the same settings
reproduces the checkpoint's numbers (blend length, share of each song played,
verse counts); a model review can still choose a different order.

## After the checkpoint (not yet a checkpoint)

- Build review answers once with no tools, sees a "mix sheet" (each song's
  length, verse/chorus outline, best-scoring next songs) and a versioned prompt
  `brain/llm_prompts/build_review.md`. First live test: Claude's review was
  accepted with the same blend/verse numbers as the baseline. Not yet listened
  to as a full mix.
