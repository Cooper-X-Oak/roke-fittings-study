# Repository workflow

- Before any repository file, Git, or GitHub mutation, use `$apply-repo-workflow`.
- workflow.default: `live-workspace-development`
- workflow.allowed: `live-workspace-development`, `github-standard-development`, `read-only-review`
- workflow.policy_docs: `docs/engineering/live-workspace-development.md`, `docs/engineering/github-standard-development.md`
- workflow.remote_sync: `current-branch`
- workflow.remote: `origin`
- workflow.branch_switch: `in-place`
- The repository root is the canonical implementation, live-review, and
  interaction-validation workspace. Verified checkpoints synchronize to the
  same-name remote branch. Development branches use `workspace/<short-slug>`;
  visual variants may use `theme/<theme-slug>`.
- Issue, PR, protected-branch integration, merge, release, and deployment are
  outside the default workflow. When the user explicitly requests Issue/PR
  review or protected-branch integration, select the allowed
  `github-standard-development` workflow and follow its dedicated policy.
  A scoped GitHub Pages publication from the current verified development
  branch is permitted only when the current control-plane entry and acceptance
  checks explicitly authorize it and the Pages publication policy is followed.
- If workflow resolution or preflight fails, remain read-only and report the blocker.

# Governance control plane

- Rules: `governance/project-rules.json`
- Validation: `governance/project-validation.json`
- Development entry: `python governance/validate_control_plane.py entry --rules governance/project-rules.json --validation governance/project-validation.json --entry-id author-control-valve-commercial-look`
- Development acceptance: `python governance/validate_control_plane.py accept --rules governance/project-rules.json --validation governance/project-validation.json --run-checks --workdir .`
- The rules and validation files above are the only current project authority.
- Missing, unreadable, duplicate, or version-mismatched control-plane artifacts fail closed.
