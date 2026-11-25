---
name: azure-devops
description: Work with Azure DevOps from the terminal - pull request status (reviewer votes, policies, open review threads), why a build or pipeline failed (first failing step, errors, log tail), work items and boards, wiki pages, agent pools, and preparing a pull request. Read-only by default; creating a PR needs explicit confirmation. Use when the user mentions Azure DevOps, ADO, dev.azure.com or visualstudio.com links, a PR / build / pipeline / work item / wiki there, or asks why their build failed or what is assigned to them.
license: MIT
compatibility: Requires Python 3.9+ (standard library only) and network access to dev.azure.com. A personal access token in AZURE_DEVOPS_PAT for private projects.
---

# Azure DevOps

One CLI, `scripts/ado.py`, over the Azure DevOps REST API. Commands are relative to this skill's folder
(in Claude Code: `${CLAUDE_SKILL_DIR}`); run them from the user's project so its `.env` is found.

```bash
python scripts/ado.py whoami                       # check connection, user, org, project - run this first
python scripts/ado.py prs [--mine|--reviewing] [--repo R] [--status active|completed|abandoned|all]
python scripts/ado.py pr ID|URL                    # votes, policies (with build ids), open review threads, work items
python scripts/ado.py builds [--failed] [--mine] [--pipeline ID] [--branch B]
python scripts/ado.py build ID|URL|last-failed     # first failing step, its errors, log tail
python scripts/ado.py pipelines [--match WORD ...] # pipelines with their latest result
python scripts/ado.py work-item ID|URL             # fields, description, acceptance criteria, links
python scripts/ado.py work-items [--mine] [--wiql "SELECT ..."]
python scripts/ado.py wiki URL [--tree] | --list
python scripts/ado.py agents [--pool NAME]
python scripts/ado.py pr-create --repo R --source B [--target B] --title T --description-file F [--work-item ID] [--draft] [--apply]
```

Every command accepts `--json` (use it when you will process the output), `--org`, `--project`, `--timeout`.
Links pasted by the user can be passed as they are - a URL carries its own org and project.

## Configuration

Environment variables, or a `.env` in the working directory or a parent (see `.env.example`):
`AZURE_DEVOPS_ORG` (or `AZURE_DEVOPS_ORG_URL`), `AZURE_DEVOPS_PROJECT`, `AZURE_DEVOPS_PAT`.
If `whoami` fails, tell the user which variable is missing and point to `.env.example` - never ask them to paste
a token into the chat, and never print, log or commit it.

## Rules

1. **Read-only unless asked.** Everything except `pr-create --apply` only reads.
2. **Creating a PR:** run `pr-create` without `--apply` first, show the user the title, branches, description and
   linked work items, and add `--apply` only after they confirm. Before writing a description, look at 2-3 recent
   PRs of the repo (`prs --repo R --status completed`) and follow their conventions. If the dry run reports an
   active PR for the same branches, tell the user and link it instead of creating another.
3. **Never** merge, approve, vote, abandon, comment or delete through this skill - there are no commands for it on
   purpose. If the user wants that, give them the link.

## Typical requests

- **"What's the status of my PR?"** → `prs --mine`, then `pr ID`. Report: votes (who still has to review),
  failing policies, open threads grouped by file. For a failing build policy, follow up with `build <id>`.
- **"Why did the build fail?"** → `build URL` or `build last-failed [--pipeline ID|--branch B|--mine]`.
  The steps are ordered by when they failed: the first one is usually the cause, later ones (monitors,
  summaries) are often consequences. When a step's error is generic ("Bash exited with code 1"), the
  *error-looking lines from the whole log* section usually holds the real cause. Quote the decisive line,
  explain it, suggest the fix; if that is still not enough, rerun with `--log-lines 200`.
- **"What's on my plate?"** → `work-items --mine`; for one item `work-item ID`.
- **"Read this wiki page / summarise the spec"** → `wiki URL`; `--tree` lists its sub-pages.
- **"Is the build agent alive?"** → `agents --pool NAME` (status online/offline, busy).

## Examples

Run from this folder (`bash examples/<name>.sh`); with no `.env` they use the public .NET project, no token needed.
- `examples/status-tour.sh` - whoami, repos, PRs, recent and failed builds, pipelines.
- `examples/why-did-build-fail.sh` - `build last-failed` on the latest failed build.
- `examples/pr-dry-run.sh` - list PRs and prepare one without creating it.

## Gotchas

- Public projects allow repos, PRs, builds and wiki anonymously, but not work items, agent pools or PR policies.
- `--mine`, `--reviewing` and `@Me` in WIQL need a token (they resolve "me" from it).
- A sign-in page instead of data means the token is missing, wrong or expired.
- Times are UTC, as the API returns them.
- Old builds disappear under retention; a 404 for a build linked from an old PR usually means exactly that.
