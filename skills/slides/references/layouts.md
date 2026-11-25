# Slide layouts

Every slide is one `<section class="slide layout-…">` between the `===== slides` markers of a deck
created by `deck.py new`. The stage is always 1600×900 px; sizes below are in those pixels.
Slide numbers are added automatically (not on title slides).

Budget per slide: **one message, ≤ 40 words of body text, ≤ 5 bullets**. `deck.py check` warns above 90 words.

## title — opening slide

```html
<section class="slide layout-title">
  <div class="kicker">Architecture review</div>
  <h1>Moving ingestion to streaming</h1>
  <p class="lead">Why batch stopped scaling, what we change, what it costs.</p>
  <div class="meta">Platform team · March 2026</div>
</section>
```

## section — divider between parts (accent background)

```html
<section class="slide layout-section">
  <div class="kicker">Part 2</div>
  <h1>The proposal</h1>
</section>
```

## bullets — plain slide (no extra class needed beyond the layout name)

```html
<section class="slide layout-bullets">
  <div class="kicker">Problem</div>
  <h2>Nightly batch misses the morning report</h2>
  <ul>
    <li>Volume grew <strong>4×</strong> in a year; the job now runs 7 h</li>
    <li>A single failure delays everything by a day</li>
    <li>Analysts work on data that is 30 h old</li>
  </ul>
  <p class="note">Source: job history, Jan–Dec</p>
</section>
```

## two-col — comparison, before/after, text + picture

`.cols` takes `wide-left` or `wide-right` for a 3:2 split, and `fill` to stretch both columns to the
bottom of the slide (use it only when both columns have enough content). Cards are optional.

```html
<section class="slide layout-two-col">
  <h2>As-is vs to-be</h2>
  <div class="cols">
    <div class="col card">
      <h3>As-is <span class="tag confirmed">confirmed</span></h3>
      <p>One nightly job, 7 h, manual restarts.</p>
    </div>
    <div class="col card accent">
      <h3>To-be <span class="tag proposed">proposed</span></h3>
      <p>Streaming ingest, data in minutes, automatic retries.</p>
    </div>
  </div>
</section>
```

## metrics — 2 to 4 big numbers

Values never wrap. Keep each value short (≤ 6 characters at 4 metrics, ≤ 9 at 3); for longer
ones add `small-value` (`<div class="value small-value">7 h → 5 min</div>`) or use fewer metrics.

```html
<section class="slide layout-metrics">
  <h2>What changes</h2>
  <div class="metrics">
    <div class="metric"><div class="value small-value">7 h → 5 min</div><div class="label">data latency</div></div>
    <div class="metric"><div class="value">−38%</div><div class="label">compute cost</div></div>
    <div class="metric"><div class="value accent">0</div><div class="label">manual restarts</div></div>
  </div>
</section>
```

## figure — one diagram, chart or screenshot

Use an SVG or PNG made by the diagrams skill. The figure fills the space under the heading (~1390×560 px).
Draw diagrams for slides on a 960×410 canvas without their own heading, so their text stays ≥ 16 px;
`deck.py check` reports `tiny-text` for diagrams drawn smaller.

```html
<section class="slide layout-figure">
  <h2>Target architecture</h2>
  <figure>
    <img src="architecture.svg" alt="Sources to stream to warehouse">
    <figcaption>Blue — confirmed, amber — proposed, red — to clarify.</figcaption>
  </figure>
</section>
```

The deck is a single file only if images are inline. To keep it single-file, paste the `<svg>…</svg>`
element itself instead of `<img>` (it scales the same way).

## quote — one statement

```html
<section class="slide layout-quote">
  <blockquote>We don't need faster batch. We need no batch.</blockquote>
  <cite>— Head of analytics</cite>
</section>
```

## table — up to ~7 rows × 5 columns

```html
<section class="slide layout-table">
  <h2>Options</h2>
  <table>
    <tr><th>Option</th><th>Latency</th><th>Cost</th><th>Status</th></tr>
    <tr><td>Bigger batch cluster</td><td>4 h</td><td>+20%</td><td><span class="tag unclear">rejected</span></td></tr>
    <tr><td>Micro-batch</td><td>30 min</td><td>±0</td><td><span class="tag proposed">fallback</span></td></tr>
    <tr><td>Streaming</td><td>5 min</td><td>−38%</td><td><span class="tag confirmed">chosen</span></td></tr>
  </table>
</section>
```

## Building blocks

| Class | Use |
|---|---|
| `.kicker` | small uppercase label above a heading |
| `.lead` | large muted paragraph under a title |
| `.card`, `.card.accent` | boxed group; accent = the recommended / new option |
| `.tag.confirmed` / `.tag.proposed` / `.tag.unclear` | status pill, same legend as the diagrams skill |
| `.note` | small source / footnote line, pinned to the bottom |
| `.muted`, `.accent`, `.small`, `.mono` | text tone and size |
| `.grow` | let an element take the remaining height |
| `data-check="off"` | exclude an element (e.g. a deliberately bleeding image) from `deck.py check` |

Per-deck CSS goes into `<style id="deck-custom">`. Prefer theme variables (`var(--accent)`) over literal colours,
so `deck.py theme` can restyle the deck later.
