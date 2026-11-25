# Hand-made SVG conventions

The source SVG carries **structure and classes only**; `diagram.py svg` inlines the colours and fonts from the
theme into `<style id="theme">` and checks the geometry. Start from `diagram.py new-svg` - it contains every
element below.

## Canvas

- Standalone (docs, README, a whole page): `viewBox="0 0 960 540"`. No `width`/`height`.
- **For a slide** (`figure` layout of the slides skill): `viewBox="0 0 960 410"`, no heading or caption inside
  (the slide has them). The figure area is ~1390×560 px, so this canvas is drawn ~1.35× larger and the smallest
  text (12.5) lands at ~17 px; the slides check wants diagram text ≥ 16 px. A 960×540 canvas on a slide
  renders text at 13–16 px and fails that check. Too much for 960×410? Split the diagram over two slides.
  Create it with `diagram.py new-svg x.svg --width 960 --height 410`, then move the nodes up.
- Margins ≥ 40 units. Heading at `y≈52`, caption at `y≈76`, content from `y≈110`.
- Work on a 10-unit grid; align node edges and centres - the eye catches 3-unit misalignments.

## Elements

```svg
<!-- node: shape FIRST, then texts; classes: accent | muted | confirmed | proposed | unclear -->
<g class="node proposed" id="stream">
  <rect x="620" y="288" width="190" height="72" rx="10"/>
  <text class="title" x="636" y="319">Event stream</text>
  <text class="sub"   x="636" y="340">to be added</text>
</g>

<!-- group: dashed container, drawn BEFORE the nodes it holds -->
<g class="group"><rect x="300" y="116" width="620" height="270" rx="12"/>
  <text class="group-title" x="320" y="142">Platform</text></g>

<!-- edge: classes accent | dashed; ends ~8 units before the target border -->
<path class="edge" d="M 510 226 C 565 226 565 202 612 202" marker-end="url(#arrow)"/>

<!-- edge label with a background, so it stays readable over lines -->
<g><rect class="edge-label-bg" x="536" y="290" width="52" height="16" rx="3"/>
   <text class="edge-label" x="562" y="302" text-anchor="middle">events</text></g>
```

Other text classes: `heading`, `caption`. Markers `#arrow` and `#arrow-accent` are in the starter's `<defs>`.

## Sizing text (the check enforces it)

- Text needs ≥ 4 units of padding inside its node on each side.
- Width estimate: title (15 px, semibold) ≈ **7.5 units per character**, sub (12.5 px) ≈ **6**, edge label (12 px) ≈ **6.5**.
  "Orders service" (14 chars) → ~105 + 32 padding → node width ≥ 140; the check reports the exact `need_width`.
- Node height: 72 for title + sub, 48 for a title alone. Title baseline = top + 31, sub baseline = top + 52.
- Two lines of sub text: add a second `<text class="sub">` 18 units lower and grow the node by 18.

## Composition

- One main direction of flow (left → right or top → bottom); the accent marks the one path or node that matters.
- At most one `accent` node per diagram; statuses for state, accent for attention - do not mix the meanings.
- Prefer straight or single-curve edges; route around nodes rather than through them.
- Every edge either has an obvious meaning or a label; no unlabelled crossing lines.

## What `diagram.py svg` checks

| Issue | Fix |
|---|---|
| `text-overflows-node` (with `need_width`) | widen the node to `need_width`, or shorten the text |
| `nodes-overlap` | move one of them; groups may contain nodes, nodes may not overlap |
| `texts-overlap` | move labels apart; give edge labels a background rect |
| `outside-canvas` | move inside or enlarge the viewBox |
| `tiny-text` (< 10 px) | use the theme classes instead of explicit font sizes |
| `node-without-shape` | the first child of `.node` must be rect / circle / ellipse / path |
