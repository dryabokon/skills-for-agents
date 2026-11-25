# skills-for-agents

**Skills are ready-made know-how for a coding agent** (Claude Code, Codex, Cursor, ...). With them the agent does
not guess how to deploy, query, report or build: it follows a tested recipe, so the work is faster, cheaper and
safer.

This repository has two kinds:

| Kind | Where | What it is |
|---|---|---|
| **General skills** | [`skills/`](skills) | Know-how for any project: GitHub, Azure DevOps, Google Cloud, BigQuery, reports, diagrams, slides |
| **Project skills** | [`skills-for-dedicated-project/`](skills-for-dedicated-project) | A recipe for a whole kind of app, with a working template |

**How a project gets them:** copy the skill folders it needs into the project's `.claude/skills/`. The agent
finds them there by itself - nothing to install, no flags. All skills sit side by side, one folder each.

## Build a new project from scratch

Example: a web app on Google Cloud Run where you **configure a run, start it and see its results**, with tabs
Settings · Runs · Run · Architecture. The project skill [`gcp-web-ui-app`](skills-for-dedicated-project/gcp-web-ui-app)
knows how such an app is built and deployed; you only say what the app should compute.

**1. Get this repository** (once): `git clone https://github.com/dryabokon/skills-for-agents`

**2. Make an empty folder for your project** (e.g. `my-app`) **and copy these folders into `my-app/.claude/skills/`**
(with the file explorer is fine):

| Take from this repository | Kind | Put into your project | Why |
|---|---|---|---|
| `skills-for-dedicated-project/gcp-web-ui-app/` | project | `.claude/skills/gcp-web-ui-app/` | the app recipe and template: tabs, runs, deploy |
| `skills/gcp/` | general | `.claude/skills/gcp/` | deploy to and check Cloud Run |
| `skills/report/` | general | `.claude/skills/report/` | result pages |
| `skills/diagrams/` | general | `.claude/skills/diagrams/` | the Architecture tab |
| `skills/git-hosting/` | general | `.claude/skills/git-hosting/` | GitHub: push, CI, pull requests |
| `skills/bigquery/` | general | `.claude/skills/bigquery/` | only if the app reads BigQuery |
| `.env.example` | settings | `.env` (fill in) | tokens and GCP project, if needed |

Result:

```text
my-app/
└── .claude/
    └── skills/
        ├── gcp-web-ui-app/
        ├── gcp/
        ├── report/
        ├── diagrams/
        └── git-hosting/
```

Copy only what the project needs; extra skills only distract the agent. Copies do not update themselves: copy
again to take a newer version.

**3. Start the agent in that folder:** `claude`

**4. Say what to build** - what it computes, not how:

```text
Build a web app "Umbrella": the user picks a city and a rain threshold, a run fetches tomorrow's hourly
forecast from Open-Meteo and says whether to take an umbrella, with a chart of rain probability by hour.
Then deploy it to Cloud Run in my project <gcp-project> as service umbrella.
```

**You get:** the app with its tabs and run history, tests, CI, an architecture diagram, a README, and a private
Cloud Run deploy behind Google sign-in. Deploying needs `gcloud` signed in to your project.

## What the general skills do for you

Ask in plain words; naming the skill (`/skills-for-agents:<skill> ...`) makes the agent use it for sure.

| Skill | Ask for example | You get |
|---|---|---|
| **gcp** | Deploy this folder to Cloud Run behind Google sign-in. | the exact plan, run only after your yes |
| **bigquery** | Which tables in analytics stopped updating this week? | the answer from free metadata; no query over your cost cap |
| **git-hosting** | Why did the last CI run fail? Where are my PRs stuck? | the failing step and error; missing approvals, open threads |
| **azure-devops** | Why did the last build of develop fail? | the failing step, the error that matters |
| **report** | Report on runs/007/results.json, failures first. | one HTML page, verdict first, light/dark |
| **diagrams** | Draw how an order flows through our services. | SVG + PNG, layout checked |
| **slides** | Turn design-note.md into 6 slides with a PDF. | one-file deck + PDF, every slide checked |

## Safe by default

Read-only unless you ask. Deploys, uploads and PRs are shown as a plan and run only after you confirm; nothing
merges, approves or deletes. BigQuery prices every query first. Tokens live in `.env` ([template](.env.example))
and are never printed.

## Or install the general skills as a plugin (all projects at once)

```text
/plugin marketplace add dryabokon/skills-for-agents
/plugin install skills-for-agents@dryabokon
```

Other agents: `npx skills add dryabokon/skills-for-agents`. Needs Python 3.9+; slides and screenshots need Chrome or
Edge. Every skill also runs by hand (`skills/<name>/examples/*.sh`); `python tests/run.py` tests them all.
