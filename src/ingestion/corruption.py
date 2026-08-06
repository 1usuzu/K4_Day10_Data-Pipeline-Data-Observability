from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import normalize_whitespace, write_json

_NOISE_TOKEN = "CORRUPTED_NOISE_TOKEN"
_STALE_DATE = "2000-01-01"


def _string_value(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return normalize_whitespace(str(value))


def _rebuild_text_for_embedding(row: pd.Series) -> str:
    return "\n".join(
        [
            f"Title: {_string_value(row.get('title'))}",
            f"Summary: {_string_value(row.get('summary'))}",
            f"Authors: {_string_value(row.get('authors_joined')) or 'Unknown'}",
            f"Categories: {_string_value(row.get('categories_joined')) or 'Uncategorized'}",
            f"Published: {_string_value(row.get('published'))}",
        ]
    )


def _sort_for_latest(df: pd.DataFrame) -> pd.DataFrame:
    sort_columns = [column for column in ("published", "paper_id") if column in df.columns]
    if not sort_columns:
        return df.reset_index(drop=True)
    ascending = [False if column == "published" else True for column in sort_columns]
    return df.sort_values(by=sort_columns, ascending=ascending, kind="mergesort").reset_index(drop=True)


def _paper_id(row: pd.Series) -> str:
    return _string_value(row.get("paper_id"))


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Create deterministic data-quality problems and write an audit log."""
    corrupted = _sort_for_latest(df.copy(deep=True))
    operations: list[dict[str, Any]] = []
    input_rows = len(corrupted)

    if corrupted.empty:
        write_json(
            Path(output_log_path),
            {
                "input_rows": input_rows,
                "output_rows": 0,
                "operations": operations,
            },
        )
        return corrupted

    if len(corrupted) >= 4:
        dropped = corrupted.iloc[:1].copy()
        corrupted = corrupted.iloc[1:].reset_index(drop=True)
        operations.append(
            {
                "type": "drop_latest_records",
                "row_count": len(dropped),
                "paper_ids": [_paper_id(row) for _, row in dropped.iterrows()],
            }
        )

    if len(corrupted) >= 1 and "summary" in corrupted.columns:
        idx = corrupted.index[0]
        operations.append(
            {
                "type": "blank_summary",
                "row_count": 1,
                "paper_ids": [_paper_id(corrupted.loc[idx])],
            }
        )
        corrupted.loc[idx, "summary"] = ""
        if "summary_chars" in corrupted.columns:
            corrupted.loc[idx, "summary_chars"] = 0

    if len(corrupted) >= 2 and "summary" in corrupted.columns:
        idx = corrupted.index[1]
        base_summary = _string_value(corrupted.loc[idx, "summary"])
        corrupted.loc[idx, "summary"] = f"{base_summary} {_NOISE_TOKEN} {_NOISE_TOKEN}"
        if "summary_chars" in corrupted.columns:
            corrupted.loc[idx, "summary_chars"] = len(corrupted.loc[idx, "summary"])
        operations.append(
            {
                "type": "inject_summary_noise",
                "row_count": 1,
                "paper_ids": [_paper_id(corrupted.loc[idx])],
                "noise_token": _NOISE_TOKEN,
            }
        )

    if len(corrupted) >= 3 and "title" in corrupted.columns:
        idx = corrupted.index[2]
        original_title = _string_value(corrupted.loc[idx, "title"])
        truncated = original_title[:40].rstrip()
        corrupted.loc[idx, "title"] = f"{truncated}..." if truncated else "..."
        operations.append(
            {
                "type": "truncate_title",
                "row_count": 1,
                "paper_ids": [_paper_id(corrupted.loc[idx])],
            }
        )

    if len(corrupted) >= 4 and "published" in corrupted.columns:
        idx = corrupted.index[3]
        corrupted.loc[idx, "published"] = _STALE_DATE
        if "updated" in corrupted.columns:
            corrupted.loc[idx, "updated"] = _STALE_DATE
        if "age_days" in corrupted.columns:
            current_max_age = pd.to_numeric(corrupted["age_days"], errors="coerce").max()
            corrupted.loc[idx, "age_days"] = int(current_max_age if pd.notna(current_max_age) else 0) + 3650
        operations.append(
            {
                "type": "make_stale_publication_date",
                "row_count": 1,
                "paper_ids": [_paper_id(corrupted.loc[idx])],
                "published": _STALE_DATE,
            }
        )

    if not corrupted.empty:
        duplicate = corrupted.tail(1).copy()
        corrupted = pd.concat([corrupted, duplicate], ignore_index=True)
        operations.append(
            {
                "type": "add_duplicate_rows",
                "row_count": len(duplicate),
                "paper_ids": [_paper_id(row) for _, row in duplicate.iterrows()],
            }
        )

    if "text_for_embedding" in corrupted.columns:
        corrupted["text_for_embedding"] = corrupted.apply(_rebuild_text_for_embedding, axis=1)

    write_json(
        Path(output_log_path),
        {
            "input_rows": input_rows,
            "output_rows": len(corrupted),
            "operations": operations,
        },
    )
    return corrupted
