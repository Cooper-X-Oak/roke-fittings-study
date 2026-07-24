# Interaction state matrix

| State/input | Visible behavior | Recovery/accessibility |
|---|---|---|
| HTML before JavaScript | Title, chapters, facts, credits, and fallback explanation are visible. | Core content does not depend on animation startup. |
| Loading | Status and progress remain visible over the stage; motion is inactive. | Polite live-region updates; no focus movement. |
| Ready / assembled | Car is centered in a stable three-quarter pose. | Status announces readiness once. |
| Scroll 0-35% | Root rotates and camera framing tightens slightly. | Scrolling backward maps to the exact earlier pose. |
| Scroll 35-78% | Rotation continues while parts separate with eased radial offsets. | No input capture; native scrolling remains interruptible. |
| Scroll 78-100% | Exploded pose holds with restrained continued camera drift. | Credits and facts remain legible. |
| Motion paused | Model damps to a stable assembled inspection pose; progress copy states paused. | Toggle uses `aria-pressed`; keyboard focus remains on the button. |
| `prefers-reduced-motion` | No scroll-linked transform; stable assembled model if WebGL is available. | Copy says the motion study is paused by system preference. |
| Narrow viewport | Bounded stage and normal-flow chapters; no 500vh scroll requirement. | No horizontal overflow at 320px. |
| WebGL unsupported / `?fallback=1` | Canvas is hidden and an explanatory fallback panel is shown. | All technical facts and credits remain accessible. |
| Model/decoder error | Human-readable failure text replaces progress. | Reload is possible through browser controls; no dead retry button. |
| Context lost | Rendering pauses and status reports context loss. | Browser reload is the explicit recovery. |
| Keyboard | Skip link and motion toggle receive visible focus; links are operable. | Canvas is not focusable and cannot trap input. |
