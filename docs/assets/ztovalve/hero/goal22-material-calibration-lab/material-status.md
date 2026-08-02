# Goal 22 Material Calibration Contact Sheet

Generated: 2026-08-02T14:25:13.064585+00:00

## Boundary

- This is a tiny Blender/Cycles material test.
- It renders 20 centered primitive swatches in one contact sheet.
- It also renders a focused cast satin stainless roughness ladder.
- It does not import the full STEP/GLB valve.
- It does not replace the homepage hero.
- It does not render 24-frame or 240-frame animation.

## Visual Correction From Previous Attempt

- The cast/sandblasted stainless variants use medium grey metallic base values, not near-white.
- Roughness is tested in several moderate bands instead of pushing everything chalky and diffuse.
- The polished ball variants rely on broad reflection panels and dark flags, not random hard blocks.
- Graphite, rubber, PTFE, fastener, machined, and dark bore materials are separated so the white/grey pieces do not wash out the whole valve later.

## Swatches

1. `cast_satin_baseline` - cast satin stainless baseline
2. `cast_darker_satin` - cast darker satin stainless
3. `fine_bead_blast_low` - fine bead blast low contrast
4. `fine_bead_blast_normal` - fine bead blast stronger normal
5. `sandblast_mid_grey` - sandblast grey midtone
6. `brochure_satin_cast` - brochure-like smooth satin
7. `machined_stainless_bright` - machined stainless bright
8. `machined_stainless_darker` - machined stainless darker
9. `brushed_aniso_stainless` - brushed anisotropic stainless
10. `polished_ball_mirror` - polished stainless ball mirror
11. `polished_ball_soft_studio` - polished ball soft studio
12. `polished_ball_darker` - polished ball darker studio
13. `chrome_like_ring` - chrome-like machined ring
14. `fastener_stainless` - fastener stainless
15. `graphite_matte_black` - graphite packing matte black
16. `graphite_slight_metal` - graphite packing slight sheen
17. `black_rubber_seal` - black rubber seal
18. `ptfe_warm_off_white` - PTFE warm off-white
19. `ptfe_pale_grey` - PTFE pale grey
20. `dark_inner_bore` - dark inner bore / cavity

## Cast Satin Roughness Ladder

File: `stills/02-cast-satin-roughness-ladder.png`

Columns:

1. roughness `0.30`
2. roughness `0.38`
3. roughness `0.46`
4. roughness `0.54`

Rows:

1. `smooth satin cast`
2. `fine cast satin`
3. `bead-blasted satin`

Current visual read: the useful region is likely the middle of the ladder,
especially `fine_r38` and `fine_r46`. The `bead` row starts to push toward a
heavier blasted look, and `roughness 0.54` risks losing too much metallic
reflection for a catalogue valve body.

## Open/Public Reference Direction

- [Poly Haven CC0 HDRIs / textures](https://polyhaven.com/license): 可用 CC0 studio HDRI 和反射环境，但本轮先用程序化棚拍反射板，避免下载依赖。
- [ambientCG CC0 PBR materials](https://ambientcg.com/): 有 CC0 PBR 贴图和 metal 类资源，可作为下一轮真实贴图库来源。
- [Blender Principled BSDF](https://docs.blender.org/manual/en/latest/render/shader_nodes/shader/principled.html): 金属/粗糙度/各向异性控制仍是 Blender/Cycles 主线做法。
- [Sketchfab flanged valve examples](https://sketchfab.com/search?features=downloadable&q=flanged%20ball%20valve&type=models): 只做视觉学习；下载或复用必须逐个检查模型授权。
- [GrabCAD flanged ball valve examples](https://grabcad.com/library?query=flanged%20ball%20valve&sort=most_downloaded): 常见工业 CAD/KeyShot 预览可学习镜头和材质，但授权不可默认商用复用。

## Current Judgment

Use `index.html` for review: commercial references appear first, followed by the 20-swatch render. If none of the cast stainless variants hits the catalogue look, iterate this contact sheet again before touching the full valve.
