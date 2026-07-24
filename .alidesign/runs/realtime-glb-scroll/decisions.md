# Decisions for realtime-glb-scroll

Record decisions that affect the current run. Do not promote a decision into project-wide policy without explicit approval.

| Date | Decision | Authority | Scope | Consequence |
|---|---|---|---|---|
| 2026-07-24 | Use Khronos `CarConcept` rather than the mirror's proprietary product GLBs. | User request to find a product model; Khronos asset license and compression documentation. | `/experiment/` model only. | The prototype can ship with traceable CC BY 4.0 attribution and pre-authored part pivots. |
| 2026-07-24 | Keep the experiment additive and self-contained. | Issue #3 and repository policy. | `docs/experiment/`. | Existing mirrored pages and the current frame animation are untouched. |
| 2026-07-24 | Use a light industrial studio with large dark type and a restrained red accent. | Inspected local mirror screenshot plus user request for source-like lighting/material presence. | Experiment visual direction. | The result relates to the study source without reproducing protected marketing content or claims. |
| 2026-07-24 | Implement scroll mapping with a small native animation loop, not a page animation framework. | Performance goal and `$review-design-quality` engineering guidance. | Runtime interaction. | Lower JavaScript overhead and a direct reduced-motion fallback. |
| 2026-07-24 | Use prototype review mode and treat missing WebGL, model load failure, and reduced motion as first-class states. | Issue acceptance criteria and WCAG-oriented quality fallback. | Evaluation. | Core text remains visible even when the signature visual cannot run. |
