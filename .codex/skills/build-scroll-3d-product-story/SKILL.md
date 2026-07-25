---
name: build-scroll-3d-product-story
description: Develop and implement a narrative-first WebGL product story from a GLB/GLTF model. Use for enterprise homepage 3D storytelling, scroll-driven product films, exploded or assembly narratives, and real-time alternatives to image sequences. Enforces model truth inspection, advertising case research, multiple creative routes, an authored five-shot script, a reviewed animatic, explicit external confirmation, and only then runtime-manifest generation, Three.js implementation, and performance evidence.
---

# Build Scroll 3D Product Story

Develop the product film before building its runtime. A model with movable parts
is technical material, not a narrative. Do not generate implementation motion
and then label five timeline intervals as a story.

## Resolve Authority And Inputs

1. Resolve the target project's rules, validation, repository workflow, and
   design basis before changing project files.
2. Require a `.glb` or `.gltf` model path and a target web route.
3. Require the product objective, intended audience, and available product
   evidence. Record unknowns as truth constraints rather than inventing claims.
4. Record the target desktop browser/device class. Compare alternatives on the
   same environment; do not introduce a fixed weak-network release gate unless
   the user asks for one.
5. Preserve model licensing and attribution files.

## Inspect Model Truth

Run:

```powershell
node <skill>/scripts/inspect-model.mjs `
  --model <model.glb> `
  --out <model-inspection.json>
```

Read [model-classification.md](references/model-classification.md) and select the
reported capability:

- `structured-named-parts`: use semantic groups only after review.
- `separated-unnamed-parts`: name and review spatial candidates.
- `partially-merged`: combine true motion with group-level reveal.
- `fused-single-mesh`: use whole-product motion or prepare a segmented model.

Record capability, supported truths, limitations, prohibited claims, usable
close-ups, and independently controllable groups in the `modelAudit` section of
`creative-development.json`. Geometry and node names may suggest a subsystem;
they do not prove product function or manufacturing order.

## Complete Creative Development

Read
[narrative-development-contract.md](references/narrative-development-contract.md)
before researching or scripting. Complete this sequence without reordering:

```text
model inspection prerequisite
  -> advertising case research
  -> at least two creative routes
  -> one selected route and exactly five authored shots
  -> fixed-duration animatic
  -> explicit external confirmation
  -> runtime implementation
```

Use `assets/creative-development.example.json` as a structural example, not as
product copy. Validate the project-authored record:

```powershell
node <skill>/scripts/validate-creative-development.mjs `
  --plan <creative-development.json>
```

Stop before runtime work when this command fails. Do not create placeholder
approval, mark an unreviewed animatic as reviewed, or name the implementing
agent as confirmer. When the user has not yet confirmed the narrative, return
the research, routes, five-shot script, and animatic for review and pause.

Treat ROKE and other references as methods, not templates. Extract narrative
thesis, information order, camera motivation, light progression, transition
logic, rhythm, and applicability. Do not copy brands, assets, product claims, or
a universal `intro/exploded/assembly/reveal/hero` sequence.

## Generate Runtime Only After Confirmation

After the creative-development validator passes, run:

```powershell
node <skill>/scripts/generate-story-manifest.mjs `
  --model <model.glb> `
  --creative-plan <creative-development.json> `
  --public-uri <browser-model-url> `
  --out <product-story.json>

node <skill>/scripts/validate-story-manifest.mjs `
  --manifest <product-story.json>
```

The generator imports the confirmed five shot IDs, normalized ranges, and copy.
It rejects a missing creative plan and a model capability that differs from the
confirmed audit.

The generated transforms remain technical candidates. Review every group whose
`reviewRequired` is true. Confirm:

- which nodes form one meaningful product subsystem;
- whether part paths and offsets collide visually;
- whether the motion communicates the selected route rather than a generic
  explosion;
- the camera, lighting, layout, transition, and hold implementation for every
  confirmed shot;
- that implementation preserves each shot's narrative purpose and truth
  constraints.

Read [choreography-contract.md](references/choreography-contract.md) before
editing the manifest. Validate it again after every structural change.

## Install The Generic Runtime

Copy `assets/threejs-scroll-story/` into the target route. Copy
`assets/product-story.schema.json` beside project validation tooling when a
schema artifact is useful. Keep these boundaries:

```text
generic runtime
  loading / scroll normalization / timeline sampling / demand rendering
  resize / DPR / poster / reduced motion / shot-content synchronization

creative-development.json
  research / routes / selected thesis / five shots / animatic / confirmation

product-story.json
  approval identity / model URI / node groups / offsets / assembly windows
  camera / rotation / copy / CTA / implementation review decisions
```

Never put product-specific node names in `app.js`, `story-engine.js`, or
`story-math.js`. Read
[threejs-runtime-patterns.md](references/threejs-runtime-patterns.md) when
adapting loaders, rendering, camera fitting, resize behavior, or fallbacks.

## Preserve Determinism And The Approved Edit

Capture every controlled node's base transform once. For every render, derive
the complete transform from:

```text
base transform + approved manifests + normalized progress
```

Do not increment the previous frame's transform. Scrolling from progress `a` to
`b` and back to `a` must reproduce the original pose without drift.

Use one normalized progress value in `[0, 1]` for model groups, product
rotation, camera, lighting, materials, layout, content shots, and CTA state.

First verify a canonical fixed-duration playback that matches the animatic.
Then map that approved time axis to scroll. Scrolling must preserve shot order,
transitions, and comprehension holds in both directions.

## Render Only On Demand

Render while loading, resizing, scrolling, easing toward a new progress value,
or running an explicit finite animation. Stop scheduling frames after the
target state settles.

Do not add an idle permanent `requestAnimationFrame` or `setAnimationLoop`.
Cap or adapt device pixel ratio after measuring the intended desktop device
class.

## Verify Narrative Before Performance

Before performance optimization, compare canonical playback and scroll playback
against the confirmed animatic. Prove:

- all five shot purposes remain legible;
- transitions preserve their visual cause;
- the intended focal subject is unambiguous;
- camera, light, layout, and copy change at meaningful narrative beats;
- comprehension holds remain available;
- product claims stay within the recorded truth constraints.

Do not optimize away an approved focal beat, transition, lighting change, or
hold without returning the change to narrative confirmation.

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
measurements from the same device, browser, viewport, and cache conditions:

- first usable product frame;
- p50 and p95 frame time during the scroll story;
- frames over 16.7 ms and 33.3 ms;
- long-animation-frame and main-thread timing when supported;
- peak JS and GPU-related memory when measurable;
- renderer frames after the final shot settles.

Do not convert asset bytes into a fabricated runtime performance conclusion.

## Required Handoff

Return:

1. model inspection and capability;
2. evidence-backed advertising reference board;
3. compared creative routes and selection decision;
4. confirmed five-shot script;
5. reviewed animatic and external confirmation evidence;
6. reviewed `product-story.json` linked to that approval;
7. generic runtime integration and canonical playback comparison;
8. poster and reduced-motion behavior;
9. asset comparison and browser measurements;
10. unresolved `reviewRequired` groups or fused-mesh limitations;
11. exact validation commands and results.
