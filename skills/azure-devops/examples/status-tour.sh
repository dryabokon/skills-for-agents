#!/usr/bin/env bash
# A read-only tour: who am I, repositories, open pull requests, recent and failed builds, pipelines.
# Run from the skill folder:   cd skills/azure-devops && bash examples/status-tour.sh
# Uses your settings (env or the nearest .env, e.g. the repo root; template: .env.example).
# If there are none, or they do not work, it reads the public .NET project - no token needed.
set -e
python scripts/ado.py whoami > /dev/null 2>&1 || { echo "(no working Azure DevOps settings in env or .env - using the public .NET project)"; export AZURE_DEVOPS_ORG=dnceng-public AZURE_DEVOPS_PROJECT=public AZURE_DEVOPS_PAT=; }

python scripts/ado.py whoami
python scripts/ado.py repos
python scripts/ado.py prs --top 5
python scripts/ado.py builds --top 5
python scripts/ado.py builds --failed --top 5
python scripts/ado.py pipelines --match ci
