# Three.js Runtime Patterns

## Loading

Use `GLTFLoader`. Configure `DRACOLoader`, `KTX2Loader`, and `MeshoptDecoder`
when the inspected model declares the corresponding extensions. Keep decoder
paths local to the target deployment when offline or deterministic hosting is
required.

Display the poster until a usable first frame has rendered. Surface loading
failure as content instead of leaving an empty canvas.

## Scene Setup

Fit camera distance and controls from the loaded model bounds. Use neutral,
product-appropriate environment lighting as the initial implementation; select
final materials and lighting from the target project's design basis.

Do not add high-resolution dynamic shadows by default. Measure them as a
separate quality choice.

## Demand Rendering

Maintain `targetProgress`, `currentProgress`, and one scheduled-frame flag.
Schedule a frame when target progress changes. After sampling, schedule another
only while interpolation has not settled.

Use `ResizeObserver`, passive scroll listeners, and visibility checks. Stop work
when the story is off-screen unless an explicit finite transition still needs
to complete.

## Transform Ownership

Capture controlled nodes after loading. Reject ambiguous duplicate names unless
the manifest uses a stronger selector. Derive positions and rotations from
captured bases on every update.

Never mutate base transforms. Never use the previously rendered transform as
the next frame's input.

## Fallbacks

- `prefers-reduced-motion`: show the final hero state without scrubbed motion.
- WebGL or load failure: show the poster and product copy.
- fused model: keep group offsets at zero and use whole-product/camera motion.
- mobile or low-power fallback: decide from the target project requirements,
  not from an assumed weak-network rule.
