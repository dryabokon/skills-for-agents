---
name: diagrams
description: Draw architecture, flow, sequence and as-is/to-be diagrams as clean SVG and PNG in a shared theme - Mermaid for quick auto-laid-out diagrams, hand-made SVG when the layout matters - and check them automatically (text overflowing boxes, overlaps, elements off canvas) before handing over. Use when the user asks for a diagram, schema, flowchart, architecture picture, sequence diagram, data-flow, or a visual for slides, docs or a report.
license: MIT
compatibility: Requires Python 3.9+ and Chrome, Edge or Chromium. Mermaid rendering also needs Node.js 18+ (npx); hand-made SVG does not.
---

# Diagrams

Two ways to draw, one theme (`theme/tokens.css`, shared with the slides skill) and one status legend.

**Paths.** Commands are relative to this skill's folder (in Claude Code: `${CLAUDE_SKILL_DIR}`).

```bash
python scripts/diagram.py mermaid flow.mmd [--out name] [--width 1600]   # -> flow.svg + flow.png
python scripts/diagram.py new-svg arch.svg [--width 960 --height 540]   # starter with all conventions
python scripts/diagram.py svg     arch.svg [--out name]                  # -> arch.out.svg + .png + check
```

## Choose the route

| Mermaid (`.mmd`) | Hand-made SVG |
|---|---|
| flowchart, sequence, state, ER, gantt, class, mindmap | architecture overviews, as-is vs to-be, anything for a slide or a cover |
| many nodes, layout is not the point | ≤ ~15 nodes, positions and grouping carry meaning |
| minutes to make, editable by anyone | exact control: alignment, grouping, emphasis |
| needs Node.js | needs nothing but a browser |

When unsure: start with Mermaid; switch to SVG if the auto layout tangles or the picture goes on a slide.

## Status legend (both routes, and the slides skill)

`confirmed` — exists or decided · `proposed` — suggested, not agreed · `unclear` — open question / to clarify.
Mermaid: `A[Orders DB]:::confirmed` — the classDef is added automatically.
SVG: `<g class="node proposed">`. Put a legend on the diagram whenever statuses are used.

## Workflow

1. Decide what the diagram must answer ("where does an order go?"); leave out what does not serve that.
2. Mermaid: write the `.mmd`, run `diagram.py mermaid`.
   SVG: `diagram.py new-svg`, then edit following [references/svg-conventions.md](references/svg-conventions.md).
3. **Look at the PNG.** For SVG also fix every issue `diagram.py svg` reports (it exits 1 while issues remain):
   widen the box or shorten the text, move overlapping items, enlarge the viewBox.
4. Hand over the SVG (scales for slides and docs) and mention the PNG.
   For a slide, paste the output SVG into a `figure` slide of the slides skill.

## Mermaid rules

- Left-to-right (`flowchart LR`) for pipelines, top-down for hierarchies. ≤ 6 words per node label.
- Wide LR diagrams render small; raise `--width` (e.g. 3000) rather than shrinking text.
- Mermaid errors are printed as the parser reports them; the usual culprits are unquoted labels with
  `()`, `:` or `/` — write `A["Label (x)"]`.
- Theme colours come from the tokens; do not add `%%{init: …}%%` theme blocks unless the user asks.

## Theme

Same lookup as the slides skill: `--theme file.css` → `AGENT_THEME` → `./.agent-theme.css` → bundled default.
The SVG output gets literal colours (not CSS variables), so it renders identically in browsers, Office and Figma.
