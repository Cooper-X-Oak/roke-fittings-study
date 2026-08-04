# Goal 23 STEP Full-Valve Material V1

Generated: 2026-08-02T16:26:18.875224+00:00

## Boundary

- This pass renders STEP-derived full-valve stills only.
- It does not replace the homepage hero.
- It does not render a 24-frame motion test or 240-frame release sequence.
- It reuses the Goal 20 STEP-derived GLB and does not overwrite source CAD.

## Material Decision

- Body/bonnet/flange: `castBlastedStainless` starts from the Goal 22 `fine_r46` direction, then darkens and strengthens cast/sanded micro-roughness for full-valve scale.
- Ball: `polishedStainlessBall`, low roughness mirror stainless with broad soft studio reflection.
- Seat: `softSealPtfe`, warm off-white PTFE treatment.
- Packing/seals: `graphitePacking`, dark grey graphite treatment.
- Fasteners: `fastenerStainless`, medium-bright stainless hardware.
- Machined parts: `machinedStainless`, brighter anisotropic stainless.

## Rendered Stills

- `assembled-material-v1`: docs/assets/ztovalve/hero/goal23-step-material-v1/stills/01-assembled-material-v1.png
- `body-flange-cast-satin-close`: docs/assets/ztovalve/hero/goal23-step-material-v1/stills/02-body-flange-cast-satin-close.png
- `ball-seat-seal-close`: docs/assets/ztovalve/hero/goal23-step-material-v1/stills/03-ball-seat-seal-close.png

## Current Review Questions

- Does the full-valve cast body now read as satin cast stainless instead of powdery near-white plastic?
- Is the cast/sanded micro-grain visible enough without becoming noisy or dirty?
- Are PTFE and graphite parts separated enough from the metal body?
- Are fasteners too dark, too bright, or about right against the cast body?

## Constraints

- Material labels are visual lookdev treatments, not certified alloy or coating claims.
- The next step after review should be parameter micro-tuning, not animation rendering.
