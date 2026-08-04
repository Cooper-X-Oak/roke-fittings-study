# Goal 25-D Zoned Body Material Proof

Generated: 2026-08-03T00:43:47.869346+00:00

## Boundary

- This pass isolates the real STEP-derived `阀体` mesh only.
- It keeps the valve body as one mesh but assigns material IDs per polygon using geometry-derived manufacturing zones.
- The clean main render disables explicit body-local trace/scratch curve geometry.
- Legacy 25-C-style trace curves are rendered only in the left side of the comparison image.
- It does not render the full valve, replace a homepage hero, publish Pages, or create animation frames.
- Material names are visual lookdev targets, not certified alloy or surface-finish claims.

## Material Library

- `G25-SS-CAST-BLASTED-SATIN-01`: 阀体主壳/柱体 - investment-cast stainless body, bead/sand blasted satin, non-directional, metal reflection retained
- `G25-SS-MACH-FLANGE-RADIAL-01`: 法兰正面 - clean machined stainless flange face with broad satin reflection; no explicit curve scratches
- `G25-SS-BRUSH-NO4-LINEAR-01`: 法兰外圆侧面 - brushed/satin stainless on flange outside diameter, directional but still industrial
- `G25-SS-MACH-BORE-CIRCULAR-01`: 内孔/流道入口 - dark clean machined bore, reflection-retaining and not dirty; no circumferential curve scratches
- `G25-SS-EDGE-BURNISH-01`: 倒角/棱线/凸筋高点 - thin bright bevel highlights from clean chamfers and final deburring
- `G25-SS-MACH-BOLT-BORE-DARK-01`: 螺栓孔内壁 - clean darker machined bolt-hole walls with crisp rims and no drawn witness rings
- `G25-SS-ROOT-DARK-AO-01`: 凹槽根部 - dark reflection-retaining clean metal in shoulder grooves and root transitions; explicitly not dirt

## Zone Assignment Evidence

- Inferred flow axis: `x`
- Estimated bore inner radius: `0.07843`
- Estimated flange outer radius: `0.13814`

- `G25-SS-CAST-BLASTED-SATIN-01`: 25462 faces, area 0.28445763
- `G25-SS-EDGE-BURNISH-01`: 170 faces, area 0.00083303
- `G25-SS-MACH-FLANGE-RADIAL-01`: 9410 faces, area 0.12215705
- `G25-SS-ROOT-DARK-AO-01`: 2390 faces, area 0.00793834
- `G25-SS-BRUSH-NO4-LINEAR-01`: 2357 faces, area 0.04408381
- `G25-SS-MACH-BOLT-BORE-DARK-01`: 1368 faces, area 0.0259487
- `G25-SS-MACH-BORE-CIRCULAR-01`: 521 faces, area 0.02488127

## Clean PBR Direction

- Main still: `02-clean-pbr-stainless-look`
- Comparison still: `00-old-vs-clean-comparison`
- Clean main trace visibility: `False`
- Legacy comparison trace objects: `114`
- Material rebuild target: clean machined flange, dark but clean bore, clean bolt holes, blasted cast body, and bevel highlights.

## Open Reference Assets

- `polyhaven-studio-small-09-1k-hdri` (CC0): `docs/assets/ztovalve/hero/goal20-blender-cycles-step-proof/studio_small_09_1k.hdr`; local=True; usage: environment reflection and soft studio value reference
- `ambientcg-metal009-1k-jpg` (CC0): `docs/assets/ztovalve/hero/goal25d-zoned-body-material-proof/references/Metal009_1K-JPG.zip`; local=True; usage: clean machined stainless roughness/normal/base-value reference

## External References Used

- [Poly Haven - studio_small_09 HDRI](https://polyhaven.com/a/studio_small_09): Use a real CC0 studio HDRI for metal reflections instead of flat grey world lighting.
- [ambientCG - Metal009 PBR material](https://ambientcg.com/view?id=Metal009): Use a traceable CC0 metal material reference for clean stainless roughness, normal and value ranges.
- [Adobe Substance 3D - The PBR Guide](https://www.adobe.com/learn/substance-3d-designer/web/the-pbr-guide-part-2): Keep metalness, roughness, normal/height and base reflection values separated; do not fake rough stainless by whitening diffuse color.
- [OpenPBR Surface Specification](https://academysoftwarefoundation.github.io/OpenPBR/): Use layered base/coat/roughness/normal/tangent controls for real material behavior instead of one monolithic shader.
- [BSSA - Bead and shot blasted stainless steel finishes](https://bssa.org.uk/bssa_articles/specifying-bead-and-shot-blasted-stainless-steel-finishes-and-their-applications/): Blasted stainless is a non-directional low-reflective satin finish, not a powder-white coating.
- [BSSA - Mechanically polished, brushed and buffed stainless finishes](https://bssa.org.uk/bssa_articles/specifying-mechanically-polished-brushed-and-buffed-stainless-steel-finishes-and-their-applications/): Machined, brushed and polished zones need named finish intent, abrasive direction and surface quality boundaries.
- [Casting Source - Surface finish requirements and inspection](https://www.castingsource.com/articles/2024/11/21/surface-finish-requirements-and-inspection): Casting texture should be treated as roughness, waviness and lay produced by process plus finishing, not as uniform noise.

## Output

- `00-old-vs-clean-comparison`: docs/assets/ztovalve/hero/goal25d-zoned-body-material-proof/stills/00-old-vs-clean-comparison.png
- `01-old-trace-scratch-look`: docs/assets/ztovalve/hero/goal25d-zoned-body-material-proof/stills/01-old-trace-scratch-look.png
- `02-clean-pbr-stainless-look`: docs/assets/ztovalve/hero/goal25d-zoned-body-material-proof/stills/02-clean-pbr-stainless-look.png
- `03-material-zone-id`: docs/assets/ztovalve/hero/goal25d-zoned-body-material-proof/stills/03-material-zone-id.png
- `04-clean-flange-bore-close`: docs/assets/ztovalve/hero/goal25d-zoned-body-material-proof/stills/04-clean-flange-bore-close.png

## Review Questions

- Does the main cast/blasted shell keep a real metal value structure instead of becoming powder white?
- Does the clean machined flange read as precision stainless without drawn-on circular scratches?
- Do the dark bore and bolt holes stay clean rather than grimy?
- Are the edge highlights useful, or do they need to be restricted to fewer raised/chamfered features?
- Does the old-vs-clean comparison make the new aesthetic direction obvious enough?
