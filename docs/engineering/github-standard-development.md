# GitHub PR integration policy

- Use this policy only after an explicit user request for an Issue, pull request,
  protected-branch integration, merge, release, or deployment.
- Preserve `github-pages-repo` as the canonical Pages source workspace. A PR
  integration branch may point at a verified checkpoint from the current
  `workspace/<short-slug>` branch; do not rewrite the Pages source branch or
  change the configured Pages source merely to create the PR.
- Create or reuse one Issue that states the source branch, target branch,
  included checkpoint, acceptance checks, and that Pages remains published from
  its current verified source until merge changes the content on `main`.
- For the PR, use `main` as the verified integration target and an isolated
  `docs/<issue>-<short-slug>` branch/worktree that starts at the verified source
  checkpoint. Do not push implementation directly to `main`.
- Before requesting review, run the declared control-plane entry and acceptance
  commands, `git diff --check`, inspect the complete `main...HEAD` comparison,
  and confirm the public Pages route remains HTTP 200 with the selected GOP 6
  story. Record any unavailable or skipped check in the PR.
- Do not merge, close the Issue, delete branches or worktrees, force-push, or
  change the Pages publication source unless the user explicitly authorizes the
  specific action.
