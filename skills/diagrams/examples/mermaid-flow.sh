#!/usr/bin/env bash
# Render a Mermaid flowchart with status colours to SVG + PNG. Needs Node.js (npx);
# the first run downloads mermaid-cli once (~30 s).
# Run from the skill folder:   cd skills/diagrams && bash examples/mermaid-flow.sh
# Results: out/order-flow.svg, out/order-flow.png
set -e

python scripts/diagram.py mermaid examples/order-flow.mmd --out out/order-flow
