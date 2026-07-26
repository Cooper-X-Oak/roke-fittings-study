# 当前验收边界

本阶段只交付用户提供的 `DN80CL2500气动串级式装配体.STEP` 对应的
广告参考板、所选创意路线与五节拍连续商业分镜脚本。不得生成或修改相机
逐帧预演、Animatic、WebGL、GLB、首帧海报、渲染证据或公开页面。

唯一可执行验收由 `governance/project-validation.json` 定义。已经发布的
旧 Animatic 只作为观看失败证据，不能反向定义新脚本。

## 必须满足

- 全片共同表达“精密核心沿一条机械轴成为完整产品”这一单一产品命题。
- 五个镜头是同一连续变换中的五个认知节拍，不是五套互不相关的运镜：
  `核心显露 → 层级归位 → 阀体闭合 → 整机成立 → 英雄确认`。
- 每个节拍的起始产品状态必须承接上一节拍的结束状态；中央机械轴、世界
  空间和主要光线方向保持连续，并允许滚动正放与反放。
- 五个节拍必须带来五个不同的观众认知结果，但不强制使用不同观察轴、
  景别、构图或相机运动。
- 产品运动承担叙事，相机只负责发现、伴随、尺度转换和最终确认；禁止用
  黑场、无动机瞬移、持续横滚、无目的内部 FPV 或多次英雄绕飞制造变化。
- 每个节拍完整定义叙事目的、观众所得、起止状态、产品动作、活动组件、
  构图、相机职责、灯光、布局、文案、状态交接、节奏、停顿和真实性边界。
- 广告方法必须来自可追溯案例，并明确其可迁移方法和限制；案例不得为当前
  产品授权性能、品牌、工况或功能结论。
- 产品事实必须停留在 STEP 标签和可见装配关系内；不得声称性能、认证、
  介质路径、工况、失效方向、维修顺序或仿真结果。
- 当前 `creative-development.json` 必须停在 `five-shot-script` 阶段，
  自动释放状态为 pending，且不得保留当前相机预演或 Animatic 记录。

## 复验命令

```powershell
python governance/validate_control_plane.py entry --rules governance/project-rules.json --validation governance/project-validation.json --entry-id author-control-valve-shot-script
python governance/validate_control_plane.py accept --rules governance/project-rules.json --validation governance/project-validation.json --run-checks --workdir .
```
