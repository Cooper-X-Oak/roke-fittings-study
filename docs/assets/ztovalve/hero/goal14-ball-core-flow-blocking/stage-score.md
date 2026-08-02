# Goal 14 Ball-Core Multi-Direction Anatomy + 90 Degree Flow Blocking

## Authority

- User-approved direction: 以球为稳定核心，按图册爆炸图做多方向有序离散；先验证不锈钢商业材质；用克制流线表达介质通路。
- Output boundary: 96 帧低清 blocking 预演，12fps，8 秒。不生成 240 帧正式序列，不替换首页，不触碰客户原始 STEP/PDF。
- Evidence: `../fixed-ball-valve.glb`, `../model-audit.json`, catalogue structure reference `../fixed-ball-valve-structure-reference.jpg`, and the user-provided brochure screenshot showing metal/soft-seat structure and a multi-direction exploded assembly.
- Product facts allowed: ZTOVALVE / 正拓阀门, fixed ball valve asset, ball-centered exploded structure, valve body, ball, stem/drive zone, seat/seal system, fasteners, catalogue/contact intent.
- No-claim boundary: 不声明压力等级、材质牌号、硬度、密封等级、零泄漏、防火、防静电、DBB/DIB、流量、介质类型、维修步骤或真实装配顺序，除非客户后续确认。

## Video Direction

- Thesis: 采购访客应看到“正拓阀门的固定式球阀以球体为功能核心，结构围绕球体有序展开，并通过 90 度启闭说明介质通路”。
- Viewer arc: 真实不锈钢产品 -> 球心锚定 -> 多方向解剖 -> 阀座/密封围绕球体 -> 球体 90 度启闭 -> 流线通过 -> 商业回正。
- Dominant staged-image rule: 球体是视觉锚点；动作可以大，但所有方向都必须服务球体、轴线和通路。
- Camera grammar: 固定三分之四商业观察角，微推近和微回正；不做自由 orbit，不追随小五金。
- Product grammar: 球体保持中心；左右阀体沿管道轴离散；阀杆/驱动区向上；下支撑向下；阀座/密封环围绕球体左右分层；只有球体做 90 度功能旋转。
- Flow grammar: 流线只在球体通道对齐后出现，3-5 条低饱和蓝白线沿管道轴穿过球体；不表达压力、流量、零泄漏或具体介质。
- Lighting/material: 银灰不锈钢、抛光球体、暗色密封层、细小高光螺栓；低反差灰白工业舞台，避免科幻发光。
- Rhythm: 前 16 帧建立商业材质；17-45 帧多方向离散；46-61 帧围绕球体分层；62-77 帧 90 度启闭；78-86 帧流线通过；87-96 帧商业回正和 hold。
- Negative list: 不让阀体/阀座/密封圈/小五金跟着球体旋转；不做随机飞散；不做强透明壳体；不做粒子喷射；不把图册材料/硬度文字变成首页宣称。

## Frame Blocks

| Frames | Beat | Purpose | Motion Contract |
| --- | --- | --- | --- |
| 001-016 | 不锈钢商业入场 | 先验证真实材质，而不是 CAD 灰模。 | 完整产品、抛光球体弱可读、商业灯光扫过，无部件分离。 |
| 017-045 | 球心锚定多方向离散 | 按图册爆炸图建立“球体为中心”的结构秩序。 | 球体保持画面中心；阀体左右打开；上驱动向上，下支撑向下，小五金从属离散。 |
| 046-061 | 阀座密封围绕球体 | 说明球体不是孤立部件，密封系统围绕它工作。 | 阀座/密封环沿左右轴轻微分层，靠近球体但不旋转。 |
| 062-077 | 90 度启闭功能动作 | 给出真正有意义的旋转。 | 只有球体做 90 度四分之一转；阀体、阀座、密封、紧固件不跟转。 |
| 078-086 | 介质通路流线 | 用克制流线说明通路，而非性能承诺。 | 球体通道对齐后出现 3 条蓝白流线，沿管道轴穿过中心。 |
| 087-096 | 商业回正 hold | 从结构解释回到首页产品主视觉。 | 零件回归，流线收掉，终帧为完整不锈钢产品。 |

## Review Gates

- 球体必须是画面中心和功能中心，不能被左右阀体或小五金抢走。
- 多方向离散必须看得出左/右/上/下/环形层级，不是随机爆炸图。
- `ballTurn` 可以明显，但只能作用于球体候选组；阀座、阀体、密封圈和小五金不得跟转。
- 流线只表达 flow path，不得暗示压力、流量、零泄漏、DBB/DIB 或具体介质。
- 不锈钢材质要先商业上成立；如果像塑料、铬玩具或灰模，不进入正式渲染。
- blocking 通过前，不生成 240 帧正式 AVIF，不替换首页。

## Open Client Confirmations

- 球体孔向和开/关方向是否与模型和客户图纸一致。
- 阀杆、连接轴、平键、球体哪些属于真实随动组。
- 固定轴、轴承是否仅作为支撑表达，是否不得随球体旋转。
- 是否允许在最终版本里继续使用抽象流线表示介质通路。
- 是否允许公开表达具体座封材料、硬度、密封等级或 DBB/DIB。
