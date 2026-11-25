# skills-for-agents

Skills for coding agents (Claude Code, Codex, Cursor, Copilot): slide decks, diagrams, reports,
Azure DevOps, GitHub/GitLab, BigQuery, Google Cloud.

## Example

```text
/skills-for-agents:slides
Source: design-note.md
Audience: the steering committee, 6 slides, with an architecture diagram of what exists and what is proposed
Save: deck.html and deck.pdf
Check every slide before you hand it over
```

![Slides the agent produced](.github/media/story-deck.png)

<sub>Real output: [input](.github/media/design-note.md) · [PDF](.github/media/story-deck.pdf)</sub>

The same shape works for every skill: **which skill · what data · for whom · what to show · where to save ·
check it**. You can also just ask ("make a 6-slide deck from design-note.md") - the agent picks the skill by
itself; naming it makes that certain.

## Install

```text
/plugin marketplace add dryabokon/skills-for-agents
/plugin install skills-for-agents@dryabokon
```

Other agents: `npx skills add dryabokon/skills-for-agents`, and start the prompt with
"Use the slides skill (skills/slides)" instead of the slash command. Needs Python 3.9+ and Chrome or Edge.
Tokens go into `.env` (template: [.env.example](.env.example)).

## Skills

- **slides** — HTML decks and PDF in one style.
- **diagrams** — Mermaid and SVG diagrams with a status legend.
- **report** — status reports (tests, checks, audits) with a verdict and light/dark theme.
- **azure-devops** — PR status, why a build failed, work items, wiki.
- **git-hosting** — GitHub and GitLab: PRs/MRs, why CI failed, issues, git with a token.
- **bigquery** — explore and query with a dry run and a cost cap.
- **gcp** — Cloud Run, logs, deploy and rollback plans, buckets, secrets.

Anything that changes something (create a PR, deploy, upload) is shown as a plan first and runs only after you
confirm. Each skill has `examples/*.sh` to run the same commands by hand; `python tests/run.py` tests them all
(report in `runs/NNN/index.html`).
