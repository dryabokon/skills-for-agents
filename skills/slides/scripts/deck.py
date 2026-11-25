#!/usr/bin/env python3
"""Single-file HTML slide decks: create, check layout, screenshot, export to PDF.

    python deck.py new    talk.html --title "Quarterly review" [--subtitle ...] [--kicker ...] [--meta ...] [--theme my.css]
    python deck.py theme  talk.html [--theme my.css]        re-inline the theme into an existing deck
    python deck.py check  talk.html                         layout problems per slide (exit 1 if any)
    python deck.py shots  talk.html [--out shots/] [--slides 2,5]   PNG per slide, 1600x900
    python deck.py pdf    talk.html [--out talk.pdf]        one 1600x900 page per slide

Needs Python 3.9+ and Chrome, Edge or Chromium (set CHROME_PATH if it is not found).
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _browser as b  # noqa: E402

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "deck.html"
THEME_BLOCK = re.compile(r'(<style id="theme">\n?)(.*?)(\n?</style>)', re.S)


def cmd_new(a) -> int:
    out = Path(a.deck)
    if out.exists() and not a.force:
        sys.exit(f"{out} exists; pass --force to overwrite")
    page = TEMPLATE.read_text(encoding="utf-8")
    page = page.replace("/*{{THEME}}*/", b.theme_css(a.theme))
    for key, val in {"TITLE": a.title, "SUBTITLE": a.subtitle, "KICKER": a.kicker, "META": a.meta}.items():
        page = page.replace("{{" + key + "}}", html.escape(val or ""))
    page = re.sub(r'\s*<(div|p) class="(kicker|lead|meta)"></\1>', "", page)  # drop empty optional lines
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"created {out.resolve()}")
    print("add slides between the '===== slides' markers; layouts: references/layouts.md")
    return 0


def cmd_theme(a) -> int:
    deck = Path(a.deck)
    page = deck.read_text(encoding="utf-8")
    if not THEME_BLOCK.search(page):
        sys.exit('no <style id="theme"> block in the deck')
    page = THEME_BLOCK.sub(lambda m: m.group(1) + b.theme_css(a.theme) + m.group(3), page, count=1)
    deck.write_text(page, encoding="utf-8")
    print(f"theme {b.resolve_theme(a.theme)} -> {deck}")
    return 0


def run_check(deck: Path) -> dict:
    dom = b.dump_dom(b.file_url(deck, "check"))
    raw = b.extract_block(dom, "deck-check")
    if not raw or not raw.strip():
        sys.exit("the deck did not report a check result - is it built from assets/deck.html?")
    return json.loads(raw)


def cmd_check(a) -> int:
    result = run_check(Path(a.deck))
    if a.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    bad = 0
    for s in result["report"]:
        head = f"slide {s['slide']:>2}  {s['layout'] or '(no layout)':<16} {s['words']:>3} words  {(s['title'] or '').strip()[:50]}"
        if not a.json:
            print(("!! " if s["issues"] else "ok ") + head)
        for i in s["issues"]:
            bad += 1
            if not a.json:
                detail = ", ".join(f"{k}={v}" for k, v in i.items() if k not in ("kind",))
                print(f"     - {i['kind']}: {detail}")
    print(f"\n{result['slides']} slides, {bad} issue(s)" + ("" if bad else " - layout is clean"))
    return 1 if bad else 0


def slide_count(deck: Path) -> int:
    page = re.sub(r"<!--.*?-->", "", deck.read_text(encoding="utf-8"), flags=re.S)
    return len(re.findall(r'<section\s+class="slide\b', page))


def cmd_shots(a) -> int:
    deck = Path(a.deck)
    out = Path(a.out or deck.with_suffix("").name + "-shots")
    n = slide_count(deck)
    wanted = [int(x) for x in a.slides.split(",")] if a.slides else range(1, n + 1)
    for i in wanted:
        if not 1 <= i <= n:
            sys.exit(f"slide {i} does not exist (deck has {n})")
        path = b.screenshot(b.file_url(deck, f"static={i}"), out / f"slide-{i:02d}.png", 1600, 900)
        print(path)
    return 0


def cmd_pdf(a) -> int:
    deck = Path(a.deck)
    out = Path(a.out or deck.with_suffix(".pdf"))
    print(b.print_pdf(b.file_url(deck), out))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    n = sub.add_parser("new", help="create a deck from the template")
    n.add_argument("deck"); n.add_argument("--title", required=True)
    n.add_argument("--subtitle"); n.add_argument("--kicker"); n.add_argument("--meta")
    n.add_argument("--theme"); n.add_argument("--force", action="store_true")
    n.set_defaults(fn=cmd_new)

    t = sub.add_parser("theme", help="re-inline the theme into a deck")
    t.add_argument("deck"); t.add_argument("--theme"); t.set_defaults(fn=cmd_theme)

    c = sub.add_parser("check", help="report layout problems")
    c.add_argument("deck"); c.add_argument("--json", action="store_true"); c.set_defaults(fn=cmd_check)

    s = sub.add_parser("shots", help="PNG screenshot per slide")
    s.add_argument("deck"); s.add_argument("--out"); s.add_argument("--slides", help="e.g. 1,3,4")
    s.set_defaults(fn=cmd_shots)

    d = sub.add_parser("pdf", help="export to PDF")
    d.add_argument("deck"); d.add_argument("--out"); d.set_defaults(fn=cmd_pdf)

    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
