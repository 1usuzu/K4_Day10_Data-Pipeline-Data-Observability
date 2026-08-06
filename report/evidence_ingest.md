# Evidence — Role 2 (Ingestion)

Ngày: 2026-08-06

## 1. Kiểm tra `paper_id` xuyên suốt raw → clean

Lệnh đã chạy:

```bash
python -c "
import json
raw = json.load(open('data/raw/crossref_records.json', encoding='utf-8'))
clean = json.load(open('data/clean/papers_clean.json', encoding='utf-8'))
print('raw count:', len(raw))
print('clean count:', len(clean))
print('raw unique ids:', len(set(r['paper_id'] for r in raw)))
print('clean unique ids:', len(set(r['paper_id'] for r in clean)))
print('ids in raw but not clean:', len(set(r['paper_id'] for r in raw) - set(r['paper_id'] for r in clean)))
"
```

Kết quả:

- `raw count = 24`, `clean count = 24` → không mất record nào ở bước clean.
- `raw unique paper_id = 24`, `clean unique paper_id = 24` → không trùng ID ở cả hai phía.
- `ids in raw but not clean = 0` → mọi `paper_id` (= DOI, lowercase) trong raw đều còn nguyên trong clean.
- Mẫu đối chiếu: `paper_id = 10.1007/s10278-026-02086-9` — title và summary khớp nguyên văn giữa `data/raw/crossref_records.json` và `data/clean/papers_clean.json`.

**Kết luận:** đoạn raw → clean của pipeline hiện tại giữ toàn vẹn `paper_id`. Chưa phát hiện record bị mất hay đổi ID âm thầm.

## 2. Đoạn clean → index

Cập nhật 2026-08-06 (sau khi pull `phase1.py`):

- `phase1.py` và `corruption_flow.py` khi pull về bị lỗi import (`from src.core...` thay vì `from core...`, không khớp `pyproject.toml` có `package-dir = {"" = "src"}`) và gọi sai signature `LocalEmbeddingIndex.build(...)` (thừa tham số `collection_name`, sai thứ tự). Đã sửa cả hai file để chạy được (xem git diff `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`).
- Sau khi sửa: `uv run python script/run_phase1.py` chạy qua được bước Ingestion → Cleaning → Build Index (Chroma collection `papers-baseline` build thành công bằng MiniLM embeddings).
- **Blocker hiện tại:** dừng ở bước 4 (Evaluation Set) vì `src/evaluation/testset.py:27` vẫn `raise NotImplementedError("Student task: implement test set builder.")` — thuộc phần việc owner `eval`, chưa pull/implement. Do đó chưa chạy hết pipeline để lấy `baseline_metrics.json`.
- Việc còn lại cho CP2 khi `testset.py` xong: lấy cùng `paper_id` mẫu (`10.1007/s10278-026-02086-9`), query metadata trong collection `papers-baseline` (`src/retrieval/index.py`), xác nhận `paper_id`/`title` khớp với clean record — index đã tồn tại nên bước này có thể làm ngay, không cần chờ testset.

### Cập nhật 2026-08-06 (lần 2) — `testset.py` đã pull xong

- `uv run python script/run_phase1.py` giờ chạy qua được Ingestion → Cleaning → Build Index → Evaluation Set → **Evaluate Baseline**.
- Có bug wiring khác phải sửa: `evaluate_pipeline(...)` trong `phase1.py`/`corruption_flow.py` gọi sai thứ tự tham số so với signature thật trong `src/evaluation/metrics.py` (`settings, index, test_set_path, metrics_output_path, answers_output_path`). Đã sửa lại cho khớp.
- Kết quả `data/results/baseline_metrics.json`: `samples=32, retrieval_hit_rate=1.0, mean_token_f1=0.969, judge_accuracy=0.938, mean_judge_score=4.78`.
- **Blocker mới:** dừng ở bước 6 (Observability → report) vì `src/observability/reporting.py::generate_phase1_report()` (và `generate_corruption_report()`) vẫn `raise NotImplementedError` — đây là code thật sự chưa viết (không phải lỗi wiring), thuộc phần việc owner `observe`. `run_data_quality_checks` và `build_freshness_report` (cùng file `quality.py`) đã implement và chạy OK (`data/quality/baseline-clean.json`, `data/quality/freshness_report.json` đã có).

### Cập nhật 2026-08-06 (lần 3) — verify `data/eval/test_set.json`

- `src/evaluation/testset.py` sinh 32 câu hỏi (8 paper đại diện × 4 loại: summary/authors/date/categories) từ `data/clean/papers_clean.json`.
- Đối chiếu toàn bộ `ground_truth_doc_ids` trong test set với tập `paper_id` của clean dataset: **0/32 ID không hợp lệ** — không có ground-truth ID bịa, mọi ID đều truy vết được về đúng record clean (và từ đó về đúng raw record theo mục 1 ở trên).

## 4. CP4/CP5 — Corruption có kiểm soát (`ingest`)

Cập nhật 2026-08-06 (lần 4), sau khi `src/ingestion/corruption.py` được implement và sửa `evaluate_pipeline`/report-call trong `corruption_flow.py`:

- `uv run python script/run_corruption_flow.py` chạy qua Load Baseline → Corrupt → Evaluate Corrupted → Repair → Evaluate Repaired; dừng ở bước cuối vì `generate_corruption_report()` (`src/observability/reporting.py`) vẫn `NotImplementedError` — cùng blocker owner `observe` như phase1.
- **Raw source integrity:** `git status data/raw/` sạch, không có thay đổi trong suốt flow.
- **Lineage/repair evidence:** `corruption_log.json` ghi record bị drop là `paper_id = 10.1007/s10278-026-02086-9`. Verify: có trong `data/raw/crossref_records.json`, bị thiếu trong `data/clean/papers_clean_corrupted.json`, xuất hiện lại đúng nguyên trong `data/clean/papers_clean_repaired.json` sau khi repair từ raw.
- **Không refetch source:** đọc code `corruption_flow.py` — chỉ gọi `load_raw_records()` (đọc snapshot cũ), không gọi `fetch_source_records()` ở bất kỳ bước nào.
- **Impact đo được** (`data/results/*_metrics.json`):

| Metric | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| retrieval_hit_rate | 1.0 | 0.75 | 1.0 |
| judge_accuracy | 0.969 | 0.75 | 0.9375 |
| mean_token_f1 | 0.969 | 0.725 | 0.969 |
| mean_judge_score | 4.875 | 4.0625 | 4.78125 |

Corruption làm giảm rõ rệt cả 4 chỉ số; repair phục hồi gần về baseline.

## 3. Nguồn dữ liệu — không refresh giữa chừng

- Baseline hiện tại dùng snapshot cố định: `data/raw/crossref_response.json` + `data/raw/crossref_records.json` (24 records, DOI làm `paper_id`).
- Chưa gọi lại `fetch_source_records()` / Crossref API kể từ khi các file raw này được tạo. Giữ nguyên snapshot này cho tới khi baseline CP3 được chốt xong.
