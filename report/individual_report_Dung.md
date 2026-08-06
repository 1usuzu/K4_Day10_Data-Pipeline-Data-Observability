# Member Role Report — Day 10: Data Pipeline & Data Observability

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Lưu Xuân Dũng       |
| MSSV               | 2A202601774                  |
| Khóa/Lớp         | K4             |
| Tên nhóm         | B4-2     |
| Vai trò chính    | Pipeline Integrator & Observability                 |
| Repository         | https://github.com/1usuzu/K4_Day10_Data-Pipeline-Data-Observability-B4-2 |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Pipeline Orchestration      | `src/pipelines/corruption_flow.py`           | Settings, Raw/Clean Data          | Báo cáo và chạy end-to-end | Hoàn thành |
| Data Observability      | `src/observability/reporting.py`           | Metrics, Quality Checks          | `corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Xây dựng Web UI Demo | Nhóm trưởng/Khách hàng | Code giao diện FastAPI + Vanilla CSS/JS tại `script/web_api.py` và `index.html` |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Sửa lỗi truyền tham số cho Index | `LocalEmbeddingIndex.build()` | Code hết lỗi TypeError | `python script/run_corruption_flow.py` |
| Bổ sung báo cáo Quality cho phần Repaired | `corruption_flow.py` | Artifact báo cáo tự động đầy đủ 3 pha | Xem file `data/reports/corruption_report.md` |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

File `data/reports/corruption_report.md` được sinh ra tự động để đối chiếu 3 trạng thái dữ liệu (Baseline, Corrupted, Repaired) cho thấy sự sụt giảm và phục hồi của F1 Score.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline ở giai đoạn chạy `run_corruption_flow.py` gặp lỗi `TypeError` do truyền sai thứ tự tham số vào hàm `LocalEmbeddingIndex.build()`, và thiếu cơ chế chạy kiểm định chất lượng (Quality/Freshness) cho dữ liệu Repaired dẫn đến không sinh được báo cáo cuối cùng.

### Cách triển khai

Sửa lại lời gọi hàm `LocalEmbeddingIndex.build()` theo đúng Argument Signature bằng kwargs. Bổ sung các lệnh gọi hàm `run_data_quality_checks` và `build_freshness_report` ngay sau khi nạp lại dữ liệu Repaired, và truyền toàn bộ 8 biến này vào hàm `generate_corruption_report()`.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Raw Data, Repaired Metadata, Metrics           |
| Output                         | `corruption_report.md` |
| Module phụ thuộc             | `src.observability.quality`, `src.observability.reporting`                    |
| Module sử dụng output        | Người dùng (Human Review)                    |
| Điều kiện lỗi cần xử lý | Xử lý lỗi thiếu tham số khi báo cáo hoặc LLM Token lỗi                   |

### Cách xác minh

```bash
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Flow chạy suôn sẻ qua 3 trạng thái: Baseline -> Corrupt -> Repair và sinh ra báo cáo.
- **Kết quả thực tế:** Flow chạy thành công hoàn toàn, không vướng Exception, F1 score hiển thị phục hồi.
- **Artifact/log:** `data/reports/corruption_report.md`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lỗi giao diện chat Streamlit bị trắng ô nhập liệu làm phá hỏng thiết kế Dark Mode, cần một giải pháp khác để Demo cho bắt mắt.
- **Các phương án đã cân nhắc:** Dùng custom CSS hack cho Streamlit, hoặc xây dựng Web App chuẩn từ đầu bằng FastAPI + Vanilla CSS/JS.
- **Phương án đã chọn:** Xây dựng Web App chuẩn bằng FastAPI và HTML/CSS thuần (`script/web_api.py`, `script/static/index.html`).
- **Lý do:** Trade-off thêm thời gian code nhưng đổi lại khả năng kiểm soát giao diện Glassmorphism 100%, Animations xịn xò và không còn bị ghi đè CSS, đem lại trải nghiệm "Wow" khi trình bày.
- **Bằng chứng quyết định phù hợp:** Chạy thử `python -m uvicorn script.web_api:app` và truy cập web thấy giao diện tối ưu.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `TypeError: LocalEmbeddingIndex.build() takes 2 positional arguments but 3 were given`
- **Lệnh hoặc bước tái hiện:** `python script/run_corruption_flow.py`
- **Nguyên nhân gốc:** Hàm `build` của Index bị truyền dư một biến số dạng Positional Argument. Cụ thể là biến `settings.paths.embeddings_json`.
- **Cách xử lý:** Gọi hàm bằng kwargs: `save_path=settings.paths.embeddings_json`.
- **Cách xác minh sau khi sửa:** Chạy lại luồng corruption không còn bắn Exception tại đoạn build vector.
- **Điều học được:** Python rất chặt chẽ về positional args và kwargs, đặc biệt khi kế thừa hoặc dùng `classmethod`.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   Dữ liệu Raw dạng JSON kéo từ API Crossref, sau đó đẩy qua Pipeline Cleaning (Dedupe, Normalize) thành DataFrame Clean. DataFrame này tạo ra cột `text_for_embedding`, sau đó được đưa vào ChromaDB bằng MiniLM để nhúng thành các Vector Index.
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   Test Set có sẵn list Ground-Truth Doc IDs. Khi hỏi câu hỏi, nếu Agent Retrieval lôi ra được ID trùng với mảng Ground-Truth thì Retrieval Hit Rate = 1.0 (True Positive). Nếu câu trả lời chứa thông tin từ tài liệu gốc, Token F1 sẽ cao.
3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   Quality Checks bắt lỗi dữ liệu ở mức tĩnh (missing fields, duplicate IDs, length constraints). Freshness Monitoring đánh giá độ "tươi" của dữ liệu dựa trên chênh lệch thời gian (age_days) so với hiện tại.
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   Để đảm bảo tính công bằng (A/B Testing). Nếu đổi Test Set, sẽ không biết F1 Score giảm là do dữ liệu rác (Corrupted) hay do bộ Test Set thứ hai hóc búa hơn.
5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   Dựa trên file `corruption_report.md` và `repaired_metrics.json`. F1 Score và Judge Accuracy phải hồi phục trở lại mức Baseline ban đầu. Quality Checks không còn bắt lỗi như 'summary_length'.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      1.000 |       0.750 |      1.000 | Giảm khi dữ liệu rác làm mờ nhoè vector |
| `mean_token_f1`      |      0.969 |       0.725 |      0.969 | Giảm mạnh do nhiễu thông tin |
| `judge_accuracy`     |      0.969 |       0.719 |      0.969 | LLM bị mất tự tin hoặc trả lời sai lệch |
| `mean_judge_score`   |      4.875 |       3.875 |      4.875 | Tương đương độ sụt giảm chất lượng câu trả lời |
| Quality checks         |      PASS (giả định) |       FAIL |      PASS (ngoại trừ freshness) | Bắt được lỗi thiếu summary và trùng ID ở Corrupted |
| Freshness status       |      FAIL |       FAIL |      FAIL | Khá cũ do bài báo khoa học tĩnh |

### Kết luận từ số liệu

Hoàn thành hai chuỗi nguyên nhân–bằng chứng sau:

1. **[Data corruption]** (mất summary, tuổi giả mạo, nhét noise token) → **[quality signal thay đổi]** (Báo lỗi FAIL paper_id_unique, summary_length) → **[agent metric thay đổi]** (F1 cắm đầu từ 96.9% xuống 72.5%).
2. **[Repair action]** (Nạp lại từ snapshot raw/clean sạch) → **[quality signal phục hồi]** (hết báo lỗi summary) → **[agent metric phục hồi]** (F1 quay về 96.9%).

**Corruption nào ảnh hưởng rõ nhất và vì sao?**
Việc "Xóa Summary" (Drop Text) ảnh hưởng rõ nhất. Bởi vì RAG phụ thuộc 90% vào Retrieval. Xóa summary làm `text_for_embedding` trống rỗng, từ đó mô hình MiniLM nhúng ra vector vô nghĩa, dĩ nhiên lúc Search không tìm thấy tài liệu, dẫn đến LLM "ảo giác".

**Kết quả nào khác với kỳ vọng ban đầu?**
Freshness lúc nào cũng FAIL (kể cả lúc Baseline). Ban đầu tưởng do code sai, nhưng sau khi kiểm chứng thì phát hiện tuổi của bài báo (age_days) thực tế lớn hơn ngưỡng Freshness, đây là điều bình thường với paper học thuật cũ nhưng lại bị filter.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Garbage In - Garbage Out:** RAG xịn cỡ mấy mà Dữ liệu cấp vào sai/rỗng thì hệ thống chết hoàn toàn.
2. **Tầm quan trọng của Observability:** Nhờ có Quality Checks, ta phát hiện được lỗi dữ liệu (trùng lặp, mất format) kịp thời trước khi nó tàn phá chỉ số LLM ở production.
3. Không bao giờ hard-code API Keys và phải cô lập Provider LLM vào layer riêng.

### Nếu có thêm thời gian

Thêm tính năng Live Data Observability Dashboard lên chính giao diện FastAPI Web UI. Lúc đó người dùng vừa chat nghiệm chứng RAG, vừa xem được biểu đồ Data Quality bên cạnh.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Lưu Xuân Dũng
**Ngày xác nhận:** 2026-08-06
