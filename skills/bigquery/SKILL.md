---
name: bigquery
description: Query and explore Google BigQuery without surprises on the bill - list datasets and tables (rows, size, last change), read schemas, find tables that stopped getting data, run SQL only after a dry run shows bytes and price and under a hard byte cap, and audit who spent what. Read-only by default. Use when the user mentions BigQuery, BQ, a GCP dataset or table, SQL over their warehouse, data freshness or stale tables, or BigQuery cost.
license: MIT
compatibility: Requires Python 3.9+ (standard library only) and the Google Cloud SDK signed in (`gcloud auth login`). GOOGLE_CLOUD_PROJECT names the billing project.
---

# BigQuery

One CLI, `scripts/bq.py`, over the BigQuery REST API with your gcloud sign-in. Commands are relative to this
skill's folder (in Claude Code: `${CLAUDE_SKILL_DIR}`); run them from the user's project so its `.env` is found.

```bash
python scripts/bq.py whoami                            # billing project, account, cap - run this first
python scripts/bq.py datasets [--project P]
python scripts/bq.py tables [project.]dataset           # rows, size, last change - free (metadata)
python scripts/bq.py schema [project.]dataset.table     # columns, partitioning, clustering
python scripts/bq.py freshness [project.]dataset [--stale-days 7]   # empty or unchanged tables - free
python scripts/bq.py query "SQL" | --file q.sql [--dry-run] [--max-gb G] [--limit N]
python scripts/bq.py costs [--days 7] [--location US]   # bytes billed per user, most expensive queries
```

Every command takes `--json`, `--project` (billing project), `--max-gb`.

## Configuration

`GOOGLE_CLOUD_PROJECT` (who pays), `BQ_MAX_GB` (default cap, 1), `BQ_LOCATION` (for `costs`) - environment or the
nearest `.env` (see `.env.example`). Auth is the user's gcloud sign-in; if `whoami` fails with 401, ask them to run
`gcloud auth login` - never ask for keys in chat.

## Rules

1. **Price before you run.** `query` always dry-runs first and refuses anything over the cap; BigQuery also gets
   `maximumBytesBilled`, so the bill cannot exceed it. If a query is over the cap, make it cheaper first: select
   only needed columns (`SELECT *` reads every column), filter on the partition column shown by `schema`, sample
   with `TABLESAMPLE SYSTEM (1 PERCENT)`. Raise `--max-gb` only after telling the user the price and getting a yes.
2. **Explore with metadata, not scans.** `tables`, `schema`, `freshness` cost nothing - use them before writing SQL;
   `LIMIT` does not reduce bytes scanned.
3. **Read-only.** Statements that change data (INSERT, UPDATE, DELETE, MERGE, CREATE, DROP...) are refused; they
   are for the user to run.
4. Report the cost line `query` prints along with the answer.

## Typical requests

- **"Which tables stopped updating?"** → `freshness dataset --stale-days N`; it flags EMPTY and STALE tables by
  last modification time. For a table that changes but may have gaps, follow up with a dated `query`
  (`SELECT DATE(ts) d, COUNT(*) FROM t WHERE ts > ... GROUP BY d`) after checking its partition column.
- **"How many / what is in X?"** → `schema` first, then a narrow `query`.
- **"Why is our BigQuery bill high?"** → `costs --days 30 --location <region>`.

## Examples

Run from this folder (`bash examples/<name>.sh`); they use public datasets, billed to your project:
- `examples/explore.sh` - whoami, tables, schema, freshness (free).
- `examples/cost-guard.sh` - dry-run price, refusal over the cap, one small query (~$0.0001), cost audit.

## Gotchas

- Price shown is the on-demand list price ($6.25 per TiB, 10 MB minimum per query); free tier, editions and
  reservations change what is actually paid.
- `costs` reads `region-<location>.INFORMATION_SCHEMA.JOBS_BY_PROJECT`: jobs in another location are not in it.
- Tables of another project are referenced as `project.dataset.table`; the billing project still pays.
