# Goal 20 Blender/Cycles Material Status

Generated: 2026-08-02

## Boundary

- This pass validates the STEP-first Blender/Cycles minimum loop only.
- It does not replace the homepage hero.
- It does not render the 240-frame release sequence.
- Material names are visual lookdev treatments based on supplier descriptions, not certified alloy or coating claims.

## Source

- Source STEP: `D:/program/WXrecord/xwechat_files/wxid_p21a7v5850v922_6db6/msg/file/2026-08/固定式球阀(1).STEP`
- Source STEP SHA256: `3ddb291607730239f5a067e9d1730acda0931874c5f42c4ac0c358516efa2547`
- Goal 20 mesh: `goal20-step-mesh.glb`
- Blender: `D:/TOOLS/render-pipeline/apps/Blender-5.2.0/Blender Foundation/Blender 5.2/blender.exe`

## Technical Feasibility

Passed for the minimum loop.

- Blender 5.2.0 LTS runs from D:.
- The supplied STEP is converted into a dedicated Goal 20 GLB.
- Blender imports 138 mesh instances.
- STEP-derived part identity is recoverable for the key review families:
  valve body, bonnet, ball, seat, seat seals, packing, stem/drive stack, fasteners and springs.
- All six requested material presets are present:
  `castBlastedStainless`, `machinedStainless`, `polishedStainlessBall`, `graphitePacking`, `softSealPtfe`, `fastenerStainless`.
- Five stills render successfully in the `smoke` profile.

## Current Visual Read

Not approved as final commercial material lookdev yet.

- The assembled and exploded views are readable, but still lean toward a pale engineering preview rather than a finished KeyShot-like industrial render.
- The `polishedStainlessBall` is correctly isolated to the ball, but its reflection is still too blocky and studio-card-like.
- The `castBlastedStainless` treatment is cleaner than the first pass, but the bead-blasted / sandblasted satin finish is still not convincing enough for hero use.
- The body/flange close-up now frames the right geometry, but the surface needs stronger midtone metal and finer, more realistic microtexture.
- The fastener/seal close-up confirms the grouping, but material separation remains subtler than desired.

## Recommendation

Use this pass as a feasibility checkpoint, not as the final visual baseline.

The next useful step is a focused Blender lookdev pass before any 24-frame or 240-frame animation work:

- replace the simple grey/white reflection cards with a more controlled product-photography light tent;
- tune the ball with softer strip reflections and fewer hard black/white blocks;
- make the cast body darker and more satin, with procedural fine bead-blast roughness instead of visible cloudy texture;
- separate fasteners and dark packing more aggressively so the render does not collapse into one light-silver material family;
- render one or two low-resolution stills per iteration before running any high-resolution proof.

