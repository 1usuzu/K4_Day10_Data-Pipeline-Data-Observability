from __future__ import annotations

import pandas as pd
from src.core.config import load_settings, require_llm_credentials
from src.core.utils import write_csv, read_json, now_utc
from src.ingestion.crossref import load_raw_records
from src.ingestion.cleaning import build_clean_dataframe
from src.ingestion.corruption import corrupt_clean_dataframe
from src.retrieval.index import LocalEmbeddingIndex
from src.evaluation.metrics import evaluate_pipeline
from src.observability.quality import run_data_quality_checks
from src.observability.reporting import generate_corruption_report


def main() -> None:
    settings = load_settings()
    require_llm_credentials(settings)

    print("--- 1. Load Baseline ---")
    # Verify baseline metrics exists before running Phase 2
    if not settings.paths.baseline_metrics.exists():
        raise FileNotFoundError("Baseline artifacts not found. Please run phase1 first.")
    
    df_clean = pd.read_csv(settings.paths.clean_csv)
    test_set = read_json(settings.paths.eval_testset)

    print("--- 2. Corrupt Dataset ---")
    df_corrupted = corrupt_clean_dataframe(df_clean, settings.paths.corruption_log)
    write_csv(df_corrupted, settings.paths.corrupted_clean_csv)
    df_corrupted.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2, force_ascii=False)

    print("--- 3. Evaluate Corrupted ---")
    idx_corrupted = LocalEmbeddingIndex.build(
        settings, 
        df_corrupted, 
        settings.corrupted_collection_name, 
        settings.paths.corrupted_embeddings_json
    )
    evaluate_pipeline(
        settings, 
        test_set, 
        idx_corrupted, 
        settings.paths.corrupted_answers, 
        settings.paths.corrupted_metrics
    )
    run_data_quality_checks(df_corrupted, settings, "Corrupted Phase")

    print("--- 4. Repair Dataset ---")
    records = load_raw_records(settings.paths.raw_records_json)
    df_repaired = build_clean_dataframe(records, now_utc())
    write_csv(df_repaired, settings.paths.repaired_clean_csv)
    df_repaired.to_json(settings.paths.repaired_clean_json, orient="records", indent=2, force_ascii=False)

    print("--- 5. Evaluate Repaired ---")
    idx_repaired = LocalEmbeddingIndex.build(
        settings, 
        df_repaired, 
        settings.repaired_collection_name, 
        settings.paths.repaired_embeddings_json
    )
    evaluate_pipeline(
        settings, 
        test_set, 
        idx_repaired, 
        settings.paths.repaired_answers, 
        settings.paths.repaired_metrics
    )

    print("--- 6. Generate Comparison Report ---")
    generate_corruption_report(settings, settings.paths.comparison_report)
    
    print("Corruption and repair pipeline completed successfully.")
