#!/usr/bin/env python3
"""Azure DevOps from the command line: pull requests, builds, work items, wiki, agent pools.

Read-only by default. The one write, `pr-create`, only prints what it would send unless --apply is given,
and nothing here ever merges, approves, votes, comments or deletes.

    python ado.py whoami                              who am I, which org / project
    python ado.py repos
    python ado.py prs        [--repo R] [--mine | --reviewing] [--status active|completed|abandoned|all] [--top N]
    python ado.py pr         ID|URL                   status, reviewers, policies (builds), open review threads
    python ado.py pr-create  --repo R --source B [--target B] --title T (--description-file F | --description D)
                             [--work-item ID ...] [--draft] [--apply]
    python ado.py builds     [--pipeline ID] [--branch B] [--failed] [--mine] [--top N]
    python ado.py build      ID|URL|last-failed [--pipeline ID] [--branch B] [--mine] [--log-lines N]
                             result, failed steps (first to fail first), their errors and log tail
    python ado.py pipelines  [--match WORD ...]       pipelines with their latest build
    python ado.py work-item  ID|URL
    python ado.py work-items [--mine] [--wiql QUERY] [--top N]
    python ado.py wiki       URL [--tree] | --list
    python ado.py agents     [--pool NAME]

Every command takes --json (machine-readable output), --org / --project (override), --timeout.
A URL argument (PR, build, work item, wiki page) carries its own org and project.

Configuration - environment variables, or a .env file in the current directory or any parent:
    AZURE_DEVOPS_ORG       organization name (https://dev.azure.com/<org>), or
    AZURE_DEVOPS_ORG_URL   full organization URL (e.g. https://<org>.visualstudio.com)
    AZURE_DEVOPS_PROJECT   project name
    AZURE_DEVOPS_PAT       personal access token; optional for public projects
Standard library only; Python 3.9+.
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "7.1"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
ERROR_LINE = re.compile(r"(?i)\b(error|errors|failed|failure|fatal|exception|traceback|assert(ion)?error|panic|denied|"
                        r"not found|no such file|timed? ?out|exit(ed)? (with )?code [1-9])\b")
NOISE_LINE = re.compile(r"(?i)^##\[(section|command|group|endgroup)\]|\b0 errors?\b|\berrors?: 0\b|\"errors?\":\s*(\[\]|0|null)|"
                        r"--fail|-e\b.*set|ignore.?errors|continueOnError")
VOTES = {10: "approved", 5: "approved with suggestions", 0: "no vote", -5: "waiting for author", -10: "rejected"}


class Fail(SystemExit):
    def __init__(self, msg: str):
        super().__init__(f"error: {msg}")


# ------------------------------------------------------------------ configuration

def load_dotenv() -> Path | None:
    """First .env from the current directory upwards; never overrides variables already set."""
    for folder in [Path.cwd(), *Path.cwd().parents]:
        env = folder / ".env"
        if env.is_file():
            for line in env.read_text(encoding="utf-8").splitlines():
                m = re.match(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$", line)
                if m and not line.lstrip().startswith("#"):
                    val = m.group(2)
                    if len(val) >= 2 and val[0] == val[-1] and val[0] in "'\"":
                        val = val[1:-1]
                    else:
                        val = re.sub(r"\s+#.*$", "", val)
                    os.environ.setdefault(m.group(1), val)
            return env
    return None


URL_RE = re.compile(r"https://(?:dev\.azure\.com/(?P<org>[^/]+)|(?P<vsorg>[^./]+)\.visualstudio\.com)/(?P<project>[^/?#]+)(?P<rest>.*)")


def parse_url(url: str) -> dict:
    m = URL_RE.match(url.strip())
    if not m:
        raise Fail(f"not an Azure DevOps URL: {url}")
    org = m.group("org") or m.group("vsorg")
    out = {"org_url": f"https://dev.azure.com/{org}" if m.group("org") else f"https://{org}.visualstudio.com",
           "project": urllib.parse.unquote(m.group("project"))}
    rest, query = m.group("rest"), urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    if mm := re.search(r"/_git/([^/]+)/pullrequest/(\d+)", rest):
        out.update(kind="pr", repo=urllib.parse.unquote(mm.group(1)), id=int(mm.group(2)))
    elif "buildId" in query:
        out.update(kind="build", id=int(query["buildId"][0]))
    elif mm := re.search(r"/_workitems/edit/(\d+)", rest):
        out.update(kind="work-item", id=int(mm.group(1)))
    elif "workitem" in query:
        out.update(kind="work-item", id=int(query["workitem"][0]))
    elif mm := re.search(r"/_wiki/wikis/([^/]+)/(\d+)", rest):
        out.update(kind="wiki", wiki=urllib.parse.unquote(mm.group(1)), id=int(mm.group(2)))
    return out


class Client:
    def __init__(self, a, url_info: dict | None = None):
        url_info = url_info or {}
        org = a.org or os.environ.get("AZURE_DEVOPS_ORG")
        self.org_url = (url_info.get("org_url") or (f"https://dev.azure.com/{a.org}" if a.org else None)
                        or os.environ.get("AZURE_DEVOPS_ORG_URL") or (f"https://dev.azure.com/{org}" if org else None))
        self.project = url_info.get("project") or a.project or os.environ.get("AZURE_DEVOPS_PROJECT")
        if not self.org_url:
            raise Fail("no organization: set AZURE_DEVOPS_ORG (or AZURE_DEVOPS_ORG_URL) in the environment or .env, "
                       "pass --org, or give a URL")
        self.org_url = self.org_url.rstrip("/")
        self.timeout = a.timeout
        pat = os.environ.get("AZURE_DEVOPS_PAT", "").strip()
        self.auth = {"Authorization": "Basic " + base64.b64encode(f":{pat}".encode()).decode()} if pat else {}

    def need_project(self) -> str:
        if not self.project:
            raise Fail("no project: set AZURE_DEVOPS_PROJECT, pass --project, or give a URL")
        return self.project

    def url(self, path: str, scope: str = "project") -> str:
        if path.startswith("https://"):
            return path
        base = self.org_url if scope == "org" else f"{self.org_url}/{urllib.parse.quote(self.need_project())}"
        return f"{base}/_apis/{path}"

    def call(self, path: str, params: dict | None = None, body=None, method: str | None = None,
             scope: str = "project", version: str = API, text: bool = False):
        params = {k: v for k, v in (params or {}).items() if v is not None}
        params.setdefault("api-version", version)
        url = self.url(path, scope)
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method or ("POST" if data else "GET"),
                                     headers={**self.auth, "Accept": "text/plain" if text else "application/json",
                                              "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                ctype = resp.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(detail).get("message", detail)
            except (ValueError, AttributeError):
                pass
            hint = {401: " - set AZURE_DEVOPS_PAT (or check it has not expired)",
                    403: " - the token lacks a scope for this (see .env.example)",
                    404: " - check org / project / id"}.get(e.code, "")
            raise Fail(f"HTTP {e.code} for {url.split('?')[0]}{hint}\n  {str(detail)[:300]}")
        except (urllib.error.URLError, TimeoutError) as e:
            raise Fail(f"cannot reach {self.org_url}: {getattr(e, 'reason', e)}")
        if text:
            return raw
        if "json" not in ctype:
            raise Fail("got a sign-in page instead of data: this needs AZURE_DEVOPS_PAT (missing, wrong or expired). "
                       "Public projects allow repos, pull requests, builds and wiki without a token, "
                       "but not work items or agent pools.")
        return json.loads(raw)

    def web(self, path: str) -> str:
        return f"{self.org_url}/{urllib.parse.quote(self.need_project())}/{path}"

    def me(self) -> dict:
        data = self.call("connectionData", scope="org", version="7.1-preview")
        user = data.get("authenticatedUser", {})
        return {"id": user.get("id"), "name": user.get("providerDisplayName") or user.get("customDisplayName"),
                "anonymous": not self.auth}


# ------------------------------------------------------------------ helpers

def when(ts: str | None) -> str:
    """'2026-11-25T10:31:07.123Z' -> '2026-11-25 10:31' (UTC, as Azure DevOps returns it)."""
    m = re.match(r"(\d{4}-\d\d-\d\d)T(\d\d:\d\d)", ts or "")
    return f"{m.group(1)} {m.group(2)}" if m else "-"


def branch(ref: str | None) -> str:
    return re.sub(r"^refs/(heads/)?", "", ref or "")


def strip_html(s: str | None, limit: int = 1500) -> str:
    s = re.sub(r"<br\s*/?>|</p>|</div>|</li>", "\n", s or "", flags=re.I)
    s = html.unescape(re.sub(r"<[^>]+>", "", s))
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    return s[:limit] + (" …" if len(s) > limit else "")


def table(rows: list[dict], cols: list[str]) -> str:
    if not rows:
        return "(none)"
    widths = {c: min(max(len(c), *(len(str(r.get(c, ""))) for r in rows)), 60) for c in cols}
    line = lambda r: "  ".join(str(r.get(c, ""))[:widths[c]].ljust(widths[c]) for c in cols).rstrip()
    return "\n".join([line({c: c for c in cols}), line({c: "-" * widths[c] for c in cols})] + [line(r) for r in rows])


def target(a, kind: str) -> tuple[dict | None, int]:
    """ID or URL argument -> (url info or None, numeric id)."""
    ref = str(a.ref)
    if ref.isdigit():
        return None, int(ref)
    info = parse_url(ref)
    if info.get("kind") != kind:
        raise Fail(f"that URL is not a {kind} link")
    return info, info["id"]


# ------------------------------------------------------------------ commands

def cmd_whoami(a):
    c = Client(a)
    me = c.me()
    out = {"org_url": c.org_url, "project": c.project, "user": None if me["anonymous"] else me["name"],
           "auth": "anonymous" if me["anonymous"] else "personal access token"}
    if c.project:
        p = c.call(f"projects/{urllib.parse.quote(c.project)}", scope="org")
        out.update(project_visibility=p.get("visibility"), project_description=(p.get("description") or "")[:200])
    return out, lambda o: "\n".join(f"{k:<20} {v}" for k, v in o.items() if v not in (None, ""))


def cmd_repos(a):
    c = Client(a)
    rows = [{"name": r["name"], "default branch": branch(r.get("defaultBranch")), "size MB": round(r.get("size", 0) / 1e6, 1),
             "url": r.get("webUrl")} for r in c.call("git/repositories")["value"]]
    rows.sort(key=lambda r: r["name"].lower())
    return rows, lambda o: table(o, ["name", "default branch", "size MB", "url"])


def pr_row(p: dict) -> dict:
    votes = [VOTES.get(r.get("vote", 0), r.get("vote")) for r in p.get("reviewers", []) if r.get("vote")]
    return {"id": p["pullRequestId"], "repo": p["repository"]["name"], "title": p["title"],
            "author": p.get("createdBy", {}).get("displayName"), "source": branch(p.get("sourceRefName")),
            "target": branch(p.get("targetRefName")), "status": p.get("status") + (" (draft)" if p.get("isDraft") else ""),
            "votes": ", ".join(votes) or "none", "created": when(p.get("creationDate"))}


def cmd_prs(a):
    c = Client(a)
    params = {"searchCriteria.status": a.status, "$top": a.top}
    if a.mine or a.reviewing:
        me = c.me()
        if me["anonymous"]:
            raise Fail("--mine / --reviewing need AZURE_DEVOPS_PAT")
        params["searchCriteria.creatorId" if a.mine else "searchCriteria.reviewerId"] = me["id"]
    path = f"git/repositories/{urllib.parse.quote(a.repo)}/pullrequests" if a.repo else "git/pullrequests"
    rows = [pr_row(p) for p in c.call(path, params)["value"]]
    return rows, lambda o: table(o, ["id", "repo", "title", "author", "source", "target", "status", "votes", "created"])


def cmd_pr(a):
    info, pid = target(a, "pr")
    c = Client(a, info)
    p = c.call(f"git/pullrequests/{pid}")
    repo_id, project_id = p["repository"]["id"], p["repository"]["project"]["id"]
    out = pr_row(p)
    out.update(
        url=c.web(f"_git/{urllib.parse.quote(p['repository']['name'])}/pullrequest/{pid}"),
        merge_status=p.get("mergeStatus"), description=(p.get("description") or "")[:1500],
        reviewers=[{"name": r.get("displayName"), "vote": VOTES.get(r.get("vote", 0), r.get("vote")),
                    "required": bool(r.get("isRequired"))} for r in p.get("reviewers", [])])
    try:
        evals = c.call("policy/evaluations", {"artifactId": f"vstfs:///CodeReview/CodeReviewId/{project_id}/{pid}"},
                       version="7.1-preview.1")["value"]
        out["policies"] = [{"policy": e["configuration"]["type"]["displayName"], "status": e.get("status"),
                            "build": (e.get("context") or {}).get("buildId")} for e in evals]
    except Fail:
        out["policies"] = "unavailable (needs a token with Code read on this project)"
    threads = c.call(f"git/repositories/{repo_id}/pullRequests/{pid}/threads")["value"]
    out["open_threads"] = [
        {"file": (t.get("threadContext") or {}).get("filePath"),
         "line": ((t.get("threadContext") or {}).get("rightFileStart") or {}).get("line"),
         "author": t["comments"][0].get("author", {}).get("displayName"),
         "comment": (t["comments"][0].get("content") or "")[:400], "replies": len(t["comments"]) - 1}
        for t in threads if t.get("status") in ("active", "pending") and t.get("comments")
        and t["comments"][0].get("commentType") != "system"]
    try:
        out["work_items"] = [int(w["id"]) for w in c.call(f"git/repositories/{repo_id}/pullRequests/{pid}/workitems")["value"]]
    except Fail:
        out["work_items"] = []

    def show(o):
        lines = [f"PR {o['id']}  {o['title']}", f"  {o['url']}",
                 f"  {o['author']}: {o['source']} -> {o['target']}   status {o['status']}, merge {o['merge_status']}",
                 "", "Reviewers:" + ("" if o["reviewers"] else " none")] + [
                     f"  {r['name']}: {r['vote']}{' (required)' if r['required'] else ''}" for r in o["reviewers"]]
        if not isinstance(o["policies"], list):
            lines += ["", f"Policies: {o['policies']}"]
        elif not o["policies"]:
            lines += ["", "Policies: none"]
        else:
            lines += ["", "Policies (build ids -> `ado.py build ID`):"] + [
                f"  {x['status']:<10} {x['policy']}" + (f"  (build {x['build']})" if x["build"] else "") for x in o["policies"]]
        lines += ["", f"Open review threads: {len(o['open_threads'])}"]
        for t in o["open_threads"]:
            where = f"{t['file']}:{t['line']}" if t["file"] else "(general)"
            lines.append(f"  - {where}  {t['author']}: {t['comment'].splitlines()[0] if t['comment'] else ''}"
                         + (f"  [+{t['replies']} replies]" if t["replies"] else ""))
        if o["work_items"]:
            lines += ["", "Work items: " + ", ".join(map(str, o["work_items"]))]
        if o["description"]:
            lines += ["", "Description:", "  " + o["description"].replace("\n", "\n  ")]
        return "\n".join(lines)
    return out, show


def cmd_pr_create(a):
    c = Client(a)
    repo = c.call(f"git/repositories/{urllib.parse.quote(a.repo)}")
    tgt = a.target or branch(repo.get("defaultBranch"))
    missing = [b for b in (a.source, tgt)
               if not c.call(f"git/repositories/{repo['id']}/refs", {"filter": f"heads/{b}"})["value"]]
    if missing:
        raise Fail(f"branch not found in {a.repo}: {', '.join(missing)} (push it first)")
    desc = Path(a.description_file).read_text(encoding="utf-8") if a.description_file else (a.description or "")
    body = {"sourceRefName": f"refs/heads/{a.source}", "targetRefName": f"refs/heads/{tgt}", "title": a.title,
            "description": desc, "isDraft": bool(a.draft)}
    if a.work_item:
        body["workItemRefs"] = [{"id": str(w)} for w in a.work_item]
    existing = c.call(f"git/repositories/{repo['id']}/pullrequests",
                      {"searchCriteria.sourceRefName": body["sourceRefName"],
                       "searchCriteria.targetRefName": body["targetRefName"], "searchCriteria.status": "active"})["value"]
    if existing:
        e = existing[0]
        link = c.web(f"_git/{urllib.parse.quote(a.repo)}/pullrequest/{e['pullRequestId']}")
        msg = f"an active PR from {a.source} into {tgt} already exists: {e['pullRequestId']} \"{e['title']}\" - {link}"
        if a.apply:
            raise Fail(msg + " (Azure DevOps allows only one)")
    if not a.apply:
        out = {"would_create": {**body, "description": f"<{len(desc)} chars>"}, "repo": a.repo,
               "warning": msg if existing else None,
               "note": "nothing was sent; repeat with --apply to create the pull request"}
        return {k: v for k, v in out.items() if v is not None}, lambda o: json.dumps(o, indent=2, ensure_ascii=False)
    p = c.call(f"git/repositories/{repo['id']}/pullrequests", body=body)
    out = {"created": p["pullRequestId"], "url": c.web(f"_git/{urllib.parse.quote(a.repo)}/pullrequest/{p['pullRequestId']}")}
    return out, lambda o: f"created PR {o['created']}: {o['url']}"


def build_row(b: dict) -> dict:
    return {"id": b["id"], "pipeline": b["definition"]["name"], "branch": branch(b.get("sourceBranch")),
            "status": b.get("status"), "result": b.get("result") or "-",
            "by": (b.get("requestedFor") or {}).get("displayName"), "finished": when(b.get("finishTime"))}


def cmd_builds(a):
    c = Client(a)
    params = {"$top": a.top, "queryOrder": "queueTimeDescending", "definitions": a.pipeline,
              "branchName": f"refs/heads/{a.branch}" if a.branch else None, "resultFilter": "failed" if a.failed else None}
    if a.mine:
        me = c.me()
        if me["anonymous"]:
            raise Fail("--mine needs AZURE_DEVOPS_PAT")
        params["requestedFor"] = me["id"]
    rows = [build_row(b) for b in c.call("build/builds", params)["value"]]
    return rows, lambda o: table(o, ["id", "pipeline", "branch", "status", "result", "by", "finished"])


def cmd_build(a):
    if a.ref == "last-failed":
        c = Client(a)
        params = {"$top": 1, "queryOrder": "finishTimeDescending", "resultFilter": "failed", "definitions": a.pipeline,
                  "branchName": f"refs/heads/{a.branch}" if a.branch else None}
        if a.mine:
            me = c.me()
            if me["anonymous"]:
                raise Fail("--mine needs AZURE_DEVOPS_PAT")
            params["requestedFor"] = me["id"]
        found = c.call("build/builds", params)["value"]
        if not found:
            raise Fail("no failed build matches")
        bid = found[0]["id"]
    else:
        info, bid = target(a, "build")
        c = Client(a, info)
    try:
        b = c.call(f"build/builds/{bid}")
    except Fail as e:
        if "HTTP 404" in str(e):
            raise Fail(f"build {bid} not found - wrong id, or deleted by the project's retention policy "
                       "(old builds of merged or stale PRs usually are)")
        raise
    out = build_row(b)
    out["url"] = c.web(f"_build/results?buildId={bid}")
    out["reason"] = b.get("reason")
    out["failed_steps"] = []
    timeline = c.call(f"build/builds/{bid}/timeline") or {}
    records = timeline.get("records") or []
    failed = [r for r in records if r.get("result") in ("failed", "canceled") and r.get("type") == "Task"] or \
             [r for r in records if r.get("result") in ("failed", "canceled") and r.get("type") in ("Job", "Stage")]
    # The step that failed first is usually the cause; monitors and summaries start early but fail last.
    failed.sort(key=lambda r: r.get("finishTime") or "9999")
    out["failed_count"] = len(failed)
    for r in failed[:a.max_steps]:
        errors = [i.get("message", "") for i in (r.get("issues") or []) if i.get("type") == "error"]
        step = {"step": r.get("name"), "type": r.get("type"), "result": r.get("result"), "finished": when(r.get("finishTime")),
                "error_count": len(errors), "errors": [e[:500] for e in dict.fromkeys(errors)][:10]}
        if r.get("log") and a.log_lines:
            log = c.call(f"build/builds/{bid}/logs/{r['log']['id']}", text=True)
            clean = [ANSI.sub("", re.sub(r"^\S+Z\s", "", l)) for l in log.splitlines()]
            step["log_tail"] = clean[-a.log_lines:]
            # The real cause is often far above the tail ("Bash exited with code 1" says nothing): collect the
            # lines that look like errors from the whole log, minus those already shown.
            tail = set(step["log_tail"])
            hits = [l.strip() for l in clean if ERROR_LINE.search(l) and not NOISE_LINE.search(l) and l not in tail]
            step["log_errors"] = list(dict.fromkeys(hits))[-15:]
        out["failed_steps"].append(step)

    def show(o):
        lines = [f"Build {o['id']}  {o['pipeline']}  ({o['branch']})", f"  {o['url']}",
                 f"  {o['status']} / {o['result']}, by {o['by']}, finished {o['finished']}, reason {o['reason']}"]
        if o["failed_count"] > len(o["failed_steps"]):
            lines.append(f"  {o['failed_count']} failed steps; showing the first {len(o['failed_steps'])} to fail (--max-steps)")
        if not o["failed_steps"]:
            lines.append("\nNo failed steps." if o["result"] != "failed" else "\nFailed, but no failed step recorded.")
        for s in o["failed_steps"]:
            more = s["error_count"] - len(s["errors"])
            lines += ["", f"FAILED {s['type']}: {s['step']}  (failed at {s['finished']})"] + [f"  error: {e}" for e in s["errors"]]
            if more > 0:
                lines.append(f"  … {more} more error line(s)")
            if s.get("log_errors"):
                lines += [f"  --- error-looking lines from the whole log ({len(s['log_errors'])}) ---"] + [
                    f"  ! {l[:300]}" for l in s["log_errors"]]
            if s.get("log_tail"):
                lines += [f"  --- last {len(s['log_tail'])} log lines ---"] + [f"  | {l}" for l in s["log_tail"]]
        return "\n".join(lines)
    return out, show


def cmd_pipelines(a):
    c = Client(a)
    defs = c.call("build/definitions", {"includeLatestBuilds": "true", "$top": 1000})["value"]
    words = [w.lower() for w in a.match]
    rows = []
    for d in defs:
        hay = f"{d['name']} {d.get('path', '')}".lower()
        if words and not any(w in hay for w in words):
            continue
        lb = d.get("latestBuild") or {}
        rows.append({"id": d["id"], "name": d["name"], "folder": d.get("path"), "last build": lb.get("id", "-"),
                     "last result": lb.get("result") or lb.get("status") or "-", "finished": when(lb.get("finishTime"))})
    rows.sort(key=lambda r: (r["folder"] or "", r["name"].lower()))
    return rows, lambda o: table(o, ["id", "name", "folder", "last build", "last result", "finished"])


WI_FIELDS = ["System.Id", "System.WorkItemType", "System.Title", "System.State", "System.AssignedTo",
             "System.IterationPath", "System.Tags", "System.ChangedDate"]


def wi_row(w: dict) -> dict:
    f = w["fields"]
    return {"id": w["id"], "type": f.get("System.WorkItemType"), "state": f.get("System.State"),
            "title": f.get("System.Title"), "assigned to": (f.get("System.AssignedTo") or {}).get("displayName", "-"),
            "iteration": f.get("System.IterationPath"), "changed": when(f.get("System.ChangedDate"))}


def cmd_work_item(a):
    info, wid = target(a, "work-item")
    c = Client(a, info)
    w = c.call(f"wit/workitems/{wid}", {"$expand": "relations"})
    f = w["fields"]
    out = wi_row(w)
    out.update(url=c.web(f"_workitems/edit/{wid}"), tags=f.get("System.Tags"),
               description=strip_html(f.get("System.Description")),
               acceptance_criteria=strip_html(f.get("Microsoft.VSTS.Common.AcceptanceCriteria")),
               links=[{"rel": (r.get("attributes") or {}).get("name") or r.get("rel"), "url": r.get("url")}
                      for r in w.get("relations") or []])

    def show(o):
        lines = [f"{o['type']} {o['id']}  {o['title']}", f"  {o['url']}",
                 f"  {o['state']}, assigned to {o['assigned to']}, {o['iteration']}, changed {o['changed']}"]
        if o["tags"]:
            lines.append(f"  tags: {o['tags']}")
        for key in ("description", "acceptance_criteria"):
            if o[key]:
                lines += ["", key.replace("_", " ").capitalize() + ":", "  " + o[key].replace("\n", "\n  ")]
        if o["links"]:
            lines += ["", "Links:"] + [f"  {l['rel']}: {l['url'].rsplit('/', 1)[-1]}" for l in o["links"]]
        return "\n".join(lines)
    return out, show


def cmd_work_items(a):
    c = Client(a)
    if a.wiql:
        query = a.wiql
    else:
        cond = " AND [System.AssignedTo] = @Me" if a.mine else ""
        query = ("SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = @project"
                 f"{cond} AND [System.State] NOT IN ('Closed', 'Done', 'Removed', 'Resolved') "
                 "ORDER BY [System.ChangedDate] DESC")
    if "@me" in query.lower() and not c.auth:
        raise Fail("--mine / @Me needs AZURE_DEVOPS_PAT")
    ids = [w["id"] for w in c.call("wit/wiql", {"$top": a.top}, body={"query": query}).get("workItems", [])][:a.top]
    rows = []
    for i in range(0, len(ids), 200):
        batch = c.call("wit/workitems", {"ids": ",".join(map(str, ids[i:i + 200])), "fields": ",".join(WI_FIELDS)})
        rows += [wi_row(w) for w in batch["value"]]
    order = {wid: i for i, wid in enumerate(ids)}  # the batch endpoint ignores the query's ORDER BY
    rows.sort(key=lambda r: order.get(r["id"], len(order)))
    return rows, lambda o: table(o, ["id", "type", "state", "title", "assigned to", "changed"])


def cmd_wiki(a):
    if a.list:
        c = Client(a)
        rows = [{"name": w["name"], "type": w.get("type"), "url": w.get("remoteUrl")} for w in c.call("wiki/wikis")["value"]]
        return rows, lambda o: table(o, ["name", "type", "url"])
    if not a.url:
        raise Fail("give a wiki page URL, or --list")
    info = parse_url(a.url)
    if info.get("kind") != "wiki":
        raise Fail("that URL is not a wiki page link")
    c = Client(a, info)
    path = f"wiki/wikis/{urllib.parse.quote(info['wiki'])}/pages/{info['id']}"
    if a.tree:
        page = c.call(path, {"recursionLevel": "oneLevel"})
        rows = [{"id": p.get("id"), "path": p.get("path")} for p in page.get("subPages", [])]
        return rows, lambda o: table(o, ["id", "path"])
    page = c.call(path, {"includeContent": "true"})
    out = {"path": page.get("path"), "url": a.url, "content": page.get("content", "")}
    return out, lambda o: f"# {o['path']}\n\n{o['content']}"


def cmd_agents(a):
    c = Client(a)
    pools = c.call("distributedtask/pools", scope="org")["value"]
    if not a.pool:
        rows = [{"id": p["id"], "pool": p["name"], "hosted": p.get("isHosted"), "size": p.get("size")} for p in pools]
        return rows, lambda o: table(o, ["id", "pool", "hosted", "size"])
    pool = next((p for p in pools if p["name"].lower() == a.pool.lower()), None)
    if not pool:
        raise Fail(f"no pool named {a.pool!r}; pools: {', '.join(p['name'] for p in pools)}")
    agents = c.call(f"distributedtask/pools/{pool['id']}/agents", {"includeAssignedRequest": "true"}, scope="org")["value"]
    rows = [{"agent": g["name"], "status": g.get("status"), "enabled": g.get("enabled"), "version": g.get("version"),
             "busy": "yes" if g.get("assignedRequest") else "no"} for g in agents]
    return rows, lambda o: table(o, ["agent", "status", "enabled", "busy", "version"])


# ------------------------------------------------------------------ main

def main() -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="machine-readable output")
    common.add_argument("--org", help="organization (default: AZURE_DEVOPS_ORG)")
    common.add_argument("--project", help="project (default: AZURE_DEVOPS_PROJECT)")
    common.add_argument("--timeout", type=float, default=30, help="seconds per request (default 30)")

    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    add = lambda name, fn, help_: sub.add_parser(name, parents=[common], help=help_).set_defaults(fn=fn) or sub.choices[name]

    add("whoami", cmd_whoami, "check the connection: user, org, project")
    add("repos", cmd_repos, "git repositories of the project")
    s = add("prs", cmd_prs, "list pull requests")
    s.add_argument("--repo"); s.add_argument("--status", default="active", choices=["active", "completed", "abandoned", "all"])
    g = s.add_mutually_exclusive_group(); g.add_argument("--mine", action="store_true"); g.add_argument("--reviewing", action="store_true")
    s.add_argument("--top", type=int, default=20)
    s = add("pr", cmd_pr, "one pull request: reviewers, policies, open threads"); s.add_argument("ref", help="PR id or URL")
    s = add("pr-create", cmd_pr_create, "open a pull request (dry run unless --apply)")
    s.add_argument("--repo", required=True); s.add_argument("--source", required=True); s.add_argument("--target")
    s.add_argument("--title", required=True)
    g = s.add_mutually_exclusive_group(required=True); g.add_argument("--description-file"); g.add_argument("--description")
    s.add_argument("--work-item", type=int, action="append"); s.add_argument("--draft", action="store_true")
    s.add_argument("--apply", action="store_true", help="really create it")
    s = add("builds", cmd_builds, "recent builds")
    s.add_argument("--pipeline", type=int); s.add_argument("--branch"); s.add_argument("--failed", action="store_true")
    s.add_argument("--mine", action="store_true"); s.add_argument("--top", type=int, default=10)
    s = add("build", cmd_build, "one build: failed steps, errors, log tail")
    s.add_argument("ref", help="build id, URL, or last-failed (narrow it with --pipeline / --branch / --mine)")
    s.add_argument("--pipeline", type=int); s.add_argument("--branch"); s.add_argument("--mine", action="store_true")
    s.add_argument("--log-lines", type=int, default=30); s.add_argument("--max-steps", type=int, default=3)
    s = add("pipelines", cmd_pipelines, "pipelines with their latest build"); s.add_argument("--match", nargs="*", default=[])
    s = add("work-item", cmd_work_item, "one work item"); s.add_argument("ref", help="work item id or URL")
    s = add("work-items", cmd_work_items, "open work items (or a WIQL query)")
    s.add_argument("--mine", action="store_true"); s.add_argument("--wiql"); s.add_argument("--top", type=int, default=30)
    s = add("wiki", cmd_wiki, "read a wiki page"); s.add_argument("url", nargs="?")
    s.add_argument("--tree", action="store_true"); s.add_argument("--list", action="store_true")
    s = add("agents", cmd_agents, "agent pools, or the agents of one pool"); s.add_argument("--pool")

    a = p.parse_args()
    for stream in (sys.stdout, sys.stderr):  # logs contain emoji etc.; never die on a Windows console code page
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    load_dotenv()
    data, show = a.fn(a)
    print(json.dumps(data, indent=2, ensure_ascii=False) if a.json else show(data))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
