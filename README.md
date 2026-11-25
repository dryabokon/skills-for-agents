# skills-for-agents

Reusable [Agent Skills](https://agentskills.io) for documentation work: slide decks, diagrams, and
(soon) reports and git hosting. Each skill is a folder with a `SKILL.md` for the agent and plain scripts
that do the work, so **what the agent runs is exactly what you can run by hand** — every skill ships a
tutorial that does just that.

| Skill | What it does | Needs |
|---|---|---|
| [slides](skills/slides/SKILL.md) | single-file HTML decks (16:9, 8 layouts, themeable), layout check, screenshots, PDF | Python 3.9+, Chrome/Edge/Chromium |
| [diagrams](skills/diagrams/SKILL.md) | Mermaid and hand-made SVG in one theme and status legend, geometry check, PNG preview | + Node.js 18+ for Mermaid |

No pip packages: the scripts use the standard library and drive a locally installed Chromium-based browser
in headless mode (set `CHROME_PATH` if it is not found).

## Try it (no agent needed)

```bash
git clone https://github.com/dryabokon/skills-for-agents && cd skills-for-agents
python tutorials/slides/01_build_a_deck.py --open        # 7-slide deck -> check -> screenshots -> PDF
python tutorials/diagrams/02_svg_and_check.py --open     # themed SVG + the layout check catching mistakes
python tutorials/diagrams/01_mermaid_flow.py --open      # Mermaid flowchart with status colours
```

Each tutorial prints every command before running it; results go to `tutorials/_out/`. See [tutorials/](tutorials/README.md).

## Install for an agent

**Claude Code** — the whole repo is one plugin; skills appear as `skills-for-agents:slides` etc.

```text
/plugin marketplace add dryabokon/skills-for-agents
/plugin install skills-for-agents@dryabokon
```
(Claude Code 2.1.275+: `/plugin install skills-for-agents --marketplace dryabokon/skills-for-agents` does both.)

**Other agents** (Codex, Cursor, GitHub Copilot, Gemini CLI) read the same `skills/<name>/` folders:

```bash
npx skills add dryabokon/skills-for-agents                       # installs into .agents/skills/
gh skill install dryabokon/skills-for-agents slides             # GitHub Copilot (gh preview)
gemini skills install https://github.com/dryabokon/skills-for-agents --path skills/slides
```
or copy a skill folder into `.agents/skills/` (project) or `~/.agents/skills/` (user). Each skill folder is
self-contained.

## Theme

Slides and diagrams share one set of CSS variables ([shared/theme/tokens.css](shared/theme/tokens.css)).
Override any of them with a small CSS file — `--theme my.css`, the `AGENT_THEME` env var, or
`.agent-theme.css` in the working directory:

```css
:root { --accent: #0f766e; --accent-soft: #e6f4f2; }
```

## Repository layout

```
skills/<name>/          SKILL.md + scripts/ + references/ + assets/   (Agent Skills format)
tutorials/<name>/       runnable walkthroughs using the same commands as SKILL.md
shared/                 source of files copied into several skills (theme, browser helper)
tools/                  sync_shared.py, check_repo.py
.claude-plugin/         plugin.json + marketplace.json (Claude Code packaging only)
```

## Contributing / changing a skill

```bash
python tools/sync_shared.py     # after editing anything under shared/
python tools/check_repo.py      # spec rules, tutorials present, sync, secrets, `claude plugin validate`
```
Rules: a skill never reaches outside its own folder; every command in a `SKILL.md` is covered by a tutorial;
no credentials or company-specific hosts in code — configuration comes from the environment.

## License

[MIT](LICENSE)
