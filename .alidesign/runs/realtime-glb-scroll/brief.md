# Design run: realtime-glb-scroll

- Project: `issue-3`
- Mode: `full`
- State: `planning`
- Milestone: [M001](../../milestones/M001.md)
- Issue: [AD-001](../../issues/AD-001.md)
- Created: `2026-07-24T09:02:33.532417Z`

## Task

Build a self-contained desktop study under `/experiment/` that replaces frame-by-frame product animation with a live WebGL product model. The page must load a compressed GLB containing Draco geometry and KTX2/BasisU textures, then bind model rotation, camera framing, and a reversible exploded view to document scroll.

## Current authority

- User authority: desktop-first, real-time GLB + WebGL, scroll controls rotation/disassembly, compressed GLB + KTX2 textures.
- Repository authority: `AGENTS.md`, `$apply-repo-workflow` with `github-standard-development`, and `docs/engineering/github-development.md`.
- Content and legal authority: Khronos `CarConcept` asset documentation and CC BY 4.0 attribution requirements.
- Visual reference scope: the local mirror screenshot establishes only a light industrial studio, large dark typography, red accent, and isolated metallic product composition. It does not authorize new ROKE brand claims.
- Quality fallback: `$review-design-quality` governs coherence, accessibility, failure visibility, purposeful motion, and template-risk checks.

## Boundaries

- Platform: modern desktop browser with WebGL 2; static GitHub Pages output.
- Language: Simplified Chinese interface with English technical identifiers where useful.
- No server, forms, analytics, tracking, credentials, or user-data collection.
- No replacement of existing mirrored pages in this issue.
- Narrow viewports receive a readable, simplified static explanation rather than full desktop interaction parity.

## Acceptance basis

- Functional scroll mapping, asset compression declarations, local-only runtime requests, readable fallbacks, keyboard-visible controls, reduced-motion behavior, and visual evidence at a desktop viewport.
- Prototype review mode; the experiment is not presented as a production configurator.

## Required artifacts

- Keep specifications, IA, component/domain maps, interaction matrices, decisions, evidence, evaluation, and feedback for this run under this directory.

## Next legal transition

Seal capability routing, pass `authority_resolved`, then progress through the full declaration gates to `implementation_authorized`.
