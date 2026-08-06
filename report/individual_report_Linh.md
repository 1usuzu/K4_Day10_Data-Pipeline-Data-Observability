# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Lê Thị Trúc Linh             |
| MSSV               | 2A202601322                   |
| Khóa/Lớp         | K4              |
| Tên nhóm         | B4-2     |
| Vai trò chính    | Vai trò 5 — Evaluation & Observability |
| Repository         | https://github.com/1usuzu/K4_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06                  |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Test set builder | `src/evaluation/testset.py` — `build_test_set()` | Cleaned dataframe (từ Vai trò 3) | `data/eval/test_set.json` — 32 câu hỏi, 4 loại (summary/authors/date/categories), `ground_truth_doc_ids` lấy từ `paper_id` thật | Hoàn thành |
| Data quality checks | `src/observability/quality.py` — `run_data_quality_checks()`, `build_freshness_report()` | Cleaned/corrupted/repaired dataframe | `data/quality/*.json` (baseline, corrupted, repaired + freshness riêng từng trạng thái) | Hoàn thành |
| Phase 1 report generator | `src/observability/reporting.py` — `generate_phase1_report()` | metrics + quality + freshness + source summary | `data/reports/phase1_report.md` | Hoàn thành |
| Baseline evaluation | Chạy `evaluate_pipeline()` (đã có sẵn từ starter) với index + test set | `papers-baseline` index, `test_set.json` | `data/results/baseline_metrics.json`, `baseline_answers.json` | Hoàn thành |
| Corrupted evaluation & phân tích impact | Chạy `evaluate_pipeline()` trên dataset đã corrupt, đối chiếu với baseline | `papers-corrupted` index, `test_set.json` (không đổi) | `data/results/corrupted_metrics.json`, `corrupted_answers.json` | Hoàn thành |

Test set được khóa từ CP2 và tái sử dụng nguyên vẹn cho cả 3 lần evaluate (baseline/corrupted/repaired) để đảm bảo so sánh công bằng.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Build `papers-baseline`/`papers-corrupted` Chroma index cục bộ khi `data/embeddings/`, `data/chroma/` chưa được push | Vai trò 4 (RAG & agent owner) | Index chạy đúng, verify search/lookup trả kết quả có nguồn trước khi Vai trò 4 push bản chính thức |
| Chạy `corrupt_clean_dataframe()` (code đã có sẵn của Vai trò 3) để tạo `papers_clean_corrupted.csv/json` khi chưa có artifact | Vai trò 3 (Cleaning & corruption owner) | Corruption log tái lập giống 100% (byte-for-byte) với bản Vai trò 3 tự chạy và commit sau đó |
| Phát hiện và báo lỗi import (`from src.xxx`) + sai chữ ký hàm (`LocalEmbeddingIndex.build()`, `evaluate_pipeline()`, `generate_phase1_report()`) trong `src/pipelines/phase1.py` và `corruption_flow.py` | Vai trò 1 (Pipeline integrator) | `corruption_flow.py` đã được sửa đúng theo báo cáo và chạy thành công end-to-end |
| Giải quyết merge conflict khi nhánh `dev` merge vào `main` (`corrupted-phase.json`), phục hồi collection `papers-baseline` bị thiếu trong `chroma.sqlite3` chung của nhóm | Toàn nhóm | Merge sạch, verify lại metrics tái lập khớp 100%, không ảnh hưởng baseline |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Implement `build_test_set()` | `src/evaluation/testset.py` | `data/eval/test_set.json` | Đọc file, kiểm tra 32/32 `id` unique, 0 dòng `ground_truth` rỗng, 0 dòng `ground_truth_doc_ids` không khớp `paper_id` thật trong clean data |
| Implement quality + freshness checks | `src/observability/quality.py` | `data/quality/phase1-baseline.json`, `corrupted-phase.json`, `repaired-phase.json` + 3 freshness report riêng | Chạy trực tiếp bằng Python, đối chiếu `corruption_log.json` với đúng check bị fail tương ứng |
| Implement `generate_phase1_report()` | `src/observability/reporting.py` | `data/reports/phase1_report.md` | Sinh lại report từ artifact thật, diff với bản đã lưu → identical (trừ timestamp) |
| Baseline & corrupted evaluation, tìm case cụ thể | `data/results/baseline_*.json`, `corrupted_*.json` | Metrics + answers chi tiết | So sánh answer của câu `q001`/`q019` giữa 2 trạng thái, truy vết nguyên nhân qua `retrieved_doc_ids` |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Case `q001` (câu hỏi về paper "JADE-Plus"): ở baseline trả lời đúng bằng summary thật; sau corruption, paper này bị `drop_latest_records` xóa khỏi index, agent fallback sang paper khác — mà paper đó lại chính là nạn nhân của `blank_summary`, dẫn đến `answer: ""`, `token_f1: 0.0`, `judge.score: 1/5`. Đây là bằng chứng trực tiếp cho thấy 2 loại lỗi dữ liệu độc lập có thể cộng hưởng làm hỏng hoàn toàn 1 câu trả lời.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần của tôi phải trả lời được 2 câu hỏi cho toàn bộ pipeline: (1) test set và metric có đo đúng chất lượng retrieval/answer không, và (2) khi dữ liệu bị lỗi (có chủ đích), hệ thống có **phát hiện được** (quality/freshness check) và **đo được ảnh hưởng thật** (metric giảm) hay không.

### Cách triển khai

Chọn 8 paper đại diện bằng cách sort theo `paper_id` (deterministic, không dùng random) để test set tái lập được giữa các lần chạy — quan trọng vì phải giữ nguyên xuyên suốt baseline/corrupted/repaired. Với mỗi paper, sinh 4 câu hỏi (summary/authors/date/categories) dùng đúng cụm từ khớp với logic routing trong `qa.py` (`"Who authored"`, `"When was"`, `"What categories"`), bọc title trong dấu nháy đơn để kích hoạt exact-lookup. Quality checks gồm 6 check độc lập, mỗi check trả `passed` + `details` có số liệu cụ thể để làm evidence, không chỉ true/false. Report gom 4 nguồn dữ liệu thật thành markdown, không hardcode số liệu.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Cleaned/corrupted dataframe (cột `paper_id`, `title`, `summary`, `authors_joined`, `categories_joined`, `published`, `age_days`, `text_for_embedding`) |
| Output                         | `test_set.json` (list dict), quality/freshness JSON report, `phase1_report.md` |
| Module phụ thuộc             | `src/ingestion/cleaning.py` (Vai trò 3), `src/retrieval/index.py` (Vai trò 4), `src/core/config.py` (Vai trò 1) |
| Module sử dụng output        | `src/evaluation/metrics.py` (`evaluate_pipeline` đọc `test_set_path`), `src/pipelines/*.py` (orchestration) |
| Điều kiện lỗi cần xử lý | Dataframe rỗng/thiếu cột → trả `passed: False` kèm lý do thay vì crash; `summary` là `NaN` sau CSV round-trip (xem mục 6) |

### Cách xác minh

```bash
.venv/Scripts/python.exe -c "
import sys; sys.path.insert(0, 'src')
from core.config import load_settings
from retrieval.index import LocalEmbeddingIndex
from evaluation.metrics import evaluate_pipeline

settings = load_settings()
index = LocalEmbeddingIndex.load(settings)
bundle = evaluate_pipeline(settings, index, settings.paths.eval_testset,
    settings.paths.baseline_metrics, settings.paths.baseline_answers)
print(bundle.summary)
"
```

- **Kết quả mong đợi:** metrics baseline tái lập lại đúng số đã commit.
- **Kết quả thực tế:** khớp 100% (`retrieval_hit_rate=1.0`, `mean_token_f1=0.969`, `judge_accuracy=0.969`, `mean_judge_score=4.875`) — verify bằng so sánh dict trực tiếp trong Python.
- **Artifact/log:** `data/results/baseline_metrics.json`, `data/results/baseline_answers.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần quyết định cách chọn mẫu paper để sinh test set — chọn ngẫu nhiên hay có quy tắc cố định.
- **Các phương án đã cân nhắc:**
  1. `df.sample(n, random_state=42)` — random nhưng seed cố định.
  2. `df.sort_values("paper_id").head(n)` — hoàn toàn deterministic, không dùng random.
- **Phương án đã chọn:** Phương án 2 (sort + head).
- **Lý do:** Test set phải dùng lại y hệt cho cả baseline/corrupted/repaired. Sort theo khóa tự nhiên (`paper_id`) loại bỏ rủi ro lệch kết quả giữa các môi trường/phiên bản thư viện khác nhau giữa các thành viên trong nhóm, so với `random_state` vốn vẫn phụ thuộc implementation của numpy/pandas.
- **Bằng chứng quyết định phù hợp:** Khi Vai trò 3 tự chạy `corrupt_clean_dataframe()` độc lập và commit `corruption_log.json`, tôi chạy lại cùng hàm trên máy mình và log ra **giống hệt byte-for-byte** — xác nhận toàn bộ pipeline deterministic xuyên suốt nhóm.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `run_data_quality_checks()` báo `summary_length: PASS` (`too_short_count: 0`) trên dataset corrupted, dù corruption log ghi rõ có 1 record bị `blank_summary`.
- **Lệnh hoặc bước tái hiện:**
  ```bash
  .venv/Scripts/python.exe -c "
  import pandas as pd
  df = pd.read_csv('data/clean/papers_clean_corrupted.csv')
  print(df['summary'].astype(str).str.len().isna().sum())  # -> 1, thay vì 0
  "
  ```
- **Nguyên nhân gốc:** Khi ghi `summary = ""` ra CSV rồi đọc lại bằng `pandas.read_csv()`, pandas mặc định chuyển ô rỗng thành `NaN` (kiểu `float`). `.astype(str).str.len()` trên `NaN` gốc trả về `NaN` (không phải chuỗi `"nan"` dài 3 ký tự), và `NaN < 40` trong pandas luôn cho `False` — khiến check bỏ sót đúng loại lỗi nó được viết ra để bắt.
- **Cách xử lý:** Thêm `.fillna("")` trước khi đo độ dài: `df["summary"].fillna("").astype(str).str.len()`.
- **Cách xác minh sau khi sửa:** Chạy lại trên baseline (vẫn `PASS`, không regression) và corrupted (chuyển sang `FAIL`, `too_short_count: 1`) — đúng kỳ vọng. Đối chiếu thêm với `corrupted-phase.json` do team tự chạy độc lập sau đó — khớp 100%.
- **Điều học được:** Không nên tin phép so sánh số học trực tiếp trên cột có thể chứa `NaN` sau CSV round-trip; luôn `fillna()` hoặc `.isna()` tường minh trước khi so sánh ngưỡng.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   `fetch_source_records()` gọi Crossref API, lưu raw response + parse thành `PaperRecord` (DOI làm `paper_id` ổn định) vào `data/raw/`. `build_clean_dataframe()` chuẩn hóa title/summary/authors/categories, tính `age_days`, tạo `text_for_embedding`. `LocalEmbeddingIndex.build()` dùng MiniLM encode `text_for_embedding` thành vector, nạp vào ChromaDB collection riêng theo từng trạng thái (`papers-baseline`/`papers-corrupted`/`papers-repaired`).
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   `test_set.json` chứa câu hỏi sinh từ dữ liệu clean thật, mỗi câu có `ground_truth_doc_ids` lấy trực tiếp từ `paper_id` của paper được hỏi. `retrieval_hit = True` nếu bất kỳ ID nào agent retrieve được nằm trong `ground_truth_doc_ids` — đo retrieval độc lập với chất lượng câu trả lời cuối cùng.
3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   Quality checks kiểm tra tính toàn vẹn cấu trúc tại 1 thời điểm (`row_count`, `paper_id` null/unique, `title` null, `summary` length). Freshness monitoring kiểm tra tính thời sự — dữ liệu có cũ (`age_days` vượt ngưỡng) so với hiện tại hay không. Một dataset có thể pass hết quality nhưng vẫn fail freshness (đúng trường hợp baseline: cấu trúc sạch nhưng 11/24 record cũ hơn 180 ngày).
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để chênh lệch metric phản ánh đúng ảnh hưởng của thay đổi dữ liệu, không lẫn với việc bộ câu hỏi khác nhau. Nếu test set đổi, không thể tách bạch "metric giảm vì data xấu" hay "vì câu hỏi khó hơn".
5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   `repaired_metrics.json` phục hồi về đúng số của `baseline_metrics.json` (thực tế đo được đúng 100%: `1.0/0.969/0.969/4.875` cả hai bên), VÀ `repaired-phase.json` (quality) không còn fail các check mà `corrupted-phase.json` từng fail (`paper_id_unique`, `summary_length`). Nếu chỉ metric phục hồi mà quality signal còn xấu thì chưa thể coi là repair thành công triệt để.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |     1.000 |     0.750 |    1.000 | Giảm 25 điểm % khi corrupt, phục hồi hoàn toàn sau repair |
| `mean_token_f1`      |     0.969 |     0.725 |    0.969 | Giảm mạnh nhất về tỉ lệ tương đối (~25%), phục hồi hoàn toàn |
| `judge_accuracy`     |     0.969 |     0.719 |    0.969 | Đồng pha với retrieval_hit_rate, không có fallback giả (đã kiểm tra `judge.reasoning`) |
| `mean_judge_score`   |     4.875 |     3.875 |    4.875 | Giảm đúng 1.0 điểm/5, phục hồi hoàn toàn |
| Quality checks         | FAIL (freshness) | FAIL (`paper_id_unique`, `summary_length`, `freshness`) | FAIL (freshness) | Repair loại bỏ đúng 2/3 lỗi cấu trúc do corruption gây ra; `freshness` fail ở cả 3 trạng thái vì là đặc điểm vốn có của raw data, không phải do corruption tạo ra |
| Freshness status       | Not fresh (11/24 stale) | Not fresh (13/24 stale) | Not fresh (11/24 stale) | Corrupted tăng thêm 2 stale row (`make_stale_publication_date`); repaired về đúng số stale của baseline |

### Kết luận từ số liệu

Hoàn thành hai chuỗi nguyên nhân–bằng chứng sau:

1. **`blank_summary` (corrupt paper `10.2196/preprints.106157`) + `drop_latest_records`** → **`summary_length` FAIL** → **q001 trả lời rỗng hoàn toàn** (agent fallback từ paper bị xóa sang đúng paper bị blank summary).
2. **Repair (rebuild từ raw source)** → **`paper_id_unique`/`summary_length` chuyển từ FAIL sang PASS** → **cả 4 metric phục hồi về đúng 100% giá trị baseline**.

Corruption nào ảnh hưởng rõ nhất và vì sao?

Tổ hợp `drop_latest_records` + `blank_summary` ảnh hưởng rõ nhất, vì nó không chỉ làm giảm điểm trung bình mà tạo ra 1 câu trả lời hỏng hoàn toàn (rỗng), khác với `truncate_title`/`inject_summary_noise` chỉ làm nhiễu nhẹ mà không phá hỏng khả năng trả lời.

Kết quả nào khác với kỳ vọng ban đầu?

Tôi dự đoán `row_count` sẽ giảm sau corruption (vì có `drop_latest_records`), nhưng thực tế `row_count` giữ nguyên 24 vì `add_duplicate_rows` (+1) triệt tiêu đúng bằng `drop_latest_records` (-1). Đã kiểm tra kỹ để không kết luận nhầm "dataset an toàn về số lượng" — con số ổn định là trùng hợp cơ học, không phản ánh chất lượng dữ liệu thật.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** Một orchestration script đúng cú pháp import vẫn có thể sai hoàn toàn về logic nếu chữ ký hàm giữa các module không khớp — cần test tích hợp thực sự (gọi hàm end-to-end), không chỉ đọc code từng file riêng lẻ.
2. **Data quality/observability:** Phép so sánh số học trên cột có thể chứa `NaN` (đặc biệt sau CSV round-trip) là nguồn lỗi âm thầm rất dễ bỏ sót — quality check tưởng đúng logic vẫn có thể im lặng bỏ sót đúng loại lỗi nó được thiết kế để bắt.
3. **Ảnh hưởng của data lên RAG agent:** Chất lượng agent không suy giảm tuyến tính theo từng loại lỗi — một số loại lỗi cộng hưởng (xóa record + blank summary) có thể phá hỏng hoàn toàn 1 câu trả lời, trong khi loại khác (truncate title) gần như không ảnh hưởng đến metric tổng.

### Nếu có thêm thời gian

Mở rộng quality checks để bắt được cả `truncate_title` và `inject_summary_noise` (hiện không bị check nào của tôi phát hiện, vì không làm field null/rỗng mà chỉ sai nội dung) — ví dụ thêm check phát hiện token lặp bất thường hoặc title ngắn bất thường so với phân phối chung. Đo cải thiện bằng cách chạy lại trên `corrupted-phase.json` và xác nhận `failed_checks` tăng đúng theo số corruption operation phát hiện được trong log.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Linh
**Ngày xác nhận:** 2026-08-06
