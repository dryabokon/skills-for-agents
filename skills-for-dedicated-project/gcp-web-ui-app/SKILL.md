---
name: gcp-web-ui-app
description: Build or change a web UI app on Google Cloud Run - tabs Settings, Runs, Run result, Architecture - where a user configures a run, starts it, watches it and browses past results, deployed to Cloud Run behind Google sign-in (IAP). Use when the task is an app of the shape "configure -> run -> see results", or when adding a tab, a setting, a result view or a deploy to such an app.
---

# GCP web UI app

The shape we use for small analysis apps (8Allo HDX Signals AI, DTC): one Python server, static pages with tabs,
every run in its own folder `runs/NNN-YYYY-MM-DD/`, deployed to Cloud Run with the runs on a Cloud Storage bucket.
The template in `template/` already works end to end; a new app changes **only the domain** (`app/runner.py`).

## Build a new app

1. **Copy the template** into the project root (do not overwrite files the project already has):
   `cp -rn .claude/skills/gcp-web-ui-app/template/. .`
2. **Write the domain in `app/runner.py`**, nothing else:
   - `TITLE` - app name in the top bar.
   - `SETTINGS` - the form on the Settings tab: `{name, label, type: int|float|text|choice|bool, default, help,
     min/max, options}`. The server validates and coerces a run's settings against this list.
   - `run(settings, out, log) -> results` - does the work. `out` is the run folder (write extra files there),
     `log(msg)` appends to the run's log and shows as progress. Raise on failure; the run is marked failed with the error.
   - `results` (saved as `results.json`, drawn by the Run tab), all keys optional:
     `headline`, `verdict` (`good|warn|bad|info`), `metrics: [{label, value, status?, hint?}]` (up to 5),
     `chart: {title, x: [...], series: [{name, values: [...]}]}`, `table: {columns: [...], rows: [[...]]}`,
     `notes: [str]`.
3. **Tests**: extend `tests/test_app.py` with the domain (a run with small settings finishes and its results
   are right). Run `python -m unittest -v`. Mock the network in tests; do one live run by hand.
4. **Run locally**: `python -m app` -> http://127.0.0.1:8080/ . Start a run, open it, check light and dark theme.
5. **Architecture tab**: edit `docs/architecture.mmd` (Mermaid, rendered by `/architecture`). If the diagrams
   skill is available, use it to check the layout.
6. **README**: what the app answers, the settings, how to run, test and deploy (keep the template's sections).
7. **Deploy**: `SERVICE=<name> ./deploy.sh deploy`, then `./deploy.sh status` (URL; open it signed in).
   `./deploy.sh remove` deletes the service. Read the header of `deploy.sh` for the variables.
8. **CI**: `.github/workflows/ci.yml` runs the tests on push and pull request; keep it green.

## How it works (change with care)

| File | Role |
|---|---|
| `app/server.py` | stdlib HTTP server. Pages `/`, `/architecture`, `/run/<name>`; API below |
| `app/runs.py` | run folders: `config.json`, `status.json`, `log.txt`, `results.json`; numbering; listing |
| `app/runner.py` | the domain (the only file a new app must change) |
| `app/static/index.html` | app shell: tabs Settings · Runs · Run · Architecture (`#settings`, `#runs`, `#run/NNN`, `#architecture`); form built from `SETTINGS` |
| `app/static/architecture.html` | draws `docs/architecture.mmd` with Mermaid |
| `tests/test_app.py` | real server on a free port: pages, run lifecycle, invalid settings, unknown run |
| `app/page.py` | one run's page: `results.json` -> report spec -> HTML via `app/report/` (a copy of the report skill); also saved as `runs/NNN/index.html` |
| `app/report/` | copy of the report skill (stdlib), so the container needs no plugin; update by copying it again |
| `deploy.sh`, `Dockerfile`, `.gcloudignore` | Cloud Run + IAP + bucket mounted at `/app/runs` |

API: `GET /api/app` (title, settings), `POST /api/runs {settings}` -> `{run}`, `GET /api/runs` (list, newest first),
`GET /api/runs/<name>` (config, status, results, log). A run executes in a background thread of the server;
its state is in `status.json` (`queued|running|done|failed`), so any page, restart or instance reads the truth
from the folder, not from memory.

## Rules and pitfalls (learned the hard way)

- **Runtime is stdlib only.** No framework, no build step; the container is `python:3.12-slim` + the code.
  Add a dependency only when the domain truly needs it (then `requirements.txt` + one line in the Dockerfile).
- **Never hand-write result HTML or CSS.** A run's results go into `results.json`; `app/page.py` turns them into a
  report spec. Need a new kind of block? Extend the spec in `page.py` (or the report skill), not the page.
- **Background runs need CPU after the reply**: Cloud Run is deployed with `--no-cpu-throttling` and
  `--max-instances=1` (runs live in the instance that started them). Long runs: `--timeout` up to 3600.
- **Runs persist only on the bucket**: gen2 execution environment + Cloud Storage volume at `/app/runs`.
  Without it every deploy or cold start loses history.
- **Private by default**: `--no-allow-unauthenticated --iap`, viewers granted via `./deploy.sh grant user:a@x.com`.
  A project outside an organization needs an OAuth client for IAP (`IAP_CLIENT_ID/SECRET` in `.env`, see deploy.sh).
  Never deploy with `--allow-unauthenticated`.
- **Own your resources only**: `deploy.sh` labels the service `app=gcp-web-ui-app` and refuses to deploy over a
  service of the same name without that label. Never reuse another app's service, bucket or secret.
- **Secrets** go from `.env` to Secret Manager through a pipe (`SECRETS="NAME ..."`), never printed, never in the image
  (`.gcloudignore` excludes `.env`, `.git`, `runs/`).
- **Git Bash on Windows** rewrites `/app/runs` into a Windows path: `deploy.sh` sets `MSYS_NO_PATHCONV=1` and
  passes `D:/...` paths to gcloud.
- **Run files are written atomically** (`runs.write`: temp file + replace, retried - on Windows a replace fails
  while the page is reading the file). Never write `status.json` or `results.json` directly.
- **External APIs** in `run()`: set a timeout (`urllib.request.urlopen(url, timeout=30)`), log what was fetched,
  keep inputs small; a run should finish in seconds to a few minutes.
- **Cloud costs**: if `run()` queries BigQuery, dry-run first and cap `maximum_bytes_billed` (bigquery skill).

## Done when

- `python -m unittest -v` is green, CI is green.
- Locally: a run started from Settings appears in Runs, finishes, and its Run tab shows the results; a failing
  run shows the error; light and dark theme both readable.
- `./deploy.sh status` shows the URL; opened signed in, a run works there and is still listed after a redeploy.
- Architecture tab matches the code; README says how to run, test, deploy and remove.
