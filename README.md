# skills-for-agents

Skills for coding agents (Claude Code, Codex, Cursor, Copilot): slide decks, diagrams, Azure DevOps.

## Example

> **"Make a 6-slide deck for the steering committee from design-note.md, with an architecture diagram.
> I also need a PDF."**

![Slides the agent produced](.github/media/story-deck.png)

One HTML deck + PDF. The agent checks the layout and looks at every slide before handing it over.
<sub>Real output: [input](.github/media/design-note.md) · [PDF](.github/media/story-deck.pdf)</sub>

## Install

```text
/plugin marketplace add dryabokon/skills-for-agents
/plugin install skills-for-agents@dryabokon
```

Other agents: `npx skills add dryabokon/skills-for-agents`. Needs Python 3.9+ and Chrome or Edge.
Tokens go into `.env` (template: [.env.example](.env.example)).

## Skills

- **slides** — HTML decks and PDF in one style.
- **diagrams** — Mermaid and SVG diagrams with a status legend.
- **azure-devops** — PR status, why a build failed, work items, wiki. Read-only unless you confirm.

Each skill has `examples/*.sh` to run the same commands by hand.
