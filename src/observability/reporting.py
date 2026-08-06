from __future__ import annotations

from typing import Any

from core.utils import now_utc, write_text


def _fmt(value: Any, digits: int = 3) -> str:
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _checks_table(checks: list[dict[str, Any]]) -> str:
    lines = ["| Check | Passed | Details |", "| --- | --- | --- |"]
    for check in checks:
        status = "PASS" if check.get("passed") else "FAIL"
        details = ", ".join(f"{k}={v}" for k, v in (check.get("details") or {}).items())
        lines.append(f"| {check.get('name')} | {status} | {details} |")
    return "\n".join(lines)


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Viet markdown report cho baseline phase tu source/metrics/quality/freshness that."""
    ragas = metrics.get("ragas")
    ragas_line = "skipped (set RUN_RAGAS=1 to enable)" if isinstance(ragas, dict) and "skipped" in ragas else str(ragas)

    content = f"""# Phase 1 Baseline Report

Generated at: {now_utc().isoformat()}

## Source

- API: {source_summary.get('source_api')}
- Query: {source_summary.get('source_query')}
- Filter: {source_summary.get('source_filter')}
- Raw records: {source_summary.get('raw_record_count')}
- Clean records: {source_summary.get('clean_record_count')}

## Retrieval & Evaluation Metrics

- Samples: {metrics.get('samples')}
- Retrieval hit rate: {_fmt(metrics.get('retrieval_hit_rate'))}
- Mean token F1: {_fmt(metrics.get('mean_token_f1'))}
- Judge accuracy: {_fmt(metrics.get('judge_accuracy'))}
- Mean judge score: {_fmt(metrics.get('mean_judge_score'))}
- Ragas: {ragas_line}

## Data Quality

- Overall status: {"PASS" if quality.get("passed") else "FAIL"}
- Row count: {quality.get('row_count')}
- Failed checks: {quality.get('failed_checks') or "none"}

{_checks_table(quality.get("checks") or [])}

## Freshness

- Latest published: {freshness.get('latest_published')}
- Oldest published: {freshness.get('oldest_published')}
- Stale rows: {freshness.get('stale_rows')} / {freshness.get('total_rows')}
- Is fresh: {freshness.get('is_fresh')}
"""
    write_text(report_path, content)


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Viet markdown report so sanh baseline/corrupted/repaired."""
    content = f"""# Phase 2 Corruption & Repair Report

Generated at: {now_utc().isoformat()}

## Retrieval & Evaluation Comparison

| Metric | Baseline | Corrupted | Repaired |
| --- | --- | --- | --- |
| Retrieval Hit Rate | {_fmt(baseline_metrics.get('retrieval_hit_rate'))} | {_fmt(corrupted_metrics.get('retrieval_hit_rate'))} | {_fmt(repaired_metrics.get('retrieval_hit_rate'))} |
| Mean Token F1 | {_fmt(baseline_metrics.get('mean_token_f1'))} | {_fmt(corrupted_metrics.get('mean_token_f1'))} | {_fmt(repaired_metrics.get('mean_token_f1'))} |
| Judge Accuracy | {_fmt(baseline_metrics.get('judge_accuracy'))} | {_fmt(corrupted_metrics.get('judge_accuracy'))} | {_fmt(repaired_metrics.get('judge_accuracy'))} |
| Mean Judge Score | {_fmt(baseline_metrics.get('mean_judge_score'))} | {_fmt(corrupted_metrics.get('mean_judge_score'))} | {_fmt(repaired_metrics.get('mean_judge_score'))} |

## Data Quality Comparison

| Metric | Corrupted | Repaired |
| --- | --- | --- |
| Overall Status | {"PASS" if corrupted_quality.get("passed") else "FAIL"} | {"PASS" if repaired_quality.get("passed") else "FAIL"} |
| Failed Checks | {corrupted_quality.get('failed_checks') or "none"} | {repaired_quality.get('failed_checks') or "none"} |
| Stale Rows | {corrupted_freshness.get('stale_rows')} | {repaired_freshness.get('stale_rows')} |
| Is Fresh | {corrupted_freshness.get('is_fresh')} | {repaired_freshness.get('is_fresh')} |
"""
    write_text(report_path, content)
