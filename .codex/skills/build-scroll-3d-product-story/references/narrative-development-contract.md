# Narrative Development Contract

## Ordered Gate

After model inspection, complete these phases in order:

1. `case-research`
2. `creative-routes`
3. `five-shot-script`
4. `camera-previs` inside the animatic phase
5. `animatic`
6. `automatic-release`
7. runtime implementation

Record phases 1–5 in one `creative-development.json`. Runtime-story generation
is phase 6 and must reject a missing or invalid creative-development record.

## Case Research

Use applicable product advertising, launch films, technical CGI, exploded-view
films, or interactive product stories. Record at least three primary or
creator-owned source pages. For each case, extract:

- its narrative thesis;
- methods that transfer to the target model;
- limitations that prevent direct transfer.

Do not collect visual references without explaining their narrative use. Do not
copy brand claims, assets, or product facts into the target story.

## Creative Routes

Develop at least two materially different routes. A route changes the viewer's
information order or causal arc, not merely its title, colors, or camera angle.
Each route must state its thesis, intended audience takeaway, five-beat arc,
model fit, and risks.

Select exactly one route before authoring the final shot script.

## Five-Shot Script

Author exactly five continuous shots. Every shot must define:

- narrative purpose and viewer takeaway;
- start and end state;
- visible action and active components;
- framing and camera movement;
- lighting;
- page layout and copy;
- incoming and outgoing transition;
- rhythm and an intentional comprehension hold;
- truth constraints.

The five normalized ranges must cover `[0, 1]` in order without gaps. Shot IDs
must match the selected route's five-beat arc. Do not reuse the fixed
`intro/exploded/assembly/reveal/hero` template unless the selected narrative
independently justifies those exact beats.

## Animatic

Create a deterministic per-frame camera previs after the script and before the
animatic. The previs must provide every canonical frame's camera position,
target, roll, FOV, focus distance, part state, light state, shot identity, and
transition occlusion. It must also declare its frame rate, total frame count,
shot boundaries, continuity path, hidden-cut reason, maximum roll, and stable
hero-hold range.

Then create a fixed-duration, reviewable animatic. It may use a
grey model, viewport captures, or low-fidelity rendering, but it must express
all five shots, transitions, holds, camera intent, lighting intent, and total
rhythm. Record its URI, duration, review status, and review notes.

Do not use a scroll-controlled implementation as the first animatic. Establish
the authored playback rhythm first; map the approved time axis to scroll later.

## Automatic Release

Release implementation when the ordered creative record, exactly five shots,
deterministic per-frame camera previs, fixed-duration animatic, truth
constraints, continuity, hidden-cut, roll, and stable-hold checks all pass.
Record the release identity, time, evidence reference, and checks. Human
screening is optional unless current project policy explicitly requires it.

Any material change to thesis, shot order, camera intent, lighting intent,
transitions, or product claims invalidates the release and returns the work to
the earliest affected phase.

## Implementation Translation

After automatic release:

1. generate the runtime story manifest from the released record;
2. translate each shot into camera, product, part, light, material, layout, and
   copy curves;
3. preserve shot purpose, transition, and hold behavior during optimization;
4. verify a canonical authored playback and the scroll-scrubbed version;
5. collect runtime performance evidence only after narrative conformance passes.
