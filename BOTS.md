# BOTS.md: Rules for bots working in this repo

These rules apply to every bot and AI agent that touches this repo, including
Ernest's Grok Bot teammates and any coding agent.

## Bot rules

- Act only as the GitHub account **yeung-assistant**.
- **Never push to `master`.** Always work on a branch and open a pull request.
- Never merge your own pull request. Ernest reviews and merges.
- Never commit secrets, tokens, or credentials.
- Marketing posts and outreach are drafts only. Never publish them without
  Ernest's go.

## Git workflow

- Periodically `git checkout master && git pull` to get the latest changes.
- Do all work on your own non-master branch (for example `bots/<topic>`).
  Never commit to `master`.
- Regularly pull `master` and rebase your working branch onto it
  (`git fetch origin && git rebase origin/master`) to avoid conflicts.
- After rebasing a branch that's already pushed, update it with
  `git push --force-with-lease` only. This is allowed only on your own unmerged
  branches. Never force-push `master` or anyone else's branch.
