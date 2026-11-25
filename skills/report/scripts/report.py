#!/usr/bin/env python3
"""Status reports as one self-contained HTML page: header with a verdict, KPI tiles, a status bar, groups, tables,
expandable items with checks / images / output, light and dark theme. Describe the report as JSON, render it.

    python report.py render spec.json [-o report.html]     build the page (CSS and JS inlined; images by relative path)
    python report.py shot   report.html [-o report.png] [--width 1280] [--dark]   screenshot to look at the result
    python report.py example [-o spec.json]                a spec using every block, to start from

Statuses everywhere: good | warn | bad | note | neutral  (aliases: pass=good, fail=bad, skip=note, error=bad).

Spec (all keys optional except title):
{
  "title": "Run 007", "crumbs": [{"text": "All runs", "href": "../index.html"}, {"text": "007"}],
  "meta": ["2026-11-25 12:40", "commit abc123", "84 s"],
  "verdict": {"status": "bad", "text": "2 failed"},
  "kpis": [{"label": "passed", "value": 27, "status": "good", "hint": "of 29"}],
  "bar": {"good": 27, "bad": 2, "note": 0},            -> proportional status bar with a legend
  "groups": [{"name": "slides", "href": "#slides", "summary": "4/4 passed", "dots": ["good", "good", "bad"]}],
  "sections": [{"title": "slides", "id": "slides", "note": "4/4 passed", "blocks": [
      {"type": "text", "text": "Plain paragraph."},
      {"type": "table", "columns": ["Case", "Result"], "rows": [["build", {"text": "pass", "status": "good"}]], "num": [2]},
      {"type": "items", "items": [{"status": "bad", "title": "...", "sub": "case-id", "right": "3.1 s", "open": true,
          "checks": [{"ok": false, "text": "exit code 0", "detail": "got 1"}],
          "images": [{"src": "01/slide.png", "caption": "slide 1"}], "links": [{"text": "output", "href": "01/out.txt"}],
          "code": "...output..."}]},
      {"type": "images", "items": [{"src": "chart.png", "caption": "..."}]},
      {"type": "code", "text": "..."}]}]
}
Standard library only; Python 3.9+. `shot` needs Chrome, Edge or Chromium (CHROME_PATH to override).
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
ALIASES = {"pass": "good", "passed": "good", "ok": "good", "success": "good", "fail": "bad", "failed": "bad",
           "error": "bad", "skip": "note", "skipped": "note", "warning": "warn"}
STATUSES = ("good", "warn", "bad", "note", "neutral")
LABELS = {"good": "pass", "warn": "warn", "bad": "fail", "note": "skip", "neutral": "info"}


def st(s: str | None) -> str:
    s = ALIASES.get((s or "neutral").lower(), (s or "neutral").lower())
    return s if s in STATUSES else "neutral"


def e(x) -> str:
    return html.escape("" if x is None else str(x))


def cell(c) -> str:
    if isinstance(c, dict):
        inner = e(c.get("text"))
        if c.get("href"):
            inner = f"<a href='{e(c['href'])}'>{inner}</a>"
        if c.get("status"):
            inner = f"<span class='pill bg-{st(c['status'])}'>{inner}</span>" if c.get("pill", True) else \
                f"<span class='s-{st(c['status'])}'>{inner}</span>"
        return inner
    return e(c)


def block(b: dict) -> str:
    t = b.get("type")
    if t == "text":
        return "".join(f"<p>{e(p)}</p>" for p in str(b.get("text", "")).split("\n\n"))
    if t == "html":  # trusted, written by the caller
        return str(b.get("html", ""))
    if t == "code":
        return f"<pre>{e(b.get('text'))}</pre>"
    if t == "table":
        num = set(b.get("num", []))
        head = "".join(f"<th class='{'num' if i + 1 in num else ''}'>{e(c)}</th>" for i, c in enumerate(b.get("columns", [])))
        rows = "".join("<tr>" + "".join(f"<td class='{'num' if i + 1 in num else ''}'>{cell(c)}</td>" for i, c in enumerate(r))
                       + "</tr>" for r in b.get("rows", []))
        return f"<div class='tablewrap'><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>"
    if t == "images":
        return images(b.get("items", []))
    if t == "items":
        return "".join(item(i) for i in b.get("items", []))
    raise SystemExit(f"error: unknown block type {t!r}")


def images(items: list) -> str:
    if not items:
        return ""
    return "<div class='imgs'>" + "".join(
        f"<figure><a href='{e(i.get('href') or i['src'])}'><img src='{e(i['src'])}' alt='{e(i.get('caption'))}' loading='lazy'></a>"
        + (f"<figcaption>{e(i['caption'])}</figcaption>" if i.get("caption") else "") + "</figure>" for i in items) + "</div>"


def item(i: dict) -> str:
    s = st(i.get("status"))
    body = ""
    if i.get("text"):
        body += f"<p>{e(i['text'])}</p>"
    if i.get("checks"):
        body += "<ul class='checks'>" + "".join(
            f"<li><span class='s-{'good' if c.get('ok') else 'bad'}'>{'✓' if c.get('ok') else '✗'}</span> {e(c.get('text'))}"
            + (f" <span class='muted'>— {e(c['detail'])}</span>" if c.get("detail") else "") + "</li>" for c in i["checks"]) + "</ul>"
    body += images(i.get("images", []))
    if i.get("links"):
        body += "<div class='links'>" + "".join(f"<a href='{e(l['href'])}'>{e(l['text'])}</a>" for l in i["links"]) + "</div>"
    if i.get("code"):
        body += f"<pre>{e(i['code'])}</pre>"
    label = i.get("label") or LABELS[s]
    return (f"<details class='item'{' open' if i.get('open') else ''}><summary><span class='pill bg-{s}'>{e(label)}</span>"
            f"<span class='t'>{e(i.get('title'))}" + (f"<div class='sub'>{e(i['sub'])}</div>" if i.get("sub") else "")
            + f"</span><span class='r'>{e(i.get('right'))}</span></summary>" + (f"<div class='b'>{body}</div>" if body else "")
            + "</details>")


def render(spec: dict) -> str:
    css = (ASSETS / "report.css").read_text(encoding="utf-8")
    js = (ASSETS / "report.js").read_text(encoding="utf-8")
    crumbs = " / ".join(f"<a href='{e(c['href'])}'>{e(c['text'])}</a>" if c.get("href") else e(c.get("text"))
                        for c in spec.get("crumbs", []))
    out = [f"<!doctype html><html lang='{e(spec.get('lang', 'en'))}'><head><meta charset='utf-8'>"
           "<meta name='viewport' content='width=device-width,initial-scale=1'>"
           f"<title>{e(spec['title'])}</title><style>{css}</style><script>{js}</script></head><body>",
           f"<div class='bar-top'><div class='crumbs'>{crumbs}</div>"
           "<button id='theme' class='theme-toggle' type='button'>◐ Dark</button></div><div class='page'>"]
    v = spec.get("verdict")
    out.append(f"<div class='head'><div><h1>{e(spec['title'])}</h1>"
               + ("<div class='meta'>" + "".join(f"<span>{e(m)}</span>" for m in spec.get("meta", [])) + "</div>" if spec.get("meta") else "")
               + "</div>" + (f"<div class='verdict bg-{st(v.get('status'))}'>{e(v.get('text'))}</div>" if v else "") + "</div>")
    if spec.get("bar"):
        counts = {st(k): n for k, n in spec["bar"].items()}
        total = sum(counts.values()) or 1
        out.append("<div class='sbar'>" + "".join(f"<i class='{k}' style='width:{n / total * 100:.2f}%'></i>"
                                                    for k, n in counts.items() if n) + "</div>")
        names = spec.get("bar_labels", {"good": "passed", "bad": "failed", "note": "skipped", "warn": "warnings", "neutral": "other"})
        out.append("<div class='legend'>" + "".join(f"<span><b class='s-{k}'>{n}</b> {e(names.get(k, k))}</span>"
                                                     for k, n in counts.items()) + "</div>")
    if spec.get("kpis"):
        out.append("<div class='kpis'>" + "".join(
            f"<div class='kpi'><div class='v s-{st(k.get('status'))}'>{e(k.get('value'))}</div><div class='l'>{e(k.get('label'))}</div>"
            + (f"<div class='h'>{e(k['hint'])}</div>" if k.get("hint") else "") + "</div>" for k in spec["kpis"]) + "</div>")
    if spec.get("groups"):
        out.append("<div class='groups'>" + "".join(
            f"<a class='group' href='{e(g.get('href', '#'))}'><div class='n'>{e(g.get('name'))}</div>"
            f"<div class='c'>{e(g.get('summary'))}</div><div class='dots'>"
            + "".join(f"<span class='dot {st(d)}'></span>" for d in g.get("dots", [])) + "</div></a>" for g in spec["groups"]) + "</div>")
    for s in spec.get("sections", []):
        sid = f" id='{e(s['id'])}'" if s.get("id") else ""
        out.append(f"<section{sid}><h2>{e(s.get('title'))}" + (f"<span class='c'>{e(s['note'])}</span>" if s.get("note") else "")
                   + "</h2>" + "".join(block(b) for b in s.get("blocks", [])) + "</section>")
    out.append("</div></body></html>")
    return "".join(out)


def write(spec: dict, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(spec), encoding="utf-8")
    return path


EXAMPLE = {
    "title": "Weekly data checks", "crumbs": [{"text": "Reports", "href": "#"}, {"text": "week 48"}],
    "meta": ["2026-11-25 09:00", "warehouse: analytics", "12 checks"],
    "verdict": {"status": "warn", "text": "2 need attention"},
    "bar": {"good": 9, "warn": 1, "bad": 1, "note": 1},
    "kpis": [{"label": "checks passed", "value": "9/12", "status": "good"},
             {"label": "stale tables", "value": 1, "status": "bad", "hint": "orders_daily, 9 days"},
             {"label": "rows loaded", "value": "4.2 M", "status": "neutral"},
             {"label": "cost this week", "value": "$1.84", "status": "neutral", "hint": "+12% vs last week"}],
    "sections": [
        {"title": "Tables", "note": "by last change", "blocks": [
            {"type": "table", "columns": ["Table", "Rows", "Last change", "Status"], "num": [2],
             "rows": [["orders", "1,204,331", "today 06:10", {"text": "fresh", "status": "good"}],
                      ["orders_daily", "3,650", "9 days ago", {"text": "stale", "status": "bad"}],
                      ["refunds", "18,092", "2 days ago", {"text": "late", "status": "warn"}],
                      ["legacy_events", "0", "-", {"text": "skipped", "status": "note"}]]}]},
        {"title": "Findings", "blocks": [{"type": "items", "items": [
            {"status": "bad", "title": "orders_daily stopped updating", "sub": "freshness", "right": "9 days", "open": True,
             "checks": [{"ok": False, "text": "updated within 2 days", "detail": "last change 2026-11-16"}],
             "text": "The nightly job has failed since the schema change on 16 Nov."},
            {"status": "good", "title": "Row counts match the source", "sub": "reconciliation", "right": "12 tables"}]}]}],
}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render", help="spec.json -> report.html"); r.add_argument("spec"); r.add_argument("-o", "--out")
    s = sub.add_parser("shot", help="screenshot a report"); s.add_argument("page"); s.add_argument("-o", "--out")
    s.add_argument("--width", type=int, default=1280); s.add_argument("--height", type=int, default=1600)
    s.add_argument("--dark", action="store_true")
    x = sub.add_parser("example", help="write an example spec"); x.add_argument("-o", "--out", default="example-report.json")
    a = p.parse_args()
    if a.cmd == "render":
        spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
        print(write(spec, Path(a.out or Path(a.spec).with_suffix(".html"))).resolve())
    elif a.cmd == "example":
        Path(a.out).write_text(json.dumps(EXAMPLE, indent=2, ensure_ascii=False), encoding="utf-8")
        print(Path(a.out).resolve())
    else:
        sys.path.insert(0, str(HERE))
        import _browser  # noqa: PLC0415
        page = Path(a.page).resolve()
        out = Path(a.out or page.with_suffix(".dark.png" if a.dark else ".png"))
        theme = "theme=dark" if a.dark else "theme=light"
        print(_browser.screenshot(_browser.file_url(page, theme), out, a.width, a.height))
    return 0


if __name__ == "__main__":
    sys.exit(main())
