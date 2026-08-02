# Goal 16 Stainless Catalogue Material + State Audit

## Authority

- Goal: re-render the fixed ball valve GLB in the catalogue-style stainless visual direction and define states that can be reused by later animation.
- Output boundary: three 4K still images, one render manifest, one state definition file, one review page. No 240-frame sequence, no homepage replacement.
- Source asset: `../fixed-ball-valve.glb`, derived from the preserved customer STEP. Original STEP, brochure, and GLB are not overwritten.
- Reference image boundary: the supplied "Floating type soft seal" image is used as material, lighting, and exploded-layout reference only. It is not treated as a fixed-ball-valve mechanical specification.
- Product truth boundary: no pressure, flow rate, zero-leakage, fire-safe, anti-static, DBB/DIB, material grade, or medium claim is made.

## Material Thesis

The revised visual hierarchy is:

1. stainless silver valve body, valve cover, pressure shell, and flanges;
2. brighter polished stainless ball core;
3. light ivory / pale grey soft-seat and seal rings;
4. machined stainless stem, drive stack, and lower support;
5. brighter stainless bolts, nuts, washers, and small hardware.

This replaces the Goal 15 black graphite shell direction. The outer shell is no longer treated as black or dark grey.

## Reusable States

| State | Use | Contract |
| --- | --- | --- |
| `assembled` | Complete catalogue product still and future opening hold. | All major groups return to base positions; ball is closed/reference orientation. |
| `exploded` | Large ordered product anatomy. | Left/right shell split along pipeline axis, drive stack lifts upward, lower support drops downward, fasteners spread as secondary detail. |
| `ball-open` | Later 90 degree functional beat. | Same partial anatomy context as `ball-closed`, but only the true ball core rotates 90 degrees. |
| `ball-closed` | Quarter-turn start/end reference. | Valve seats and seat seals remain fixed; only ball orientation differs from `ball-open`. |

## Rendered Stills

| File | Source State | Purpose |
| --- | --- | --- |
| `stills/01-stainless-product-4k.png` | `assembled` | Validate high-key stainless body, flanges, valve cover, and complete product read. |
| `stills/02-catalog-explosion-4k.png` | `exploded` | Validate catalogue-style explosion order and later animation feasibility. |
| `stills/03-ball-seat-soft-seal-4k.png` | `ball-open` | Validate polished ball core, light soft-seat/seal material, and fixed-seat boundary. |

## Grouping Evidence

- `ball`: expected 1 mesh, the true ball core only.
- `seat`: light soft-seat / seal visual treatment; remains fixed during ball turn.
- `leftBody`, `rightBody`, `centerBody`: stainless pressure shell / valve cover / flanges.
- `upperDrive`, `lowerSupport`: machined stainless drive and support groups.
- `fastener`: brighter stainless bolts, nuts, washers, springs, and small hardware.

## Known Limits

- Current environment does not expose Blender, so this is still a high-resolution Three.js lookdev/render-state pass, not a Cycles or KeyShot path-traced final.
- The reference image is a floating soft-seal illustration while the GLB audit names a fixed ball valve with fixed-axis components. Material and layout may be borrowed; product type claims may not.
- CAD edges may still need bevel/weighted-normal cleanup in a final offline renderer.
- This state system is suitable for the next 240-frame blocking/render pass, but the formal 240-frame production sequence has not started.
