# Model provenance and compression decision

## Selected asset

- Model: **Car Concept**
- Source: <https://github.com/KhronosGroup/glTF-Sample-Assets/tree/main/Models/CarConcept>
- Source variant: `glTF-KTX-BasisU-Draco`
- Asset summary: concept car with logical part names, authored pivots, and material variants.

## Why it fits

- The source started from a public-domain concept car and was optimized as a high-quality web glTF showcase.
- Logical node names and adjusted pivots make doors, wheels, body panels, interior, and engine suitable for an exploded-view study.
- The selected source variant declares `KHR_draco_mesh_compression` and `KHR_texture_basisu`.
- The source README documents a 10.3 MB transfer size and 14.9 MB video-memory footprint for the compressed variant, compared with 48.8 MB video memory for PNG/JPG/WebP texture variants.
- The currently downloaded source folder totaled 3.57 MB; after single-file packing and Draco re-encoding at the source's documented 10-bit position/normal/UV quantization, the shipped GLB is 2,605,580 bytes (2.48 MiB).

## Packaging decision

The source `.gltf`, Draco-compressed binary geometry, and `.ktx2` textures are packed into one `.glb` container. KTX2 images remain BasisU-compressed buffer views inside the GLB, so the browser downloads one model asset while the GPU can keep supported compressed texture formats resident. Inspection of the shipped file confirms both `KHR_draco_mesh_compression` and `KHR_texture_basisu` are required extensions.

## License and attribution

- Primary optimized asset: Darmstadt Graphics Group GmbH, CC BY 4.0.
- Original concept source and additional credits remain documented in the upstream `LICENSE.md`.
- The experiment footer links the source model and license and does not imply endorsement or ROKE ownership.

## Rejected candidates

- Existing mirrored ROKE GLBs: closer to the source site but rights are not sufficiently broad for a new public experiment.
- Khronos ToyCar: CC0 and attractive, but the curated source does not provide a KTX2 + compressed-geometry variant.
- Khronos ChronographWatch: smaller KTX2 package and strong product semantics, but fewer separable authored parts after mesh optimization.
