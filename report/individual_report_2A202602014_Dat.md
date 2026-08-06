# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Ngô Lưu Quốc Đạt             |
| MSSV               | 2A202602014                     |
| Khóa/Lớp         | K4              |
| Tên nhóm         | B4-2     |
| Vai trò chính    | Người phụ trách Ingestion                 |
| Repository         | K4_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Raw data ingestion từ Crossref | `src/ingestion/crossref.py` (`fetch_source_records`, `parse_crossref_payload`, `load_raw_records`); `src/core/config.py` (đổi `source_filter` sang cửa sổ `from-update-date`/`until-update-date`) | Crossref REST API (`query.bibliographic`, `filter`, `select` theo `Settings`) | `data/raw/crossref_response.json` (raw payload), `data/raw/crossref_records.json` (24 `PaperRecord`, `paper_id` = DOI lowercase) | Hoàn thành |
| CP2 traceability audit (`paper_id` xuyên suốt raw → clean → index) | `report/cp2_evidence_ingest.md`; sửa wiring bug (sai import `src.`, sai signature `LocalEmbeddingIndex.build`/`evaluate_pipeline`) trong `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` | `data/raw/*.json`, `data/clean/papers_clean.json`, Chroma collection `papers-baseline` | `report/cp2_evidence_ingest.md` (đối chiếu 24/24 `paper_id` khớp raw↔clean); baseline pipeline chạy được tới `data/results/baseline_metrics.json` (`retrieval_hit_rate=1.0`, `judge_accuracy=0.969`) | Một phần — báo cáo `phase1_report.md` chưa sinh vì `src/observability/reporting.py::generate_phase1_report` chưa được owner `observe` implement |
| CP4/CP5 corruption lineage audit | `report/cp2_evidence_ingest.md` (mục 4); verify raw source không đổi (`git status data/raw/`), verify record bị corrupt/xoá phục hồi đúng từ raw | `data/raw/crossref_records.json`, `data/results/corruption_log.json`, `data/clean/papers_clean_corrupted.json`, `data/clean/papers_clean_repaired.json` | Bằng chứng: `paper_id = 10.1007/s10278-026-02086-9` bị `drop_latest_records` ở bước corrupt, xuất hiện lại nguyên vẹn ở bước repair; xác nhận `corruption_flow.py` không gọi `fetch_source_records()` (không refetch source) | Hoàn thành (audit); riêng `data/reports/corruption_report.md` chưa sinh vì cùng lý do `generate_corruption_report` chưa implement |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| [Debug/tích hợp/tài liệu] | [Tên hoặc module] | [Kết quả và bằng chứng] |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Fetch + parse Crossref, lưu raw snapshot | `src/ingestion/crossref.py` | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` (24 records, dedupe theo DOI, retry/backoff cho 429/5xx) | `uv run python script/run_phase1.py` (bước "--- 1. Ingestion ---") + kiểm tra `len(json.load(...)) == 24` |
| Audit `paper_id` xuyên suốt raw → clean → index → test set | `data/raw/crossref_records.json`, `data/clean/papers_clean.json`, `data/eval/test_set.json`, Chroma `papers-baseline` | `report/cp2_evidence_ingest.md`: 24/24 `paper_id` khớp raw↔clean, 0/32 `ground_truth_doc_ids` sai lệch | Script Python đối chiếu tập `paper_id` giữa 2 file JSON (lệnh ghi trong `report/cp2_evidence_ingest.md`) |
| Audit lineage/repair sau corruption | `data/results/corruption_log.json`, `data/clean/papers_clean_corrupted.json`, `data/clean/papers_clean_repaired.json` | Xác nhận record `10.1007/s10278-026-02086-9` bị drop rồi phục hồi đúng từ raw; raw source không đổi trong suốt flow | `git status data/raw/` (không có thay đổi) + so sánh `paper_id` có/không có mặt qua 3 file JSON |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

`data/raw/crossref_records.json` là artifact gốc mà toàn bộ pipeline phụ thuộc vào — mọi `paper_id` (DOI) xuất hiện trong `data/clean/`, `data/eval/test_set.json`, metadata trong Chroma collection `papers-baseline`, và cuối cùng là `data/results/baseline_metrics.json` đều truy ngược được về đúng record trong file này. Đây cũng là artifact tôi dùng làm "điểm khôi phục" (recovery point) trong bước repair ở CP5/CP6: khi `corrupt_clean_dataframe()` xoá record `10.1007/s10278-026-02086-9`, bước repair đọc lại chính file raw này và tái tạo đúng record đó trong `papers_clean_repaired.json`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần của tôi là điểm khởi đầu của toàn bộ pipeline: lấy metadata công bố khoa học thật (không bịa dữ liệu) từ Crossref REST API, chuẩn hoá thành một schema ổn định (`PaperRecord`), và đảm bảo mỗi record có một khoá định danh (`paper_id`) không đổi để các bước sau (clean, index, eval, quality) có thể join/tra cứu ngược lại nguồn gốc.

### Cách triển khai

- Gọi `GET https://api.crossref.org/works` với `query.bibliographic`, `filter=from-update-date:...,until-update-date:...` và `select` giới hạn field cần dùng, có retry/backoff theo cấp số nhân (tối đa 4 lần) cho status 429/500/502/503/504, tôn trọng header `Retry-After` nếu Crossref trả về.
- Parse payload: bỏ item thiếu `DOI`/`title`/`abstract`, hoặc `abstract` ngắn hơn 40 ký tự; dedupe theo DOI (lowercase) ngay trong lúc parse.
- `paper_id = DOI` (lowercase) — dùng làm khoá ổn định vì DOI là định danh duy nhất, bất biến theo chuẩn học thuật, không phụ thuộc vào cách Crossref sắp xếp response.
- Ngày `published`/`updated` được trích từ nhiều field khả dụng (`published`, `issued`, `published-online`, `published-print`, `created`, `indexed`, `deposited`) theo thứ tự ưu tiên, vì không phải record nào cũng có đủ tất cả các trường ngày.
- Ghi cả raw response gốc (`crossref_response.json`) lẫn record đã parse (`crossref_records.json`) — raw response gốc dùng làm bằng chứng nguồn khi cần tra ngược lỗi ở các bước sau.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `Settings` (`source_query`, `source_filter`, `max_results`, `select` fields) từ `core/config.py`; response JSON từ Crossref `/works` |
| Output                         | `list[PaperRecord]` (`paper_id, title, summary, authors, categories, primary_category, published, updated, abs_url, pdf_url, comment`); ghi ra `data/raw/crossref_response.json` và `data/raw/crossref_records.json` |
| Module phụ thuộc             | `core.config.Settings`, `core.utils` (`compact_join`, `normalize_whitespace`, `read_json`/`write_json`) |
| Module sử dụng output        | `ingestion.cleaning.build_clean_dataframe` (qua `load_raw_records`), `pipelines.phase1`, `pipelines.corruption_flow` (bước repair) |
| Điều kiện lỗi cần xử lý | Crossref trả 429/5xx → retry với backoff, hết `MAX_RETRIES` thì raise `RuntimeError`; item thiếu DOI/title/abstract hoặc abstract quá ngắn → loại khỏi kết quả, không raise lỗi toàn cục |

### Cách xác minh

```bash
uv run python script/run_phase1.py
python -c "import json; print(len(json.load(open('data/raw/crossref_records.json', encoding='utf-8'))))"
```

- **Kết quả mong đợi:** Bước "--- 1. Ingestion ---" chạy không lỗi; `data/raw/crossref_records.json` có 24 record, mỗi record có `paper_id` là DOI hợp lệ, không trùng.
- **Kết quả thực tế:** Đúng như mong đợi — 24/24 record, `paper_id` unique cả ở raw lẫn sau khi qua `cleaning.py` (đối chiếu chi tiết trong `report/cp2_evidence_ingest.md`).
- **Artifact/log:** `data/raw/crossref_response.json`, `data/raw/crossref_records.json`, `report/cp2_evidence_ingest.md` (không chứa secret).

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần chọn `source_filter` cho query Crossref để giới hạn tập dữ liệu ingest, đồng thời tạo được dữ liệu có ý nghĩa để test freshness monitoring ở các bước sau.
- **Các phương án đã cân nhắc:**
  1. `from-pub-date:{from_date},has-abstract:true` — lọc theo ngày xuất bản (chỉ có cận dưới) và để Crossref tự lọc record có abstract.
  2. `from-update-date:{from_date},until-update-date:{until_date}` — lọc theo thời điểm Crossref cập nhật/deposit record, có cả cận dưới và cận trên; việc lọc abstract chuyển hẳn vào logic parse (`MIN_SUMMARY_CHARS`).
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** `published date` trên Crossref không hoàn toàn đáng tin (nhiều record cập nhật/deposit trễ so với ngày công bố in trên giấy), và không có cận trên nên kết quả giữa các lần chạy dễ trôi. `update-date` với cả `from`/`until` cho một cửa sổ thời gian cố định, tái lập được (reproducible) — đúng tinh thần "không refresh source giữa chừng làm baseline thay đổi" ở CP2. Đồng thời việc lọc `has-abstract` để nằm trong code parse (thay vì để API tự lọc) giúp logic lọc dữ liệu chỉ nằm ở một chỗ, dễ audit hơn khi có record bị loại.
- **Bằng chứng quyết định phù hợp:** Sau khi đổi filter, toàn bộ 24 record thu được đều pass được điều kiện abstract ≥ 40 ký tự (0 record bị loại vì thiếu abstract ở bước clean). Đồng thời, `freshness_report.json` cho thấy 11/24 record có `age_days` > 180 ngày (stale) — chứng tỏ cửa sổ theo update-date rộng hơn theo published-date thuần tuý, tạo ra dữ liệu "vừa mới vừa cũ" thực tế để bài lab có ý nghĩa khi test freshness monitoring (nếu lọc quá chặt theo pub-date, mọi record sẽ luôn fresh và check freshness trở nên vô nghĩa).

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** [Che toàn bộ secret trước khi ghi.]
- **Lệnh hoặc bước tái hiện:** [Lệnh/bước.]
- **Nguyên nhân gốc:** [Root cause, không chỉ mô tả triệu chứng.]
- **Cách xử lý:** [Thay đổi cụ thể.]
- **Cách xác minh sau khi sửa:** [Lệnh và kết quả.]
- **Điều học được:** [Bài học kỹ thuật.]

Nếu chưa xử lý xong:

- **Phạm vi bị ảnh hưởng:** [Module/artifact.]
- **Những gì đã loại trừ:** [Các giả thuyết đã kiểm tra.]
- **Bước tiếp theo:** [Hành động có thể kiểm chứng.]

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Crossref → vector index:** `fetch_source_records()` gọi `GET /works` với query/filter cấu hình sẵn, lưu raw response gốc và list `PaperRecord` (khoá `paper_id` = DOI) vào `data/raw/`. `build_clean_dataframe()` chuẩn hoá text, dedupe theo `paper_id`, tính `age_days`, ghép `text_for_embedding`, lưu ra `data/clean/`. `LocalEmbeddingIndex.build()` encode `text_for_embedding` bằng MiniLM, đẩy vào Chroma collection (`papers-baseline`/`papers-corrupted`/`papers-repaired`) kèm metadata (`paper_id`, `title`, `published`, ...) và ghi manifest JSON mô tả collection đó.
2. **Evaluation set & ground-truth doc IDs:** `build_test_set()` chọn 8 paper đại diện từ clean dataframe, sinh 4 loại câu hỏi (summary/authors/date/categories) mỗi paper; `ground_truth_doc_ids` chính là `paper_id` của paper đó. Khi evaluate, agent retrieve top-k từ index, so `retrieved_doc_ids` với `ground_truth_doc_ids` để tính `retrieval_hit_rate`, so câu trả lời với `ground_truth` để tính `token_f1` và điểm LLM-judge.
3. **Quality checks vs freshness monitoring:** quality checks (`run_data_quality_checks`) kiểm tra tính toàn vẹn cấu trúc tại một thời điểm (row count, `paper_id` có mặt/unique, title có mặt, độ dài summary) — giống kiểm tra schema/snapshot. Freshness monitoring (`build_freshness_report`) đo "dữ liệu có còn mới không" dựa trên `published`/`age_days` so với ngưỡng (180 ngày) — một dữ liệu có thể pass hết quality check nhưng vẫn "stale" về mặt thời gian, và ngược lại.
4. **Vì sao dùng chung test set:** Nếu câu hỏi/ground truth đổi giữa baseline, corrupted, repaired thì chênh lệch metric có thể do đổi câu hỏi chứ không phải do corruption/repair — phá vỡ quan hệ nhân quả cần chứng minh. Dùng chung một `test_set.json` cố định đảm bảo mọi khác biệt về metric chỉ đến từ khác biệt về dữ liệu.
5. **Repair thành công dựa trên:** (a) bằng chứng lineage — record bị corrupt/xoá phải xuất hiện lại đúng trong repaired dataset khi build lại từ raw (đã verify với `paper_id = 10.1007/s10278-026-02086-9`); và (b) `repaired_metrics.json` phải quay lại gần bằng `baseline_metrics.json` trên cùng test set — không chỉ "file tồn tại" mà số liệu phải chứng minh được sự phục hồi.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |     1.0 |      0.75 |     1.0 | Giảm đúng bằng tỷ lệ record bị corrupt (6/24 ≈ 25%), phục hồi 100% sau repair |
| `mean_token_f1`      |    0.969 |     0.725 |    0.969 | Giảm mạnh nhất trong các metric — nhạy với `blank_summary`/`inject_summary_noise` vì so trực tiếp nội dung câu trả lời |
| `judge_accuracy`     |    0.969 |     0.75 |   0.9375 | Phục hồi gần hoàn toàn nhưng không tuyệt đối 1:1 với baseline — hợp lý vì LLM-judge có biến động giữa các lần gọi |
| `mean_judge_score`   |    4.875 |    4.0625 |  4.78125 | Cùng xu hướng với judge_accuracy |
| Quality checks         | FAIL (`freshness`) | FAIL (`paper_id_unique`, `summary_length`, `freshness`) | FAIL (`freshness`, ad-hoc verify) | Corrupted fail thêm 2 check mới đúng như log corruption mô tả (`add_duplicate_rows`, `blank_summary`); freshness fail ở cả 3 vì bản chất filter ingestion theo update-date window, không phải do corruption |
| Freshness status       | stale_rows=11/24 | stale_rows=13/24 | stale_rows=11/24 (ad-hoc verify) | Corrupted tăng thêm 2 stale row (`drop_latest_records` bỏ 1 record mới nhất + `make_stale_publication_date` set 1 record về năm 2000); repaired quay lại đúng con số baseline |

### Kết luận từ số liệu

1. **Data corruption → quality/freshness signal thay đổi → agent metric thay đổi:** `corrupt_clean_dataframe()` xoá record mới nhất, làm rỗng/nhiễu 2 summary, cắt ngắn 1 title, làm cũ 1 ngày xuất bản, và thêm 1 dòng trùng `paper_id` → quality check `paper_id_unique` và `summary_length` chuyển từ PASS sang FAIL, `freshness` stale_rows tăng 11→13 → `retrieval_hit_rate` giảm 1.0→0.75 (mất hẳn 1 document + nội dung 2 document khác bị hỏng làm sai hướng retrieval), `judge_accuracy`/`mean_token_f1` giảm theo vì câu trả lời agent dựa trên context bị hỏng.
2. **Repair → quality/freshness signal phục hồi → agent metric phục hồi:** đọc lại `data/raw/crossref_records.json` (không đổi trong suốt flow) và chạy lại `build_clean_dataframe()` từ đầu → `freshness_report` quay lại đúng `stale_rows=11/24` như baseline, mọi `paper_id` bị mất được khôi phục → `retrieval_hit_rate` về đúng 1.0, `judge_accuracy`/`mean_token_f1` phục hồi gần bằng baseline (không tuyệt đối 100% vì LLM-judge có yếu tố ngẫu nhiên).

Corruption nào ảnh hưởng rõ nhất và vì sao?

`drop_latest_records` (xoá hẳn 1 paper khỏi index) và `blank_summary` ảnh hưởng rõ nhất, vì cả hai đánh trực tiếp vào nội dung dùng để retrieve: xoá record khiến 4 câu hỏi liên quan paper đó chắc chắn miss (`retrieval_hit_rate` không thể đạt), còn `blank_summary` làm `text_for_embedding` của record đó mất phần nội dung quan trọng nhất, khiến semantic search khó match đúng câu hỏi về summary của paper đó. Ngược lại, `truncate_title` và `add_duplicate_rows` ít ảnh hưởng metric hơn vì title chỉ là một phần nhỏ trong `text_for_embedding` và duplicate không xoá thông tin nào.

Kết quả nào khác với kỳ vọng ban đầu?

Ban đầu tôi kỳ vọng **baseline** phải pass hết mọi quality/freshness check (vì chưa corrupt gì). Thực tế `data/quality/baseline-phase-1.json` cho thấy baseline fail check `freshness` (11/24 record stale) ngay từ đầu. Tôi đã kiểm tra và xác nhận đây không phải bug: do quyết định ở mục 5 dùng cửa sổ `update-date` (rộng hơn `published-date`) cho `source_filter`, một số record có ngày xuất bản (`published`) cũ hơn 180 ngày vẫn lọt vào vì chúng mới được Crossref cập nhật/deposit gần đây — đúng theo thiết kế, không phải lỗi ingestion.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về data pipeline:** một khoá định danh ổn định (`paper_id` = DOI) phải được chốt và giữ nguyên xuyên suốt raw → clean → index → eval; chỉ cần một module đổi format khoá (vd. đổi hoa/thường, đổi field) là toàn bộ lineage audit và ground-truth mapping sụp đổ.
2. **Về data quality/observability:** quality check (đúng schema, unique key) và freshness monitoring (dữ liệu có còn mới không) là hai lớp độc lập — dữ liệu có thể "sạch" về cấu trúc nhưng vẫn "cũ" về thời gian, cần đo riêng cả hai thay vì gộp chung một khái niệm "dữ liệu tốt".
3. **Về ảnh hưởng của data đến RAG agent:** corruption chỉ trên 6/24 record (25%) đã kéo `retrieval_hit_rate` giảm đúng 25 điểm phần trăm — chứng minh được quan hệ nhân quả rõ ràng giữa chất lượng dữ liệu nguồn và chất lượng câu trả lời của agent, thay vì chỉ suy đoán định tính.

### Nếu có thêm thời gian

Sẽ thêm structured logging cho từng lần gọi Crossref (số lần retry thực tế, status code gặp phải, thời gian chờ backoff) ngay trong `data/raw/crossref_response.json` hoặc một manifest riêng, thay vì chỉ in ra console. Đo cải thiện bằng cách so sánh số lần phải retry giữa các lần fetch khác nhau và có audit trail đầy đủ khi cần debug lý do một lần ingest bị thiếu record so với lần trước.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Ngô Lưu Quốc Đạt
**Ngày xác nhận:** 2026-08-06
