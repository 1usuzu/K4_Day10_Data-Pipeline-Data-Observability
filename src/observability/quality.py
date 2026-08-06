from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import now_utc, safe_slug, write_json

MIN_SUMMARY_CHARS = 40


def _missing_mask(series: pd.Series) -> pd.Series:
    return series.isna() | (series.astype(str).str.strip() == "")


def _check_row_count(df: pd.DataFrame) -> dict[str, Any]:
    row_count = len(df)
    return {"name": "row_count", "passed": row_count > 0, "details": {"row_count": row_count}}


def _check_paper_id_present(df: pd.DataFrame) -> dict[str, Any]:
    if "paper_id" not in df.columns:
        return {"name": "paper_id_present", "passed": False, "details": {"error": "missing paper_id column"}}
    missing = int(_missing_mask(df["paper_id"]).sum())
    return {"name": "paper_id_present", "passed": missing == 0, "details": {"missing_count": missing}}


def _check_paper_id_unique(df: pd.DataFrame) -> dict[str, Any]:
    if "paper_id" not in df.columns:
        return {"name": "paper_id_unique", "passed": False, "details": {"error": "missing paper_id column"}}
    duplicate_count = int(df["paper_id"].duplicated().sum())
    duplicate_ids = sorted(set(df.loc[df["paper_id"].duplicated(keep=False), "paper_id"]))
    return {
        "name": "paper_id_unique",
        "passed": duplicate_count == 0,
        "details": {"duplicate_count": duplicate_count, "duplicate_ids": duplicate_ids},
    }


def _check_title_present(df: pd.DataFrame) -> dict[str, Any]:
    if "title" not in df.columns:
        return {"name": "title_present", "passed": False, "details": {"error": "missing title column"}}
    missing = int(_missing_mask(df["title"]).sum())
    return {"name": "title_present", "passed": missing == 0, "details": {"missing_count": missing}}


def _check_summary_length(df: pd.DataFrame) -> dict[str, Any]:
    if "summary" not in df.columns:
        return {"name": "summary_length", "passed": False, "details": {"error": "missing summary column"}}
    too_short = df["summary"].fillna("").astype(str).str.len() < MIN_SUMMARY_CHARS
    too_short_count = int(too_short.sum())
    return {
        "name": "summary_length",
        "passed": too_short_count == 0,
        "details": {"too_short_count": too_short_count, "min_summary_chars": MIN_SUMMARY_CHARS},
    }


def _check_freshness(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    if "age_days" not in df.columns:
        return {"name": "freshness", "passed": False, "details": {"error": "missing age_days column"}}
    stale = df["age_days"] > settings.freshness_threshold_days
    stale_count = int(stale.sum())
    return {
        "name": "freshness",
        "passed": stale_count == 0,
        "details": {"stale_count": stale_count, "freshness_threshold_days": settings.freshness_threshold_days},
    }


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Chay bo data quality checks tren cleaned dataframe va ghi report ra `data/quality/`."""
    checks = [
        _check_row_count(df),
        _check_paper_id_present(df),
        _check_paper_id_unique(df),
        _check_title_present(df),
        _check_summary_length(df),
        _check_freshness(df, settings),
    ]
    failed_checks = [check["name"] for check in checks if not check["passed"]]

    result = {
        "report_name": report_name,
        "generated_at": now_utc().isoformat(),
        "row_count": len(df),
        "checks": checks,
        "passed": len(failed_checks) == 0,
        "failed_checks": failed_checks,
    }

    output_path = settings.paths.quality_dir / f"{safe_slug(report_name)}.json"
    write_json(output_path, result)
    return result


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Tong hop freshness report tu cot `published`/`age_days` va ghi JSON."""
    total_rows = len(df)

    if total_rows == 0 or "published" not in df.columns or "age_days" not in df.columns:
        payload = {
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "total_rows": total_rows,
            "is_fresh": total_rows > 0,
        }
        write_json(report_path, payload)
        return payload

    published = pd.to_datetime(df["published"], errors="coerce")
    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())

    payload = {
        "latest_published": published.max().date().isoformat() if published.notna().any() else None,
        "oldest_published": published.min().date().isoformat() if published.notna().any() else None,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "is_fresh": stale_rows == 0,
    }
    write_json(report_path, payload)
    return payload
