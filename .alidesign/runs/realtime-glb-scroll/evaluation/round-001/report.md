# Evaluation round

- Run: `realtime-glb-scroll`
- Round: `round-001`
- Review mode: `prototype`
- Artifact: `docs/experiment/index.html`
- Verdict: `passed`
- Routing revision: `revision-002`
- Evidence collector: `evidence-collector`
- Independent design reviewer: `independent-design-review`
- Gate resolver: `alidesign-gate-resolver`

## Applicable rules

- User direction: desktop WebGL, compressed GLB with KTX2 textures, and scroll-driven reversible rotation and exploded movement.
- Prototype blockers and evidence requirements in `.alidesign/evaluation-profile.yaml`.
- Interaction and fallback acceptance in `spec.md` and `interaction-state-matrix.md`.
- Visual direction in `visual-direction.md`.
- Model provenance and license requirements in `model-provenance.md` and `docs/experiment/MODEL-LICENSE.txt`.
- Repository delivery policy in `AGENTS.md` and `docs/engineering/github-development.md`.
- General design-quality review criteria from `$review-design-quality`.

## Evidence collected

- Local HTTP audit returned `200` for the `/experiment/` entry and all 22 shipped files.
- Desktop browser run reached `ready`, reported `WEBGL2 · ACTIVE`, discovered 39 explodable top-level part groups, had zero horizontal overflow, no page errors, no failed requests, and no external runtime requests. Decoder-created same-origin `blob:` URLs were treated as local runtime objects, not network dependencies.
- Scroll traces were captured at assembled (`0%`), rotating (`24%`), exploded (`72%`), and reverse-scrolled reassembled (`0%`) states.
- Pause/resume changed `aria-pressed`, label, and runtime status correctly.
- A fresh reduced-motion run reached `ready`, hid the motion toggle, and retained the assembled inspection pose.
- Forced fallback at a narrow viewport retained 717 characters of readable core content, ordinary-flow layout, zero horizontal overflow, and visible first-tab focus on the skip link.
- `node --check` passed. glTF Validator exited `0`. The 2,605,580-byte GLB requires `KHR_draco_mesh_compression` and `KHR_texture_basisu` and contains 14 KTX2 images.
- Repository policy audit found no zero-byte or temporary files, files over 100 MB, or unprefixed same-site root references.
- An isolated reviewer inspected the final artifact, declarations, state specification, and screenshots. Its verdict remained `passed` after the transfer label and technical-rail contrast refinements.

## Evidence gaps

- No production deployment was requested, so this prototype round proves local HTTP health but not a public GitHub Pages URL.
- A supported-WebGL narrow screenshot and 200%/400% text reflow check are deferred to a future release-mode review. They are outside this desktop-first prototype profile.

## Subchecks

| Dimension | Check | Verdict | Evidence | Rule | Owner phase | Blocking |
|---|---|---|---|---|---|---|
| Product intent | One live asset clearly proves the frame-sequence replacement idea without invented product claims | pass | `desktop-assembled-final.png`, `desktop-exploded-final.png`, `spec.md` | User direction; prototype profile | planning | no |
| Product intent | Model source, license, and non-official status are explicit | pass | `MODEL-LICENSE.txt`, `model-provenance.md`, page credits | Model provenance rules | planning | no |
| Interaction readiness | Native scroll creates materially different rotation and exploded states | pass | `desktop-rotated-center-final.png`, `desktop-exploded-final.png`, browser trace | Interaction matrix | interaction_states | no |
| Interaction readiness | Reverse scroll reassembles from saved transforms; pause and recovery states work | pass | `desktop-reassembled-final.png`, pause/resume trace, `app.js` | Interaction matrix | interaction_states | no |
| System craft and implementation consistency | Local PBR runtime, Draco/KTX2 loaders, and technical presentation form one coherent system | pass | source inspection, glTF inspection, desktop screenshots | Visual direction; spec | implementing | no |
| Visual expression | The live product remains the signature visual while story copy and progress stay legible | pass | four desktop screenshots; independent review | Visual direction; design-quality review | design_ready | no |
| Accessibility and responsive resilience | Semantic progress/status controls, visible focus, reduced-motion behavior, and readable fallback are present | pass | source inspection, reduced-motion trace, `narrow-fallback.png` | Prototype profile; interaction matrix | interaction_states | no |
| Runtime and delivery | Entry, dependencies, model, and decoders load locally with no critical console/request failure | pass | HTTP audit, browser report, validator report | Prototype blockers; repository policy | implementing | no |

## Blocking issues

None.

## Accepted exceptions

- Narrow screens intentionally use a simplified, non-animated explanation rather than feature parity. This is authorized by the desktop-first brief.
- Headless SwiftShader logged only `KHR_parallel_shader_compile extension not supported`; this is an environment capability warning, not an artifact failure.
- The licensed sample model retains its authored details. Explicit attribution is present and the page does not present the asset as a ROKE-owned model.

## Directed revisions

The independent review proposed two non-blocking refinements, both completed and rechecked in this round:

1. Correct the displayed binary size from `2.49 MiB` to `2.48 MiB`.
2. Add a restrained translucent studio backing to the technical rail so dark model surfaces cannot reduce metadata contrast.

No open directed revision remains.

## Next legal transition or stop reason

Transition `evaluating → accepted` through `evaluation_passed`. All prototype blockers are clear, all required evidence categories are indexed, and the final independent design verdict is `passed`.
