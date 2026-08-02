# Goal 21 Blender/Cycles Material Micro Loop

Generated: 2026-08-02

## Boundary

- Goal 21 renders exactly two material stills.
- It does not replace the homepage hero.
- It does not render a 24-frame motion test or 240-frame release sequence.
- The source mesh remains the Goal 20 STEP-derived GLB.

## Focus

1. `castBlastedStainless`: darker midtone stainless with fine procedural bead-blast roughness.
2. `polishedStainlessBall`: wider, softer studio reflections with reduced hard black/white blocks.

## Implementation Notes

- The white-dominant Goal 20 studio was replaced with a neutral grey floor/cyc and camera-invisible soft reflection panels.
- The ball material uses low roughness variation to keep a polished read while softening card-shaped reflections.
- The cast body uses high-frequency procedural noise for bump, roughness and subtle color variation. This avoids UV dependency on the STEP-derived CAD mesh.
- External PBR texture libraries were not imported in this pass because this CAD mesh has no reviewed UV unwrap. Procedural object-space shading is the safer small-loop test.

## Current Assessment

This is a material-direction iteration, not final approval.

- The body has moved away from the obvious white engineering-preview material.
- The body now has more usable midtone metal and shadow separation.
- The bead-blasted / sandblasted surface is still not fully convincing as a premium commercial product material.
- The ball is back to a polished read, but the reflection is still more card-shaped than a high-end KeyShot studio setup.
- The next commercial-quality route should test a better light tent/HDRI setup and, if UVs can be generated cleanly, CC0 PBR metal roughness/normal maps.

## External Material Route Checked

- Blender's native Principled BSDF remains the right base shader for this loop because it exposes metallic, roughness, coat and anisotropy controls.
- Poly Haven provides CC0 HDRIs and can be used for studio/environment lighting.
- ambientCG provides CC0 PBR materials, including metal material maps, but those are safer after UV/tri-planar mapping is designed for this CAD mesh.

## Render

- Profile: `smoke`
- Size: `1600x900`
- Samples: `48`
- Stills: `2`

