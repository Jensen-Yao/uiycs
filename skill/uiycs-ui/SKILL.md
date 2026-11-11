---
name: uiycs-ui
description: "Build UI from real references instead of invented ones. Calls the local uiycs MCP for captured product screens with extracted design tokens and per-screen OCR text, plus licensed fonts (217 families incl. CJK), icons (6,307 names across four sets) and Lottie animations (750) — every result a local file path with license attached. Use when a UI task needs a concrete reference, a real font file, a specific icon, or a motion asset. Not a review gate — shipping checks belong to anti-ui-slop."
license: MIT
metadata:
  author: Jensen Yao
  version: "1.0.0"
disable-model-invocation: true
---

# uiycs UI

Build interfaces from evidence. The local `uiycs` MCP holds 685 captured products with
their design tokens, 217 font families, 6,307 icon names and 750 animations — all offline,
all local files. Use it instead of guessing what a good settings screen, empty state or
data table looks like.

## Build the UI

Work from the project's own code, assets and contracts first. The MCP is for the moments
where you do not know what the right answer looks like.

1. Inspect the screen, components, tokens and data contracts. Identify the primary task
   and preserve working behavior.
2. Improve layout, hierarchy, typography and spacing. Implement the requested controls and
   the loading, empty, error and success states that apply. Do not invent backend behavior.
3. Run it and look at it at the sizes that matter. Check keyboard access, focus and
   overflow, fix what you observe, and report what you actually verified.

## When to call the MCP

Call only when it answers a concrete question you cannot answer from the project:

| Situation | Call |
|---|---|
| "What does a real billing settings screen look like?" | `find_ui_references` |
| "Which type scale and palette does a fintech dashboard actually use?" | `find_ui_materials` `kind=pack` |
| "Give me this project's display font as a file." | `find_ui_materials` `kind=font` |
| "Which icon set has this at the right stroke weight?" | `find_ui_materials` `kind=icon` |
| "What animation fires on a successful copy?" | `find_ui_materials` `kind=animated_icon` |

An empty result is a real answer: it means the corpus does not cover that case. Say so and
continue with the project's own conventions. Do not retry with synonyms until something
comes back.

## Reading the results

**References.** Each pack returns a palette, a typography scale, a component inventory and
screens with OCR text. Screens are images at a known viewport — treat them as visual
specification, not as code to copy. Show a returned image once through the host's gallery
or attachment mechanism. Never copy another product's branding, logotype, proprietary copy
or screenshots into the app you are building.

**Fonts.** Every family returns absolute paths to real `.woff2` / `.ttf` files plus
`weight`, `italics`, `license` and `license_file`. Read the license before shipping a
commercial-free family into a product. Never substitute a system fallback and claim the
requested font was applied.

**Icons.** A name can exist in several sets with different grid and stroke conventions.
`arrow-right` returns lucide at 24px/2px and heroicons at three sizes plus outline — pick
the one matching the project's existing icon system, and do not mix sets inside one
surface.

**Animations.** Results are Lottie JSON or `.lottie` zip. Always pair an animation with a
`prefers-reduced-motion` fallback. Name the triggering event in the query (`copy success`,
`form error`) rather than the visual (`spinner`) when you know the event.

## Present and apply

Show each reference image once. Cite what you took from it — a spacing rhythm, a status
treatment, an empty-state structure — rather than claiming a design is "inspired by" a
screenshot you did not examine.

Apply what you retrieved through the implementation loop above. Preserve the project's
stack and behavior. Report which sources you actually used, and state plainly when a
material was unavailable rather than fabricating a result.

## Agent instructions

Before UI work, read `references/workflow.md` next to this file and follow it. It defines
the image-first procedure: set direction, generate or obtain a target image, implement 1:1,
then render and correct. Respect the project's own rules; report only what you verified.
