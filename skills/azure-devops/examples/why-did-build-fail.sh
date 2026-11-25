#!/usr/bin/env bash
# The most recent failed build: which step failed first, its errors, the end of its log.
# Run from the skill folder:   cd skills/azure-devops && bash examples/why-did-build-fail.sh
# Narrow it down with --pipeline ID, --branch NAME or --mine (needs a token).
set -e
[ -f .env ] || [ -n "$AZURE_DEVOPS_ORG" ] || export AZURE_DEVOPS_ORG=dnceng-public AZURE_DEVOPS_PROJECT=public

python scripts/ado.py build last-failed --log-lines 15
