# Live workspace development policy

- The repository root is the canonical implementation and live-review surface.
- `main` remains protected and must not receive implementation pushes.
- Normal development stays in the current checkout on
  `workspace/<short-slug>` or `theme/<theme-slug>` branches.
- Before switching branches in place, preserve meaningful work in a focused
  commit, push the current same-name branch to `origin`, and verify the remote
  ref. Do not stash, clean, reset, force-push, or discard work.
- GitHub Pages publishes from `/docs`. A user-authorized, control-plane-gated
  Pages publication may set the Pages source to the current verified
  `workspace/<short-slug>` branch and `/docs`, without merging to `main`.
  Before changing that source, record the initial Pages state, confirm the
  current branch is clean and synchronized to `origin`, and run the declared
  publication entry check. After configuration, wait for the public URL to
  return HTTP 200 and prove the selected route exposes `#story` and the GOP 6
  media. Record the source branch, source path, commit, public URL and any
  previous Pages state for rollback. Restore the recorded Pages source if the
  release acceptance gate cannot pass. Issue, PR, merge, protected-branch
  integration, branch deletion, and worktree deletion remain unauthorized.
- Before a verified checkpoint, run the project-declared acceptance command,
  `git diff --check`, inspect the complete diff, and verify there are no
  zero-byte or temporary files, unprefixed same-site root references, or files
  above GitHub's 100 MB limit.
- This repository is an unofficial educational mirror. Do not add credentials,
  working forms, analytics secrets, or user-data collection.
