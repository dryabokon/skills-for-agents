#!/usr/bin/env bash
# Look at pull requests, then prepare one WITHOUT creating it (no --apply = nothing is sent).
# Run from the skill folder:   cd skills/azure-devops && bash examples/pr-dry-run.sh
# To prepare a PR in your project, name a repository and a pushed branch:
#   REPO=MyRepo SOURCE=feature/x bash examples/pr-dry-run.sh
# Uses your settings (env or the nearest .env); without working ones, the public .NET project.
set -e
python scripts/ado.py whoami > /dev/null 2>&1 || { echo "(no working Azure DevOps settings in env or .env - using the public .NET project)"; export AZURE_DEVOPS_ORG=dnceng-public AZURE_DEVOPS_PROJECT=public AZURE_DEVOPS_PAT=; REPO=${REPO:-dotnet-public-wiki} SOURCE=${SOURCE:-main}; }

python scripts/ado.py prs --status all --top 3

if [ -z "$REPO" ] || [ -z "$SOURCE" ]; then
  echo "To prepare a PR: REPO=<repository> SOURCE=<pushed branch> bash examples/pr-dry-run.sh"
  exit 0
fi
python scripts/ado.py pr-create --repo "$REPO" --source "$SOURCE" --title "Example pull request" --description "Prepared by the azure-devops skill example."
