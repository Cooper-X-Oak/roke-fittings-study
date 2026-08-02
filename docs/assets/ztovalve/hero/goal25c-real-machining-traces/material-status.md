# Goal 25-C Real Machining Traces

Generated: 2026-08-02T23:27:12.140423+00:00

## Boundary

- This pass isolates machining-trace implementation methods as reusable samples.
- It does not render the full valve or replace the Goal 25-D zoned body proof.
- It does not publish Pages or create animation frames.
- Visible machining marks are explicit curve/torus/dot geometry, not Blender procedural `Wave`, `Noise`, or `Bump` shader nodes.
- Material names remain visual lookdev targets, not certified surface-finish claims.

## Trace Library

- `G25-TRACE-MACH-FLANGE-RADIAL-GEOM-01`: 法兰端面车削/平面加工痕 - Concentric tool-path rings and hole-rim witness marks are explicit torus geometry on a machined stainless flange coupon. Applies to `G25-SS-MACH-FLANGE-RADIAL-01`.
- `G25-TRACE-BRUSH-NO4-LINEAR-GEOM-01`: #4 线性拉丝/砂带痕 - Overlapping short linear strokes with small angle and length variation are explicit curve geometry, not a shader wave. Applies to `G25-SS-BRUSH-NO4-LINEAR-01`.
- `G25-TRACE-MACH-BORE-CIRCULAR-GEOM-01`: 内孔环向加工痕 - A cutaway bore wall uses circumferential curve rings at varying pitch to read as boring/turning marks inside the flow passage. Applies to `G25-SS-MACH-BORE-CIRCULAR-01`.
- `G25-TRACE-MACH-BOLT-BORE-DARK-GEOM-01`: 螺栓孔暗加工内壁 - Small dark cylindrical hole caps and rim witness rings separate bolt bores from broad flange faces. Applies to `G25-SS-MACH-BOLT-BORE-DARK-01`.
- `G25-TRACE-EDGE-DEBURR-BURNISH-GEOM-01`: 倒角去毛刺磨亮痕 - Thin bright strokes on bevel-adjacent edges emulate final deburring and handling polish without brightening the whole part. Applies to `G25-SS-EDGE-BURNISH-01`.
- `G25-TRACE-BLAST-BEAD-MICROPIT-GEOM-01`: 珠喷/喷砂微坑参考 - Non-directional micro-pit dots are small geometry marks on a satin cast coupon, useful as the restrained boundary for blasted body surfaces. Applies to `G25-SS-CAST-BLASTED-SATIN-01`.

## Anti-Fake-Texture Rule

- No `ShaderNodeTexWave`.
- No `ShaderNodeTexNoise`.
- No shader `Bump` node.
- Trace direction comes from manufacturing semantics: concentric tool rings, linear brush strokes, bore circumferential bands, hole rims, edge witness marks and non-directional pit dots.

## External References Used

- [BSSA - Mechanically polished, brushed and buffed stainless finishes](https://bssa.org.uk/bssa_articles/specifying-mechanically-polished-brushed-and-buffed-stainless-steel-finishes-and-their-applications/): Mechanical stainless finishes need named process intent and direction, not a generic roughness/noise label.
- [BSSA - Bead and shot blasted stainless steel finishes](https://bssa.org.uk/bssa_articles/specifying-bead-and-shot-blasted-stainless-steel-finishes-and-their-applications/): Blasted stainless is non-directional and low reflective; it should not become powder-white.
- [Adobe Substance 3D - The PBR Guide](https://www.adobe.com/learn/substance-3d-designer/web/the-pbr-guide-part-2): Separate metallic response from roughness/normal/detail data; machining traces should not be baked into diffuse whiteness.
- [OpenPBR Surface Specification](https://academysoftwarefoundation.github.io/OpenPBR/): Layer material response and micro-surface detail explicitly so reusable trace methods can be attached to named base materials.

## Output

- `01-real-machining-trace-contact-sheet`: docs/assets/ztovalve/hero/goal25c-real-machining-traces/stills/01-real-machining-trace-contact-sheet.png
- `02-g25-trace-mach-flange-radial-geom-01`: docs/assets/ztovalve/hero/goal25c-real-machining-traces/stills/02-g25-trace-mach-flange-radial-geom-01.png
- `03-g25-trace-brush-no4-linear-geom-01`: docs/assets/ztovalve/hero/goal25c-real-machining-traces/stills/03-g25-trace-brush-no4-linear-geom-01.png
- `04-g25-trace-mach-bore-circular-geom-01`: docs/assets/ztovalve/hero/goal25c-real-machining-traces/stills/04-g25-trace-mach-bore-circular-geom-01.png
- `05-g25-trace-mach-bolt-bore-dark-geom-01`: docs/assets/ztovalve/hero/goal25c-real-machining-traces/stills/05-g25-trace-mach-bolt-bore-dark-geom-01.png
- `06-g25-trace-edge-deburr-burnish-geom-01`: docs/assets/ztovalve/hero/goal25c-real-machining-traces/stills/06-g25-trace-edge-deburr-burnish-geom-01.png
- `07-g25-trace-blast-bead-micropit-geom-01`: docs/assets/ztovalve/hero/goal25c-real-machining-traces/stills/07-g25-trace-blast-bead-micropit-geom-01.png

## Review Questions

- Which trace family looks real enough to migrate back into the Goal 25-D valve-body zones?
- Are any marks too visually loud for commercial industrial photography?
- Should 25-C next add UV/tangent-bound texture maps for the actual STEP body, or keep the marks as explicit geometric overlays?
