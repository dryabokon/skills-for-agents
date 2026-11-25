#!/usr/bin/env python3
"""Tutorial: render a Mermaid flowchart with status colours to SVG + PNG.

    python tutorials/diagrams/01_mermaid_flow.py [--open]

Needs Node.js (npx). The first run downloads mermaid-cli once (~30 s); later runs take a few seconds.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _tutorial import ROOT, done, out_dir, run, step  # noqa: E402

CLI = ROOT / "skills" / "diagrams" / "scripts" / "diagram.py"
here = Path(__file__).resolve().parent
out = out_dir("diagrams")

if not shutil.which("npx"):
    sys.exit("This tutorial needs Node.js (npx). Tutorial 02 (hand-made SVG) works without it.")

step("1. The source: a plain .mmd file; ':::proposed' etc. mark status, no colours in the file")
print((here / "order_flow.mmd").read_text(encoding="utf-8"))

step("2. Render it in the theme (status classDefs are added automatically)")
run(CLI, "mermaid", here / "order_flow.mmd", "--out", out / "order_flow")

done(out / "order_flow.svg", out / "order_flow.png")
