#!/usr/bin/env bash
# The most recent failed build: which step failed first, its errors, the end of its log.
# Run from the skill folder:   cd skills/azure-devops && bash examples/why-did-build-fail.sh
# Narrow it down with --pipeline ID, --branch NAME or --mine (needs a token).
# Uses your settings (env or the nearest .env); without working ones, the public .NET project.
set -e
python scripts/ado.py whoami > /dev/null 2>&1 || { echo "(no working Azure DevOps settings in env or .env - using the public .NET project)"; export AZURE_DEVOPS_ORG=dnceng-public AZURE_DEVOPS_PROJECT=public AZURE_DEVOPS_PAT=; }

python scripts/ado.py build last-failed --log-lines 15
