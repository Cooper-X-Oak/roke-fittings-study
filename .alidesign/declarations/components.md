# Component declaration

## Available primitives and source

- Native HTML landmarks, headings, links, buttons, progress, and status regions.
- Three.js WebGL renderer and official GLTF/Draco/KTX2 loaders, vendored locally.
- No UI component framework.
## Semantic component map

- `experiment-shell`: document and scroll progress owner.
- `viewer-stage`: fixed desktop canvas region with non-canvas fallback content.
- `loading-status`: polite live region and measurable progress.
- `chapter`: semantic section with heading and explanatory copy.
- `technical-rail`: real asset facts and live renderer state.
- `motion-toggle`: button that disables/enables scroll-linked transforms without hiding content.
- `credits`: source, license, and educational boundary.
## Easily confused components and selection rules

- Technical facts are plain definition-list content, not status badges.
- Chapters are sections, not clickable cards.
- Progress is a native progress semantic mirrored by a visual rule.
## Required states and accessibility behavior

- Viewer: loading, ready, unsupported, error, reduced-motion.
- Motion toggle: pressed state, visible focus, stable label.
- Links: visible underline or equivalent non-color affordance.
- Status changes use text in the live region and never rely on color alone.
## Composition and responsive rules

- Desktop: fixed canvas; chapter copy alternates between left and right clear zones while the model remains central.
- Narrow: canvas becomes a bounded block, chapters return to linear flow, and sticky behavior is removed.
## Deprecated components

- None.
## Missing component process

- Use a semantic native element first. Add a custom component only if the model interaction cannot be represented natively and document it in this run.
