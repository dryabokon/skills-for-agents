#!/usr/bin/env bash
# The cost guard: price a big query without running it, see it refused over the cap, run a small one, audit spend.
# Run from the skill folder:   cd skills/bigquery && bash examples/cost-guard.sh
# Bills about $0.0001 (one 10 MB minimum query) to GOOGLE_CLOUD_PROJECT.
set -e

python scripts/bq.py query 'SELECT * FROM `bigquery-public-data.samples.trigrams`' --dry-run
python scripts/bq.py query 'SELECT * FROM `bigquery-public-data.samples.trigrams`' || echo "^ refused: over the cap, nothing billed"
python scripts/bq.py query 'SELECT corpus, SUM(word_count) AS words FROM `bigquery-public-data.samples.shakespeare` GROUP BY corpus ORDER BY words DESC' --limit 5
python scripts/bq.py costs --days 7
