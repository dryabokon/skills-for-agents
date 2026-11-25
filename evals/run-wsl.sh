#!/usr/bin/env bash
# Run the eval suite under WSL2 (native Windows has no sandbox for Bash-granting cases).
# Usage (from Windows):  wsl -e bash evals/run-wsl.sh [extra claude plugin eval args...]
# Tokens: repo-root .env is mapped to EVAL_* variables - eval runs only see EVAL_* from the parent shell, and
# drop any whose name contains TOKEN or PAT, hence EVAL_ADO_CRED / EVAL_GH_CRED.
set -euo pipefail
cd "$(dirname "$0")/.."
while IFS='=' read -r k v; do
  v="$(printf %s "$v" | tr -d '\r')"
  case "$k" in
    AZURE_DEVOPS_ORG|AZURE_DEVOPS_PROJECT) export "EVAL_$k=$v";;
    AZURE_DEVOPS_PAT) export EVAL_ADO_CRED="$v";;
    GH_TOKEN) export EVAL_GH_CRED="$v";;
  esac
done < <(grep -E '^[A-Z_]+=' .env)
# Docker Desktop puts symlinks into ~/.docker, which the eval sandbox refuses (it checks $HOME/.docker).
# The cases need no Docker, so run under a separate HOME that carries only the Claude login.
EVAL_HOME="${TMPDIR:-/tmp}/claude-eval-home"; mkdir -p "$EVAL_HOME"
rm -rf "$EVAL_HOME/.claude"; mkdir -p "$EVAL_HOME/.claude"; chmod 700 "$EVAL_HOME" "$EVAL_HOME/.claude"
install -m 600 "$HOME/.claude/.credentials.json" "$EVAL_HOME/.claude/.credentials.json"
install -m 600 "$HOME/.claude.json" "$EVAL_HOME/.claude.json"
export DOCKER_CONFIG="$EVAL_HOME/.docker"; mkdir -p "$DOCKER_CONFIG"
CLAUDE_BIN="$HOME/.local/bin/claude"; export HOME="$EVAL_HOME"
exec "$CLAUDE_BIN" plugin eval . --trust-plugin --no-publish \
  --allow-tools Bash "WebFetch(domain:dev.azure.com)" "WebFetch(domain:*.visualstudio.com)" \
                "WebFetch(domain:api.github.com)" "WebFetch(domain:github.com)" \
                "WebFetch(domain:*.blob.core.windows.net)" "WebFetch(domain:*.actions.githubusercontent.com)" \
                "WebFetch(domain:pkg.go.dev)" \
  "$@"
