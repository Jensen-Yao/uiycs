# uiycs-ui

An image-first UI workflow for coding agents, backed by a fully local material library.

## What it does

Most UI mistakes come from the agent not having looked at anything. This skill fixes the
input, not the output:

1. **Set direction from evidence.** `find_ui_references` returns captured product screens
   with their real type scales, palettes and component inventories. You read two, note why
   each is specific to its product, and design something specific to yours.
2. **Resolve materials before building.** `find_ui_materials` returns absolute file paths
   for a font family, an icon across four sets, or an animation — with license attached.
   A font substituted after the mockup is generated breaks the 1:1 match.
3. **Build 1:1 from a target image.** The target image is the specification. Layout,
   proportions, type, spacing and crops match it; behavior comes from the project's own
   contracts, not from the picture.
4. **Render, compare, correct.** Capture at the target's dimensions, diff, fix layout first
   then type then detail, capture again.

## Install

```bash
cp -r uiycs-ui ~/.agents/skills/
```

Requires the `uiycs` MCP server running (see the repository root README). The skill degrades
gracefully without it — it becomes a plain image-first workflow with no reference corpus.

## Trigger policy

`disable-model-invocation: true`. This skill is invoked by name when a UI task needs
reference hunting or material sourcing. Ordinary product interface work routes to
`ui-design`; pre-ship checks route to `anti-ui-slop`; screenshot reconstruction routes to
`image-to-ui`.

## Files

```text
SKILL.md              frontmatter + routing + tool usage
references/
└── workflow.md       the six-step procedure, read before any UI work
```

## License

MIT. See the repository root [LICENSE](../../LICENSE).
