from __future__ import annotations

import pandas as pd
from src.core.config import load_settings, require_llm_credentials
from src.core.utils import now_utc, write_csv, read_json
from src.ingestion.crossref import fetch_source_records, load_raw_records
from src.ingestion.cleaning import build_clean_dataframe
from src.retrieval.index import LocalEmbeddingIndex
from src.evaluation.testset import build_test_set
from src.evaluation.metrics import evaluate_pipeline
from src.observability.quality import run_data_quality_checks, build_freshness_report
from src.observability.reporting import generate_phase1_report


def main() -> None:
    settings = load_settings()
    require_llm_credentials(settings)

    print("--- 1. Ingestion ---")
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(settings.paths.raw_records_json)

    print("--- 2. Cleaning ---")
    df_clean = build_clean_dataframe(records, now_utc())
    write_csv(df_clean, settings.paths.clean_csv)
    df_clean.to_json(settings.paths.clean_json, orient="records", indent=2, force_ascii=False)

    print("--- 3. Build Index ---")
    index = LocalEmbeddingIndex.build(
        settings, 
        df_clean, 
        settings.baseline_collection_name, 
        settings.paths.embeddings_json
    )

    print("--- 4. Evaluation Set ---")
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        test_set = build_test_set(df_clean, settings.paths.eval_testset)
    else:
        test_set = read_json(settings.paths.eval_testset)

    print("--- 5. Evaluate Baseline ---")
    evaluate_pipeline(
        settings, 
        test_set, 
        index, 
        settings.paths.baseline_answers, 
        settings.paths.baseline_metrics
    )

    print("--- 6. Observability ---")
    run_data_quality_checks(df_clean, settings, "Baseline Phase 1")
    build_freshness_report(df_clean, settings, settings.paths.freshness_report)
    generate_phase1_report(settings, settings.paths.baseline_report)
    
    print("Baseline pipeline completed successfully.")
