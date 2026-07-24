# Feature specification: realtime GLB scroll study

## 1. Positioning and intent

An educational proof-of-concept compares real-time WebGL with the existing frame-sequence approach. The visitor should understand, by scrolling once, that a compact 3D asset can be inspected, rotated, and spatially separated without downloading hundreds of prerendered images.

Primary user: a desktop visitor studying product-web interaction.
Primary task: scroll through the model from assembled inspection to exploded construction.
Non-goals: configurator commerce, engineering instruction, mobile parity, analytics, or replacement of the existing mirror.

## 2. Information areas

1. Persistent experiment label and normalized progress.
2. Fixed live 3D stage.
3. Four scroll chapters: assembled, rotate, separate, understand.
4. Technical facts: packed transfer size, compressed geometry, KTX2 GPU texture path, and renderer status.
5. Source/license and educational-use boundary.

## 3. Core flow and states

1. HTML renders meaningful copy immediately.
2. The loader initializes local Three.js, Draco, KTX2, and the packed GLB.
3. While loading, a visible status reports percentage when known.
4. At ready, scroll progress maps to camera/model transforms.
5. Scrolling backward reverses transforms exactly.
6. A motion toggle or reduced-motion preference freezes the model in an assembled inspection pose.
7. Unsupported WebGL or load failure reveals a readable fallback and keeps the source/technical explanation.

## 4. Component behavior

- Native document scroll is the only required input.
- The canvas never traps keyboard focus.
- The motion toggle is the only button and uses `aria-pressed`.
- Each chapter has a real heading and remains in the DOM at all times.
- The technical rail uses a definition list and live renderer status.

## 5. Boundary conditions

- Static hosting under `/roke-fittings-study/experiment/` and local root testing under `/experiment/` must both work through relative URLs.
- No network request may leave the page origin at runtime.
- The desktop animation is disabled below 900px and under reduced-motion preference.
- Device pixel ratio is capped to limit fill cost.
- WebGL context loss pauses rendering and reports an error state.

## 6. Acceptance criteria

- Local HTTP status 200 for page, modules, decoders, and model.
- Model inspection confirms `KHR_draco_mesh_compression` and `KHR_texture_basisu`.
- Three recorded scroll states show assembled, rotated, and exploded poses.
- Reverse scrolling reassembles the model.
- Reduced motion, forced fallback, keyboard focus, and narrow width preserve complete readable content.
- No console errors, zero-byte/temp files, third-party runtime requests, unprefixed same-site root paths, files over 100 MB, tracking, or forms.
