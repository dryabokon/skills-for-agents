#!/usr/bin/env bash
# Build a 7-slide deck, check its layout, screenshot every slide, export a PDF.
# Run from the skill folder:   cd skills/slides && bash examples/build-a-deck.sh
# Results: out/streaming.html (open in a browser), out/streaming-shots/, out/streaming.pdf
set -e

python scripts/deck.py new   out/streaming.html --title "Moving ingestion to streaming" --kicker "Architecture review" --subtitle "Why batch stopped scaling, what we change, what it costs." --meta "Platform team · 2026" --content examples/demo-slides.html --force
python scripts/deck.py check out/streaming.html
python scripts/deck.py shots out/streaming.html
python scripts/deck.py pdf   out/streaming.html
