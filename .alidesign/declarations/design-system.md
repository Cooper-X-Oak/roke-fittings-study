# Design-system declaration

## Source of truth and version

- Task-local v1 for `docs/experiment/`; no project-wide promotion.
- Visual relationship is derived from the inspected educational mirror screenshot, not from a formal ROKE brand specification.
## Color and semantic tokens

- `--studio: #f1f1ef`
- `--paper: #fafaf8`
- `--ink: #24282b`
- `--muted: #666d72`
- `--line: rgba(36, 40, 43, 0.16)`
- `--accent: #c51f2a`
- `--focus: #005fcc`
- Status text always accompanies color.
## Typography and language coverage

- Display/body: `Arial, "Helvetica Neue", "Microsoft YaHei", system-ui, sans-serif`.
- Technical metadata: `ui-monospace, "SFMono-Regular", Consolas, monospace`.
- Use fluid display sizes with `clamp()` and normal Chinese tracking.
## Spacing, sizing, geometry, and layout tokens

- Base spacing: 8px; primary steps: 8, 16, 24, 32, 48, 64, 96px.
- Desktop page gutter: `clamp(24px, 4vw, 72px)`.
- Viewer uses the whole viewport; text measure stays under 34rem.
- Geometry is mostly square or minimally rounded (2-6px), matching precision hardware rather than soft consumer cards.
## Surface, border, elevation, and layering tokens

- Surfaces separate through value and hairlines, not card shadows.
- Canvas at base layer, copy above it, technical rail above copy, fallback status above canvas.
- A single soft ground shadow may anchor the model.
## Motion and timing tokens

- UI feedback: 120-180ms.
- Scroll smoothing: frame-rate independent damping, target half-life approximately 80-120ms.
- No unattended loop.
## Themes, responsive behavior, and platform variants

- Light theme only for this experiment.
- Full scrollytelling at `min-width: 900px` and normal motion preference.
- Narrow/reduced-motion layouts collapse to ordinary document flow with a stable 3D or fallback panel.
## Known gaps and extension process

- No production device matrix or mobile orbit controls in Issue #3.
- Any reuse elsewhere requires a new task-specific decision; these tokens are not global project policy.
