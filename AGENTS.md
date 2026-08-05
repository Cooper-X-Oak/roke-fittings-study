# Repository workflow

这里是 ztovale 的官方网站的开发构建仓库，ztovale 官网是由和平广告打造的，1:1仿制 roke 的企业阀门官网。

- Before any repository file, Git, or GitHub mutation, use `$apply-repo-workflow`.
- workflow.default: `live-workspace-development`
- workflow.allowed: `live-workspace-development`, `github-standard-development`, `read-only-review`
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
  `github-standard-development` workflow and follow `$apply-repo-workflow`
  references.
  A scoped GitHub Pages publication from the current verified development
  branch is permitted only when the current control-plane entry and acceptance
  checks explicitly authorize it.
- If workflow resolution or preflight fails, remain read-only and report the blocker.
