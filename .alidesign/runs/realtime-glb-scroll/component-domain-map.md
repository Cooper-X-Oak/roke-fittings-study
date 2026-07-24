# Component and domain map

| Product meaning | UI/runtime primitive | Rules |
|---|---|---|
| Realtime product | `<canvas>` managed by Three.js | Decorative canvas is `aria-hidden`; nearby HTML names and explains the product. |
| Load state | `<progress>` + `role="status"` | Percentage text when available; failure never removes explanatory content. |
| Scroll chapter | `<section>` + heading | Visible in source order; active styling supplements, not replaces, the heading. |
| Experiment progress | Native `<progress>` mirrored by CSS line | Normalized 0-100 value with text alternative. |
| Compression facts | `<dl>` | Values are measured or attributed; no decorative metrics. |
| Motion preference | `<button aria-pressed>` | Pauses scroll-linked transforms and preserves a stable assembled pose. |
| Asset credit | `<footer>` links | Names Khronos source, authorship, CC BY 4.0, and educational scope. |
| Assembly transform | Saved base transform per movable mesh | Every scroll transform is reversible and does not mutate geometry. |
| Exploded transform | World-space radial/semantic displacement converted to parent-local space | Clamp tiny vectors and give named mechanical groups deterministic fallbacks. |

No permissions, destructive actions, sensitive data, or persistent state are present.
