# Web UI app

<!-- What question this app answers, in one or two sentences. -->

Tabs: **Settings** (configure a run) · **Runs** (past runs, newest first) · **Run** (one run's results) ·
**Architecture** (`docs/architecture.mmd`). Every run lives in `runs/NNN-YYYY-MM-DD/`
(`config.json`, `status.json`, `log.txt`, `results.json`, `index.html`).

## Settings

<!-- One line per setting: what it changes. -->

## Run locally

```bash
python -m app            # http://127.0.0.1:8080/
python -m unittest -v    # tests (no network)
```

## Deploy (Cloud Run, private behind Google sign-in)

```bash
cp .env.example .env     # fill in SERVICE, PROJECT, ...
./deploy.sh deploy       # build, deploy, grant VIEWERS
./deploy.sh status       # URL
./deploy.sh remove --all # delete the service, bucket, image
```
