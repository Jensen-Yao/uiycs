# Agent workflow

Image-first UI/UX for agents.

Make the UI image first, then build what is in it. Give the design a strong visual
direction and real product logic; the image becomes the visual specification, not loose
inspiration.

## Set the direction

Read the brief, the relevant code, components, assets and data contracts. Identify the
screen's user, primary task, content and target viewport. Respect the app's brand and
working behavior; only redesign what was requested.

Choose one visually ambitious, coherent direction: purposeful composition, clear
hierarchy, deliberate typography and spacing. Make it specific to the app, not a generic
dashboard or a flashy concept that makes no UX sense.

Before fixing the direction, spend one call on evidence. `find_ui_references` with the
product category and platform returns captured screens with their real type scales and
palettes. Read two of them, note what makes each one specific to its product, and then
design something that is specific to *this* product. Do not copy the reference's layout —
copy the reasoning that made it work.

## Generate the UI image

If the host has an image-generation tool, use it before writing UI code. Include the
screen's purpose, real copy, controls, visual direction, known fonts and assets, and the
viewport size in the prompt. Use non-sensitive content; never send secrets or private
customer data.

Generate the actual UI at a straight-on view, with legible text and realistic controls —
not a poster, device mockup or tilted presentation. Inspect the output. Correct unreadable
labels, broken hierarchy, impossible layouts or invented actions before implementing it.

Save one clear target image and record its actual dimensions. Keep that target stable while
building. If the requested font or icon is not available in the project, resolve it now
through `find_ui_materials` — a font substituted after the image is generated will break
the match.

## Implement it 1:1

Match the target at its original viewport: layout, proportions, typography, text, colors,
spacing, borders, icons and image crops. Do not quietly redesign it during implementation.

Use the project's stack and real layout primitives. Build actual text, components and
working controls; never flatten the whole image into a background. Reuse assets that match,
and identify missing fonts or imagery rather than substituting and claiming an exact
result.

Preserve existing data, auth and app behavior. A picture does not define unseen
interactions; use the brief and existing contracts, not invented backend behavior.

## Render, compare, correct

Run the UI and capture it at the target image's dimensions after fonts and images load.
Compare side by side or with an overlay. Fix layout and proportions first, then typography,
spacing, color and details; render again after corrections.

Check affected controls and requested screen sizes without changing the design's identity.
Report what was compared and any remaining mismatch. If rendering is unavailable, the 1:1
match is unverified — say that.

## Using the local material library

The `uiycs` MCP is a directory tree with a search front. Treat it as a supplier, not an
oracle.

- `find_ui_materials` `kind=font` — returns absolute paths to the actual `.woff2` / `.ttf`
  files with weights, italics and the license file. Check the license before shipping;
  OFL, ITF Free Font License and Apache-2.0 all carry different redistribution terms.
  Copy the file into the project and reference it from the project's own font loader.
- `find_ui_materials` `kind=icon` — the same name exists across lucide (24px, 2px stroke),
  heroicons (16/20/24, solid + outline) and Material Symbols (filled + outlined, three
  optical variants). Choose by the project's existing icon grid, never by what looks best
  in isolation. Stay inside one set per surface.
- `find_ui_materials` `kind=animated_icon` — Lottie JSON or `.lottie`. Query by the
  triggering event (`copy success`) not the visual (`spinner`). Every animation needs a
  reduced-motion fallback.
- `find_ui_materials` `kind=pack` and `find_ui_references` — captured products. Use them
  to answer "what is the conventional treatment for this control" and to avoid inventing
  an unusual pattern where a familiar one is correct.

Limits: 1–10 results per call. An empty result means the corpus does not cover it. State
that and fall back to the project's own conventions rather than retrying until noise comes
back.

## If image generation is unavailable

Use a supplied image as the target. If none exists, state the limitation and build directly
from the brief and existing UI/UX conventions. Do not fabricate a generated image or claim
a 1:1 match without a real target. Follow the host's permission and safety checks; do not
set up another image service without authorization.
