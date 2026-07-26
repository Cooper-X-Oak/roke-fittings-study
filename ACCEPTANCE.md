# 当前验收边界

本阶段交付对象是用户提供的 `DN80CL2500气动串级式装配体.STEP` 对应的六语义组轻量 GLB 与经过重新导演的专业商业 Animatic，不是完整 CAD/BOM 或数字孪生。该模型按 STEP 产品树识别为气动串级式调节阀，不得继续沿用球阀的 90° 阀球旋转叙事。

唯一可执行验收由 `governance/project-validation.json` 定义。人工描述、历史汽车实验测试或旧页面部署状态不能替代控制面验收命令。

## 必须证明

- 实际视觉检查的源资产、工具和转换路径可追溯；不可见或未确认结构被明确标记。
- 每个商业镜头都有几何保留、合并、重建、实例化和删除决定。
- GLB 恰好暴露六个镜头语义组，并能支持完整、执行器至推杆线性动作、串级内件揭示、流路视觉化、局部特写和成组装配状态。
- Animatic 恰好包含五个连续镜头；不得使用黑场、隐藏剪辑、相机瞬移或穿入狭窄几何内部。
- 每一 canonical frame 的相机 roll 为 0°，FOV 变化受限，镜头保持完整产品或阀体空间参照。
- 内部结构通过外壳透明度、灯光焦点和适度语义组分离解释；不得以眩晕性 FPV 运镜代替产品认知。
- 页面必须形成可追溯的“克制工业权威”创意方向：更安静的文字层级、石墨与冷钢主色、单一铜色焦点、清楚停顿；不得把该方向冒充为未提供的企业品牌规范。
- 确定性逐帧时间线、五镜头实拍和完整固定时长播放必须证明叙事连续、易懂且无突发黑帧。
- 产品事实、视觉推断和未解决声明分开记录。
- 不把几百个 CAD 零件、维修仿真、CFD 或 FEA 纳入当前交付。

## 复验命令

```powershell
python governance/validate_control_plane.py entry --rules governance/project-rules.json --validation governance/project-validation.json --entry-id revise-control-valve-story
python governance/validate_control_plane.py accept --rules governance/project-rules.json --validation governance/project-validation.json --run-checks --workdir .
```
