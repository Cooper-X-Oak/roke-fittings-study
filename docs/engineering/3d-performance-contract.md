# Realtime 3D performance contract

## Status

- Issue: `#5`
- Initial phase: `RED`
- Scope: `docs/experiment/`
- Blocking workflow: `3D Performance Gate / Realtime 3D E2E contract`

This contract converts the realtime 3D performance decisions into executable acceptance. The test suite is intentionally introduced before the production optimization. The current implementation is expected to fail the first branch because it does not yet provide poster-first loading or the required lifecycle marks, continuously schedules animation frames, and exceeds the frozen drawing-buffer budget at the representative desktop viewport.

The RED result is not permission to merge. It is the executable problem definition for the following GREEN implementation phase.

## Authority and measurement boundary

The permanent PR gate uses Playwright with Chromium, a local deterministic static server, a fixed 1440×1000 HiDPI viewport, and a project-defined 4 Mbps / 80 ms network profile. These are repeatable laboratory conditions, not a claim about every customer device.

Core Web Vitals field success remains a separate production obligation. In particular, a single CI interaction cannot represent field INP at the 75th percentile. The PR suite therefore blocks on lab LCP and CLS, plus a direct scroll-response assertion, while future real-user monitoring must own field LCP, INP, and CLS.

Absolute FPS, GPU memory, and hardware-specific frame pacing are not hard blockers on GitHub-hosted headless runners. SwiftShader and shared CI hardware are not representative product GPUs. Those values may be recorded as evidence, but can become release blockers only after a representative-device benchmark is established.

## Frozen hard gates

The source of truth for numeric thresholds is `tests/performance-budget.json`.

| Gate | Observable effect | Failure meaning |
|---|---|---|
| Poster first | `[data-3d-poster]` is visible within the poster budget and before interactive 3D | The page exposes loading chrome or blank canvas as its first product visual |
| Lifecycle marks | All required `roke:*` performance marks exist once and remain ordered | Download, decode, compile, and readiness costs cannot be attributed |
| Lab loading | LCP, first 3D frame, and interactive-ready remain within budget | Perceived or actual readiness regressed |
| Resource budget | Initial request count and bytes for model, poster, JavaScript, and WASM stay bounded | A code or asset change silently increases cold-start cost |
| Local-only runtime | No third-party runtime resources, page errors, or failed critical requests | The self-contained delivery contract regressed |
| Drawing-buffer budget | Canvas pixel count and effective pixel ratio remain bounded | HiDPI screens can create an unbounded fill-rate cost |
| Reversible state | A runtime snapshot generated from actual camera, model, and part transforms changes at exploded progress and returns near the assembled signature | Scroll no longer has reliable spatial meaning |
| Finite rendering | RAF callbacks stop after damping settles | The page burns GPU and battery while visually idle |
| Failure resilience | GLB/WASM failure leaves poster, fallback, and core copy visible | 3D failure turns into a blank or unusable page |
| Reduced motion | The visual remains stable and RAF sleeps | Accessibility preference still causes motion or continuous rendering |

## Required performance marks

Production code must expose the following marks using `performance.mark()`:

```text
roke:poster-visible
roke:model-request-start
roke:model-download-end
roke:model-decoded
roke:shader-compiled
roke:first-3d-frame
roke:interactive-ready
```

The marks are a public observability contract for tests and diagnostics. They must describe real completed states, not be emitted early merely to satisfy the test.

## Runtime spatial snapshot contract

Production code must expose a read-only diagnostic surface at `window.__ROKE_3D_RUNTIME__.snapshot()`. It must return a structured-clone-compatible object containing:

```js
{
  renderedProgress: 0.0,
  spatialSignature: [/* finite numbers derived from live camera/model/part transforms */],
  frameCount: 0
}
```

`spatialSignature` must be calculated from the actual Three.js scene state after rendering. It must not be copied directly from scroll position or a test-only constant. A practical signature should include camera transform values, model transform values, and an aggregate of the movable part transforms so that rotation, explosion, and reverse assembly all change the observable state.

GitHub-hosted SwiftShader can block for tens of seconds while capturing a continuously rendered full-screen WebGL surface. Therefore pixel screenshots and retained video remain review evidence, not a deterministic hard assertion. The blocking spatial behavior gate uses the runtime snapshot, while the browser independently measures drawing-buffer size, scroll response, and RAF activity.

## Budget-change rule

A threshold may be tightened with ordinary review. A threshold may be loosened only when the same pull request includes:

1. Before and after Playwright trace/report evidence.
2. The exact product reason the previous threshold is no longer achievable.
3. Alternatives attempted and why they were rejected.
4. The affected user/device/network segment.
5. A rollback condition and owner.

Deleting an assertion, increasing a timeout, adding retries, updating a visual baseline, or excluding a resource solely to make CI green is a contract change and requires the same evidence. Flaky measurements must be repaired at the measurement layer rather than hidden with retries.

## TDD transition

```text
RED
├─ Contract and budgets committed
├─ Current violations visible in CI
└─ No production optimization mixed into the test-definition commit

GREEN
├─ Poster-first handoff implemented
├─ Lifecycle marks implemented truthfully
├─ Finite RAF and pixel budget implemented
├─ Asset/request budgets satisfied
└─ All blocking tests pass without weakening thresholds

REFACTOR
├─ Simplify implementation without changing observables
├─ Preserve all gate results
└─ Attach before/after evidence for material pipeline changes
```

## Local verification

```powershell
npm ci
npx playwright install chromium
npm run test:e2e:3d
```

On Linux CI, Playwright installs the required Chromium system dependencies with `npx playwright install --with-deps chromium`.

## Branch protection

After the GREEN implementation is merged and the workflow is stable, configure `3D Performance Gate / Realtime 3D E2E contract` as a required status check for `main`. The workflow file alone runs the check; repository branch protection is what makes it impossible to bypass during merge.
