#!/usr/bin/env python3
"""Render and check diagrams in the shared theme.

    python diagram.py mermaid  flow.mmd [--out flow] [--width 1600] [--theme my.css]
        -> flow.svg + flow.png  (Mermaid via @mermaid-js/mermaid-cli, pinned; needs Node.js)
    python diagram.py svg      arch.svg [--out arch.out] [--theme my.css] [--scale 2]
        -> arch.out.svg (theme styles inlined, standalone) + arch.out.png + layout check (exit 1 on issues)
    python diagram.py new-svg  arch.svg [--width 960 --height 540]
        -> starter SVG with the node / edge / group / legend conventions

Needs Python 3.9+ and Chrome, Edge or Chromium (CHROME_PATH to override).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _browser as b  # noqa: E402

SKILL = Path(__file__).resolve().parent.parent
MERMAID_CLI = "@mermaid-js/mermaid-cli@11.4.2"
STATUSES = ("confirmed", "proposed", "unclear")


# ---------------------------------------------------------------- mermaid

def mermaid_config(v: dict) -> dict:
    return {
        "theme": "base",
        "themeVariables": {
            "background": v["surface"], "fontFamily": v["font-sans"], "fontSize": "16px",
            "primaryColor": v["surface"], "primaryTextColor": v["ink"], "primaryBorderColor": v["muted"],
            "secondaryColor": v["accent-soft"], "secondaryBorderColor": v["accent"], "secondaryTextColor": v["ink"],
            "tertiaryColor": v["surface-2"], "tertiaryBorderColor": v["line"], "tertiaryTextColor": v["ink"],
            "lineColor": v["muted"], "textColor": v["ink"], "clusterBkg": v["surface-2"], "clusterBorder": v["line"],
            "edgeLabelBackground": v["surface"], "noteBkgColor": v["status-proposed-soft"], "noteBorderColor": v["status-proposed"],
            "actorBkg": v["surface"], "actorBorder": v["muted"], "signalColor": v["ink"],
        },
        "flowchart": {"curve": "basis", "padding": 16, "nodeSpacing": 48, "rankSpacing": 56},
        "sequence": {"mirrorActors": False},
    }


def with_status_classes(src: str, v: dict) -> str:
    """Append classDef for :::confirmed / :::proposed / :::unclear in flowcharts that use them without defining them."""
    first = next((l.strip() for l in src.splitlines() if l.strip() and not l.strip().startswith(("%%", "---"))), "")
    if not re.match(r"(flowchart|graph)\b", first):
        return src
    extra = []
    for s in STATUSES:
        used = re.search(rf"(:::{s}\b)|(^\s*class\s+[^\n]*\b{s}\s*;?\s*$)", src, re.M)
        if used and not re.search(rf"classDef\s+{s}\b", src):
            extra.append(f"  classDef {s} fill:{v[f'status-{s}-soft']},stroke:{v[f'status-{s}']},color:{v['ink']},stroke-width:1.5px")
    return src.rstrip() + ("\n" + "\n".join(extra) + "\n" if extra else "\n")


def cmd_mermaid(a) -> int:
    src_path = Path(a.source)
    base = Path(a.out) if a.out else src_path.with_suffix("")
    npx = shutil.which("npx")
    if not npx:
        sys.exit("Mermaid needs Node.js (npx not found). Install Node 18+ or draw the diagram as SVG instead.")
    v = b.theme_vars(a.theme)
    with tempfile.TemporaryDirectory(prefix="agent-skills-mmd-") as tmp:
        tmp = Path(tmp)
        (tmp / "in.mmd").write_text(with_status_classes(src_path.read_text(encoding="utf-8"), v), encoding="utf-8")
        (tmp / "config.json").write_text(json.dumps(mermaid_config(v)), encoding="utf-8")
        (tmp / "puppeteer.json").write_text(json.dumps({"executablePath": b.find_browser(), "headless": "new"}), encoding="utf-8")
        env = dict(os.environ, PUPPETEER_SKIP_DOWNLOAD="1", PUPPETEER_SKIP_CHROMIUM_DOWNLOAD="1")
        outputs = []
        for ext, extra in ((".svg", []), (".png", ["-w", str(a.width), "-s", "2"])):
            out = base.with_name(base.name + ext).resolve()
            out.parent.mkdir(parents=True, exist_ok=True)
            cmd = [npx, "-y", MERMAID_CLI, "-i", str(tmp / "in.mmd"), "-o", str(out), "-c", str(tmp / "config.json"),
                   "-p", str(tmp / "puppeteer.json"), "-b", v["surface"], *extra]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, timeout=300)
            if res.returncode != 0 or not out.is_file():
                err = (res.stderr or res.stdout).strip()
                parse = re.search(r"(Parse error.*?)(\n\s*at |\Z)", err, re.S)
                sys.exit("mermaid-cli failed:\n" + (parse.group(1) if parse else err[-1500:]))
            outputs.append(out)
    for out in outputs:
        print(out)
    return 0


# ---------------------------------------------------------------- svg

def svg_theme_css(v: dict) -> str:
    """Theme as literal values (no CSS variables), so the SVG renders the same in any viewer."""
    css = f"""
  text {{ font-family: {v['font-sans']}; fill: {v['ink']}; }}
  .node > rect, .node > circle, .node > ellipse, .node > path {{ fill: {v['surface']}; stroke: {v['muted']}; stroke-width: 1.5; }}
  .node.accent > rect, .node.accent > circle, .node.accent > ellipse, .node.accent > path {{ fill: {v['accent']}; stroke: {v['accent']}; }}
  .node.accent text {{ fill: #ffffff; }}
  .node.accent .sub {{ fill: #ffffff; fill-opacity: .8; }}
  .node.muted > rect {{ fill: {v['surface-2']}; stroke: {v['line']}; }}
  .node .title {{ font-size: 15px; font-weight: 600; }}
  .node .sub {{ font-size: 12.5px; fill: {v['muted']}; }}
  .edge {{ fill: none; stroke: {v['muted']}; stroke-width: 1.5; }}
  .edge.accent {{ stroke: {v['accent']}; stroke-width: 2; }}
  .edge.dashed {{ stroke-dasharray: 6 4; }}
  .edge-label {{ font-size: 12.5px; fill: {v['muted']}; font-weight: 600; }}
  .edge-label-bg {{ fill: {v['surface']}; }}
  .group > rect {{ fill: {v['surface-2']}; stroke: {v['line']}; stroke-width: 1; stroke-dasharray: 5 4; }}
  .group .group-title {{ font-size: 12.5px; font-weight: 700; letter-spacing: 1px; fill: {v['muted']}; text-transform: uppercase; }}
  .heading {{ font-size: 20px; font-weight: 700; }}
  .caption, .legend text {{ font-size: 12.5px; fill: {v['muted']}; }}
  .arrowhead {{ fill: {v['muted']}; }}
  .arrowhead.accent {{ fill: {v['accent']}; }}"""
    for s in STATUSES:
        css += (f"\n  .node.{s} > rect, .node.{s} > circle, .node.{s} > ellipse, .node.{s} > path, .legend .{s} "
                f"{{ fill: {v[f'status-{s}-soft']}; stroke: {v[f'status-{s}']}; }}")
    return css + "\n"


STYLE_RE = re.compile(r'<style id="theme"\s*(/>|>.*?</style>)', re.S)

CHECK_JS = r"""
(function () {
  const svg = document.querySelector('svg'), out = [], vb = svg.viewBox.baseVal;
  const sr = svg.getBoundingClientRect(), k = sr.width / (vb && vb.width ? vb.width : sr.width);
  const R = el => { const r = el.getBoundingClientRect(); return { x: (r.left - sr.left) / k, y: (r.top - sr.top) / k, w: r.width / k, h: r.height / k }; };
  const label = el => (el.textContent || el.id || el.tagName).replace(/\s+/g, ' ').trim().slice(0, 40);
  const hit = (a, b, pad) => a.x < b.x + b.w - pad && b.x < a.x + a.w - pad && a.y < b.y + b.h - pad && b.y < a.y + a.h - pad;
  const W = vb && vb.width ? vb.width : sr.width / k, H = vb && vb.height ? vb.height : sr.height / k;

  document.querySelectorAll('svg .node').forEach(g => {
    const shape = g.querySelector(':scope > rect, :scope > circle, :scope > ellipse, :scope > path');
    if (!shape) { out.push({ kind: 'node-without-shape', node: label(g) }); return; }
    const box = R(shape);
    g.querySelectorAll('text').forEach(t => {
      const r = R(t), m = 4;
      if (r.x < box.x + m - 0.5 || r.x + r.w > box.x + box.w - m + 0.5 || r.y < box.y + 1 || r.y + r.h > box.y + box.h - 1)
        out.push({ kind: 'text-overflows-node', text: label(t), node: g.id || label(g),
                   need_width: Math.ceil(r.w + 2 * m), node_width: Math.round(box.w) });
    });
  });
  const nodes = Array.from(document.querySelectorAll('svg .node'));
  for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) {
    const a = R(nodes[i]), b = R(nodes[j]);
    if (hit(a, b, 1) && !nodes[i].contains(nodes[j]) && !nodes[j].contains(nodes[i]))
      out.push({ kind: 'nodes-overlap', a: nodes[i].id || label(nodes[i]), b: nodes[j].id || label(nodes[j]) });
  }
  const texts = Array.from(document.querySelectorAll('svg text')).filter(t => t.textContent.trim());
  for (let i = 0; i < texts.length; i++) for (let j = i + 1; j < texts.length; j++)
    if (hit(R(texts[i]), R(texts[j]), 1)) out.push({ kind: 'texts-overlap', a: label(texts[i]), b: label(texts[j]) });
  svg.querySelectorAll('text, rect, circle, ellipse, path, line, polyline, polygon').forEach(el => {
    if (el.closest('defs, marker')) return;
    const r = R(el);
    if (r.w === 0 && r.h === 0) return;
    if (r.x < -1 || r.y < -1 || r.x + r.w > W + 1 || r.y + r.h > H + 1)
      out.push({ kind: 'outside-canvas', el: el.tagName, text: label(el), box: [r.x, r.y, r.w, r.h].map(Math.round), canvas: [Math.round(W), Math.round(H)] });
  });
  texts.forEach(t => { const fs = parseFloat(getComputedStyle(t).fontSize); if (fs < 10) out.push({ kind: 'tiny-text', text: label(t), font_px: fs }); });
  document.getElementById('svg-check').textContent = JSON.stringify({ width: W, height: H, nodes: nodes.length, issues: out });
})();
"""


def build_svg(src: str, v: dict) -> str:
    style = f'<style id="theme">{svg_theme_css(v)}</style>'
    if STYLE_RE.search(src):
        return STYLE_RE.sub(lambda m: style, src, count=1)
    return re.sub(r"(<svg\b[^>]*>)", lambda m: m.group(1) + "\n" + style, src, count=1)


def svg_size(svg: str) -> tuple[float, float]:
    m = re.search(r'viewBox="\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)\s*"', svg)
    if m:
        return float(m.group(1)), float(m.group(2))
    w, h = re.search(r'\bwidth="([\d.]+)', svg), re.search(r'\bheight="([\d.]+)', svg)
    if w and h:
        return float(w.group(1)), float(h.group(1))
    sys.exit("the SVG needs a viewBox (or width and height)")


def cmd_svg(a) -> int:
    src_path = Path(a.source)
    base = Path(a.out) if a.out else src_path.with_name(src_path.stem + ".out")
    svg = build_svg(src_path.read_text(encoding="utf-8"), b.theme_vars(a.theme))
    out_svg = base.with_name(base.name + ".svg").resolve()
    out_png = base.with_name(base.name + ".png").resolve()
    out_svg.parent.mkdir(parents=True, exist_ok=True)
    out_svg.write_text(svg, encoding="utf-8")

    w, h = svg_size(svg)
    inline = re.sub(r"<\?xml[^>]*\?>", "", svg)
    bg = b.theme_vars(a.theme)["surface"]
    with tempfile.TemporaryDirectory(prefix="agent-skills-svg-") as tmp:
        page = Path(tmp) / "view.html"
        page.write_text(
            f'<!doctype html><meta charset="utf-8"><style>html,body{{margin:0;background:{bg}}}'
            f'svg{{display:block;width:{w * a.scale:.0f}px;height:{h * a.scale:.0f}px}}</style>{inline}'
            f'<pre id="svg-check" hidden></pre><script>{CHECK_JS}</script>', encoding="utf-8")
        size = f"{int(w * a.scale)},{int(h * a.scale)}"
        report = json.loads(b.extract_block(b.dump_dom(b.file_url(page), size=size), "svg-check") or "{}")
        b.screenshot(b.file_url(page), out_png, int(w * a.scale), int(h * a.scale))

    print(out_svg)
    print(out_png)
    issues = report.get("issues", [])
    for i in issues:
        print(f"  - {i['kind']}: " + ", ".join(f"{k}={v}" for k, v in i.items() if k != "kind"))
    print(f"{report.get('nodes', 0)} nodes, {len(issues)} issue(s)" + ("" if issues else " - layout is clean"))
    return 1 if issues else 0


def cmd_new_svg(a) -> int:
    out = Path(a.target)
    if out.exists() and not a.force:
        sys.exit(f"{out} exists; pass --force to overwrite")
    src = (SKILL / "assets" / "starter.svg").read_text(encoding="utf-8")
    if a.width or a.height:
        w, h = a.width or 960, a.height or 540
        src = re.sub(r'viewBox="[^"]*"', f'viewBox="0 0 {w} {h}"', src, count=1)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(src, encoding="utf-8")
    print(f"created {out.resolve()} - edit it, then: python scripts/diagram.py svg {out}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("mermaid", help="render a .mmd file to SVG + PNG")
    m.add_argument("source"); m.add_argument("--out", help="output path without extension")
    m.add_argument("--width", type=int, default=1600, help="PNG width in px (default 1600)")
    m.add_argument("--theme"); m.set_defaults(fn=cmd_mermaid)

    s = sub.add_parser("svg", help="inline the theme into a hand-made SVG, check its layout, render PNG")
    s.add_argument("source"); s.add_argument("--out", help="output path without extension (default <name>.out)")
    s.add_argument("--scale", type=float, default=2.0, help="PNG pixels per SVG unit (default 2)")
    s.add_argument("--theme"); s.set_defaults(fn=cmd_svg)

    n = sub.add_parser("new-svg", help="create a starter SVG")
    n.add_argument("target"); n.add_argument("--width", type=int); n.add_argument("--height", type=int)
    n.add_argument("--force", action="store_true"); n.set_defaults(fn=cmd_new_svg)

    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
