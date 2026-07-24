# Craft declaration

## Product-specific quality intent

- The product itself is the signature element. Composition, lighting, and type must frame the model rather than compete with it.
- The exploded view must explain spatial construction: parts move away from the model center with readable depth, then reassemble when scrolling backward.
## Content truth and prohibited fabrication

- Label all transfer/memory values as asset documentation or measured build output.
- Show the Khronos asset credit and CC BY 4.0 link.
- Do not imply the concept car is a ROKE product, a commercial configurator, or a measured engineering assembly.
## Information density and hierarchy

- One fixed 3D stage, one compact technical rail, and four scroll chapters.
- The active chapter may be emphasized; inactive content stays readable and does not become a stack of decorative cards.
## Typography, imagery, material, and visual-expression expectations

- Light gray studio background, charcoal display type, restrained red status/accent, subtle cool-gray technical metadata.
- Use local/system fonts with robust Chinese fallback. No external font request.
- Physically based materials render under a generated neutral studio environment, with controlled tone mapping and a grounded contact shadow.
- Avoid ornamental gradients, glass cards, glow, fake dashboards, logos, or unsupported claims.
## Interaction and motion intent

- Scroll has direct spatial meaning: inspect, rotate, separate, understand.
- Smooth toward the current scroll target without autoplay or perpetual looping.
- Scrolling backward must reverse every transform.
## Accessibility and responsive baseline

- Text exists in HTML before scripts execute.
- Visible focus, skip link, semantic headings, live loading/error status, and links with accessible names.
- `prefers-reduced-motion: reduce` renders a stable assembled model and replaces motion instructions with a static explanation.
- Below the desktop breakpoint, keep content readable and avoid a forced 500vh interaction.
## Generic-output risks relevant to this product

- Generic premium-car landing page styling would obscure the experiment's engineering purpose.
- Excessive chrome, floating chips, or decorative data panels would compete with the real model.
## Accepted exceptions

- Mobile receives a simplified static study; full touch orbit and exploded interaction are out of scope.
