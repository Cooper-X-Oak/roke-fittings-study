# Goal 24 Body Stainless Render Matrix

Generated: 2026-08-02T21:45:28.758900+00:00

## Boundary

- This pass isolates the real STEP-derived `阀体` mesh only.
- It does not render the full valve.
- It does not replace the homepage hero.
- It does not render a 24-frame motion test or 240-frame release sequence.
- Material labels remain visual lookdev treatments, not certified alloy claims.

## Matrix Rows

- `pure-stainless`: 纯不锈钢 - No procedural grit; only metallic base, roughness, anisotropy and studio reflections.
- `coarse-grit-stainless`: 纯不锈钢 + 粗粒磨砂 - Same stainless base plus coarse roughness variation and bump texture.

## Matrix Columns

- `r24-bright-controlled`: R0.24 bright controlled
- `r32-commercial-satin`: R0.32 commercial satin
- `r40-industrial-satin`: R0.40 industrial satin
- `r48-muted-satin`: R0.48 muted satin

## External References Used

- [Blender Manual - Principled BSDF](https://docs.blender.org/manual/en/2.83/render/shader_nodes/shader/principled.html): Use a metallic material model with roughness and anisotropic controls instead of treating stainless as diffuse grey.
- [ambientCG metal PBR materials](https://ambientcg.com/list?category=Metal): Industrial metal assets separate base color, roughness and normal/height information; Goal 24 mirrors that separation procedurally.
- [Poly Haven Studio Small 09 HDRI](https://polyhaven.com/a/studio_small_09): Use a studio HDRI and visible dark/bright reflection bands so metal has something real to reflect.
- [yuki-koyama/blender-cli-rendering](https://github.com/yuki-koyama/blender-cli-rendering): Keep Blender lookdev repeatable from CLI scripts so material matrices can be rerun after small parameter changes.

## Output

- Contact sheet target: docs/assets/ztovalve/hero/goal24-body-stainless-render-matrix/stills/01-body-stainless-render-matrix.png
- Cell stills:
- `pure-stainless__r24-bright-controlled`: docs/assets/ztovalve/hero/goal24-body-stainless-render-matrix/stills/cells/01-pure-stainless-r24-bright-controlled.png
- `pure-stainless__r32-commercial-satin`: docs/assets/ztovalve/hero/goal24-body-stainless-render-matrix/stills/cells/02-pure-stainless-r32-commercial-satin.png
- `pure-stainless__r40-industrial-satin`: docs/assets/ztovalve/hero/goal24-body-stainless-render-matrix/stills/cells/03-pure-stainless-r40-industrial-satin.png
- `pure-stainless__r48-muted-satin`: docs/assets/ztovalve/hero/goal24-body-stainless-render-matrix/stills/cells/04-pure-stainless-r48-muted-satin.png
- `coarse-grit-stainless__r24-bright-controlled`: docs/assets/ztovalve/hero/goal24-body-stainless-render-matrix/stills/cells/05-coarse-grit-stainless-r24-bright-controlled.png
- `coarse-grit-stainless__r32-commercial-satin`: docs/assets/ztovalve/hero/goal24-body-stainless-render-matrix/stills/cells/06-coarse-grit-stainless-r32-commercial-satin.png
- `coarse-grit-stainless__r40-industrial-satin`: docs/assets/ztovalve/hero/goal24-body-stainless-render-matrix/stills/cells/07-coarse-grit-stainless-r40-industrial-satin.png
- `coarse-grit-stainless__r48-muted-satin`: docs/assets/ztovalve/hero/goal24-body-stainless-render-matrix/stills/cells/08-coarse-grit-stainless-r48-muted-satin.png

## Review Questions

- Which pure stainless column first stops reading as powdery grey and starts reading as real stainless?
- Which coarse grit column adds useful sanded texture without becoming cast iron, dirty coating, or cement-grey plastic?
- Does the studio reflection environment give the metal enough dark/bright value structure?
