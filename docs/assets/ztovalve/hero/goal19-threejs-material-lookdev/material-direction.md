# Goal 19 Three.js Material Direction

## Scope

Goal 19 is a fast Three.js material-lookdev loop derived from Goal 16. It keeps
the existing `fixed-ball-valve.glb` animation grouping and upgrades the visual
material families from supplier terminology. It does not replace the homepage,
does not render the 240-frame sequence, and does not claim certified material
grades.

## Supplier Terms

- `castBlastedStainless`: 不锈钢硅溶胶铸造材质，表面有喷砂效果; investment cast stainless steel with bead-blasted / sandblasted satin finish.
- `polishedStainlessBall`: 不锈钢高亮度抛光球体; mirror polished stainless steel ball.
- `machinedStainless`: 机加工不锈钢零件; machined stainless steel.
- `graphitePackingDarkSeal`: 石墨填料 / 黑色密封圈; graphite packing or dark sealing ring.
- `softSealPtfe`: PTFE 或浅色软密封视觉; PTFE or light soft-seat visual treatment.
- `fastenerStainless`: 不锈钢紧固件; stainless fasteners.

## Render Intent

- The valve body, bonnet, and casting-heavy shell should read satin, granular,
  and metallic, not white plastic or mirror chrome.
- The ball should stay the brightest and most reflective object, but with softer
  studio reflections and fewer harsh black-white blocks.
- Machined shafts, rings, and drive/support details should sit between the cast
  shell and mirror ball in brightness.
- Dark seals, packing, and cavities should create readable black-level contrast.
- The stills are visual lookdev references for review before any 240-frame
  sequence or homepage connection.
