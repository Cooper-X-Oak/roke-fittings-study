# Goal 25-D Zoned Body Material Proof

Generated: 2026-08-03T00:16:00.004271+00:00

## Boundary

- This pass isolates the real STEP-derived `阀体` mesh only.
- It keeps the valve body as one mesh but assigns material IDs per polygon using geometry-derived manufacturing zones.
- It migrates restrained Goal 25-C explicit machining trace geometry back onto the flange face, main bore and bolt-hole zones.
- It does not render the full valve, replace a homepage hero, publish Pages, or create animation frames.
- Material names are visual lookdev targets, not certified alloy or surface-finish claims.

## Material Library

- `G25-SS-CAST-BLASTED-SATIN-01`: 阀体主壳/柱体 - investment-cast stainless body, bead/sand blasted satin, non-directional, metal reflection retained
- `G25-SS-MACH-FLANGE-RADIAL-01`: 法兰正面 - flat machined flange face with restrained explicit concentric tool-path trace migrated from Goal 25-C
- `G25-SS-BRUSH-NO4-LINEAR-01`: 法兰外圆侧面 - brushed/satin stainless on flange outside diameter, directional but still industrial
- `G25-SS-MACH-BORE-CIRCULAR-01`: 内孔/流道入口 - darker cylindrical machined bore with restrained circumferential cutting trace migrated from Goal 25-C
- `G25-SS-EDGE-BURNISH-01`: 倒角/棱线/凸筋高点 - thin brighter worn edges and bevel highlights from handling or final deburring
- `G25-SS-MACH-BOLT-BORE-DARK-01`: 螺栓孔内壁 - smaller darker, rougher machined cylindrical walls with local rim and inside-ring witness traces
- `G25-SS-ROOT-DARK-AO-01`: 凹槽根部 - dark reflection-retaining metal in shoulder grooves and root transitions; explicitly not lifted to powder white

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

## Migrated 25-C Trace Geometry

- Source manifest: `docs/assets/ztovalve/hero/goal25c-real-machining-traces/render-manifest.json`
- Applied trace IDs: `G25-TRACE-MACH-FLANGE-RADIAL-GEOM-01`, `G25-TRACE-MACH-BORE-CIRCULAR-GEOM-01`, `G25-TRACE-MACH-BOLT-BORE-DARK-GEOM-01`
- Implementation: explicit body-local bevel curve geometry parented to the STEP-derived valve body
- Flange trace rings per end: `9`
- Flange trace curve segments: `82`
- Bore circumferential rings: `10`
- Bore mouth rim objects: `4`
- Bolt-hole ring objects: `18`

## External References Used

- [Adobe Substance 3D - The PBR Guide](https://www.adobe.com/learn/substance-3d-designer/web/the-pbr-guide-part-2): Keep metalness, roughness, normal/height and base reflection values separated; do not fake rough stainless by whitening diffuse color.
- [OpenPBR Surface Specification](https://academysoftwarefoundation.github.io/OpenPBR/): Use layered base/coat/roughness/normal/tangent controls for real material behavior instead of one monolithic shader.
- [BSSA - Bead and shot blasted stainless steel finishes](https://bssa.org.uk/bssa_articles/specifying-bead-and-shot-blasted-stainless-steel-finishes-and-their-applications/): Blasted stainless is a non-directional low-reflective satin finish, not a powder-white coating.
- [BSSA - Mechanically polished, brushed and buffed stainless finishes](https://bssa.org.uk/bssa_articles/specifying-mechanically-polished-brushed-and-buffed-stainless-steel-finishes-and-their-applications/): Machined, brushed and polished zones need named finish intent, abrasive direction and surface quality boundaries.
- [Casting Source - Surface finish requirements and inspection](https://www.castingsource.com/articles/2024/11/21/surface-finish-requirements-and-inspection): Casting texture should be treated as roughness, waviness and lay produced by process plus finishing, not as uniform noise.

## Output

- `01-zoned-body-material-proof`: docs/assets/ztovalve/hero/goal25d-zoned-body-material-proof/stills/01-zoned-body-material-proof.png
- `02-material-zone-id`: docs/assets/ztovalve/hero/goal25d-zoned-body-material-proof/stills/02-material-zone-id.png
- `03-flange-bore-zone-close`: docs/assets/ztovalve/hero/goal25d-zoned-body-material-proof/stills/03-flange-bore-zone-close.png

## Review Questions

- Does the main cast/blasted shell keep a real metal value structure instead of becoming powder white?
- Do the flange face, bore and bolt-hole migrated trace families read as real manufacturing evidence without becoming decorative striping?
- Are the edge highlights useful, or do they need to be restricted to fewer raised/chamfered features?
- Does the dark groove/root treatment make the body feel heavier and more machined without looking dirty?
