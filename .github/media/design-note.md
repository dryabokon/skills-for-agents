# Design note: moving order ingestion from nightly batch to streaming

## Context
Orders from the web shop and the mobile app land in the warehouse through one nightly batch job.
Volume grew 4x in the last 12 months. The job now runs about 7 hours and fails roughly twice a month;
every failure delays the morning sales report by a full day. Analysts work on data that is ~30 hours old.

## Current architecture (exists today)
Web shop and mobile app -> Orders API -> Orders DB (Postgres) -> nightly batch export (Airflow) -> Warehouse (BigQuery) -> Sales dashboards.

## Proposal
Add change-data-capture on the Orders DB (Debezium) publishing to an event stream (Kafka).
A streaming loader writes to the warehouse within minutes. The nightly batch stays for one quarter as a fallback,
then is switched off. Fraud scoring could consume the same stream later - not decided, owner unclear.

## Expected impact
- Data latency: 30 h -> about 5 min
- Compute cost: -38% (no 7-hour cluster)
- Manual restarts: from ~2 per month to none expected

## Options considered
| Option | Latency | Cost | Verdict |
|---|---|---|---|
| Bigger batch cluster | 4 h | +20% | rejected |
| Micro-batch every 30 min | 30 min | same | fallback |
| CDC + streaming | 5 min | -38% | chosen |

## Open questions
1. Who owns the Kafka cluster - platform team or data team?
2. Does fraud scoring consume the stream in phase 1?
3. Retention period for raw events.
