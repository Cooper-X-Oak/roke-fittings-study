# 当前验收边界

本阶段从已经通过的 18 秒、30 fps、540 状态灰模 Animatic 派生一个
“预渲染视频由滚动寻帧控制”的真实浏览器实验，用于比较 GOP 3、6、10
三种短关键帧间隔。实验不得改变五节拍叙事、相机、零件、灯光或真实性边界。

本阶段允许生成无 UI 逐帧素材、三种匹配编码、Pages 实验路由和本机浏览器
运行证据；不允许替换现有 GLB 路由、生成 runtime story manifest、作普遍
性能结论、合并或部署。

## 必须满足

- 从同一确定性状态采样器导出恰好 540 张无 UI 产品帧；分辨率、帧率、
  首帧、节拍边界和英雄帧可复验。
- GOP 3、6、10 使用同一帧源、分辨率、30 fps、编解码器系列和质量策略；
  唯一设计变量是关键帧间隔。
- 每个视频都必须是 18 秒、540 帧、无音轨、低于 GitHub 单文件 100 MB
  限制，并用 FFprobe 记录字节数、帧数和关键帧数。
- 页面文案、章节和控制状态必须保留为 HTML/CSS，不烘焙进视频。
- 页面必须先显示非空产品海报；视频未出现可用帧时不得显示空白。
- 滚动控制器只保留最新目标，最多一次在途 seek；必须等待浏览器实际显示
  目标附近帧，而不是把 `currentTime` 赋值当作完成。
- 三个版本必须在同一浏览器、同一视口、同一 DPR、同一本地 origin 和明确
  cache 条件下测试：
  - 冷启动第一张可用视频帧；
  - 有序正向寻帧；
  - 有序反向寻帧；
  - 快速交替寻帧；
  - 重复目标的时间误差与超时。
- 文件大小与浏览器寻帧数据必须分开报告；不得用“文件更小”推断“交互更快”。
- 现有灰模 Animatic 的几何分离、阀体闭合、五节拍、正反顺序和确定性门禁
  必须继续通过。

## 复验命令

```powershell
python governance/validate_control_plane.py entry --rules governance/project-rules.json --validation governance/project-validation.json --entry-id build-control-valve-video-scrub-experiment
python governance/validate_control_plane.py accept --rules governance/project-rules.json --validation governance/project-validation.json --run-checks --workdir .
```
