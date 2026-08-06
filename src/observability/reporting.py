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
    """TODO(student): viet markdown report so sanh baseline/corrupted/repaired."""
    raise NotImplementedError("Student task: implement corruption comparison report.")


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
    """TODO(student): viet markdown report so sanh baseline/corrupted/repaired."""
    raise NotImplementedError("Student task: implement corruption comparison report.")
