# 5.5. Công nghệ sử dụng

> **Yêu cầu 5.5 (đề bài):** Liệt kê từng công nghệ và giải thích vai trò. Không chấp nhận chỉ liệt kê tên công cụ mà không mô tả lý do lựa chọn và vị trí trong kiến trúc.

Bảng: Công nghệ, phiên bản, vai trò, vị trí trong kiến trúc và lý do chọn {w=2.6,2.4,3.1,2.6,5.3}
| Công nghệ | Phiên bản | Vai trò | Vị trí trong kiến trúc | Vì sao chọn (so với phương án khác) |
|---|---|---|---|---|
| Apache Parquet (Snappy) | — | Định dạng dữ liệu bàn giao | Input: `data/analytics/`, `data/gold/` | Định dạng cột có schema và kiểu `decimal`/`date`; giữ nguyên kiểu Spark, nén tốt; CSV sẽ mất kiểu và lớn hơn ~2,5 lần |
| Python + pyarrow + pandas | Python 3.12; pyarrow 17.0, pandas 2.2.3 | Đọc Parquet (kể cả phân vùng Hive), sinh DDL, chuyển CSV trong RAM | Container `tools` (`loader/`) | Đọc bảng đã cô đọng không cần dựng cụm Spark; chạy trong `python:3.12-slim` nên máy Windows không cần cài Python |
| psycopg 3 + lệnh `COPY` | psycopg 3.2.3 | Nạp hàng loạt `COPY ... FROM STDIN (FORMAT csv)` theo khối 1 MiB | Loader → Neon, qua endpoint direct | `COPY` nhanh hơn INSERT từng dòng nhiều lần; hỗ trợ giao dịch nên nạp idempotent |
| Neon Serverless Postgres | PostgreSQL 18.6, gói free, 0,25 CU, `aws-ap-southeast-1` (Singapore) | Serving layer: lưu 25 bảng + 22 view | Giữa loader và Superset | SQL chuẩn, tách compute/storage, scale-to-zero, TLS, chia sẻ qua Internet cho cả nhóm và giai đoạn sau; Postgres cục bộ không chia sẻ được, ClickHouse chỉ có lợi ở hàng tỷ dòng chi tiết, BigQuery tính phí theo truy vấn. Endpoint *direct* cho DDL/COPY, *pooled* (PgBouncer) cho Superset |
| View SQL (semantic layer) | `sql/10_presentation_views.sql` | Định nghĩa KPI một lần, thêm cột trình bày, luật quyết định | Schema `presentation` trên Neon | Dùng chung cho dashboard và Decision/Action, quản lý phiên bản bằng Git; không để mỗi biểu đồ tự viết SQL |
| SQLAlchemy + psycopg2 | SQLAlchemy 2.0.36; psycopg2-binary 2.9.10 | Driver Superset → Neon | Superset → Neon, TLS `sslmode=require` | Superset kết nối mọi CSDL qua SQLAlchemy; image Superset gốc không kèm driver Postgres |
| Apache Superset | 4.1.2, 4 worker Gunicorn, cache 600 s | Dashboard 7 tab, 45 biểu đồ, 7 bộ lọc native; giao diện tiếng Việt (536 chuỗi), thương hiệu Olist Insight | Tầng trình bày, cổng 8088 | Mã nguồn mở, SQL-native, có bản đồ Brazil, **REST API để dựng dashboard bằng mã** (tái lập); Power BI/Tableau thương mại, tệp nhị phân; Grafana yếu với Pareto/xếp hạng; Metabase ít loại biểu đồ |
| PostgreSQL (metadata) | `postgres:16-alpine` | Lưu người dùng, biểu đồ, dashboard của Superset | Container `superset-db` | SQLite khoá ghi toàn cục làm biểu đồ tải song song phải xếp hàng |
| Docker Compose | Docker 29 (Docker Desktop) | Đóng gói 5 service: `superset-db`, `superset`, `tools`, `screenshots`, `web` | Toàn hệ thống | Một lệnh dựng lại trên máy bất kỳ, cùng phiên bản thư viện |
| Playwright + Chromium headless | 1.48.0 | Chụp ảnh minh chứng, đo thời gian tải dashboard, kiểm thử QA 41 ca | Service `screenshots` (`scripts/`) | Tự động, lặp lại được, đọc được response `/api/v1/chart/data` để kiểm giá trị |
| nginx | 1.27-alpine | Phục vụ landing page tĩnh | Service `web`, cổng 8090 | Nhẹ; trang chỉ đọc `kpi.json`, không giữ thông tin kết nối CSDL |
| Git + GitHub | Git 2.49 | Quản lý mã, cấu hình, minh chứng, báo cáo | `https://github.com/viettuong287/BigDataProject` | Lưu lịch sử, chia sẻ cho nhóm và giảng viên; `.env` có trong `.gitignore` |

**Upstream (nhóm trước, không do nhóm em vận hành):** Apache Spark 3.5.3 trên cụm 1 master + 2 worker (4 core) đã tính 16 bảng Analytics (14 truy vấn Spark SQL + K-Means k = 4). Nhóm em không dùng Spark ở tầng Presentation vì Spark là hệ xử lý theo lô, khởi động job mất hàng chục giây, không phù hợp trả lời từng cú nhấp trong vài trăm mili giây; phần tính nặng đã xong ở tầng trước.
