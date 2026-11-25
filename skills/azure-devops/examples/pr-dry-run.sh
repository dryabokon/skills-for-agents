#!/usr/bin/env bash
# Look at pull requests, then prepare one WITHOUT creating it (no --apply = nothing is sent).
# Run from the skill folder:   cd skills/azure-devops && bash examples/pr-dry-run.sh
# With your .env, set REPO and SOURCE to a repository and a pushed branch of yours:
#   REPO=MyRepo SOURCE=feature/x bash examples/pr-dry-run.sh
set -e
[ -f .env ] || [ -n "$AZURE_DEVOPS_ORG" ] || export AZURE_DEVOPS_ORG=dnceng-public AZURE_DEVOPS_PROJECT=public

python scripts/ado.py prs --status all --top 3
python scripts/ado.py pr-create --repo "${REPO:-dotnet-public-wiki}" --source "${SOURCE:-main}" --title "Example pull request" --description "Prepared by the azure-devops skill example."
