# Performance Contract

## Comparison Rule

Measure the real-time route and the frame-sequence route on the same:

- desktop device and GPU;
- browser version;
- viewport and device pixel ratio;
- cache state;
- hosting origin where practical.

A fixed 4 Mbps cold-start profile is not a default acceptance condition.

## Asset Evidence

Report:

- request count;
- encoded file bytes;
- compressed transfer bytes from browser tooling when available;
- decoded model geometry and texture estimates when available;
- number and dimensions of frame images.

Asset size does not prove frame pacing. Keep transfer evidence separate from
runtime evidence.

## Runtime Evidence

Capture:

- first usable product frame;
- p50 and p95 animation frame time through a scripted scroll;
- frames over 16.7 ms and 33.3 ms;
- Long Animation Frames;
- main-thread scripting/rendering time;
- peak JS heap and GPU-related memory when supported;
- idle behavior after the hero settles.

Evaluate visual fidelity beside performance. Reducing DPR, shadow resolution, or
material complexity is acceptable only when the intended design quality remains
intact.

## Runtime Defaults

- Render on demand.
- Avoid object creation inside the per-frame transform path.
- Reuse materials and geometry where the model permits.
- Prefer compressed GLB plus KTX2/BasisU textures.
- Fit the camera from model bounds instead of product-specific constants.
- Use a measured DPR cap or dynamic scaling.
- Provide a poster and reduced-motion hero state.
