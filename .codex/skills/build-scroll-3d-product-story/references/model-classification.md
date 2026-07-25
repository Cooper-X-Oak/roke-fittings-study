# Model Classification

## Capability Matrix

| Capability | Evidence | Allowed motion | Required action |
| --- | --- | --- | --- |
| `structured-named-parts` | At least four mesh-bearing nodes and at least half have meaningful names | Semantic explode and assembly candidates | Review group membership and order |
| `separated-unnamed-parts` | At least four independently transformable mesh nodes with weak names | Spatial explode candidates | Name and regroup before publishing |
| `partially-merged` | Two or three independently transformable mesh nodes | Group reveal plus limited true assembly | Confirm that the reduced story is honest |
| `fused-single-mesh` | Zero or one independently transformable mesh node | Whole-product rotation, camera, reveal, cutaway, poster | Segment externally for true part assembly |

Node count, not primitive count, determines whether parts can receive independent
object transforms. Several primitives inside one mesh do not automatically form
independent parts.

## Inspection Signals

Use these signals together:

- node hierarchy and mesh-bearing node count;
- uniqueness and semantic quality of node names;
- accessor bounds and spatial centers;
- shared materials and parent assemblies;
- Draco, Meshopt, BasisU/KTX2 declarations;
- animations or skins that already control nodes;
- duplicate node names and instancing.

Do not infer engineering assembly order from distance to the model center alone.
Use geometry only to produce reviewable candidates.

## Escalation Conditions

Stop automatic choreography and request model preparation when:

- one fused mesh must visibly separate into real manufactured parts;
- node names are duplicated and selectors would be ambiguous;
- required parts are hidden inside skinned or baked animation data;
- missing accessor bounds prevent safe spatial inference;
- the product owner cannot confirm subsystem grouping.
