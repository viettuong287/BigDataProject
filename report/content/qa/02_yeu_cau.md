# 2. Trả lời theo từng yêu cầu của đề bài

Mỗi mục dưới đây trả lời một yêu cầu trong "Yêu cầu đồ án": nhóm đáp ứng thế nào và bằng chứng nằm ở đâu (tệp trong repo, hình/mục trong báo cáo `report/BaoCao_DoAn_BigData.docx`).

## 2.1. Mục 1 – Mục tiêu của đồ án

Bảng: Đối chiếu năm mục tiêu của đề bài
| Mục tiêu của đề | Nhóm đáp ứng | Bằng chứng |
|---|---|---|
| Nhận diện đặc trưng Big Data, giải thích nhu cầu xử lý phân tán/quy mô lớn | Phân tích Volume, Variety, Veracity, Value; chỉ ra phần phân tán nằm ở Spark (upstream), tầng phục vụ đọc kết quả đã cô đọng; chứng minh bằng thí nghiệm ×10 | Báo cáo 2.1, 3.2, 6.6; `scale_experiment.md` |
| Thiết kế luồng dữ liệu, chỉ rõ thành phần và giao diện dữ liệu | Parquet → loader (COPY, TLS) → Neon (`analytics`, `gold` → `presentation`) → Superset → người dùng / Decision | Hình 4.1, bảng luồng dữ liệu 4.2; `docs/architecture.png` |
| Áp dụng nội dung học phần (Data Lake, Spark, phân tích, trực quan hoá) | Đọc Data Lake Parquet; dùng kết quả Spark SQL + K-Means; serving layer OLAP; dashboard | Báo cáo chương 2, 4 |
| Thí nghiệm/demo có số liệu, log, ảnh, dashboard | 7 kịch bản E1–E7: đối chiếu, nạp, độ trễ, tải dashboard, bộ lọc, ×10, QA 41 ca | Chương 6, 7; thư mục `evidence/` |
| Làm việc nhóm, tài liệu hoá | 3 thành viên, phân công rõ; README, báo cáo, tài liệu này | Phụ lục G; README |

## 2.2. Mục 5.1 – Quy trình được lựa chọn và ranh giới

Nhóm làm **Analytics → Presentation**. *Bắt đầu*: 16 bảng Parquet trong `data/analytics/` (kèm 7 bảng gold) và tài liệu `ANALYTICS_HANDOVER.md`. *Kết thúc*: (1) 25 bảng + 22 view trên Neon; (2) dashboard Superset 7 tab; (3) view `presentation.v_decision_hints` cho nhóm Decision/Action đọc bằng SQL. *Không làm*: không chạy lại Spark, không sửa số của Analytics. Giao diện với nhóm trước là data contract (grain, khoá, kiểu, số neo); với nhóm sau là view SQL ổn định. Bằng chứng: báo cáo 1.2, README mục 1.

## 2.3. Mục 5.2 – Bài toán và tính chất Big Data (≥ 2 V)

Bài toán: đưa kết quả phân tích của một sàn thương mại điện tử tới 5 nhóm người dùng nghiệp vụ (ban điều hành, ngành hàng, logistics, CRM, quản lý người bán) để theo dõi và ra quyết định. Các V nhóm trình bày:

- **Volume:** nguồn ~1,55 triệu dòng; vào tầng của nhóm 505.592 dòng; thí nghiệm nhân bản tới 1,12 triệu dòng trên Neon. Nhóm nói thẳng: khối lượng giảm dần qua từng tầng — đó là thiết kế đúng của pipeline, phần xử lý phân tán nặng nằm ở Spark.
- **Variety:** 23 bảng, 10+ grain khác nhau (tháng, danh mục, bang, khách, người bán, cụm…), nhiều kiểu (decimal, date, timestamp, boolean), fact phân vùng Hive.
- **Veracity:** cờ chất lượng `dq_*`, tháng thiếu dữ liệu, `customer_id` ≠ khách thật; giữ đúng quy tắc bàn giao và kiểm 19 số neo.
- **Value / phục vụ quy mô lớn:** nhiều người dùng đồng thời, tải không đều → serving layer serverless, cache; luật gợi ý quyết định.

Bằng chứng: báo cáo 3.2, 6.6; README mục 2.

## 2.4. Mục 5.3 – Input

Nguồn: bàn giao của nhóm Analytics (bản sao trong repo `data/analytics/`, `data/gold/`). Định dạng: Parquet + Snappy, mỗi bảng một thư mục kiểu Spark; hai bảng fact phân vùng `purchase_year/purchase_month`. Quy mô: 23 bảng, 505.592 dòng, 42,88 MB. Tốc độ: theo lô (mỗi lần Analytics chạy lại). Trường chính và ví dụ bản ghi: báo cáo 3.3, data contract 3.5, Phụ lục C (schema đầy đủ); `evidence/parquet_schema_inspect.txt`.

## 2.5. Mục 5.4 – Output

(1) Bảng phục vụ trên Neon: schema `analytics` (16 + `load_log`), `gold` (7); (2) tầng ngữ nghĩa `presentation`: 22 view + `dim_state`; (3) dashboard Superset tại `:8088` (7 tab, 45 chart, 7 bộ lọc); (4) `v_decision_hints` 7 luật + `v_seller_watchlist` (mức ĐỎ/VÀNG, lý do, hành động); (5) landing page `:8090` với `web/data/kpi.json` xuất từ Neon; (6) minh chứng trong `evidence/`. Ví dụ đầu ra: một dòng `v_decision_hints` — "ưu tiên 2, CAO, Giao hàng, review đúng hạn 4,29 vs trễ 2,56, ngưỡng chênh > 1 sao, hành động: cảnh báo seller khi đơn trễ 1–3 ngày". Bằng chứng: báo cáo 3.4, 7.3–7.5.

## 2.6. Mục 5.5 – Công nghệ và lý do chọn

Bảng: Công nghệ, vai trò, lý do (tóm tắt để nói)
| Công nghệ | Vai trò | Lý do chọn (một câu) |
|---|---|---|
| Parquet + pyarrow | Đọc input, cả phân vùng Hive | Giữ kiểu Spark (decimal, date), không cần Spark để đọc bảng đã cô đọng |
| Python loader + `COPY` (psycopg 3) trong Docker | Nạp hàng loạt, PK/index, `load_log` | `COPY` nhanh hơn INSERT nhiều lần; chạy lại được; máy Windows không cần cài Python |
| Neon Postgres 18 serverless | Serving layer | SQL chuẩn, tách compute/storage, scale-to-zero, chia sẻ qua Internet + TLS, không phải tự vận hành |
| View SQL | Semantic layer, luật cảnh báo | KPI định nghĩa một nơi, có version control, dùng chung cho dashboard và Decision |
| Apache Superset 4.1.2 | Dashboard, bộ lọc, cache | Mã nguồn mở, REST API dựng dashboard bằng mã (tái lập), Country Map Brazil |
| Postgres 16 (`superset-db`) | Metadata Superset | SQLite khoá ghi toàn cục làm chart tải song song phải xếp hàng |
| Playwright | Ảnh minh chứng, đo tải, QA 41 ca | Tự động, chạy lại được |
| nginx (`web/`) | Landing page `:8090` | Trang tĩnh, chỉ đọc `kpi.json`, không giữ thông tin kết nối |

Bằng chứng: báo cáo 4.6, Phụ lục B (so sánh với Power BI, Tableau, Grafana, Metabase; Postgres cục bộ, ClickHouse, DuckDB).

## 2.7. Mục 5.6 – Sơ đồ luồng xử lý

Sơ đồ data-flow có thành phần, giao thức và nơi xử lý: `docs/architecture.png` (= `evidence/architecture_pipeline.png`), Hình 4.1 báo cáo; bảng 7 bước ở mục 4.2 (Parquet → Arrow/CSV trong RAM → `COPY` qua TLS 5432 endpoint direct → view SQL → SQLAlchemy/psycopg2 endpoint pooled → HTTP 8088 → SQL/CSV/API cho Decision). Bản Mermaid trong `docs/architecture.md`.

## 2.8. Mục 5.7 – Kết quả demo/thực nghiệm

Log: `load_run.log`, `apply_sql.log`; số liệu: `load_log.csv`, `validation.md/json`, `query_latency.md`, `dashboard_load_latency.md`, `superset_chart_latency.csv`, `scale_experiment.md`, `qa_test_cases.md`; ảnh: 7 tab, 6 bộ lọc, watchlist, giao diện tiếng Việt/Olist Insight, landing page, kiểm kê Neon. Báo cáo chương 6 (E1–E7) và chương 7. Kịch bản demo trực tiếp ở mục 4 tài liệu này.

## 2.9. Mục 5.8 – Khả năng tái lập

Toàn bộ chạy bằng Docker Compose (service `superset-db`, `superset`, `tools`, `screenshots`, `web`); dashboard dựng bằng `build_dashboard.py` (hoặc import ZIP); loader và view idempotent; README mục 5 có lệnh từng bước; dữ liệu mẫu (toàn bộ Parquet đầu vào) nằm sẵn trong repo; QA TC41 kiểm mọi lệnh/script README nhắc tới đều tồn tại và `docker compose config` hợp lệ. Bằng chứng: README, Phụ lục A báo cáo, `qa_test_cases.md`.

## 2.10. Mục 6.2 – Thang điểm và bằng chứng theo từng tiêu chí

Bảng: Tự đối chiếu với thang điểm 10
| Tiêu chí (điểm) | Nhóm đáp ứng thế nào | Bằng chứng ở đâu |
|---|---|---|
| Mức độ hoàn thành hệ thống (2,5) | Pipeline chạy đầu-cuối: Parquet → Neon → view → dashboard 7 tab → `v_decision_hints`; 0 chart lỗi; QA 41/41 | Chương 5, 7; `qa_test_cases.md`; ảnh `dashboard_tab*.png` |
| Thiết kế và triển khai kỹ thuật (2,0) | Kiến trúc phân tầng 3 schema; DDL tự sinh; nạp trong giao dịch, idempotent; dashboard-as-code; Docker Compose | Chương 4, 5; `loader/`, `sql/`, `superset/` |
| Thực nghiệm và bằng chứng (2,0) | 7 kịch bản có số đo và cách đo rõ (log, CSV, ảnh); đối chiếu 23/23 + 19/19 | Chương 6; `evidence/` |
| Đặc trưng Big Data và mở rộng (1,5) | Lập luận V's + thí nghiệm ×10 (thô 47 → 507 ms, view 1,1 ms); phân tích nút thắt mạng; hướng mở rộng | Báo cáo 3.2, 6.6, 8.3 |
| Phân tích kết quả và thảo luận (1,0) | Giải thích số (mạng chiếm độ trễ, NullPool, cache); hạn chế trung thực (3/7 tab cold > 5 s) | Chương 6.8, 8 |
| Chất lượng báo cáo và tái lập (1,0) | Báo cáo đúng cấu trúc 6.1, tài liệu tham khảo, README, phân công, ghi chú AI | Báo cáo, README, Phụ lục A, G, H |

## 2.11. Mục 8 – Công cụ AI và tính trung thực học thuật

Nhóm có dùng trợ lý AI (các agent trong Cursor) để gợi ý khung mã (loader, script dựng dashboard, script đo, Dockerfile), gợi ý SQL, dựng script sinh báo cáo và bản nháp nội dung. Nhóm tự chạy toàn bộ hệ thống, đọc và sửa mã, đối chiếu mọi con số với tệp trong `evidence/` và 19 số neo; các quyết định kỹ thuật (Neon, Superset, schema, KPI, luật, tiêu chí đánh giá) do nhóm thảo luận và có lập luận. Đã ghi rõ trong Phụ lục H báo cáo và README mục 10. Khi được hỏi, mỗi thành viên phải giải thích được phần mình phụ trách (xem câu hỏi theo thành viên ở mục 3.10).
