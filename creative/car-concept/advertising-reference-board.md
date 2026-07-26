# 汽车概念模型广告参考板

## 任务边界

- 对象：`docs/experiment/assets/models/car-concept-web.glb`
- 目的：为通用网页实时 3D 产品叙事开发一个可审片的汽车案例。
- 本阶段产物：参考方法、创意路线、五镜头脚本和固定时长 Animatic。
- 本阶段不做：最终 WebGL 页面、品牌声明、生产级工程解释或真实制造顺序。

## 模型对创意的实际约束

模型审查结果：

- 2,605,580 bytes；
- 97 个独立 Mesh 节点、109 个 Primitive、211,306 个三角面；
- 93/97 个网格节点具有可读名称；
- Draco 几何压缩，14 张 KTX2/BasisU 纹理；
- 没有内置动画、骨骼或相机；
- 能力分类为 `structured-named-parts`。

适合广告特写的区域：

- 前后轮圈、制动盘和制动块；
- 方向盘、仪表结构、座椅和座舱骨架；
- 车门、机盖、挡风玻璃和整体红色外壳；
- 四轮、车轴和车身之间的空间关系。

不适合承担广告主镜头的区域：

- 名为 `Engine` 的节点只有 60 个三角面，只能作为低细节结构占位；
- 车轴和若干机械节点能说明空间关系，但不能证明真实传动或动力流；
- 节点层级不是制造 BOM，不能把视觉汇聚描述成真实装配顺序。

因此，本项目不采用“发动机精密特写 → 动力流”路线。开场改用模型细节最可靠的
“轮圈 / 制动 / 接地点”，再通过圆形 Match Cut 进入方向盘和驾驶空间。

## 一手案例与可迁移方法

### 1. Honda — Cog

来源：[Honda Engine Room — Cog](https://www.honda.co.uk/engineroom/cog/)

叙事命题：

> 工程能力可以通过一连串可理解的物理因果成为故事。

可迁移方法：

- 每一个运动必须给下一个运动提供视觉原因；
- 零件本身不是信息，零件之间的关系才是信息；
- 观众不需要先懂工程，也能通过因果理解“精密协作”。

对当前模型的限制：

- 当前 GLB 没有真实机械约束或验证过的动力链；
- 只能借鉴“视觉因果”，不能假装展示真实机械因果。

### 2. Mercedes-AMG ONE — Core Systems CGI

来源：[Relative Berlin — Mercedes-AMG ONE](https://www.relative.berlin/project/mercedes-benz)

叙事命题：

> 把不可见的动力、能量和空气动力学系统变成各自清晰的视觉语言。

可迁移方法：

- 一个镜头只承担一个系统级认知；
- 灯光、粒子和运动语言用于区分不同系统；
- 技术受众与设计受众可以通过同一影片获得不同层次的信息。

对当前模型的限制：

- 当前概念模型没有可验证的空气动力或混合动力数据；
- 不使用能量流、气流或 F1 动力等具体工程隐喻。

### 3. Formula E Gen2 Car Exploded

来源：[AltSpace — Formula E Gen2 Car Exploded](https://www.behance.net/gallery/76199617/Formula-E-Gen2-Car-Exploded?locale=en_US)

叙事命题：

> 拆解的意义是让隐藏技术成为“未来赛车”的证据。

可迁移方法：

- 拆解必须围绕一个传播命题，而不是平均展示所有零件；
- 环境、灯光、模型细节和汇聚节奏共同建立可信度；
- 爆炸和重组可以构成影片的认知高潮。

对当前模型的限制：

- 原案例为可信技术展示补建了大量工程细节；
- 当前模型不能承受“每颗螺丝都真实”的视觉承诺；
- 只采用受控的系统分层，不做满屏零件爆炸。

### 4. Toyota LC150 Movies

来源：[Dassault Systèmes — Toyota LC150 Movies](https://www.3ds.com/insights/customer-stories/toyota-lc150-movies)

叙事命题：

> 先选择需要证明的功能，再为每个功能选择外观、X-Ray 或穿越镜头。

可迁移方法：

- 产品范围和价值信息先于摄像机运动；
- 从外部到内部的穿越用于解释驾驶空间，而不是炫技；
- 镜头尺度跟随信息尺度变化。

对当前模型的限制：

- 当前模型没有真实车型功能简报；
- Animatic 只表达“结构围绕驾驶空间形成”，不宣称座椅、载物或越野功能。

### 5. Petrol Ofisi — Adaptech Maxima

来源：[Lighthouse VFX — Adaptech Maxima](https://www.lhvfx.com/project/adaptech-maxima)

叙事命题：

> 宏观道路、发动机内部和微观保护通过连续尺度转换成为一段旅程。

可迁移方法：

- 用尺度转换连接镜头，而不是用硬切拼接段落；
- 前一镜头的形状或运动成为下一镜头的入口；
- 从宏观进入内部后，必须回到完整产品完成传播闭环。

对当前模型的限制：

- 不进入低细节发动机；
- 将“轮圈圆形 → 方向盘圆形”作为可由现有模型支持的 Match Cut。

### 6. Porsche 911 Turbo S — Encounter

来源：[Arevera — Porsche Encounter Case Study](https://vimeo.com/260363413)

叙事命题：

> 先用一个情绪词定义影片，再让摄影、动画和光线共同表达它。

可迁移方法：

- 先确定情绪核心，再决定镜头速度和表面光；
- 最终英雄镜头不是技术阶段，而是情绪结论；
- 车辆运动和光线要表现同一种性格。

对当前模型的限制：

- 当前模型没有品牌定位，不能借用 Porsche 的“brutality”；
- 本项目的候选情绪定义为：`PRECISION BECOMES PRESENCE / 精密成为存在感`。

### 7. Mercedes-Benz Genuine Parts — Give Something Back

来源：[Storz & Escherich — Give Something Back](https://www.storzescherich.de/portfolio/mb-gsb/)

叙事命题：

> 一次连续穿越内部结构的镜头，可以把“复杂产品”转成沉浸式体验。

可迁移方法：

- 连续镜头通过空间关系维持方向感；
- 结构细节的出现顺序与情绪节奏同步；
- 产品片可以同时具有解释性和电影感。

对当前模型的限制：

- 当前网页 Animatic 不采用无休止的一镜到底；
- 只在镜头 1–2 使用一次明确的空间连续动作，随后进入可理解的系统全景。

## 综合决策

当前汽车模型最值得迁移的组合不是“发动机拆解”，而是：

```text
Honda Cog 的视觉因果
+ Adaptech Maxima 的尺度 / 形状 Match Cut
+ Toyota 的信息驱动镜头
+ Formula E 的受控系统分层
+ Porsche 的单一情绪定义
```

候选影片命题：

> 精密并不藏在某一个零件里；它从接地点开始，围绕驾驶空间组织，最终成为完整形态。

候选情绪：

> `PRECISION BECOMES PRESENCE / 精密成为存在感`

视觉原则：

- 一个时刻只有一个焦点；
- 背景保持深灰黑，不用白色技术面板与模型争夺注意力；
- 红色车漆只在系统汇聚后逐步成为主色；
- 解释阶段使用窄光、局部光和受控暗部；
- 最终阶段才使用完整车身表面光；
- 文案作为电影字幕层，不制造网页仪表盘；
- 所有拆分沿少数清晰轴线，禁止全方向随机爆炸。
