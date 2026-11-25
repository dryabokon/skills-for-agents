---
name: report
description: Make status reports as one self-contained HTML page in a consistent style - test runs, CI or check results, data-quality and freshness checks, audits, before/after comparisons, run histories - with a verdict, KPI tiles, a green/orange/red/yellow status bar, compact tables, expandable findings with checks, screenshots and output, and a light/dark theme switch. Also use it when writing code that produces an HTML report (a test runner, a CI step, a monitoring script) - render through scripts/report.py instead of hand-writing HTML and CSS. Use when the user asks for a report, a summary page, a dashboard of results, an HTML overview, or a nicer look for existing results.
license: MIT
compatibility: Requires Python 3.9+ (standard library only). Screenshots need Chrome, Edge or Chromium.
---

# Report

A report is a JSON description rendered by `scripts/report.py` into one HTML file with the CSS and theme switch
inlined - it opens anywhere and looks the same every time. Commands are relative to this skill's folder (in Claude
Code: `${CLAUDE_SKILL_DIR}`).

```bash
python scripts/report.py example -o spec.json          # a spec using every block - start from it
python scripts/report.py render spec.json -o report.html
python scripts/report.py shot report.html [--dark]      # PNG to look at; --dark checks the dark theme
```

From Python (a test runner, a CI script): `sys.path.insert(0, "<skill>/scripts"); import report;
report.write(spec, Path("runs/007/index.html"))`.

## Building blocks

| Spec key / block | Use for |
|---|---|
| `title`, `crumbs`, `meta` | page name, path back (e.g. `All runs / 007`), date · commit · duration |
| `verdict` `{status, text}` | the one-line answer, top right: "All passed", "2 failed", "3 need attention" |
| `bar` `{good: n, bad: n, ...}` | proportional status bar with legend - the shape of the result at a glance |
| `kpis` | 2-5 numbers that matter, each with a status colour and an optional hint |
| `groups` | one card per area (skill, service, table) with a dot per item; `href` jumps to its section |
| `table` | compact rows; a cell `{text, status}` becomes a coloured pill; `num` right-aligns columns |
| `items` | expandable findings / cases: status pill, title, sub-id, right note, checks ✓/✗, images, links, output |
| `text`, `images`, `code` | prose, screenshots, raw output |

Statuses: `good` (green) · `warn` (orange) · `bad` (red) · `note` (yellow, e.g. skipped) · `neutral` (grey);
`pass/fail/skip/error` are accepted as aliases.

## Rules

1. **Answer first.** The verdict and the bar must tell the result without scrolling; failures come first and are
   `open`; passing items stay collapsed.
2. **Numbers with meaning.** A KPI has a unit or a comparison in its hint ("of 29", "+12% vs last week").
3. **Evidence, not decoration.** Each failed item shows what was expected and what happened (checks with detail),
   plus the output or screenshot that proves it. Link full logs instead of pasting them whole.
4. **Do not hand-write HTML/CSS for a report** - extend the spec; if a block is missing, add it to report.py so every
   report keeps the same look. Use the `html` block only for one-off content.
5. **Look at it**: `shot` light and `--dark` before handing over.

## Examples

Run from this folder (`bash examples/<name>.sh`):
- `examples/weekly-checks.sh` - the example spec rendered and screenshot in both themes.
- The skill tests of this repository render their run reports with this skill (`python tests/run.py`, see
  `runs/NNN/index.html` and the history in `runs/index.html`).

## Gotchas

- Images and links are relative to the HTML file; keep them next to it (e.g. one folder per run).
- `?theme=dark` / `?theme=light` in the URL forces a theme (for links and screenshots); otherwise the reader's last
  choice, then the system setting, is used.
