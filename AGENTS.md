# Repository workflow

- Before any repository file, Git, or GitHub mutation, use `$apply-repo-workflow`.
- workflow.default: `github-standard-development`
- workflow.allowed: `github-standard-development`, `read-only-review`
- workflow.policy_docs: `docs/engineering/github-development.md`
- If workflow resolution or preflight fails, remain read-only and report the blocker.