#!/usr/bin/env python3
"""BigQuery with a cost guard: explore datasets, check freshness, run queries that cannot surprise the bill.

    python bq.py whoami                                   billing project, account, location
    python bq.py datasets   [--project P]
    python bq.py tables     DATASET                       rows, size, last modified (free: table metadata)
    python bq.py schema     TABLE                         columns, partitioning, clustering
    python bq.py freshness  DATASET [--stale-days N]      which tables got no new data for N days (free)
    python bq.py query      "SQL" | --file F [--max-gb G] [--limit N] [--dry-run]
                            always a dry run first: shows bytes and price; runs only under --max-gb,
                            and BigQuery itself refuses to bill more (maximumBytesBilled)
    python bq.py costs      [--days N] [--location L]     bytes billed per user and the most expensive queries

DATASET is `dataset` (billing project) or `project.dataset`; TABLE is `dataset.table` or `project.dataset.table`.
Every command takes --json and --project.

Configuration - environment variables, or a .env file in the current directory or any parent:
    GOOGLE_CLOUD_PROJECT   the project that runs (and pays for) queries
    BQ_MAX_GB              default cap per query in GB (default 1)
    BQ_LOCATION            default location for `costs` (default US)
Authentication: your gcloud sign-in (`gcloud auth login`) - the access token comes from `gcloud auth
print-access-token`; or GOOGLE_OAUTH_ACCESS_TOKEN. Standard library only; Python 3.9+.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://bigquery.googleapis.com/bigquery/v2"
USD_PER_TIB = 6.25  # on-demand list price; reservations and free tier change what you actually pay
MIN_BILLED = 10 * 1024 ** 2  # on-demand bills at least 10 MB per query that reads anything


class Fail(SystemExit):
    def __init__(self, msg: str):
        super().__init__(f"error: {msg}")


# ------------------------------------------------------------------ configuration

def load_dotenv() -> None:
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
            return


def gcloud(*args: str) -> str:
    exe = shutil.which("gcloud")
    if not exe:
        raise Fail("gcloud not found - install the Google Cloud SDK and run `gcloud auth login`, "
                   "or set GOOGLE_OAUTH_ACCESS_TOKEN")
    res = subprocess.run([exe, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    if res.returncode:
        raise Fail(f"gcloud {' '.join(args)} failed: {res.stderr.strip()[:300]}")
    return res.stdout.strip()


class BQ:
    def __init__(self, a):
        self.project = a.project or os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("CLOUDSDK_CORE_PROJECT")
        if not self.project:
            try:
                self.project = gcloud("config", "get-value", "project") or None
            except Fail:
                self.project = None
        if not self.project:
            raise Fail("no billing project: set GOOGLE_CLOUD_PROJECT (env or .env) or pass --project")
        self.timeout = a.timeout
        self._token = os.environ.get("GOOGLE_OAUTH_ACCESS_TOKEN")

    def token(self) -> str:
        if not self._token:
            self._token = gcloud("auth", "print-access-token")
        return self._token

    def call(self, path: str, params: dict | None = None, body=None):
        url = f"{API}/{path}"
        params = {k: v for k, v in (params or {}).items() if v is not None}
        if params:
            url += "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Authorization": f"Bearer {self.token()}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            try:
                msg = json.loads(raw)["error"]["message"]
            except (ValueError, KeyError, TypeError):
                msg = raw[:300]
            hint = {401: " - run `gcloud auth login` (the sign-in has expired)",
                    403: " - no permission, or the BigQuery API is not enabled for the billing project"}.get(e.code, "")
            raise Fail(f"HTTP {e.code}{hint}\n  {msg}")
        except (urllib.error.URLError, TimeoutError) as e:
            raise Fail(f"cannot reach BigQuery: {getattr(e, 'reason', e)}")

    def split(self, ref: str, parts: int) -> list[str]:
        """'d' / 'p.d' (parts=2) or 'd.t' / 'p.d.t' (parts=3) -> fully qualified pieces."""
        bits = ref.strip("`").split(".")
        if len(bits) == parts - 1:
            bits = [self.project, *bits]
        if len(bits) != parts:
            raise Fail(f"expected {'[project.]dataset' if parts == 2 else '[project.]dataset.table'}, got {ref!r}")
        return bits


# ------------------------------------------------------------------ helpers

def human_bytes(n: float | int | None) -> str:
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def price(bytes_: int) -> str:
    if not bytes_:
        return "$0"
    billed = max(bytes_, MIN_BILLED)
    usd = billed / 1024 ** 4 * USD_PER_TIB
    return f"~${usd:.4f}" if usd < 0.01 else f"~${usd:.2f}"


def ms_date(ms) -> str:
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M") if ms else "-"


def table(rows: list[dict], cols: list[str], width: int = 50) -> str:
    if not rows:
        return "(none)"
    w = {c: min(max(len(c), *(len(str(r.get(c, ""))) for r in rows)), width) for c in cols}
    line = lambda r: "  ".join(str(r.get(c, ""))[:w[c]].ljust(w[c]) for c in cols).rstrip()
    return "\n".join([line({c: c for c in cols}), line({c: "-" * w[c] for c in cols})] + [line(r) for r in rows])


def rows_of(result: dict) -> list[dict]:
    names = [f["name"] for f in result.get("schema", {}).get("fields", [])]
    out = []
    for r in result.get("rows", []):
        vals = []
        for cell in r["f"]:
            v = cell.get("v")
            vals.append(json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v)
        out.append(dict(zip(names, vals)))
    return out


def run_sql(bq: BQ, sql: str, max_bytes: int, limit: int) -> dict:
    """Run a query billed to bq.project with a hard cap; wait for it; return rows and statistics."""
    body = {"query": sql, "useLegacySql": False, "maximumBytesBilled": str(max_bytes), "maxResults": limit,
            "timeoutMs": 60000}
    r = bq.call(f"projects/{bq.project}/queries", body=body)
    job = r["jobReference"]
    while not r.get("jobComplete"):
        time.sleep(1)
        r = bq.call(f"projects/{bq.project}/queries/{job['jobId']}",
                    {"location": job.get("location"), "maxResults": limit, "timeoutMs": 60000})
    return r


def dry(bq: BQ, sql: str) -> int:
    r = bq.call(f"projects/{bq.project}/queries", body={"query": sql, "useLegacySql": False, "dryRun": True})
    return int(r.get("totalBytesProcessed", 0))


# ------------------------------------------------------------------ commands

def cmd_whoami(a):
    bq = BQ(a)
    try:
        account = gcloud("config", "get-value", "account")
    except Fail:
        account = "(token from GOOGLE_OAUTH_ACCESS_TOKEN)"
    bq.call(f"projects/{bq.project}/datasets", {"maxResults": 1})  # proves access and that the API is on
    out = {"billing project": bq.project, "account": account, "max per query": f"{a.max_gb} GB",
           "costs location": os.environ.get("BQ_LOCATION", "US")}
    return out, lambda o: "\n".join(f"{k:<16} {v}" for k, v in o.items())


def cmd_datasets(a):
    bq = BQ(a)
    ds = bq.call(f"projects/{bq.project}/datasets", {"all": "false", "maxResults": 1000}).get("datasets", [])
    rows = [{"dataset": d["datasetReference"]["datasetId"], "location": d.get("location")} for d in ds]
    return rows, lambda o: table(o, ["dataset", "location"]) if o else f"(no datasets in {bq.project})"


def table_meta(bq: BQ, project: str, dataset: str) -> list[dict]:
    """Rows, size and last change of every table, from __TABLES__ (metadata: 0 bytes processed)."""
    sql = (f"SELECT table_id, row_count, size_bytes, last_modified_time, type "
           f"FROM `{project}.{dataset}.__TABLES__` ORDER BY table_id")
    r = run_sql(bq, sql, MIN_BILLED, 10000)
    rows = rows_of(r)
    kinds = {"1": "table", "2": "view", "3": "external", "4": "model"}
    return [{"table": x["table_id"], "rows": int(x["row_count"] or 0), "size": human_bytes(x["size_bytes"]),
             "bytes": int(x["size_bytes"] or 0), "modified": ms_date(x["last_modified_time"]),
             "modified_ms": int(x["last_modified_time"] or 0), "type": kinds.get(str(x["type"]), x["type"])} for x in rows]


def cmd_tables(a):
    bq = BQ(a)
    project, dataset = bq.split(a.dataset, 2)
    rows = table_meta(bq, project, dataset)
    return rows, lambda o: table(o, ["table", "type", "rows", "size", "modified"])


def flat_fields(fields: list, prefix: str = "") -> list[dict]:
    out = []
    for f in fields:
        name = prefix + f["name"]
        out.append({"column": name, "type": f["type"] + ("[]" if f.get("mode") == "REPEATED" else ""),
                    "mode": f.get("mode", "NULLABLE"), "description": (f.get("description") or "")[:80]})
        if f.get("fields"):
            out += flat_fields(f["fields"], name + ".")
    return out


def cmd_schema(a):
    bq = BQ(a)
    p, d, t = bq.split(a.table, 3)
    m = bq.call(f"projects/{p}/datasets/{d}/tables/{t}")
    out = {"table": f"{p}.{d}.{t}", "type": m.get("type"), "rows": int(m.get("numRows", 0)),
           "size": human_bytes(m.get("numBytes")), "modified": ms_date(m.get("lastModifiedTime")),
           "partitioning": (m.get("timePartitioning") or m.get("rangePartitioning") or None),
           "clustering": (m.get("clustering") or {}).get("fields"),
           "columns": flat_fields(m.get("schema", {}).get("fields", []))}

    def show(o):
        head = [f"{o['table']}  ({o['type']}, {o['rows']:,} rows, {o['size']}, modified {o['modified']})"]
        if o["partitioning"]:
            head.append(f"  partitioned: {json.dumps(o['partitioning'])}  - filter on it to scan less")
        if o["clustering"]:
            head.append(f"  clustered by: {', '.join(o['clustering'])}")
        return "\n".join(head + ["", table(o["columns"], ["column", "type", "mode", "description"], 60)])
    return out, show


def cmd_freshness(a):
    bq = BQ(a)
    project, dataset = bq.split(a.dataset, 2)
    now = time.time() * 1000
    rows = [r for r in table_meta(bq, project, dataset) if r["type"] == "table"]
    for r in rows:
        r["age days"] = round((now - r["modified_ms"]) / 86400000, 1) if r["modified_ms"] else None
        r["status"] = "STALE" if r["age days"] is None or r["age days"] > a.stale_days else "fresh"
        if r["rows"] == 0:
            r["status"] = "EMPTY"
    rows.sort(key=lambda r: (r["status"] == "fresh", -(r["age days"] or 0)))
    stale = sum(r["status"] != "fresh" for r in rows)

    def show(o):
        return (f"{project}.{dataset}: {stale} of {len(o)} tables empty or unchanged for more than {a.stale_days} days "
                f"(by last modification time)\n\n" + table(o, ["table", "status", "age days", "modified", "rows", "size"]))
    return rows, show


def cmd_query(a):
    bq = BQ(a)
    sql = Path(a.file).read_text(encoding="utf-8") if a.file else a.sql
    if not sql:
        raise Fail("give SQL or --file")
    if re.match(r"(?is)^\s*(insert|update|delete|merge|create|drop|alter|truncate)\b", sql) and not a.allow_write:
        raise Fail("this statement changes data; this skill only reads. Pass --allow-write if the user asked for it.")
    bytes_ = dry(bq, sql)
    cap = int(a.max_gb * 1024 ** 3)
    plan = {"bytes processed": human_bytes(bytes_), "estimated cost": price(bytes_) + " (on-demand list price)",
            "cap": f"{a.max_gb} GB"}
    if a.dry_run:
        return plan, lambda o: "\n".join(f"{k:<16} {v}" for k, v in o.items()) + "\n(dry run - nothing was billed)"
    if bytes_ > cap:
        raise Fail(f"the query would scan {human_bytes(bytes_)} ({price(bytes_)}), over the {a.max_gb} GB cap. "
                   "Filter on the partition column, select fewer columns, or raise --max-gb if the user agrees.")
    r = run_sql(bq, sql, max(cap, MIN_BILLED), a.limit)
    billed = int(r.get("totalBytesBilled") or r.get("totalBytesProcessed") or 0)
    rows = rows_of(r)
    total = int(r.get("totalRows", len(rows)))
    out = {"rows": rows, "total_rows": total, "bytes_billed": billed, "cost": price(billed),
           "job": r["jobReference"]["jobId"]}

    def show(o):
        cols = list(o["rows"][0].keys()) if o["rows"] else []
        more = f" (showing {len(o['rows'])} of {o['total_rows']}; --limit)" if o["total_rows"] > len(o["rows"]) else ""
        return (table(o["rows"], cols, 60) + f"\n\n{o['total_rows']} rows{more} · billed {human_bytes(o['bytes_billed'])}"
                f" · {o['cost']}")
    return out, show


def cmd_costs(a):
    bq = BQ(a)
    loc = (a.location or os.environ.get("BQ_LOCATION") or "US").lower()
    src = f"`{bq.project}`.`region-{loc}`.INFORMATION_SCHEMA.JOBS_BY_PROJECT"
    where = f"creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {int(a.days)} DAY) AND job_type = 'QUERY'"
    per_user = rows_of(run_sql(bq, f"SELECT user_email, COUNT(*) AS queries, SUM(total_bytes_billed) AS billed "
                                   f"FROM {src} WHERE {where} GROUP BY 1 ORDER BY billed DESC", 1024 ** 3, 100))
    top = rows_of(run_sql(bq, f"SELECT creation_time, user_email, total_bytes_billed AS billed, "
                              f"SUBSTR(REGEXP_REPLACE(query, r'\\s+', ' '), 1, 90) AS query FROM {src} WHERE {where} "
                              f"ORDER BY total_bytes_billed DESC LIMIT 5", 1024 ** 3, 5))
    for r in per_user + top:
        r["cost"] = price(int(r["billed"] or 0))
        r["billed"] = human_bytes(r["billed"])
    for r in top:
        r["when"] = datetime.fromtimestamp(float(r.pop("creation_time")), tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    out = {"location": loc, "days": a.days, "per_user": per_user, "top_queries": top}
    return out, lambda o: (f"Last {o['days']} days, {o['location']}:\n\n" + table(o["per_user"], ["user_email", "queries", "billed", "cost"])
                           + "\n\nMost expensive:\n" + table(o["top_queries"], ["when", "user_email", "billed", "cost", "query"], 90))


# ------------------------------------------------------------------ main

def main() -> int:
    load_dotenv()
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="machine-readable output")
    common.add_argument("--project", help="billing project (default: GOOGLE_CLOUD_PROJECT, then gcloud config)")
    common.add_argument("--timeout", type=float, default=90)
    common.add_argument("--max-gb", type=float, default=float(os.environ.get("BQ_MAX_GB") or 1),
                        help="largest query to run, in GB scanned (default BQ_MAX_GB or 1)")

    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, fn, help_):
        s = sub.add_parser(name, parents=[common], help=help_)
        s.set_defaults(fn=fn)
        return s

    add("whoami", cmd_whoami, "billing project, account, caps")
    add("datasets", cmd_datasets, "datasets of the project")
    add("tables", cmd_tables, "tables of a dataset with rows, size, last change").add_argument("dataset")
    add("schema", cmd_schema, "columns of a table").add_argument("table")
    s = add("freshness", cmd_freshness, "tables with no new data for N days"); s.add_argument("dataset")
    s.add_argument("--stale-days", type=float, default=7)
    s = add("query", cmd_query, "run SQL behind a dry run and a byte cap"); s.add_argument("sql", nargs="?")
    s.add_argument("--file"); s.add_argument("--limit", type=int, default=50); s.add_argument("--dry-run", action="store_true")
    s.add_argument("--allow-write", action="store_true", help=argparse.SUPPRESS)
    s = add("costs", cmd_costs, "bytes billed per user and the most expensive queries")
    s.add_argument("--days", type=int, default=7); s.add_argument("--location")

    a = p.parse_args()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    data, show = a.fn(a)
    if a.json:
        if isinstance(data, list):
            data = [{k: v for k, v in r.items() if k not in ("modified_ms",)} for r in data]
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    else:
        print(show(data))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
