#!/usr/bin/env python3
"""Tutorial: build a 7-slide deck, check its layout, screenshot it and export a PDF.

    python tutorials/slides/01_build_a_deck.py [--open]

These are the same commands the agent runs (skills/slides/SKILL.md). The one step an agent does
by hand - writing the slides - is done here by pasting tutorials/slides/demo_slides.html.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _tutorial import ROOT, done, out_dir, run, step  # noqa: E402

DECK_CLI = ROOT / "skills" / "slides" / "scripts" / "deck.py"
out = out_dir("slides")
deck = out / "streaming.html"

step("1. Create the deck from the template (title slide + theme)")
run(DECK_CLI, "new", deck, "--title", "Moving ingestion to streaming", "--kicker", "Architecture review",
    "--subtitle", "Why batch stopped scaling, what we change, what it costs.", "--meta", "Platform team · 2026", "--force")

step("2. Write the slides (the agent edits the file; here we paste a prepared fragment)")
marker = "<!-- ===== end of slides ===== -->"
fragment = (Path(__file__).parent / "demo_slides.html").read_text(encoding="utf-8")
deck.write_text(deck.read_text(encoding="utf-8").replace(marker, fragment + "\n" + marker), encoding="utf-8")
print(f"inserted {fragment.count('<section')} slides into {deck.name}")

step("3. Check the layout: overflow, clipped or tiny text, too many words, broken images")
run(DECK_CLI, "check", deck)

step("4. Screenshot every slide (what the agent looks at to judge the result)")
run(DECK_CLI, "shots", deck, "--out", out / "shots")

step("5. Export to PDF, one 16:9 page per slide")
run(DECK_CLI, "pdf", deck, "--out", out / "streaming.pdf")

done(deck, out / "streaming.pdf", out / "shots")
print("\nIn the browser: arrows / space / click to move, F for full screen, #3 in the URL opens slide 3.")
