# skills-for-agents

**Skills are ready-made know-how for a coding agent** (Claude Code, Codex, Cursor, ...). With them the agent does
not guess how to deploy, query, report or build: it follows a tested recipe, so the work is faster, cheaper and
safer.

**How to use:** copy the skill folders you need from [`skills/`](skills) into your project's `.claude/skills/`.
The agent finds them there by itself. That's all.

## Build a new project from scratch

Example: a web app on Google Cloud Run where you **configure a run, start it and see its results**, with tabs
Settings · Runs · Run · Architecture.

**1.** Make an empty folder for your project, e.g. `my-app`.

**2.** Copy these folders from [`skills/`](skills) into `my-app/.claude/skills/` (the file explorer is fine):

| Folder | Kind | Why |
|---|---|---|
| `gcp-web-ui-app` | project | the app recipe and template: tabs, runs, deploy |
| `gcp` | general | deploy to and check Cloud Run |
| `report` | general | result pages |
| `diagrams` | general | the Architecture tab |
| `git-hosting` | general | GitHub: push, CI, pull requests |
| `bigquery` | general | only if the app reads BigQuery |

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

**3.** In `my-app`, start the agent: `claude`

**4.** Say what to build - what it computes, not how:

```text
Build a web app "Umbrella": the user picks a city and a rain threshold, a run fetches tomorrow's hourly
forecast from Open-Meteo and says whether to take an umbrella, with a chart of rain probability by hour.
Then deploy it to Cloud Run in my project <gcp-project> as service umbrella.
```

**You get:** the app with its tabs and run history, tests, CI, an architecture diagram, a README, and a private
Cloud Run deploy behind Google sign-in. Deploying needs `gcloud` signed in to your project.

## All skills

**Project** skills are a recipe for a whole kind of app: copy one into one project. **General** skills help in
any project.

| Skill | Kind | Ask for example | You get |
|---|---|---|---|
| **gcp-web-ui-app** | project | Build a web app that ... and deploy it to Cloud Run. | the app, tests, CI, diagram, private deploy |
| **gcp** | general | Deploy this folder to Cloud Run behind Google sign-in. | the exact plan, run only after your yes |
| **bigquery** | general | Which tables in analytics stopped updating this week? | the answer from free metadata; no query over your cost cap |
| **git-hosting** | general | Why did the last CI run fail? Where are my PRs stuck? | the failing step and error; missing approvals, open threads |
| **azure-devops** | general | Why did the last build of develop fail? | the failing step, the error that matters |
| **report** | general | Report on runs/007/results.json, failures first. | one HTML page, verdict first, light/dark |
| **diagrams** | general | Draw how an order flows through our services. | SVG + PNG, layout checked |
| **slides** | general | Turn design-note.md into 6 slides with a PDF. | one-file deck + PDF, every slide checked |

Copy only what a project needs; extra skills only distract the agent. Copies do not update themselves: copy again
to take a newer version.

## Safe by default

Read-only unless you ask. Deploys, uploads and PRs are shown as a plan and run only after you confirm; nothing
merges, approves or deletes. BigQuery prices every query first. Tokens live in the project's `.env`
([template](.env.example)) and are never printed. Needs Python 3.9+; slides and screenshots need Chrome or Edge.
