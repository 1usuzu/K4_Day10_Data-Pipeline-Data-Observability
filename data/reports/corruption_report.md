# Phase 2 Corruption & Repair Report

Generated at: 2026-08-06T09:49:41.909061+00:00

## Retrieval & Evaluation Comparison

| Metric | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| Retrieval Hit Rate | 1.000 | 0.750 | 1.000 |
| Mean Token F1 | 0.969 | 0.725 | 0.969 |
| Judge Accuracy | 0.969 | 0.719 | 0.969 |
| Mean Judge Score | 4.875 | 3.875 | 4.875 |

## Data Quality Comparison

| Metric | Corrupted | Repaired |
| --- | --- | --- |
| Overall Status | FAIL | FAIL |
| Failed Checks | ['paper_id_unique', 'summary_length', 'freshness'] | ['freshness'] |
| Stale Rows | 13 | 11 |
| Is Fresh | False | False |
