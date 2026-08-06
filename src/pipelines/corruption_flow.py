from __future__ import annotations

import pandas as pd
from core.config import load_settings, require_llm_credentials
from core.utils import write_csv, read_json, now_utc
from ingestion.crossref import load_raw_records
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from retrieval.index import LocalEmbeddingIndex
from evaluation.metrics import evaluate_pipeline
from observability.quality import run_data_quality_checks, build_freshness_report
from observability.reporting import generate_corruption_report


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
        df_corrupted,
        settings,
        settings.paths.corrupted_embeddings_json
    )
    evaluate_pipeline(
        settings=settings,
        index=idx_corrupted,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_quality = run_data_quality_checks(df_corrupted, settings, "Corrupted Phase")
    corrupted_freshness = build_freshness_report(df_corrupted, settings, settings.paths.quality_dir / "corrupted_freshness.json")

    print("--- 4. Repair Dataset ---")
    records = load_raw_records(settings.paths.raw_records_json)
    df_repaired = build_clean_dataframe(records, now_utc())
    write_csv(df_repaired, settings.paths.repaired_clean_csv)
    df_repaired.to_json(settings.paths.repaired_clean_json, orient="records", indent=2, force_ascii=False)

    print("--- 5. Evaluate Repaired ---")
    idx_repaired = LocalEmbeddingIndex.build(
        df_repaired,
        settings,
        settings.paths.repaired_embeddings_json
    )
    evaluate_pipeline(
        settings=settings,
        index=idx_repaired,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )

    repaired_quality = run_data_quality_checks(df_repaired, settings, "Repaired Phase")
    repaired_freshness = build_freshness_report(df_repaired, settings, settings.paths.quality_dir / "repaired_freshness.json")

    print("--- 6. Generate Comparison Report ---")
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    corrupted_metrics = read_json(settings.paths.corrupted_metrics)
    repaired_metrics = read_json(settings.paths.repaired_metrics)
    
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_metrics,
        repaired_metrics=repaired_metrics,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    
    print("Corruption and repair pipeline completed successfully.")
