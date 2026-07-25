# 验收边界

本项目只有在以下边界全部通过时才视为可交付。部署成功本身不等于验收通过。

## 内容与路由

- 八个真实页面及其 `index.html` 地址均返回 HTTP 200。
- 页面语言为 `zh-CN`，标题和可见主标题存在。
- 桌面端、390px 移动端和 320px 回流环境均不得出现可见俄文、HTTrack 路径泄露或横向溢出。
- 可翻译的界面文案、占位符和可访问名称使用简体中文；品牌、型号、标准、邮箱、电话和技术单位保持原样。
- 所有站内导航链接返回 HTTP 200。

## 资源、动画与媒体

- 无零字节、临时、缺失或超过 100MB 的发布文件。
- 三套 AVIF 帧分别为 240、240、170 张。
- 首页拆解动画在 0%、20%、40%、60%、80%、100% 六个进度点均有非空画面和六个不同帧。
- 首页第二段动画在五个进度点均有非空画面和五个不同帧。
- 关于页动画只绘制已加载帧；快速滚动和缺帧场景不得出现空白或 JavaScript 错误。
- 懒加载图片滚动进入视口后必须成功加载；视频必须可播放并使用 fast-start MP4。
- 360° 模型必须打开、渲染 WebGL 画布并可关闭。

## 实时 3D 性能门禁

`/experiment/` 的性能不是人工观感项，而是永久 E2E 契约。数值来源为 `tests/performance-budget.json`，完整规则见 `docs/engineering/3d-performance-contract.md`。

- Poster 必须先于实时 3D 可交互状态可见，加载过程中不得以空白 Canvas 作为首屏产品视觉。
- 页面必须暴露下载、解码、Shader 编译、首个 3D 帧和可交互就绪的有序 `roke:*` Performance Marks。
- 固定实验室网络下的 LCP、首个 3D 帧和可交互就绪时间必须在预算内；CLS 不得超过 0.1。
- 初始请求数、总传输量、模型、Poster、关键 JavaScript 和解码器 WASM 均不得突破预算。
- 1440×1000、DPR 2 环境下，Canvas drawing buffer 像素数和有效 pixel ratio 必须受限。
- 滚动必须改变实时 3D 状态，反向滚动必须恢复接近原始装配画面。
- 滚动阻尼收敛后必须停止持续 RAF；静止页面不得永久占用 GPU 渲染循环。
- GLB、WASM 或 WebGL 失败时，Poster、中文回退说明和核心正文必须继续可用。
- `prefers-reduced-motion: reduce` 下，主视觉保持稳定并停止持续渲染。
- GitHub 托管 Headless/SwiftShader 的绝对 FPS 和显存仅作为证据，不作为 PR 硬门禁；代表性真机基线建立后才能升级为 Release Gate。
- 不得通过增加重试、放宽超时、删除断言或排除资源来消除失败；放宽预算必须提交前后证据、适用用户、替代方案和回滚条件。

## 静态交互与隐私

- 移动菜单可通过点击和 Escape 键打开、关闭。
- 网格、视频、360° 模型及其他自定义控件支持键盘，并具有中文可访问名称。
- 键盘焦点始终可见。
- 静态镜像不得向 Bitrix、Mango、Yandex 或原站接口发送跟踪、表单、上传和目录 AJAX 请求。
- 无后端能力的控件必须给出中文静态镜像说明，不得报英文服务器错误或静默失败。

## 响应式与降级

- 1440×1000、390×844、320×800 三个代表性视口通过。
- `prefers-reduced-motion: reduce` 下，滚动帧动画保持静态，CSS 动画和过渡被压缩。
- 关于页核心介绍文本在 JavaScript 禁用时仍然可见。
- 页面控制台不得出现未处理的 JavaScript 异常。

## 复验命令

```powershell
node scripts/localize-pages.mjs docs --check
node scripts/sanitize-static-pages.mjs docs --check
node scripts/verify-pages.mjs docs /roke-fittings-study
npm ci
npx playwright install chromium
npm run test:e2e:3d
```

常规镜像浏览器验收和部署烟测必须针对公开 GitHub Pages 地址执行。实时 3D PR 性能门禁使用固定本地静态服务器以获得可重复结果；合并后的公开部署仍需继续通过 HTTP、资源与运行时烟测。
