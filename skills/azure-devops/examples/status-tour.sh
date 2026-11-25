#!/usr/bin/env bash
# A read-only tour: who am I, repositories, open pull requests, recent and failed builds, pipelines.
# Run from the skill folder:   cd skills/azure-devops && bash examples/status-tour.sh
# Uses your .env (copy .env.example). Without one it reads the public .NET project - no token needed.
set -e
[ -f .env ] || [ -n "$AZURE_DEVOPS_ORG" ] || export AZURE_DEVOPS_ORG=dnceng-public AZURE_DEVOPS_PROJECT=public

python scripts/ado.py whoami
python scripts/ado.py repos
python scripts/ado.py prs --top 5
python scripts/ado.py builds --top 5
python scripts/ado.py builds --failed --top 5
python scripts/ado.py pipelines --match ci
