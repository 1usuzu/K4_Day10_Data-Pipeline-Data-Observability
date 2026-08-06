from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json

MIN_DOCUMENTS = 3
MAX_REPRESENTATIVE_PAPERS = 8
QUESTION_TYPES = ("summary", "authors", "date", "categories")


def _build_question(question_type: str, row: pd.Series) -> dict[str, str]:
    title = row["title"]
    if question_type == "summary":
        return {
            "question": f"What is this paper about: '{title}'?",
            "ground_truth": first_sentence(row["summary"]),
        }
    if question_type == "authors":
        return {
            "question": f"Who authored '{title}'?",
            "ground_truth": row["authors_joined"],
        }
    if question_type == "date":
        return {
            "question": f"When was '{title}' published?",
            "ground_truth": row["published"],
        }
    if question_type == "categories":
        return {
            "question": f"What categories does '{title}' belong to?",
            "ground_truth": row["categories_joined"],
        }
    raise ValueError(f"Unknown question_type: {question_type}")


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Tao evaluation set tu cleaned dataframe: N paper dai dien x 4 loai cau hoi."""
    if len(df) < MIN_DOCUMENTS:
        raise ValueError(f"Can it nhat {MIN_DOCUMENTS} document de tao test set, hien co {len(df)}.")

    sample_size = min(MAX_REPRESENTATIVE_PAPERS, len(df))
    representative = df.sort_values("paper_id").head(sample_size)

    test_set: list[dict[str, Any]] = []
    counter = 1
    for _, row in representative.iterrows():
        for question_type in QUESTION_TYPES:
            built = _build_question(question_type, row)
            test_set.append(
                {
                    "id": f"q{counter:03d}",
                    "question_type": question_type,
                    "question": built["question"],
                    "ground_truth": built["ground_truth"],
                    "ground_truth_doc_ids": [row["paper_id"]],
                }
            )
            counter += 1

    write_json(output_path, test_set)
    return test_set
