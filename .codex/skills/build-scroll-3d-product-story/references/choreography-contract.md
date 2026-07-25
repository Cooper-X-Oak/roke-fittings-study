# Choreography Contract

## Story Stages

Keep the five-stage information arc:

1. `intro`: establish product category and visual identity.
2. `exploded`: hold a legible component structure long enough to understand it.
3. `assembly`: assemble subsystems in a meaningful order.
4. `reveal`: complete the silhouette and rotate toward the selling angle.
5. `hero`: settle the camera, product, copy, and CTA.

Stage ranges must be ordered, contiguous enough for smooth reading, and inside
`[0, 1]`. Avoid making every part move over the full range; stagger subsystem
windows so the viewer can understand causality.

## Group Decisions

For each group, confirm:

- selectors identify unique independently transformable nodes;
- label describes product meaning rather than material color;
- exploded offset follows a plausible access or assembly direction;
- distance keeps the group inside the camera composition;
- assembly window matches subsystem dependencies;
- confidence reflects evidence, not aesthetic preference;
- `reviewRequired` remains true until a human confirms uncertain inference.

Use authored offsets for the final experience. Geometric radial directions are
only a first-pass candidate.

## Camera And Rotation

Use camera motion to clarify structure, not to compensate for arbitrary part
motion. Keep the product readable at stage boundaries. Make the final hero pose
stable enough for copy and CTA interaction.

Prefer a small number of camera and rotation keyframes. Sample keyframes from
normalized progress so reverse scrolling remains exact.

## Content

Bind content to stages rather than arbitrary scroll pixels. Keep business copy
outside the generic runtime. Include an explicit final CTA in the product
manifest or target page.
