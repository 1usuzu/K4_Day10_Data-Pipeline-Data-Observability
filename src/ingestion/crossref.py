from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from html import unescape
import os
from pathlib import Path
import re
import time
from typing import Any

import requests

from core.config import Settings
from core.utils import compact_join, normalize_whitespace, read_json, write_json

CROSSREF_API_URL = "https://api.crossref.org/works"
CROSSREF_SELECT_FIELDS = (
    "DOI",
    "title",
    "abstract",
    "author",
    "subject",
    "published",
    "issued",
    "created",
    "indexed",
    "deposited",
    "URL",
    "link",
    "type",
    "container-title",
    "publisher",
)

MIN_SUMMARY_CHARS = 40
REQUEST_TIMEOUT_SECONDS = 30
MAX_RETRIES = 4
BACKOFF_SECONDS = 2.0
RETRY_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
# Nhieu item Crossref khong co abstract va bi `parse_crossref_payload` loai bo,
# nen fetch du ra roi moi cat xuong `max_results`.
ROWS_MULTIPLIER = 3
MAX_ROWS_PER_REQUEST = 100

_TAG_RE = re.compile(r"<[^>]+>")
_ABSTRACT_LABEL_RE = re.compile(r"^\s*abstract\s*[:.-]?\s*", flags=re.IGNORECASE)


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


_RECORD_FIELD_NAMES = tuple(field.name for field in fields(PaperRecord))
_RECORD_LIST_FIELDS = frozenset({"authors", "categories"})


def _clean_text(value: Any) -> str:
    """Bo JATS/HTML tag, unescape entity va gom whitespace ve 1 space."""
    if not isinstance(value, str):
        return ""
    return normalize_whitespace(unescape(_TAG_RE.sub(" ", value)))


def _first_text(value: Any) -> str:
    """Crossref tra ve title/container-title duoi dang list."""
    if isinstance(value, list):
        for item in value:
            text = _clean_text(item)
            if text:
                return text
        return ""
    return _clean_text(value)


def _date_from_parts(node: Any) -> str:
    """`{"date-parts": [[2025, 8, 6]]}` -> `2025-08-06` (thieu thi pad bang 01)."""
    if not isinstance(node, dict):
        return ""
    parts = node.get("date-parts") or []
    if not parts or not isinstance(parts[0], list) or not parts[0]:
        return ""
    values = [int(part) for part in parts[0][:3] if isinstance(part, int)]
    if not values:
        return ""
    year, month, day = (values + [1, 1])[:3]
    return f"{year:04d}-{month:02d}-{day:02d}"


def _pick_date(item: dict, keys: tuple[str, ...]) -> str:
    for key in keys:
        node = item.get(key)
        if isinstance(node, dict) and node.get("date-time"):
            date_time = _clean_text(node["date-time"])
            if date_time:
                return date_time[:10]
        date = _date_from_parts(node)
        if date:
            return date
    return ""


def _parse_authors(item: dict) -> list[str]:
    authors: list[str] = []
    for author in item.get("author") or []:
        if not isinstance(author, dict):
            continue
        name = _clean_text(author.get("name")) or compact_join(
            [_clean_text(author.get("given")), _clean_text(author.get("family"))], sep=" "
        )
        if name and name not in authors:
            authors.append(name)
    return authors


def _parse_categories(item: dict) -> list[str]:
    categories: list[str] = []
    for subject in item.get("subject") or []:
        category = _clean_text(subject)
        if category and category not in categories:
            categories.append(category)
    if not categories:
        fallback = _first_text(item.get("container-title")) or _clean_text(item.get("type"))
        if fallback:
            categories.append(fallback)
    return categories


def _parse_pdf_url(item: dict) -> str:
    links = [link for link in item.get("link") or [] if isinstance(link, dict)]
    for link in links:
        if _clean_text(link.get("content-type")).lower() == "application/pdf":
            url = _clean_text(link.get("URL"))
            if url:
                return url
    for link in links:
        url = _clean_text(link.get("URL"))
        if url:
            return url
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref `/works` payload thanh list `PaperRecord`.

    Bo qua record thieu DOI/title/abstract va de-duplicate theo DOI.
    """
    items = ((payload or {}).get("message") or {}).get("items") or []

    records: list[PaperRecord] = []
    seen_ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue

        doi = _clean_text(item.get("DOI")).lower()
        title = _first_text(item.get("title"))
        summary = _ABSTRACT_LABEL_RE.sub("", _clean_text(item.get("abstract")))
        if not doi or not title or len(summary) < MIN_SUMMARY_CHARS:
            continue
        if doi in seen_ids:
            continue
        seen_ids.add(doi)

        categories = _parse_categories(item)
        published = _pick_date(item, ("published", "issued", "published-online", "published-print", "created"))
        updated = _pick_date(item, ("indexed", "deposited")) or published
        if not published:
            continue

        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=summary,
                authors=_parse_authors(item),
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=published,
                updated=updated,
                abs_url=_clean_text(item.get("URL")) or f"https://doi.org/{doi}",
                pdf_url=_parse_pdf_url(item),
                comment=compact_join(
                    [
                        _clean_text(item.get("type")),
                        _first_text(item.get("container-title")),
                        _clean_text(item.get("publisher")),
                    ]
                ),
            )
        )

    return records


def _user_agent() -> str:
    """Set `CROSSREF_MAILTO` trong .env de vao polite pool cua Crossref."""
    mailto = os.getenv("CROSSREF_MAILTO", "").strip()
    contact = f"; mailto:{mailto}" if mailto else ""
    return f"day10-data-observability-lab/0.1 (+https://api.crossref.org{contact})"


def _retry_after_seconds(response: requests.Response) -> float | None:
    try:
        return float(response.headers.get("Retry-After", ""))
    except ValueError:
        return None


def _request_payload(params: dict) -> dict:
    """GET Crossref voi exponential backoff cho 429/5xx va loi network."""
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        wait_seconds = BACKOFF_SECONDS * attempt
        try:
            response = requests.get(
                CROSSREF_API_URL,
                params=params,
                headers={"User-Agent": _user_agent()},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            last_error = exc
        else:
            if response.status_code not in RETRY_STATUS_CODES:
                response.raise_for_status()
                return response.json()
            last_error = requests.HTTPError(
                f"Crossref tra ve status {response.status_code}", response=response
            )
            wait_seconds = _retry_after_seconds(response) or wait_seconds

        if attempt < MAX_RETRIES:
            time.sleep(wait_seconds)

    raise RuntimeError(f"Khong goi duoc Crossref API sau {MAX_RETRIES} lan thu.") from last_error


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi Crossref, luu raw response + parsed records vao `data/raw/`."""
    params = {
        "query.bibliographic": settings.source_query,
        "filter": settings.source_filter,
        "rows": min(settings.max_results * ROWS_MULTIPLIER, MAX_ROWS_PER_REQUEST),
        "select": ",".join(CROSSREF_SELECT_FIELDS),
    }

    payload = _request_payload(params)
    write_json(settings.paths.raw_api_response, payload)

    records = parse_crossref_payload(payload)[: settings.max_results]
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc snapshot `raw_records_json` va map lai thanh `PaperRecord`."""
    rows = read_json(path)
    if not isinstance(rows, list):
        return []

    records: list[PaperRecord] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        values: dict[str, Any] = {}
        for name in _RECORD_FIELD_NAMES:
            value = row.get(name)
            if name in _RECORD_LIST_FIELDS:
                values[name] = [str(item) for item in value] if isinstance(value, list) else []
            else:
                values[name] = str(value) if value is not None else ""
        if values["paper_id"] and values["title"]:
            records.append(PaperRecord(**values))
    return records
