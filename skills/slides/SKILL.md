---
name: slides
description: Build presentation slide decks as a single self-contained HTML file (16:9, keyboard navigation, themeable) and export them to PDF; check the layout automatically and look at screenshots before handing over. Use when the user asks for slides, a deck, a presentation, a pitch, a talk, a one-slide summary, or to turn a document, report or notes into slides. Not for editing existing .pptx files.
license: MIT
compatibility: Requires Python 3.9+ and Chrome, Edge or Chromium (set CHROME_PATH if not auto-detected). No pip packages.
---

# Slides

A deck is one HTML file: theme + layout engine + `<section class="slide layout-…">` per slide.
It opens in any browser, prints to PDF one slide per page, and needs no build step.

**Paths.** Commands below are relative to this skill's folder (in Claude Code: `${CLAUDE_SKILL_DIR}`);
from elsewhere call e.g. `python <this-folder>/scripts/deck.py`. Everything goes through one CLI:

```bash
python scripts/deck.py new   DECK.html --title "…" [--kicker "…"] [--subtitle "…"] [--meta "…"] [--theme my.css]
python scripts/deck.py check DECK.html                  # layout problems per slide; exit 1 if any
python scripts/deck.py shots DECK.html [--slides 2,5]   # PNG per slide -> DECK-shots/
python scripts/deck.py pdf   DECK.html [--out x.pdf]    # one 16:9 page per slide
python scripts/deck.py theme DECK.html --theme my.css   # restyle an existing deck
```

## Workflow

1. **Plan the story first**, in chat or in your head: audience, the one thing they must leave with, 5–12 slides.
   One message per slide; the heading states the message ("Batch misses the morning report"), not the topic ("Batch").
2. `deck.py new` creates the file with the title slide and the theme inlined.
3. **Write the slides** between `<!-- ===== slides` and `<!-- ===== end of slides ===== -->`, picking a layout per
   slide from [references/layouts.md](references/layouts.md): `title`, `section`, `bullets`, `two-col`, `metrics`,
   `figure`, `quote`, `table`. Copy the snippet, replace the text. Do not invent new CSS unless no layout fits.
4. `deck.py check` — fix every issue it reports (overflow, clipped or tiny text, >90 words, broken image) by cutting
   text, splitting the slide or choosing another layout. Never by shrinking fonts below the defaults.
5. `deck.py shots` and **look at the PNGs** — check balance, emptiness, alignment and that nothing reads awkwardly.
   The checker catches geometry, not taste.
6. `deck.py pdf` if the user needs a file to send. Hand over the HTML path (and PDF), and say how to navigate:
   arrows / space / click, `F` full screen, `#3` in the URL opens slide 3.

## Content rules

- ≤ 40 words of body text and ≤ 5 bullets per slide; details go to speaker notes in chat or an appendix slide.
- Numbers: give the unit and the comparison ("−38% compute cost vs today"), not a bare figure.
- Status pills use the shared legend: `.tag.confirmed` (decided / true now), `.tag.proposed` (suggested),
  `.tag.unclear` (open question / rejected). The diagrams skill uses the same three colours.
- Diagrams: make them with the diagrams skill and put them on a `figure` slide; paste the `<svg>` inline to keep
  the deck one file.
- Language: write slides in the language the user writes to you in, unless told otherwise.

## Theme

Colours and fonts are CSS variables (`theme/tokens.css`). A custom theme overrides only what it changes:

```css
:root { --accent: #0f766e; --accent-soft: #e6f4f2; --font-sans: "Inter", sans-serif; }
```

Lookup order: `--theme file.css` → `AGENT_THEME` env var → `./.agent-theme.css` in the working directory → bundled
default. In slide HTML use `var(--accent)` etc., never literal colours, so `deck.py theme` can restyle later.

## Gotchas

- Fonts: the default stack is system fonts, so the deck looks the same offline. A web font needs a `<link>` in the
  head and makes the deck depend on the network.
- Images by relative path work while the PNG/SVG sits next to the HTML; for a file to send, inline SVG or use the PDF.
- `check` runs the deck in headless Chrome; if it reports nothing at all, the file was not made from the template.
