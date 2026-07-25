---
name: build-scroll-3d-product-story
description: Inspect a GLB/GLTF product model and build a reusable ROKE-style WebGL scroll story with meaningful exploded structure, semantic assembly, product and camera motion, final hero reveal, poster fallback, and performance evidence. Use for enterprise homepage 3D product storytelling, scroll-driven exploded views, converting image-sequence product animation to real-time Three.js, assessing whether a model can support true part animation, or adapting the included configuration-driven runtime to cars, machinery, fittings, electronics, and other products.
---

# Build Scroll 3D Product Story

Create a product-specific story manifest and use one generic Three.js runtime.
Treat ROKE as a narrative reference: introduction, exploded structure, assembly,
complete-product reveal, and final hero. Do not copy its brand, product, copy, or
assets.

## Resolve Authority And Inputs

1. Resolve the target project's rules, validation, repository workflow, and
   design basis before changing project files.
2. Require a `.glb` or `.gltf` model path and a target web route.
3. Record the target desktop browser/device class. Compare alternatives on the
   same environment; do not introduce a fixed weak-network release gate unless
   the user asks for one.
4. Preserve model licensing and attribution files.

## Inspect Before Designing Motion

Run:

```powershell
node <skill>/scripts/inspect-model.mjs `
  --model <model.glb> `
  --out <model-inspection.json>
```

Read [model-classification.md](references/model-classification.md) and select the
reported capability:

- `structured-named-parts`: generate semantic groups, then review them.
- `separated-unnamed-parts`: generate spatial candidates and require review.
- `partially-merged`: mix true part animation with group-level reveal.
- `fused-single-mesh`: use whole-product motion, cutaway, or poster; do not claim
  semantic assembly without a separate segmentation step.

Do not skip inspection because a model looks correct in a viewer.

## Generate The Candidate Story

Run:

```powershell
node <skill>/scripts/generate-story-manifest.mjs `
  --model <model.glb> `
  --public-uri <browser-model-url> `
  --out <product-story.json>

node <skill>/scripts/validate-story-manifest.mjs `
  --manifest <product-story.json>
```

Treat the generated manifest as a candidate, not product truth. Review every
group whose `reviewRequired` is true. Confirm:

- which nodes form one meaningful product subsystem;
- the assembly order and whether parts collide visually;
- the explode direction and distance;
- the camera side that best explains the product;
- the content shown at each stage;
- the final hero pose and CTA.

Read [choreography-contract.md](references/choreography-contract.md) before
editing the manifest. Validate it again after every structural change.

## Install The Generic Runtime

Copy `assets/threejs-scroll-story/` into the target route. Copy
`assets/product-story.schema.json` beside project validation tooling when a
schema artifact is useful. Replace the example manifest with the reviewed
`product-story.json`.

Keep these boundaries:

```text
generic runtime
  loading / scroll normalization / timeline sampling / demand rendering
  resize / DPR / poster / reduced motion / stage-content synchronization

product-story.json
  model URI / node groups / offsets / assembly windows
  camera / rotation / copy / CTA / hero pose / review decisions
```

Never put product-specific node names in `app.js`, `story-engine.js`, or
`story-math.js`.

Read [threejs-runtime-patterns.md](references/threejs-runtime-patterns.md) when
adapting loaders, rendering, camera fitting, resize behavior, or fallbacks.

## Preserve Determinism

Capture every controlled node's base transform once. For every render, derive
the complete transform from:

```text
base transform + manifest + normalized progress
```

Do not increment the previous frame's transform. Scrolling from progress `a` to
`b` and back to `a` must reproduce the original pose without drift.

Use one normalized progress value in `[0, 1]` for model groups, product
rotation, camera, content stages, and CTA state.

## Render Only On Demand

Render while loading, resizing, scrolling, easing toward a new progress value,
or running an explicit finite animation. Stop scheduling frames after the
target state settles.

Do not add an idle permanent `requestAnimationFrame` or `setAnimationLoop`.
Cap or adapt device pixel ratio in the target project after measuring the
intended desktop device class.

Read [performance-contract.md](references/performance-contract.md) before
claiming that the real-time version outperforms an image sequence.

## Compare With The Frame Baseline

Run:

```powershell
node <skill>/scripts/benchmark-assets.mjs `
  --runtime-dir <deployed-3d-route-directory> `
  --frames-dir <240-frame-directory> `
  --out <asset-benchmark.json>
```

Report transfer candidates and request counts from the script. Add browser
measurements from the same device/browser/cache conditions:

- first usable product frame;
- p50 and p95 frame time during the scroll story;
- long-animation-frame count and duration;
- main-thread time;
- peak JS and GPU-related memory when measurable.

Do not convert asset bytes into a fabricated runtime performance conclusion.

## Required Handoff

Return:

1. model inspection and capability;
2. reviewed `product-story.json`;
3. generic runtime integration;
4. poster/reduced-motion behavior;
5. asset comparison and browser measurements;
6. unresolved `reviewRequired` groups or fused-mesh limitations;
7. exact validation commands and results.
