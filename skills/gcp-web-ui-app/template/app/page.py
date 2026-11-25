"""The Run tab: one run's folder -> a report spec -> HTML through the report skill (app/report/, a copy of it).

Never hand-write result HTML: extend the spec here. The chart is the one inline SVG (the report skill has no chart
block yet); it uses the report's CSS variables, so it follows the light/dark theme.
"""
from __future__ import annotations

import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).with_name("report") / "scripts"))
import report  # noqa: E402

from . import runs  # noqa: E402

STATE = {"queued": ("neutral", "queued"), "running": ("note", "running…"), "done": ("good", "done"),
         "failed": ("bad", "failed"), "unknown": ("neutral", "unknown")}
COLORS = ["var(--good)", "var(--warn)", "var(--bad)", "var(--muted)"]


def chart(c: dict) -> str:
    xs, series = c.get("x") or [], [s for s in c.get("series", []) if s.get("values")]
    vals = [v for s in series for v in s["values"] if isinstance(v, (int, float))]
    if not vals:
        return ""
    w, h, pad = 720, 220, 32
    lo, hi = min(vals), max(vals)
    hi = hi if hi > lo else lo + 1
    n = max(len(s["values"]) for s in series)

    def pt(i, v):
        return f"{pad + i * (w - 2 * pad) / max(n - 1, 1):.1f},{h - pad - (v - lo) * (h - 2 * pad) / (hi - lo):.1f}"

    lines = "".join(f"<polyline fill='none' stroke='{COLORS[k % len(COLORS)]}' stroke-width='2' points='"
                    + " ".join(pt(i, v) for i, v in enumerate(s["values"]) if isinstance(v, (int, float))) + "'/>"
                    for k, s in enumerate(series))
    axis = (f"<text x='4' y='{pad}' font-size='11' fill='var(--muted)'>{hi:g}</text>"
            f"<text x='4' y='{h - pad}' font-size='11' fill='var(--muted)'>{lo:g}</text>"
            + (f"<text x='{pad}' y='{h - 8}' font-size='11' fill='var(--muted)'>{html.escape(str(xs[0]))}</text>"
               f"<text x='{w - pad}' y='{h - 8}' font-size='11' fill='var(--muted)' text-anchor='end'>{html.escape(str(xs[-1]))}</text>" if xs else ""))
    legend = " · ".join(f"<span style='color:{COLORS[k % len(COLORS)]}'>■</span> {html.escape(str(s.get('name', '')))}"
                        for k, s in enumerate(series))
    return (f"<figure style='margin:0'><svg viewBox='0 0 {w} {h}' style='width:100%;max-width:{w}px;height:auto' role='img' "
            f"aria-label='{html.escape(c.get('title', 'chart'))}'><line x1='{pad}' y1='{h - pad}' x2='{w - pad}' y2='{h - pad}' "
            f"stroke='var(--line)'/>{axis}{lines}</svg><figcaption class='muted'>{legend}</figcaption></figure>")


def spec(d: Path) -> dict:
    i = runs.info(d, full=True)
    res = i["results"] or {}
    status, word = STATE.get(i["state"] or "unknown", STATE["unknown"])
    verdict = {"status": res.get("verdict", "neutral").replace("info", "neutral"), "text": res["headline"]} \
        if i["state"] == "done" and res.get("headline") else {"status": status, "text": i["error"] or word}
    meta = [x for x in ((i["started"] or "").replace("T", " "), f"{i['seconds']} s" if i["seconds"] is not None else None, word) if x]
    sections = []
    if res.get("chart"):
        sections.append({"title": res["chart"].get("title", "Chart"), "blocks": [{"type": "html", "html": chart(res["chart"])}]})
    if res.get("table"):
        t = res["table"]
        sections.append({"title": t.get("title", "Results"), "blocks": [{"type": "table", "columns": t.get("columns", []), "rows": t.get("rows", [])}]})
    if res.get("notes"):
        sections.append({"title": "Notes", "blocks": [{"type": "text", "text": "\n\n".join(map(str, res["notes"]))}]})
    sections.append({"title": "Settings", "blocks": [{"type": "table", "columns": ["setting", "value"],
                                                      "rows": [[k, str(v)] for k, v in i["settings"].items()]}]})
    if i["log"]:
        sections.append({"title": "Log", "blocks": [{"type": "code", "text": i["log"]}]})
    return {"title": f"Run {d.name}", "crumbs": [{"text": "Runs", "href": "/#runs"}, {"text": d.name}], "meta": meta,
            "verdict": verdict, "kpis": [{"label": m.get("label"), "value": m.get("value"), "status": m.get("status", "neutral"),
                                          **({"hint": m["hint"]} if m.get("hint") else {})} for m in res.get("metrics", [])][:5],
            "sections": sections}


def render(d: Path, embed: bool = False) -> str:
    s = spec(d)
    if embed:  # inside the app's Run tab: the tabs are the way back
        s["crumbs"] = [{"text": d.name}]
    page = report.render(s)
    if (runs.info(d)["state"] or "") in ("queued", "running"):  # refresh until finished
        page = page.replace("</head>", "<meta http-equiv='refresh' content='2'></head>", 1)
    return page


def write(d: Path) -> None:
    """A finished run also keeps its page as runs/NNN/index.html, so the bucket alone is a browsable archive."""
    report.write(spec(d), d / "index.html")
