#!/usr/bin/env bash
# The example report: a spec with every block, rendered to one HTML file and screenshot in light and dark.
# Run from the skill folder:   cd skills/report && bash examples/weekly-checks.sh
# Results: out/weekly.html (open it), out/weekly.png, out/weekly.dark.png
set -e

python scripts/report.py example -o out/weekly.json
python scripts/report.py render out/weekly.json -o out/weekly.html
python scripts/report.py shot out/weekly.html
python scripts/report.py shot out/weekly.html --dark
