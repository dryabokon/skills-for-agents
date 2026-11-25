# Tutorials

Runnable walkthroughs, one folder per skill. Each script:

- runs from anywhere (`python tutorials/<skill>/<nn>_<name>.py`), always against the repository root;
- **prints every command before running it** — the same commands the agent runs from the skill's `SKILL.md`;
- writes results to `tutorials/_out/<skill>/` (git-ignored) and lists them at the end;
- opens the results with `--open`.

If a tutorial works and the agent's result does not, the difference is in what the agent wrote,
not in the tools — that is the point of keeping them identical.

| Tutorial | Shows | Needs |
|---|---|---|
| [slides/01_build_a_deck.py](slides/01_build_a_deck.py) | new deck → add slides → `check` → `shots` → `pdf` | browser |
| [diagrams/01_mermaid_flow.py](diagrams/01_mermaid_flow.py) | `.mmd` with status classes → themed SVG + PNG | browser, Node.js |
| [diagrams/02_svg_and_check.py](diagrams/02_svg_and_check.py) | starter SVG → themed SVG + PNG; a broken SVG and what the check reports | browser |

Adding a skill? Add `tutorials/<skill>/01_….py` — `tools/check_repo.py` fails without one.
