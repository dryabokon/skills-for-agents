#!/usr/bin/env python3
"""Tutorial: hand-made SVG - start from the template, render it in the theme, and see the layout check catch mistakes.

    python tutorials/diagrams/02_svg_and_check.py [--open]

No Node.js needed, only Chrome / Edge / Chromium.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _tutorial import ROOT, done, out_dir, run, step  # noqa: E402

CLI = ROOT / "skills" / "diagrams" / "scripts" / "diagram.py"
here = Path(__file__).resolve().parent
out = out_dir("diagrams")

step("1. Create a starter SVG: nodes, a group, edges with labels, a status legend")
run(CLI, "new-svg", out / "architecture.svg", "--force")

step("2. Inline the theme, check the layout, render a PNG (this is what you edit and re-run)")
run(CLI, "svg", out / "architecture.svg", "--out", out / "architecture.final")

step("3. A broken copy: a label too long for its box and a caption on top of the heading")
print("   expected: exit code 1 with 'text-overflows-node' (and the width it needs) and 'texts-overlap'")
run(CLI, "svg", here / "broken.svg", "--out", out / "broken.final", ok_codes=(1,))

done(out / "architecture.final.svg", out / "architecture.final.png", out / "broken.final.png")
