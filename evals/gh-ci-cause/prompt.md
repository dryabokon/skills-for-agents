---
description: Find why a public GitHub Actions run failed (job logs need a token)
expected_outcome: govulncheck found 1 vulnerability, GO-2026-6278 in github.com/gorilla/websocket@v1.5.3
runs: 3
max_turns: 25
timeout_seconds: 600
allowed_tools: [Bash, Read, Glob, Grep, Skill]
append_system_prompt: "Credentials for this task are in environment variables: EVAL_AZURE_DEVOPS_ORG, EVAL_AZURE_DEVOPS_PROJECT, EVAL_ADO_CRED (Azure DevOps personal access token), EVAL_GH_CRED (GitHub token). Never print their values."
---

Why did GitHub Actions run 45503045682 in cli/cli fail? Name the failing job and the actual finding behind it.
