# Goal 17 Offline Render Lookdev Plan

## Scope

Goal 17 turns the Goal 16 state work into an offline-render-ready lookdev package. It does not replace the homepage, render 240 frames, or overwrite the STEP, brochure PDF, or `fixed-ball-valve.glb`.

The current machine does not expose Blender, KeyShot, or SOLIDWORKS Visualize in PATH or common install folders. Because of that, this goal ships a reproducible Blender Cycles scene-generation script plus the material and studio-lighting contracts. The first photoreal stills should be rendered when Blender is available.

## Diagnosis

Goal 16 fixed the main direction problem: the outer shell is no longer black/graphite, and the ball/seat animation states are usable. It is still not a professional catalogue render because the metal is too uniform. The brochure references use material contrast: satin body, brighter machined cuts, dark fasteners, black cavities, pale soft seals, and controlled white/black reflections.

The next quality jump is not another Three.js exposure tweak. It requires an offline product-rendering pass with:

- bevel and weighted normals on hard CAD edges;
- multiple stainless material families instead of one silver shader;
- black reflection cards and strip lights;
- a shadow catcher rather than a visible white floor plane;
- final stills rendered through Cycles/KeyShot/SOLIDWORKS Visualize.

## Files

- `material-layers.json`: material families and assignment rules.
- `studio-lighting.json`: studio light rig, render settings, and camera targets.
- `render-manifest.json`: package status and output contract.
- `index.html`: visual review page comparing brochure, Goal 16, and Goal 17 target.
- `scripts/render_goal17_blender_lookdev.py`: Blender Cycles scene and still-render script.

## Blender Command

Install Blender 4.x, then run from the repository root:

```powershell
& "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe" --background --python scripts\render_goal17_blender_lookdev.py -- --repo-root . --profile preview
```

For a slower final still pass:

```powershell
& "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe" --background --python scripts\render_goal17_blender_lookdev.py -- --repo-root . --profile final
```

Expected rendered outputs:

- `docs/assets/ztovalve/hero/goal17-offline-lookdev/renders/01-assembled-photoreal.png`
- `docs/assets/ztovalve/hero/goal17-offline-lookdev/renders/02-exploded-photoreal.png`
- `docs/assets/ztovalve/hero/goal17-offline-lookdev/renders/03-ball-seat-photoreal.png`
- `docs/assets/ztovalve/hero/goal17-offline-lookdev/render-results.json`

## Acceptance

Goal 17 is ready for visual review when the Blender run produces three 3840 x 2160 stills and `render-results.json` reports:

- `renderer` is Blender Cycles;
- `sourceModelSha256` matches the current GLB;
- the still count is three;
- `ball` classification count is one;
- `homepageConnected` is false;
- `fullReleaseFrameCount` is zero.

The first visual review should compare the stills against brochure Page 11/12 and Page 13/14, not against Goal 16 alone.
