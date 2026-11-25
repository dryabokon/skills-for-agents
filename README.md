# skills-for-agents

Reusable [Agent Skills](https://agentskills.io) for documentation work: slide decks and diagrams
(reports and git hosting next). Each skill is a folder with a `SKILL.md` for the agent and plain scripts
that do the work. **What the agent runs is exactly what you can run by hand** — every skill has an
`examples/` script made of the same commands.

| Skill | What it does | Needs |
|---|---|---|
| [slides](skills/slides/SKILL.md) | single-file HTML decks (16:9, 8 layouts, themeable), layout check, screenshots, PDF | Python 3.9+, Chrome/Edge/Chromium |
| [diagrams](skills/diagrams/SKILL.md) | Mermaid and hand-made SVG in one theme and status legend, geometry check, PNG preview | + Node.js 18+ for Mermaid |

No pip packages: the scripts use the standard library and drive a locally installed Chromium-based browser
in headless mode (set `CHROME_PATH` if it is not found).

## Try it by hand

```bash
git clone https://github.com/dryabokon/skills-for-agents
cd skills-for-agents/skills/slides
bash examples/build-a-deck.sh          # -> out/streaming.html, out/streaming.pdf, out/streaming-shots/
```

```bash
cd skills-for-agents/skills/diagrams
bash examples/svg-and-check.sh         # -> out/architecture.out.svg/.png, and what the check reports on a broken one
bash examples/mermaid-flow.sh          # -> out/order-flow.svg/.png
```

The example files are short lists of commands — open one, copy any line, change the arguments.
On Windows run them from Git Bash, or paste the lines into PowerShell one by one.

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

Slides and diagrams use the same CSS variables (`assets/theme.css` in each skill). Override any of them with
a small CSS file — `--theme my.css`, the `AGENT_THEME` env var, or `.agent-theme.css` in the working directory:

```css
:root { --accent: #0f766e; --accent-soft: #e6f4f2; }
```

## Layout

```
skills/<name>/
  SKILL.md        instructions for the agent
  scripts/        the tools (one CLI per skill)
  assets/         templates and theme
  references/     detail the agent reads on demand
  examples/       runnable *.sh using the same commands as SKILL.md; output goes to out/ (git-ignored)
.claude-plugin/   plugin + marketplace manifests (Claude Code packaging)
.github/          CI and check.py
```

## Changing a skill

```bash
python .github/check.py      # spec rules, examples present, shared copies identical, secrets, `claude plugin validate`
```
Rules: a skill never reaches outside its own folder; files two skills both carry (`scripts/_browser.py`,
`assets/theme.css`) stay identical; every command in a `SKILL.md` appears in an example; no credentials or
company-specific hosts in code — configuration comes from the environment.

## License

[MIT](LICENSE)
