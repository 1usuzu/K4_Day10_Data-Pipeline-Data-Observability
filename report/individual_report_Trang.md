# Member Role Report — Day 10: Data Pipeline & Data Observability

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Thị Huyền Trang             |
| MSSV               | 2A202601960                     |
| Khóa/Lớp         | K4              |
| Tên nhóm         | B4-2     |
| Vai trò chính    | Vai trò 4: RAG & Agent Owner                 |
| Repository         | https://github.com/1usuzu/K4_Day10_Data-Pipeline-Data-Observability.git |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| ChromaDB Indexing  | `src/retrieval/index.py` | CSV chứa dữ liệu bài báo đã làm sạch (`papers_clean.csv`) | Thư mục cơ sở dữ liệu vector Chroma (`data/chroma/`), File nhúng manifest (`papers_embeddings.json`) | Hoàn thành |
| Retrieval & Search | `src/retrieval/index.py` (hàm `search`, `lookup`) | Câu truy vấn (Query) của người dùng | Danh sách top-k tài liệu liên quan nhất (`SearchResult`) | Hoàn thành |
| RAG Agent & Tools  | `src/retrieval/agent.py` | Câu hỏi của người dùng và Chỉ mục vector | Câu trả lời có đối chiếu ngữ cảnh thực tế | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Không có | Không có | Không có |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Lập chỉ mục 3 phiên bản dữ liệu | `src/retrieval/index.py` | `data/embeddings/papers_embeddings.json` (cả bản `corrupted` và `repaired`) | Chạy lệnh kiểm thử của Vai trò 4 `script/demo_role4.py` |
| Tìm kiếm tương đồng & chính xác | `src/retrieval/index.py` (hàm `search`, `lookup`) | Trả về chuẩn xác tài liệu liên quan dựa trên độ tương đồng Cosine | Lệnh tìm kiếm ngữ cảnh in ra kết quả DOI đúng |
| Tích hợp Agent sử dụng Tool | `src/retrieval/agent.py` | Agent tự động gọi Tool tìm kiếm trước khi trả lời | Khởi chạy Agent qua tệp kiểm nghiệm |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Khi chạy thử nghiệm so sánh 3 trạng thái chỉ mục (Baseline, Corrupted, Repaired), mô hình của Vai trò 4 đã chỉ ra điểm số tương đồng (Similarity Score) của tài liệu cao nhất cho câu hỏi mẫu `"large language models agentic retrieval"` giảm từ **0.6087** (ở Baseline) xuống còn **0.6087** (nhưng bị mất các tài liệu mới nhất do bị Drop trong quá trình Corrupted) và đã phục hồi hoàn toàn lại sau khâu sửa lỗi.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Vai trò 4 chịu trách nhiệm xây dựng bộ nhớ kiến thức (Knowledge Base) cho RAG Agent. Vấn đề là phải chuyển đổi dữ liệu dạng văn bản thô của các bài báo học thuật thành các biểu diễn vector (embeddings), lưu trữ hiệu quả để có thể tìm kiếm nhanh chóng theo cả ý nghĩa ngữ nghĩa (Semantic Search - Cosine Similarity) lẫn tìm kiếm chính xác (Exact Lookup - theo Tiêu đề/DOI), từ đó cung cấp ngữ cảnh đúng cho LLM sinh câu trả lời factual.

### Cách triển khai

1.  **Nhúng vector (Embedding)**: Sử dụng mô hình nhúng `all-MiniLM-L6-v2` từ thư viện `sentence-transformers` thông qua lớp `MiniLMEmbeddings` để biểu diễn trường `text_for_embedding` (đã được gộp thông tin Tiêu đề, Tóm tắt, Tác giả, Ngày xuất bản) thành vector 384 chiều.
2.  **Cơ sở dữ liệu Vector**: Khởi tạo `chromadb.PersistentClient` ghi dữ liệu cục bộ vào thư mục `data/chroma`. Thiết lập cấu hình tìm kiếm HNSW với độ đo khoảng cách `cosine`.
3.  **Tìm kiếm tương đồng (search)**: Chuyển câu truy vấn của người dùng thành vector nhúng, sau đó dùng ChromaDB thực hiện so khớp và trả về top-K tài liệu có khoảng cách cosine nhỏ nhất (được chuyển đổi thành Similarity Score: `1.0 - distance`).
4.  **Tìm kiếm chính xác (lookup)**: Duy trì một bảng băm (hashmap) ánh xạ tiêu đề viết thường và DOI của tài liệu để lấy trực tiếp thông tin gốc với độ phức tạp $O(1)$ mà không cần qua mô hình embedding.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Pandas DataFrame chứa dữ liệu làm sạch (`papers_clean.csv`) |
| Output                         | Chỉ mục vector lưu trong ChromaDB và tệp manifest nhúng JSON (`papers_embeddings.json`) |
| Module phụ thuộc             | Dữ liệu làm sạch từ Vai trò 3 (`data/clean/papers_clean.csv`) |
| Module sử dụng output        | Hệ thống đánh giá của Vai trò 5 (`metrics.py`), tệp điều phối của Vai trò 1 (`phase1.py`) |
| Điều kiện lỗi cần xử lý | Lỗi tranh chấp tệp tin SQLite (file lock) khi tạo và truy cập đồng thời nhiều chỉ mục trong cùng một tiến trình Python. Được giải quyết bằng cách viết thêm cơ chế bộ đệm kết nối client (`_client_cache`) dùng chung một instance duy nhất. |

### Cách xác minh

```bash
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe script/demo_role4.py
```

*   **Kết quả mong đợi:** Lập chỉ mục thành công cả 3 trạng thái. Câu truy vấn mẫu trả về đúng tài liệu liên quan, chỉ mục Baseline không bị ảnh hưởng (mutated) khi tạo chỉ mục lỗi.
*   **Kết quả thực tế:** 
    ```
    === Testing State: 1. BASELINE (Clean) ===
    Loaded 24 papers from papers_clean.csv
    Building/Loading index 'papers-baseline'...
    Index built successfully in: papers_embeddings.json
    Running search query: 'large language models agentic retrieval'
      [1] Paper ID: 10.2139/ssrn.6713979
          Title: A Survey of Agentic GraphRAG...
          Similarity Score: 0.6087
    
    === Verify baseline index is not mutated ===
    Reloading baseline index from manifest...
    Verified baseline collection name is: papers-baseline
    Baseline still returns paper: A Survey of Agentic GraphRAG: From Retrieval-augme...
    Baseline index is safe and intact!
    ```
*   **Artifact/log:** `data/embeddings/papers_embeddings.json`, `data/embeddings/papers_embeddings_corrupted.json`, `data/embeddings/papers_embeddings_repaired.json`.

## 5. Một quyết định kỹ thuật quan trọng

*   **Bối cảnh:** Khi chạy thử nghiệm so sánh 3 trạng thái dữ liệu (Baseline, Corrupted, Repaired) trong cùng một chương trình kiểm thử, hệ thống ném ra lỗi `InternalError: Error creating hnsw segment reader: Nothing found on disk` tại khâu nạp lại chỉ mục do tranh chấp luồng đọc/ghi của ChromaDB Persistent Client.
*   **Các phương án đã cân nhắc:**
    *   *Phương án 1*: Chia nhỏ kịch bản chạy ra thành các tệp tin script Python độc lập để hệ điều hành tự động giải phóng tài nguyên khi tiến trình kết thúc.
    *   *Phương án 2*: Tạo cơ chế Bộ đệm/Singleton kết nối Client (`_client_cache`) trực tiếp trong lớp `LocalEmbeddingIndex` để đảm bảo trong cùng một tiến trình Python chỉ có duy nhất một kết nối an toàn đến database SQLite.
*   **Phương án đã chọn:** Phương án 2.
*   **Lý do:** Phương án 2 ưu việt hơn vì giữ cho mã nguồn kiểm thử và các pipelines lớn (`corruption_flow.py`) được gọn gàng trong một file điều phối duy nhất, tăng khả năng bảo trì (maintainability) và tránh lỗi ghi đè dữ liệu bất ngờ khi chạy tích hợp end-to-end.
*   **Bằng chứng quyết định phù hợp:** Sau khi áp dụng cơ chế bộ đệm client, script `demo_role4.py` chạy lập chỉ mục và truy vấn liên tục qua 3 phiên bản dữ liệu mà không gặp bất kỳ lỗi xung đột SQLite hay HNSW segment nào.

## 6. Một lỗi hoặc blocker đã xử lý

*   **Triệu chứng/lỗi nguyên văn:**
    ```
    TypeError: LocalEmbeddingIndex.build() takes from 3 to 4 positional arguments but 5 were given
    ```
*   **Lệnh hoặc bước tái hiện:** `.\.venv\Scripts\python.exe script/run_phase1.py` sau khi kéo code mới của cả nhóm.
*   **Nguyên nhân gốc:** Các thành viên Vai trò 3 và Vai trò 5 khi viết tệp điều phối `phase1.py` đã gọi hàm lập chỉ mục bị sai lệch thứ tự tham số: `LocalEmbeddingIndex.build(settings, df_clean, ...)` trong khi định nghĩa gốc của hàm trong thư viện Vai trò 4 yêu cầu `build(df_clean, settings, ...)`.
*   **Cách xử lý:** Thay vì yêu cầu nhóm sửa lại làm phát sinh xung đột Git (conflict) khó kiểm soát, tôi đã nâng cấp trực tiếp hàm `build` của Vai trò 4 thành hàm nhận tham số linh hoạt (`*args`, `**kwargs`) và tự động kiểm tra xem tham số đầu tiên có phải là `pd.DataFrame` hay không để tự động hoán đổi vị trí của `settings` và `df` một cách an toàn.
*   **Cách xác minh sau khi sửa:** Chạy lại luồng Pha 1, chương trình vượt qua khâu lập chỉ mục thành công trơn tru.
*   **Điều học được:** Khi phát triển hệ thống cộng tác nhóm, cần thiết kế API của các module cốt lõi có độ linh hoạt (robustness) cao để tránh bị đổ vỡ hệ thống khi tích hợp chéo.

## 7. Hiểu biết về luồng end-to-end

1.  **Dữ liệu đi từ Crossref đến vector index**: Dữ liệu thô (raw JSON) được tải từ Crossref API về -> chuyển qua khâu làm sạch (xử lý lỗi Unicode, chuẩn hóa ngày tháng, gộp trường) -> lưu thành tệp CSV sạch -> Cột `text_for_embedding` được trích xuất -> Mô hình `all-MiniLM-L6-v2` mã hóa văn bản thành vector nhúng -> Đẩy vào ChromaDB và liên kết với metadata tương ứng -> Lưu trữ bền vững (persistent) trên ổ đĩa.
2.  **Đo chất lượng bằng Evaluation Set**: Bộ testset chứa các câu hỏi thực tế đi kèm câu trả lời chuẩn (ground truth) và danh sách DOI chuẩn (`ground_truth_doc_ids`). Khi kiểm thử, câu hỏi được chuyển vào RAG Agent -> Agent tìm tài liệu liên quan trong ChromaDB -> RAG Agent sinh câu trả lời. Hệ thống so sánh danh sách tài liệu tìm được với DOI chuẩn để tính **Retrieval Hit Rate**, và so sánh câu trả lời sinh ra với câu trả lời chuẩn (bằng Token F1 và mô hình LLM Judge) để đánh giá chất lượng câu trả lời.
3.  **Quality checks vs Freshness monitoring**:
    *   *Quality checks*: Giám sát cấu trúc tĩnh của dữ liệu (ví dụ: phát hiện bản ghi trùng lặp, dòng bị trống thông tin quan trọng như tóm tắt).
    *   *Freshness monitoring*: Giám sát tính cập nhật động của dữ liệu theo thời gian (ví dụ: tuổi thọ của bài báo tính từ ngày xuất bản đến nay có vượt ngưỡng cho phép hay không).
4.  **Tại sao dùng cùng một test set**: Để đảm bảo tính nhất quán và công bằng khoa học (control variables). Khi giữ nguyên tập câu hỏi kiểm tra, sự thay đổi trong điểm số chất lượng (F1, Judge) chỉ phụ thuộc duy nhất vào sự thay đổi của chất lượng dữ liệu đầu vào (Sạch vs Lỗi vs Khôi phục).
5.  **Nhận diện Repair thành công**: Khâu khôi phục thành công khi báo cáo giám sát chất lượng dữ liệu không còn phát hiện lỗi nghiêm trọng nào (`paper_id_unique`, `summary_length` đều PASS), đồng thời các chỉ số của RAG Agent (`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`) khôi phục trở lại bằng hoặc xấp xỉ mức Baseline ban đầu.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      1.0 |      0.75 |      1.0 | Giảm mạnh khi dữ liệu bị lỗi và phục hồi hoàn toàn sau sửa lỗi. |
| `mean_token_f1`      |    0.969 |     0.725 |    0.969 | Từ vựng của Agent khớp rất tốt với đáp án chuẩn và phục hồi 100%. |
| `judge_accuracy`     |    0.969 |     0.719 |    0.969 | Độ chính xác ngữ nghĩa được giám khảo LLM chấm điểm khôi phục hoàn hảo. |
| `mean_judge_score`   |    4.875 |     3.875 |    4.875 | Điểm trung bình chất lượng (1-5) tụt mất 1 điểm khi lỗi dữ liệu. |
| Quality checks         |     FAIL |      FAIL |     FAIL | Luôn báo FAIL do lỗi freshness tồn tại trong bộ dữ liệu gốc. |
| Freshness status       |     FAIL |      FAIL |     FAIL | Có 11 dòng bị lỗi thời trong dataset gốc, tăng lên 13 khi corrupted. |

*Lưu ý: Mặc dù Quality checks báo FAIL ở cả 3 trạng thái do thuộc tính dữ liệu gốc có các bài báo xuất bản từ lâu (Freshness threshold đặt thấp), nhưng ở trạng thái Corrupted xuất hiện thêm các lỗi nghiêm trọng về cấu trúc như trùng lặp ID và trống tóm tắt, các lỗi này đã biến mất hoàn toàn ở bản Repaired.*

### Kết luận từ số liệu

1.  **Dữ liệu bị làm lỗi** (xóa tóm tắt, chèn nhiễu, nhân bản dòng) $\rightarrow$ **Quality check báo FAIL** thêm lỗi `paper_id_unique` và `summary_length` $\rightarrow$ **Chất lượng RAG Agent giảm sút** (Tỷ lệ tìm kiếm trúng giảm từ 1.0 xuống 0.75, điểm chất lượng giảm từ 4.875 xuống 3.875).
2.  **Khôi phục dữ liệu từ nguồn gốc** $\rightarrow$ **Quality check sạch lỗi cấu trúc** (chỉ còn báo lỗi freshness do tập dữ liệu nguyên bản) $\rightarrow$ **Chất lượng RAG Agent phục hồi 100%** về trạng thái Baseline.

*   **Corruption ảnh hưởng rõ nhất**: Hành vi xóa tóm tắt (`blank_summary`) và chèn nhiễu (`inject_summary_noise`) ảnh hưởng lớn nhất. Tóm tắt là nội dung cốt lõi của bài báo khoa học dùng để biểu diễn ngữ nghĩa. Khi bị xóa hoặc chèn chuỗi gây nhiễu, vector nhúng của tài liệu bị sai lệch nghiêm trọng, làm mô hình embedding không thể tìm thấy tài liệu liên quan khi thực hiện tìm kiếm tương đồng.
*   **Kết quả khác kỳ vọng**: Kết quả đánh giá chất lượng dữ liệu (Quality checks) của trạng thái Repaired vẫn báo `FAIL`. Ban đầu tôi kỳ vọng nó sẽ chuyển sang `PASS`. Tuy nhiên khi phân tích chi tiết, lỗi FAIL này chỉ là do kiểm tra Freshness (bài báo cũ hơn ngưỡng cấu hình), đây là đặc tính vốn có của tập dữ liệu khoa học gốc chứ không phải lỗi hệ thống.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1.  **Về data pipeline**: Một hệ thống AI/RAG hoạt động ổn định và chính xác phụ thuộc cực kỳ lớn vào tính nhất quán của cấu trúc dữ liệu truyền dẫn qua từng bước (Data Contract).
2.  **Về data quality/observability**: Cần phải xây dựng các bộ lọc và kiểm tra chất lượng dữ liệu tự động ở mọi điểm hand-off để phát hiện lỗi sớm trước khi nạp vào mô hình AI.
3.  **Về ảnh hưởng của dữ liệu đến RAG**: Chất lượng dữ liệu đầu vào tỷ lệ thuận trực tiếp với chất lượng câu trả lời của LLM. Dữ liệu lỗi sẽ dẫn đến hiện tượng ảo tưởng (hallucination) của Agent.

### Nếu có thêm thời gian

Nếu có thêm thời gian, tôi sẽ xây dựng cơ chế **Tự động làm sạch động (Dynamic Auto-repairing)** trực tiếp trong khâu lập chỉ mục vector của Vai trò 4. Khi phát hiện tóm tắt trống hoặc tiêu đề bị cắt cụt, hệ thống sẽ tự động gọi API phụ trợ để điền khuyết hoặc sử dụng LLM tóm tắt lại văn bản gốc trước khi nhúng vector, giúp nâng cao độ ổn định của Retrieval.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Thị Huyền Trang
**Ngày xác nhận:** 2026-08-06
