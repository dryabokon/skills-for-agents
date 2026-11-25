#!/usr/bin/env bash
# Hand-made SVG: start from the template, render it in the theme, then watch the check catch mistakes.
# Run from the skill folder:   cd skills/diagrams && bash examples/svg-and-check.sh
# Results: out/architecture.out.svg + .png (clean), out/broken.svg + .png (with problems)
set -e

python scripts/diagram.py new-svg out/architecture.svg --force
python scripts/diagram.py svg     out/architecture.svg

# This one is broken on purpose: a label too long for its box, a caption on top of the heading.
# The check prints both problems and exits with code 1.
python scripts/diagram.py svg     examples/broken.svg --out out/broken || echo "^ expected: the check found the problems"
