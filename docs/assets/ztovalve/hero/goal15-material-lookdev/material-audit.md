# Goal 15 Material Lookdev Audit

## Authority

- Goal: create ultra-high-resolution industrial material lookdev stills for the fixed ball valve.
- Output boundary: 4K still images only. No 240-frame release sequence, no homepage replacement, no fluid animation optimization.
- Source asset: `../fixed-ball-valve.glb`, derived from the preserved customer STEP. Original STEP and brochure are not modified.
- Product truth boundary: only visible part identity and catalogue-supported structure are used. No pressure, flow rate, zero-leakage, fire-safe, anti-static, DBB/DIB, material grade, or medium claim is made.

## Material Thesis

The visual hierarchy should read as:

1. graphite-black pressure body with long studio highlights;
2. polished stainless ball core as the brightest functional anchor;
3. fixed dark valve seat / seal system with lower reflection;
4. satin machined stem, drive, and lower support;
5. brighter steel fasteners as detail texture, not hero subjects.

## Rendered Stills

| File | Purpose | Acceptance Focus |
| --- | --- | --- |
| `stills/01-master-product-4k.png` | Complete commercial product view. | Black body must keep volume through reflected softboxes, not become flat plastic. |
| `stills/02-ball-seat-core-4k.png` | Ball core and valve seat material close view. | Ball reads polished; seats read fixed, dark, and lower-reflection. |
| `stills/03-flange-fastener-detail-4k.png` | Flange and fastener detail close view. | Edge highlights, hole rhythm, bolt material, and contact shadows must carry realism. |

## Grouping Evidence

- `ball`: expected 1 mesh, the true ball core only.
- `seat`: fixed valve seat / seat-seal system, not included in ball rotation.
- `leftBody`, `rightBody`, `centerBody`: graphite-black pressure shell treatment.
- `upperDrive`, `lowerSupport`: satin machined metal treatment.
- `fastener`: brighter steel treatment for bolts, nuts, washers, and small hardware.

## Known Limits

- This pass uses high-resolution Three.js capture because Blender is not available in the current environment.
- It is a lookdev baseline, not a final Cycles/KeyShot path-traced master.
- The GLB has no original texture maps, cameras, or baked materials; all material and lighting decisions are authored treatments.
- CAD edges may still need real bevel/weighted-normal processing in a later offline renderer for the highest-end final master.
- Fluid lines are intentionally excluded. They may return later as a low-opacity post layer only after material approval.

## Next Decision

If these stills pass visual direction, the next production step should be a high-quality render pipeline for the 240-frame sequence using the same material assignments and approved camera path.
