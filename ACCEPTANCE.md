# 当前验收边界

本阶段只交付用户提供的 `DN80CL2500气动串级式装配体.STEP` 对应的
五镜头商业分镜脚本与所选创意路线。不得生成或修改相机逐帧预演、
Animatic、WebGL、GLB、首帧海报、渲染证据或公开页面。

唯一可执行验收由 `governance/project-validation.json` 定义。已经发布的
旧 Animatic 只作为观看失败证据，不能反向定义新脚本。

## 必须满足

- 五个镜头共同回答“一条命令如何被组织成精密机械动作”。
- 五镜头必须在景别、观察轴、构图、可见动作、转场装置和节奏上存在
  实质差异，不能把五次轻微 dolly 和透明度变化重新命名为叙事。
- 每镜明确一个叙事问题、一个观众认知结果和一个视觉主语。
- 每镜完整定义起止状态、运镜、灯光、布局、文案、转场、节奏、停顿和
  真实性边界。
- 允许有动机的匹配剪辑和几何擦镜；禁止用黑场、无动机瞬移、持续横滚
  或无目的内部 FPV 制造变化。
- 产品事实必须停留在 STEP 标签和可见装配关系内；不得声称性能、认证、
  工况、失效方向、维修顺序或仿真结果。
- 当前 `creative-development.json` 必须停在 `five-shot-script` 阶段，
  自动释放状态为 pending，且不得保留当前相机预演或 Animatic 记录。

## 复验命令

```powershell
python governance/validate_control_plane.py entry --rules governance/project-rules.json --validation governance/project-validation.json --entry-id author-control-valve-shot-script
python governance/validate_control_plane.py accept --rules governance/project-rules.json --validation governance/project-validation.json --run-checks --workdir .
```
