# 当前验收边界

本阶段把已经批准的五节拍脚本翻译为固定时长灰模 Animatic，并只验证：

1. `CASCADE_TRIM` 的实际解码几何能否拆出四个非空连通岛，使三级阀笼候选
   与阀座候选具备独立镜头位移，而不是只改变发光；
2. 阀体闭合期间，核心是否在建立位置关系前持续可读，且没有黑场或隐藏
   相机迁移；
3. 中央机械轴、相机和部件状态能否在正放、反放及往返取样中保持确定性。

本阶段不得生成 runtime story manifest、最终 WebGL 产品页、最终材质、
性能结论、自动创意发布、合并或部署。

## 必须满足

- Camera previs 为固定 `30 fps`，每个 canonical frame 恰有一条完整状态；
  五个节拍连续覆盖完整时间轴。
- 每帧记录相机位置、目标、roll、FOV、焦距、完整部件状态、四个 trim
  几何岛状态、阀体透明度、灯光、节拍身份和遮挡值。
- `CASCADE_TRIM` 必须从真实解码几何得到四个非空连通岛；若只能把整个
  `CASCADE_TRIM` 一起移动或只改变灯光，本阶段验收失败。
- 四个几何岛只按相机可读的轴向顺序编号；未经独立证据不得断言每个岛
  分别对应哪一个源 STEP 标签，也不得把镜头顺序描述为制造或维修顺序。
- 阀体闭合区间必须存在“核心可读 → 阀体建立位置 → 最终闭合”的连续
  透明度变化；全帧遮挡始终为零。
- 正放必须依次观察五个批准节拍，反放必须以精确逆序观察五个节拍。
- 同一进度的前后往返取样必须复现相机、焦距、阀体与所有活动部件状态，
  不得累计漂移。
- 最后 15% 固定为完全静止的英雄停顿。
- 灰模页面、关键帧、正反向播放证据和结构化浏览器采样必须来自实际 GLB。
- `creative-development.json` 停在 `animatic` 阶段，确认状态仍为 pending；
  不得生成自动 release 或 runtime manifest。

## 复验命令

```powershell
python governance/validate_control_plane.py entry --rules governance/project-rules.json --validation governance/project-validation.json --entry-id author-control-valve-animatic
python governance/validate_control_plane.py accept --rules governance/project-rules.json --validation governance/project-validation.json --run-checks --workdir .
```
