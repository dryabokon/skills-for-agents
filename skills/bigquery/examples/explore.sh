#!/usr/bin/env bash
# Explore a dataset for free: tables with rows / size / last change, one table's columns, and which tables went stale.
# Run from the skill folder:   cd skills/bigquery && bash examples/explore.sh
# Needs gcloud signed in and GOOGLE_CLOUD_PROJECT (env or .env). These commands bill nothing.
set -e

python scripts/bq.py whoami
python scripts/bq.py tables bigquery-public-data.samples
python scripts/bq.py schema bigquery-public-data.samples.shakespeare
python scripts/bq.py freshness bigquery-public-data.samples --stale-days 365
