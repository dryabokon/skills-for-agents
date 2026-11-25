# Agent instructions

This repository builds skills for coding agents. **Use them here for everything they cover** - every task done
here is also a test of a skill. Never fall back to plain tools for a job a skill does; if a skill cannot do it,
fix the skill.

| Task | Use |
|---|---|
| push, fetch, any git over HTTPS | `python skills/git-hosting/scripts/githost.py git push ...` |
| PRs, CI runs, why CI failed, issues | `python skills/git-hosting/scripts/githost.py ...` |
| any HTML report or results page | `skills/report/scripts/report.py` (render a spec; never hand-write HTML/CSS) |
| slides, diagrams | `skills/slides/scripts/deck.py`, `skills/diagrams/scripts/diagram.py` |
| Azure DevOps, BigQuery, Google Cloud | `skills/azure-devops/scripts/ado.py`, `skills/bigquery/scripts/bq.py`, `skills/gcp/scripts/gcp.py` |

Before a commit: `python .github/check.py` and `python tests/run.py` (or `--skill <name>`) are green.
Settings and tokens come from `.env` (template `.env.example`); never print or commit them.
To have the skills loaded as skills in a Claude Code session here: `claude --plugin-dir .`
