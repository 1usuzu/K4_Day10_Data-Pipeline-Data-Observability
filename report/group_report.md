# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4              |
| Tên nhóm         | B4-2     |
| Repository         | https://github.com/1usuzu/K4_Day10_Data-Pipeline-Data-Observability-B4-2 |
| Ngày hoàn thành | 2026-08-06               |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Lưu Xuân Dũng | 2A202601774 | Pipeline Integrator & UI | `src/pipelines/corruption_flow.py`, `script/web_api.py` |
| 2 | Đạt | 2A202602014 | Ingestion & Cleaning | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py` |
| 3 | Linh | 2A202601322 | Embedding & Indexing | `src/retrieval/index.py`, `LocalEmbeddingIndex` |
| 4 | Trang | 2A202601960 | Evaluation & Agent | `src/retrieval/agent.py`, `src/evaluation/ragas_eval.py` |
| 5 | Nguyễn Phương Thuỳ | 2A202601953 | Observability | `src/observability/quality.py`, `reporting.py` |

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành toàn bộ End-to-End Pipeline cho dự án RAG Agentic, từ bước thu thập dữ liệu (Crossref), làm sạch, nhúng vector (ChromaDB), đánh giá (Ragas/Custom Eval) đến giám sát chất lượng (Data Observability) và xây dựng Web UI tương tác.

Baseline pipeline đã tạo ra các artifact cốt lõi: `papers_clean.json`, file nhúng `papers_embeddings.json`, ChromaDB index và các báo cáo `baseline_metrics.json`. 

Trong quá trình mô phỏng lỗi (Corruption Flow), kịch bản "Xóa trắng Summary" (Blank Summary) gây hậu quả nghiêm trọng nhất, làm sập hoàn toàn khả năng tìm kiếm của RAG, đẩy F1 Score từ 96.9% tụt thê thảm xuống 72.5%. 

Nhờ hệ thống Quality Checks, các đứt gãy này bị bắt trúng (FAIL ở check summary_length và uniqueness). Cơ chế Repair sau đó đã kéo lại dữ liệu từ snapshot sạch, giúp các chỉ số F1 và Accuracy phục hồi ngoạn mục về mức ban đầu. Blocker duy nhất còn sót lại là "Freshness Check" luôn báo lỗi do bản chất các bài báo học thuật thường được xuất bản từ nhiều năm trước.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> raw response/raw records (JSON)
    -> cleaning và data modeling (Dedupe, Normalize)
    -> embedding (MiniLM) + ChromaDB index
    -> evaluation baseline (Hit Rate, F1)
    -> quality/freshness reports (Observability)
    -> corruption (Bug Injections)
    -> re-index và re-evaluate
    -> repair từ dữ liệu nguồn (Snapshot Restore)
    -> comparison report (corruption_report.md)
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref API | Fetch data, pagination   | `raw/crossref_records.json` | Đạt |
| Cleaning          | Raw JSON       | Dedupe, Format datetime     | `clean/papers_clean.json` | Đạt |
| Embedding/index   | Clean JSON     | Embed MiniLM, Build DB       | `Chroma DB`, `embeddings.json` | Linh |
| Evaluation        | Agent + DB       | Đo Hit Rate, Token F1     | `results/baseline_metrics.json` | Trang |
| Observability     | Clean JSON       | Check schema, null, length | `quality/quality_report.json` | Thuỳ |
| Corruption/repair | Clean JSON       | Inject noise, delete fields    | `results/corruption_log.json` | Dũng |
| Orchestration     | Toàn bộ Pipeline | Trigger theo sequence           | `corruption_report.md`        | Dũng |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | openrouter         |
| `LLM_MODEL`                | google/gemini-pro         |
| Embedding model              | all-MiniLM-L6-v2         |
| Số lượng Crossref records | 24         |
| Retrieval `top_k`           | 4         |
| Freshness threshold          | 30 days         |
| Random seed, nếu có        | 42         |

### Lệnh cài đặt

```bash
uv sync
```

### Lệnh chạy

Baseline:

```bash
uv run python script/run_phase1.py
```

Corruption flow:

```bash
uv run python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái                                    | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công | 2026-08-06                  | `data/reports/phase1_report.md` |
| Corruption flow   | Thành công | 2026-08-06                  | `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | api.crossref.org/works |
| Query/filter                | Agentic AI, LLM Multi-agent                  |
| Số record nhận được    | 24                         |
| Cơ chế retry/backoff      | Exponential Backoff (3 retries)                       |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| paper_id | string         | Có | Định danh bài báo (DOI) | Bỏ qua record        |
| title | string         | Có | Tên bài báo | Báo lỗi Quality Check        |
| summary | string         | Có | Tóm tắt (Abstract) | Báo lỗi Quality Check        |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Số record bị tác động | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Loại bỏ HTML tags trong Abstract | Format/Validity  |              24 | Check `papers_clean.json` |
| Lowercase toàn bộ DOI | Consistency                  |              24 | Check `papers_clean.json` |

Giải thích cách nhóm tạo `text_for_embedding`, document ID và `age_days`:
- `text_for_embedding`: Nối chuỗi "Title: ... \n Summary: ... \n Authors: ..." để nhúng vector nguyên khối.
- Document ID: Dùng chính DOI của bài báo để làm định danh duy nhất trong ChromaDB.
- `age_days`: Lấy ngày hiện tại trừ đi cột `published` để tính tuổi đời dữ liệu bằng đơn vị ngày.

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 8                 |
| Các `question_type`                    | direct_factual, comparison                  |
| Ground-truth document ID                 | Hardcode DOI trong `test_set.json`     |
| Embedding model                          | all-MiniLM-L6-v2                  |
| Vector store/collection                  | papers-baseline                 |
| Retrieval `top_k`                       | 4                   |
| LLM provider/model                       | OpenRouter (Gemini Pro)                   |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` |

Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:
Để đảm bảo môi trường A/B Testing công bằng. Nếu đổi câu hỏi ở bộ test, ta sẽ không xác định được nguyên nhân F1 Score giảm là do dữ liệu Database bị rác hay do bộ câu hỏi mới quá hóc búa. Giữ nguyên Test Set giúp cô lập biến số data.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái |
| ------------------------ | -------------------------------------- | ------------ |
| Raw response/records     | `data/raw/`                          | Có |
| Cleaned dataset          | `data/clean/`                        | Có |
| Embedding manifest/index | `data/embeddings/`                   | Có |
| Evaluation set           | `data/eval/`                         | Có |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có |
| Quality/freshness        | `data/quality/`                      | Có |
| Baseline report          | `data/reports/phase1_report.md`      | Có |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` |     1.000 | Tìm trúng 100% tài liệu kỳ vọng  |
| `mean_token_f1`      |     0.969 | Câu trả lời của AI trùng khớp 96.9% với ground truth |
| `judge_accuracy`     |     0.969 | LLM Judge đánh giá độ chính xác rất cao |
| `mean_judge_score`   |     4.875 | Gần đạt điểm tuyệt đối 5/5 |

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline      | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| `paper_id_unique` | Uniqueness       | 100% unique         | PASS | `quality_report_baseline.json`   |
| `summary_length` | Completeness       | > 10 chars         | PASS | `quality_report_baseline.json`   |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | `papers_clean.json`            |
| Ngưỡng freshness         | 30 days                         |
| Trạng thái baseline      | FAIL (Stale)               |
| Lý do                     | Dữ liệu báo khoa học thường xuất bản từ vài tháng đến vài năm trước, tuổi đời `age_days` > 30 nên luôn bị đánh cờ FAIL. |

## 9. Corruption scenarios và repair

| Corruption         | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair   |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| Xóa sạch Summary | Đưa cột summary về rỗng  |          1 | Báo lỗi `summary_length`              | Gây mất vector context, F1 giảm mạnh     | Khôi phục snapshot |
| Giả mạo tuổi Data | Đổi published về năm 2000  |          1 | Freshness báo FAIL cực mạnh              | Thấy rõ giới hạn của stale data     | Khôi phục snapshot |

Corruption log:
- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Ghi log đầy đủ 6 hành động tiêm lỗi dữ liệu.

Giải thích cách repair:
Thay vì tìm và vá từng dòng lỗi (chi phí cao và rủi ro bỏ sót), cơ chế Repair ở bài Lab lấy lại bản Snapshot (dữ liệu sạch ban đầu) và Re-Index lại ChromaDB từ con số 0. Đây là cách làm triệt để nhất để Roll-back hệ thống.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   |      1.000 |       0.750 |      1.000 |                      -0.250 |             +0.250 | Phục hồi hoàn hảo |
| `mean_token_f1`        |      0.969 |       0.725 |      0.969 |                      -0.244 |             +0.244 | Phục hồi hoàn hảo |
| `judge_accuracy`       |      0.969 |       0.719 |      0.969 |                      -0.250 |             +0.250 | Phục hồi hoàn hảo |
| Quality checks pass/fail |      PASS |       FAIL |      PASS |                      FAIL |             PASS | Observability hoạt động tốt |
| Freshness status         |      FAIL |       FAIL |      FAIL |                      0 |             0 | Bản chất data cũ |

Nêu ít nhất hai kết luận có quan hệ nhân quả được hỗ trợ bởi artifacts:
1. Xóa Summary (Data corruption) → Lỗi `summary_length` xuất hiện trong `quality_report.json` → `retrieval_hit_rate` giảm còn 0.75 do không tìm thấy tài liệu.
2. Trigger Repair (Action) → Hệ thống hết lỗi `summary_length` → RAG tìm lại được tài liệu và đẩy `mean_token_f1` lên 0.969 trở lại.

## 11. Vấn đề tích hợp quan trọng

Mô tả một vấn đề phát sinh khi ghép các module trong pipeline:
- **Triệu chứng:** Bị lỗi `TypeError` khi gọi hàm `LocalEmbeddingIndex.build()`.
- **Nguyên nhân:** Truyền dư tham số positional cho một classmethod trong Python.
- **Cách xử lý:** Đổi sang truyền bằng `kwargs` (ví dụ `save_path=...`).
- **Cách xác minh:** Chạy `python script/run_corruption_flow.py` hết lỗi văng Exception.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Evaluation dùng ID cố định | Không chấp nhận tài liệu mới hay hơn | Nâng cấp lên LLM-as-a-judge để tự động chấm điểm nội dung thay vì check ID. |
| DB không xóa dòng cũ | Bị phình to dung lượng và rác dữ liệu | Tích hợp ChromaDB `delete_collection` trước khi Build hoặc dùng CDC Upsert. |
| Tool `lookup` quá cứng nhắc | Gõ sai 1 chữ là lỗi | Bổ sung thuật toán Fuzzy Search hoặc ElasticSearch. |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
