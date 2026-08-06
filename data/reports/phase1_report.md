# Phase 1 Baseline Report

Generated at: 2026-08-06T09:18:52.921177+00:00

## Source

- API: Crossref REST API
- Query: agentic retrieval augmented generation large language model
- Filter: from-update-date:2026-02-07,until-update-date:2026-08-06
- Raw records: 24
- Clean records: 24

## Retrieval & Evaluation Metrics

- Samples: 32
- Retrieval hit rate: 1.000
- Mean token F1: 0.969
- Judge accuracy: 0.969
- Mean judge score: 4.875
- Ragas: skipped (set RUN_RAGAS=1 to enable)

## Data Quality

- Overall status: FAIL
- Row count: 24
- Failed checks: ['freshness']

| Check | Passed | Details |
| --- | --- | --- |
| row_count | PASS | row_count=24 |
| paper_id_present | PASS | missing_count=0 |
| paper_id_unique | PASS | duplicate_count=0, duplicate_ids=[] |
| title_present | PASS | missing_count=0 |
| summary_length | PASS | too_short_count=0, min_summary_chars=40 |
| freshness | FAIL | stale_count=11, freshness_threshold_days=180 |

## Freshness

- Latest published: 2026-07-13
- Oldest published: 2024-01-01
- Stale rows: 11 / 24
- Is fresh: False
