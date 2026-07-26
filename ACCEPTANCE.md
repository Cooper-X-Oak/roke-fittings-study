# 当前验收边界

本阶段交付对象是用户提供的 `DN80CL2500气动串级式装配体.STEP` 对应的六语义组轻量 GLB 与专业商业 Animatic，不是完整 CAD/BOM、生产网页或数字孪生。该模型按 STEP 产品树识别为气动串级式调节阀，不得继续沿用球阀的 90° 阀球旋转叙事。

唯一可执行验收由 `governance/project-validation.json` 定义。人工描述、历史汽车实验测试或旧页面部署状态不能替代控制面验收命令。

## 必须证明

- 实际视觉检查的源资产、工具和转换路径可追溯；不可见或未确认结构被明确标记。
- 每个商业镜头都有几何保留、合并、重建、实例化和删除决定。
- GLB 恰好暴露六个镜头语义组，并能支持完整、执行器至推杆线性动作、串级内件揭示、流路视觉化、局部特写和成组装配状态。
- Animatic 恰好包含五个连续镜头、专业且有叙事动机的相机运动、遮挡驱动的内部转场、确定性逐帧时间线和渲染证据。
- 产品事实、视觉推断和未解决声明分开记录。
- 不把几百个 CAD 零件、维修仿真、CFD 或 FEA 纳入当前交付。

## 复验命令

```powershell
python governance/validate_control_plane.py entry --rules governance/project-rules.json --validation governance/project-validation.json --entry-id build-control-valve-shot-asset
python governance/validate_control_plane.py accept --rules governance/project-rules.json --validation governance/project-validation.json --run-checks --workdir .
```
