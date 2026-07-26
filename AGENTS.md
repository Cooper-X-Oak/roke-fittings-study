# Repository workflow

- Before any repository file, Git, or GitHub mutation, use `$apply-repo-workflow`.
- workflow.default: `github-standard-development`
- workflow.allowed: `github-standard-development`, `read-only-review`
- workflow.policy_docs: `docs/engineering/github-development.md`
- If workflow resolution or preflight fails, remain read-only and report the blocker.

# Governance control plane

- Rules: `governance/project-rules.json`
- Validation: `governance/project-validation.json`
- Development entry: `python governance/validate_control_plane.py entry --rules governance/project-rules.json --validation governance/project-validation.json --entry-id implement-car-story-runtime`
- Development acceptance: `python governance/validate_control_plane.py accept --rules governance/project-rules.json --validation governance/project-validation.json --run-checks --workdir .`
- The rules and validation files above are the only current project authority.
- Missing, unreadable, duplicate, or version-mismatched control-plane artifacts fail closed.
