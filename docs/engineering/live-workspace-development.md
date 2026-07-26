# Live workspace development policy

- The repository root is the canonical implementation and live-review surface.
- `main` remains protected and must not receive implementation pushes.
- Normal development stays in the current checkout on
  `workspace/<short-slug>` or `theme/<theme-slug>` branches.
- Before switching branches in place, preserve meaningful work in a focused
  commit, push the current same-name branch to `origin`, and verify the remote
  ref. Do not stash, clean, reset, force-push, or discard work.
- GitHub Pages publishes from `/docs`; release, deployment, Issue, PR, merge,
  protected-branch integration, branch deletion, and worktree deletion are not
  authorized by the default workflow.
- Before a verified checkpoint, run the project-declared acceptance command,
  `git diff --check`, inspect the complete diff, and verify there are no
  zero-byte or temporary files, unprefixed same-site root references, or files
  above GitHub's 100 MB limit.
- This repository is an unofficial educational mirror. Do not add credentials,
  working forms, analytics secrets, or user-data collection.
