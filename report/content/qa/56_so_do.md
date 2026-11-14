# 5.6. Sơ đồ luồng xử lý

> **Yêu cầu 5.6 (đề bài):** Có sơ đồ kiến trúc hoặc data-flow từ input đến output, thể hiện thành phần, luồng dữ liệu, giao thức/định dạng chính và nơi xử lý/lưu trữ.

Sơ đồ data-flow của nhóm em (`docs/architecture.png`, bản Mermaid trong `docs/architecture.md`; cũng là Hình 4.1 trong báo cáo):

{{image:PROJECT:docs/architecture.png|Sơ đồ data-flow Analytics → Presentation: Parquet → Loader (COPY, TLS 5432, endpoint direct) → Neon (gold, analytics → presentation) → Superset (SQLAlchemy/psycopg2, endpoint pooled) → người dùng; nhánh v_decision_hints → Decision/Action|h=11}}

Giải thích từng mũi tên trên sơ đồ:

Bảng: Các bước trong luồng dữ liệu {w=1.4,2.9,5.8,3.0,2.9}
| Bước | Từ → Đến | Định dạng / giao thức | Nơi xử lý | Nơi lưu trữ |
|---|---|---|---|---|
| 1 | Spark (nhóm Analytics) → Data Lake | Tệp Parquet + Snappy | Cụm Spark upstream | `data/analytics/` (16 bảng, ~8 MB), `data/gold/` (7 bảng, ~35 MB) |
| 2 | Data Lake → Loader | Đọc tệp → bảng Arrow (cột) trong RAM → CSV trong RAM (`pyarrow.csv`, mọi giá trị đặt trong dấu nháy để phân biệt chuỗi rỗng với NULL) | Container `tools` (`loader/load_to_neon.py`) | Bộ nhớ của container |
| 3 | Loader → Neon | Giao thức Postgres (wire protocol v3) qua TLS, cổng 5432, endpoint **direct**; `COPY … FROM STDIN (FORMAT csv)` khối 1 MiB, trong một giao dịch mỗi bảng; sau đó PK, index, `ANALYZE`, ghi `load_log` | Compute Neon (Postgres 18.6, 0,25 CU) | Storage Neon (Singapore): schema `analytics`, `gold` |
| 4 | `analytics`, `gold` → `presentation` | SQL view (`sql/10_presentation_views.sql`, chạy trong một giao dịch, `DROP SCHEMA … CASCADE` rồi tạo lại) | Compute Neon | Schema `presentation`: 22 view + `dim_state` |
| 5 | Kiểm chứng | `loader/validate.py`: đọc lại Parquet, `COUNT(*)` và 19 truy vấn số neo (`sql/90_anchor_checks.sql`) | Container `tools` + Neon | `evidence/validation.md/.json` |
| 6 | Neon → Superset | SQLAlchemy + psycopg2 qua TLS, endpoint **pooled** (PgBouncer); mỗi biểu đồ sinh một câu SQL đẩy xuống Neon | Compute Neon thực thi SQL; Superset (4 worker) ghép kết quả | Cache kết quả Superset 600 s; metadata trong Postgres 16 `superset-db` |
| 7 | Superset → người dùng | HTTP cổng 8088, JSON (`/api/v1/chart/data`) → React + ECharts vẽ trong trình duyệt | Trình duyệt | — |
| 8 | Neon → Decision/Action | SQL đọc `v_decision_hints`, `v_seller_watchlist`; hoặc CSV / Chart Data API | Hệ thống của giai đoạn sau | — |
| 9 | Neon → landing page | `scripts/export_landing_kpi.py` xuất JSON; nginx phục vụ HTTP cổng 8090 | Container `tools` khi xuất; trình duyệt khi xem | `web/data/kpi.json` |

Dashboard được dựng (không phải kéo thả tay) bởi `superset/build_dashboard.py` gọi REST API của Superset: tạo kết nối CSDL, 22 dataset, 45 biểu đồ, 7 tab, 7 bộ lọc. Nguyên tắc xuyên suốt: **tính nặng một lần ở Spark, phục vụ nhẹ nhiều lần ở Neon** — Neon chỉ lọc và cộng trên bảng đã cô đọng nên thời gian thực thi phía server khoảng 1 ms.
