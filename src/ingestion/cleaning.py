from __future__ import annotations

from datetime import datetime
from html import unescape
import re
from typing import Any

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord

_TAG_RE = re.compile(r"<[^>]+>")
_MIN_SUMMARY_CHARS = 40
_CLEAN_COLUMNS = [
    "paper_id",
    "title",
    "summary",
    "authors",
    "authors_joined",
    "categories",
    "categories_joined",
    "primary_category",
    "published",
    "updated",
    "age_days",
    "summary_chars",
    "abs_url",
    "pdf_url",
    "comment",
    "text_for_embedding",
]


def _clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return normalize_whitespace(unescape(_TAG_RE.sub(" ", value)))


def _clean_unique_list(values: Any) -> list[str]:
    if isinstance(values, str):
        candidates = [values]
    elif isinstance(values, list):
        candidates = values
    else:
        candidates = []

    cleaned: list[str] = []
    seen: set[str] = set()
    for value in candidates:
        item = _clean_text(value)
        key = item.lower()
        if item and key not in seen:
            cleaned.append(item)
            seen.add(key)
    return cleaned


def _parse_date(value: Any):
    text = _clean_text(value)
    if not text:
        return None
    parsed = pd.to_datetime(text, errors="coerce", utc=True)
    if pd.isna(parsed):
        return None
    return parsed.date()


def _text_for_embedding(
    title: str,
    summary: str,
    authors_joined: str,
    categories_joined: str,
    published: str,
) -> str:
    return "\n".join(
        [
            f"Title: {title}",
            f"Summary: {summary}",
            f"Authors: {authors_joined}",
            f"Categories: {categories_joined}",
            f"Published: {published}",
        ]
    )


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw `PaperRecord` values into the dataframe contract used downstream."""
    run_day = run_date.date()
    rows: list[dict[str, Any]] = []

    for record in records:
        paper_id = _clean_text(record.paper_id).lower()
        title = _clean_text(record.title)
        summary = _clean_text(record.summary)
        published_date = _parse_date(record.published)
        if not paper_id or not title or len(summary) < _MIN_SUMMARY_CHARS or published_date is None:
            continue

        updated_date = _parse_date(record.updated) or published_date
        authors = _clean_unique_list(record.authors)
        categories = _clean_unique_list(record.categories)
        authors_joined = compact_join(authors) or "Unknown"
        categories_joined = compact_join(categories) or "Uncategorized"
        primary_category = categories[0] if categories else "uncategorized"
        published = published_date.isoformat()
        updated = updated_date.isoformat()
        age_days = max((run_day - published_date).days, 0)

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "authors_joined": authors_joined,
                "categories": categories,
                "categories_joined": categories_joined,
                "primary_category": primary_category,
                "published": published,
                "updated": updated,
                "age_days": age_days,
                "summary_chars": len(summary),
                "abs_url": _clean_text(record.abs_url),
                "pdf_url": _clean_text(record.pdf_url),
                "comment": _clean_text(record.comment),
                "text_for_embedding": _text_for_embedding(
                    title=title,
                    summary=summary,
                    authors_joined=authors_joined,
                    categories_joined=categories_joined,
                    published=published,
                ),
            }
        )

    if not rows:
        return pd.DataFrame(columns=_CLEAN_COLUMNS)

    df = pd.DataFrame(rows, columns=_CLEAN_COLUMNS)
    df = df.sort_values(
        by=["paper_id", "summary_chars", "updated"],
        ascending=[True, False, False],
        kind="mergesort",
    )
    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    return df.sort_values(by=["published", "paper_id"], ascending=[False, True], kind="mergesort").reset_index(
        drop=True
    )
