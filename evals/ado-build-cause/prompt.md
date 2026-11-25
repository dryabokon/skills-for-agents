---
description: Find the root cause of a failed Azure DevOps build (private project, needs the PAT)
expected_outcome: Names the missing build input infrastructure/Dockerfile_SITL_PX4_and_ardu in step "Build fly2_base + sim images"
runs: 3
max_turns: 25
timeout_seconds: 600
allowed_tools: [Bash, Read, Glob, Grep, Skill]
append_system_prompt: "Credentials for this task are in environment variables: EVAL_AZURE_DEVOPS_ORG, EVAL_AZURE_DEVOPS_PROJECT, EVAL_ADO_CRED (Azure DevOps personal access token), EVAL_GH_CRED (GitHub token). Never print their values."
---

Why did build 4109 in our Azure DevOps project OsyFly fail? Give the failing step and the root-cause error line.
