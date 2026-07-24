# Domain declaration

## Product objects and terminology

- `产品模型`: the credited Khronos CarConcept asset, not a ROKE product.
- `装配态`: all parts at authored transforms.
- `拆解态`: reversible educational separation of model meshes; not an engineering assembly instruction.
- `滚动进度`: normalized page progress from 0 to 1.
- `实时 3D`: WebGL rendering of the model, distinct from pre-rendered frame playback.
## Users, roles, permissions, and responsibility boundaries

- Anonymous learner on a desktop browser.
- No sign-in, role, permission, upload, storage, or submission surface exists.
## States, severity, risk, and status semantics

- Loading, ready, assembled, rotating, exploded, reduced-motion, unsupported, and load-error.
- Unsupported/load-error are blocking only for the 3D signature visual; explanatory content remains available.
## Sensitive data and reveal rules

- None. The page must not collect or transmit user data.
## Dangerous or irreversible operations

- None. Scroll state is ephemeral and fully reversible.
## Domain-specific evidence and compliance sources

- Khronos glTF Sample Assets `CarConcept` README and `LICENSE.md`.
- Repository `DISCLAIMER.md` principles: educational, unofficial, non-commercial study.
## Unknowns that block design decisions

- None for this prototype. Exact production hardware support and mobile interaction parity are intentionally out of scope.
