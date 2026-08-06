# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Phương Thuỳ          |
| MSSV               | 2A202601953                    |
| Khóa/Lớp         | K4        |
| Tên nhóm         | B4 -2    |
| Vai trò chính    | Role 3 - Observability owner |
| Repository         | https://github.com/1usuzu/K4_Day10_Data-Pipeline-Data-Observability.git |
| Ngày hoàn thành | 2026-08-06             |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ------------ |
| Data quality checks | `src/observability/quality.py` - `run_data_quality_checks`, các hàm `_check_*` | Cleaned dataframe từ `data/clean/papers_clean.csv`, corrupted/repaired dataframe, `Settings` | Quality JSON trong `data/quality/`: `baseline-phase-1.json`, `corrupted-phase.json`, `repaired-phase.json` | Hoàn thành |
| Freshness monitoring | `src/observability/quality.py` - `build_freshness_report` | Dataframe có cột `published`, `age_days`, ngưỡng `freshness_threshold_days=180` | Freshness JSON: `freshness_report.json`, `corrupted_freshness.json`, `repaired_freshness.json` | Hoàn thành |
| Markdown reporting | `src/observability/reporting.py` - `generate_phase1_report`, `generate_corruption_report` | Source summary, metrics, quality report, freshness report | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Đối chiếu metrics giữa baseline, corrupted và repaired | Corruption/integration flow trong `src/pipelines/corruption_flow.py` | Xác nhận corrupted làm giảm retrieval/answer metrics và repaired phục hồi về baseline qua `data/results/*_metrics.json` |
| Kiểm tra nội dung report cuối | Reporting và pipeline integration | `phase1_report.md` và `corruption_report.md` khớp với JSON artifact, không chứa secret |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Xây dựng bộ quality checks cho cleaned dataframe | `src/observability/quality.py`, `data/quality/baseline-phase-1.json` | 6 checks: `row_count`, `paper_id_present`, `paper_id_unique`, `title_present`, `summary_length`, `freshness` | Đọc `data/quality/baseline-phase-1.json` |
| Theo dõi freshness dựa trên `published` và `age_days` | `build_freshness_report`, `data/quality/freshness_report.json` | Baseline có latest `2026-07-13`, oldest `2024-01-01`, stale `11/24`, `is_fresh=false` | Đọc `data/quality/freshness_report.json` |
| Tạo báo cáo baseline và comparison từ artifact thật | `src/observability/reporting.py`, `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Báo cáo Markdown thể hiện metrics và quality/freshness status của từng trạng thái | Đọc report Markdown và đối chiếu với `data/results/*_metrics.json` |

Output cụ thể của phần việc là bộ artifact observability trong `data/quality/` và hai báo cáo Markdown trong `data/reports/`. Các artifact này cho thấy corruption tạo thêm lỗi `paper_id_unique`, `summary_length`, tăng stale rows từ 11 lên 13; sau repair, duplicate và short summary được phục hồi, stale rows quay về 11 như baseline.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần observability cần trả lời câu hỏi: dữ liệu sạch, dữ liệu bị corrupt và dữ liệu đã repair có còn đáp ứng contract tối thiểu để phục vụ RAG agent hay không. Nếu retrieval hoặc answer quality giảm, nhóm cần có signal dữ liệu đủ rõ để truy vết nguyên nhân thay vì chỉ nhìn vào điểm agent.

### Cách triển khai

`run_data_quality_checks` nhận một dataframe đã clean và chạy tuần tự các kiểm tra có tính contract:

- `row_count`: dataframe không rỗng.
- `paper_id_present`: không thiếu document ID.
- `paper_id_unique`: không có document ID trùng.
- `title_present`: không thiếu title.
- `summary_length`: summary phải có tối thiểu 40 ký tự.
- `freshness`: `age_days` không vượt quá ngưỡng 180 ngày.

Mỗi check trả về `name`, `passed`, `details`; hàm tổng hợp danh sách `failed_checks`, trạng thái overall và ghi JSON theo `report_name`. `build_freshness_report` tách riêng freshness signal thành latest/oldest published, số stale rows, total rows và `is_fresh`. `reporting.py` không tự tính lại số liệu mà chỉ render từ metrics/quality/freshness artifact để tránh lệch giữa report và dữ liệu nguồn.

### Input, output và contract

| Thành phần | Mô tả |
| ------------------------------ | ------------------------------------------- |
| Input | `pandas.DataFrame` có các cột `paper_id`, `title`, `summary`, `published`, `age_days`; `Settings` chứa `freshness_threshold_days=180` và đường dẫn `data/quality/` |
| Output | JSON report gồm `report_name`, `generated_at`, `row_count`, `checks`, `passed`, `failed_checks`; freshness JSON gồm `latest_published`, `oldest_published`, `stale_rows`, `total_rows`, `is_fresh` |
| Module phụ thuộc | `src/ingestion/cleaning.py` tạo clean schema; `src/core/config.py` cung cấp paths và threshold |
| Module sử dụng output | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `src/observability/reporting.py`, báo cáo trong `data/reports/` |
| Điều kiện lỗi cần xử lý | Thiếu cột bắt buộc, `paper_id` trùng, summary rỗng/quá ngắn, dữ liệu stale, dataframe rỗng |

### Cách xác minh

```bash
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
jq . data/quality/baseline-phase-1.json
jq . data/quality/corrupted-phase.json
jq . data/quality/repaired-phase.json
jq . data/results/baseline_metrics.json
jq . data/results/corrupted_metrics.json
jq . data/results/repaired_metrics.json
```

- **Kết quả mong đợi:** Baseline có quality/freshness artifact; corrupted xuất hiện thêm lỗi duplicate/short summary/freshness; repaired phục hồi duplicate và summary length về baseline.
- **Kết quả thực tế:** Baseline fail `freshness` với `stale_count=11`; corrupted fail `paper_id_unique`, `summary_length`, `freshness` với `stale_count=13`; repaired chỉ còn fail `freshness` với `stale_count=11`, giống baseline.
- **Artifact/log:** `data/quality/*.json`, `data/results/*_metrics.json`, `data/reports/phase1_report.md`, `data/reports/corruption_report.md`; không chứa secret.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần quyết định nên gộp freshness vào overall quality hay tách freshness thành report riêng.
- **Các phương án đã cân nhắc:** Chỉ dùng một quality JSON tổng hợp; hoặc vừa có check `freshness` trong quality JSON vừa tạo freshness report riêng.
- **Phương án đã chọn:** Giữ freshness trong quality checks để overall status phản ánh dữ liệu stale, đồng thời tạo JSON freshness riêng để phân tích ngày mới nhất/cũ nhất và số stale rows.
- **Lý do:** Cách này giúp pipeline vừa có signal pass/fail đơn giản, vừa có chi tiết để giải thích vì sao baseline vẫn fail overall dù các trường ID/title/summary đều hợp lệ.
- **Bằng chứng quyết định phù hợp:** `baseline-phase-1.json` cho biết failed check là `freshness`; `freshness_report.json` giải thích rõ `stale_rows=11/24`, latest `2026-07-13`, oldest `2024-01-01`.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Baseline quality report có `Overall status: FAIL` dù cleaned dataset có 24 records, không thiếu `paper_id`, không trùng ID, không thiếu title và không có summary quá ngắn.
- **Lệnh hoặc bước tái hiện:** Chạy/đọc `data/quality/baseline-phase-1.json` sau phase 1.
- **Nguyên nhân gốc:** Freshness threshold là 180 ngày, trong khi cleaned dataset còn 11 records có `age_days` vượt ngưỡng. Đây là vấn đề freshness thật của nguồn dữ liệu, không phải lỗi code.
- **Cách xử lý:** Giữ trạng thái fail `freshness`, tách freshness report riêng và ghi rõ trong phân tích rằng repaired thành công khi quay về trạng thái baseline, không phải khi mọi check đều pass.
- **Cách xác minh sau khi sửa:** `repaired-phase.json` chỉ còn failed check `freshness`; `repaired_freshness.json` có `stale_rows=11`, bằng baseline.
- **Điều học được:** Observability phải phân biệt lỗi schema/contract với signal chất lượng dữ liệu theo ngưỡng nghiệp vụ; không nên chỉnh report để “đẹp số” nếu artifact đang phản ánh dữ liệu thật.

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu được lấy từ Crossref REST API theo query `agentic retrieval augmented generation large language model`, lưu raw response/records trong `data/raw/`. `cleaning.py` chuẩn hóa text, bỏ record thiếu ID/title/summary/date, tạo `paper_id`, `summary_chars`, `age_days`, `text_for_embedding`; sau đó `LocalEmbeddingIndex` dùng model `sentence-transformers/all-MiniLM-L6-v2` để tạo embedding và Chroma index.
2. Evaluation set được tạo từ tối đa 8 paper đại diện, mỗi paper có 4 loại câu hỏi: `summary`, `authors`, `date`, `categories`, tổng cộng 32 samples. Mỗi câu hỏi giữ `ground_truth` và `ground_truth_doc_ids`; retrieval được tính hit khi document ID đúng xuất hiện trong danh sách retrieved doc IDs.
3. Quality checks kiểm tra contract và tính hợp lệ của dataframe như ID trùng, thiếu title, summary quá ngắn. Freshness monitoring tập trung vào độ mới của dữ liệu dựa trên `published`, `age_days` và ngưỡng 180 ngày; vì vậy freshness có thể fail ngay cả khi schema sạch.
4. Phải dùng cùng test set cho baseline, corrupted và repaired để đảm bảo khác biệt metrics đến từ thay đổi dữ liệu/index, không đến từ thay đổi câu hỏi hoặc ground truth.
5. Repair được xem là thành công khi `data/clean/papers_clean_repaired.*`, `data/embeddings/papers_embeddings_repaired.json`, `data/results/repaired_metrics.json`, `data/quality/repaired-phase.json` và `data/reports/corruption_report.md` cho thấy dữ liệu/metrics quay về baseline. Trong artifact hiện tại, repaired khôi phục `retrieval_hit_rate=1.000`, `mean_token_f1=0.969`, `judge_accuracy=0.938`, `mean_judge_score=4.781`.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | 1.000 | 0.750 | 1.000 | Corruption làm mất/biến dạng context nên retrieval giảm 0.250; repair phục hồi hoàn toàn. |
| `mean_token_f1` | 0.969 | 0.725 | 0.969 | Answer overlap giảm rõ khi summary bị blank/noise và một record mới nhất bị drop. |
| `judge_accuracy` | 0.938 | 0.750 | 0.938 | Judge đánh giá ít câu đúng hơn ở corrupted; repaired quay lại baseline. |
| `mean_judge_score` | 4.781 | 4.031 | 4.781 | Điểm chất lượng câu trả lời giảm 0.750 sau corruption và phục hồi sau repair. |
| Quality checks | FAIL: `freshness` | FAIL: `paper_id_unique`, `summary_length`, `freshness` | FAIL: `freshness` | Corruption tạo thêm duplicate ID và summary quá ngắn; repair loại bỏ hai lỗi này. |
| Freshness status | Stale: `11/24` | Stale: `13/24` | Stale: `11/24` | Freshness không pass ở baseline, nhưng corruption làm stale rows tăng thêm 2 và repair đưa về mức ban đầu. |

### Kết luận từ số liệu

1. `blank_summary`, `inject_summary_noise`, `drop_latest_records`, `add_duplicate_rows` và stale date corruption → quality signal đổi từ chỉ fail `freshness` sang fail thêm `paper_id_unique`, `summary_length`, stale rows tăng từ 11 lên 13 → agent metric giảm: `retrieval_hit_rate` 1.000 xuống 0.750, `mean_token_f1` 0.969 xuống 0.725.
2. Repair bằng cách rebuild dataframe từ raw records tin cậy → duplicate ID và summary ngắn biến mất, stale rows quay từ 13 về 11 → agent metric phục hồi về baseline: `retrieval_hit_rate=1.000`, `mean_token_f1=0.969`, `judge_accuracy=0.938`, `mean_judge_score=4.781`.

Corruption ảnh hưởng rõ nhất là nhóm làm sai nội dung retrieval context: drop latest record, blank summary và noise trong summary. Chúng tác động trực tiếp đến `text_for_embedding` và khả năng lấy đúng document, thể hiện qua `retrieval_hit_rate` giảm xuống 0.750. Duplicate ID và stale date cũng là signal observability quan trọng, nhưng tác động agent nhìn rõ nhất qua retrieval/answer metrics.

Kết quả khác kỳ vọng ban đầu là baseline quality không PASS toàn bộ. Sau khi kiểm tra artifact, nguyên nhân là freshness threshold 180 ngày khiến 11/24 records bị stale. Vì vậy không nên kết luận repair làm quality pass hoàn toàn; kết luận đúng là repair phục hồi dữ liệu về trạng thái baseline.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Data pipeline cần contract rõ từ raw đến clean schema; các trường như `paper_id`, `summary`, `published`, `age_days`, `text_for_embedding` ảnh hưởng trực tiếp đến downstream index và evaluation.
2. Data observability không chỉ là pass/fail; cần đọc chi tiết `details` để biết fail do schema lỗi, duplicate, summary quá ngắn hay freshness threshold.
3. RAG agent rất nhạy với chất lượng dữ liệu đầu vào: chỉ vài corruption có chủ đích cũng đủ làm retrieval và answer quality giảm rõ.

### Nếu có thêm thời gian

Em muốn bổ sung bảng so sánh theo từng `question_type` để biết corruption ảnh hưởng mạnh nhất đến câu hỏi summary, authors, date hay categories. Cải thiện này có thể đo bằng retrieval hit rate, token F1 và judge score tách theo từng nhóm câu hỏi.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Phương Thuỳ
**Ngày xác nhận:** 2026-08-06
