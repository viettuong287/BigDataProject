# 5. Cài đặt và triển khai

## 5.1. Môi trường và cấu trúc mã nguồn

Bảng: Môi trường cài đặt và triển khai
| Thành phần | Phiên bản / cấu hình |
|---|---|
| Máy chạy | Windows 11, PowerShell, Docker Desktop (Docker 29, Compose v2); mạng Internet tại Việt Nam → Neon Singapore (RTT ~{{var:latency_rtt_ms}} ms) |
| Container `tools` | `python:3.12-slim` + pyarrow 17, pandas 2.2, psycopg 3.2, SQLAlchemy 2.0, requests |
| Superset | `apache/superset:4.1.2` + `psycopg2-binary`, 4 worker Gunicorn, cache filesystem 600 s, giao diện mặc định tiếng Việt, theme Olist Insight |
| Landing page | `nginx:1.27-alpine` (service `web`, cổng 8090), phục vụ thư mục `web/` |
| Metadata Superset | `postgres:16-alpine` (container `superset-db`, volume riêng) |
| Ảnh chụp / đo tải | Playwright + Chromium headless, viewport 1600×1900 |
| Tầng phục vụ | Neon PostgreSQL 18.6, `aws-ap-southeast-1`, {{var:neon_cu}} CU, gói {{var:neon_plan}} |
| Đầu vào | {{var:n_tables}} bảng Analytics ({{var:total_rows}} dòng) + {{var:n_gold}} bảng gold ({{var:gold_rows}} dòng) |

Repo được tổ chức theo thành phần kiến trúc: `data/` (Parquet đầu vào), `loader/` (nạp, áp dụng SQL, kiểm chứng), `sql/` (tầng ngữ nghĩa, 19 kiểm tra số neo), `superset/` (Dockerfile, cấu hình, bản dịch `i18n/`, `build_dashboard.py`, `import_dashboard.py`, bản export ZIP), `scripts/` (đo độ trễ, thí nghiệm scale, chụp ảnh, vẽ sơ đồ, kiểm kê Neon, xuất số liệu landing), `web/` (landing page), `evidence/`, `docs/`, `report/`. Cây thư mục đầy đủ ở Phụ lục F. Mọi script chạy trong container nên máy Windows không cần cài Python, và mọi thành viên dùng cùng phiên bản thư viện.

## 5.2. Khởi tạo Neon và nạp dữ liệu

Nhóm tạo project `bigdata-olist-presentation` (PostgreSQL 18, AWS Singapore) và database `olist_analytics`; chuỗi kết nối pooled được ghi vào `NEON_DATABASE_URL` trong `.env` (không commit). Loader `loader/load_to_neon.py` khai báo tường minh 23 bảng cùng khoá chính, chỉ mục và grain trong từ điển `TABLES`. Một lần chạy: (1) tự bỏ hậu tố `-pooler` để dùng endpoint direct, ghi phiên bản Postgres và chuỗi kết nối đã che mật khẩu vào `evidence/load_run.log`; (2) tạo schema và `load_log`; (3) với mỗi bảng, đọc bằng `pyarrow.dataset` (nhận phân vùng Hive), sinh DDL, chuyển CSV trong bộ nhớ; (4) nạp trong một giao dịch; (5) tạo PK/chỉ mục, `ANALYZE`, đếm dòng, ghi `load_log`; (6) áp dụng `sql/[0-8]*.sql`; (7) xuất `evidence/load_log.csv`. Lõi phần nạp:

```python
table, nfiles, nbytes = read_table(src)          # pyarrow.dataset, partitioning="hive"
payload = to_csv_bytes(table)                     # pyarrow.csv, quoting_style="all_valid"
with conn.transaction():
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {fq} CASCADE")
        cur.execute(f"CREATE TABLE {fq} (\n    {cols_ddl}\n)")
        with cur.copy(f"COPY {fq} ({collist}) FROM STDIN WITH (FORMAT csv)") as cp:
            view = memoryview(payload)
            for i in range(0, len(view), 1 << 20):   # khối 1 MiB
                cp.write(view[i : i + (1 << 20)])
```

Sau khi nạp, `loader/validate.py` đọc lại Parquet để so số dòng với Postgres và chạy 19 truy vấn trong `sql/90_anchor_checks.sql` (mỗi truy vấn kèm chú thích `-- check: tên | expected | tol`), xuất `evidence/validation.md/.json`. Khi chỉ sửa view, chạy `loader/apply_sql.py` (tạo lại 22 view + `dim_state` trong dưới một giây).

## 5.3. Triển khai Apache Superset

Superset được đóng gói từ image `apache/superset:4.1.2` cài thêm `psycopg2-binary`; `docker-init.sh` chạy `superset db upgrade`, tạo tài khoản quản trị từ biến môi trường, `superset init` rồi khởi động web server với 4 worker — mọi bước idempotent. Metadata nằm trong container Postgres 16 `superset-db` thay vì SQLite. `superset/build_dashboard.py` dựng toàn bộ dashboard qua **REST API** (dashboard-as-code): lấy token, tạo *Database* trỏ tới Neon, đăng ký 22 view thành dataset, tạo 45 chart, dashboard 7 tab và 7 native filter kèm phạm vi; chạy lại sẽ cập nhật thay vì tạo trùng. Bản export `superset/export/dashboard_olist_presentation.zip` cùng `import_dashboard.py` là phương án dự phòng. Nhờ vậy dashboard dựng lại giống hệt trên máy khác chỉ bằng một lệnh.

**Giao diện tiếng Việt.** Superset 4.1.2 không có gói ngôn ngữ `vi`, nên nhóm tự soạn `superset/i18n/vi/LC_MESSAGES/messages.po` gồm 536 chuỗi hay gặp (menu, đăng nhập, trang chủ, thanh tiêu đề và menu dashboard, thanh bộ lọc, bộ chọn thời gian, menu "⋮" của chart, nút chung). Khi build image, `build_catalog.py` biên dịch thành `messages.mo` (backend) và `messages.json` (frontend). `BABEL_DEFAULT_LOCALE` giữ `en` (Superset dịch nhãn menu một lần lúc khởi động), tiếng Việt được gán mặc định cho từng phiên mới qua `FLASK_APP_MUTATOR`. Bấm cờ ngôn ngữ vốn bị đưa về trang chủ; script trong `tail_js_custom_extra.html` gọi ngầm `/lang/<mã>` rồi tải lại đúng URL, giữ tab và bộ lọc (`native_filters_key`). Số/ngày định dạng kiểu Việt Nam. Còn tiếng Anh: chuỗi chưa dịch ở SQL Lab, màn hình sửa chart, trang quản trị, vài nhãn ECharts và giá trị dữ liệu gốc (*Champions*, *At Risk*).

**Giao diện "Olist Insight".** Cùng nhận diện với landing: `APP_NAME`, logo, favicon, nút "Trang giới thiệu"; `THEME_OVERRIDES` (chàm `#6366f1`, xanh ngọc `#10b981`, font Be Vietnam Pro); bảng màu chart `olistInsight`/`olistInsightSeq`; `dashboard.css` (đi kèm ZIP) tạo nền gradient tối, thẻ KPI kính tối. Superset 4.1 chưa có dark mode cho chart nên thẻ biểu đồ giữ nền sáng cho dễ đọc.

**Landing page.** `docker compose up -d web` chạy nginx phục vụ `web/` ở cổng 8090; sau mỗi lần nạp, `scripts/export_landing_kpi.py` (container `tools`) xuất lại `web/data/kpi.json` từ Neon, `scripts/screenshot_landing.py` chụp ảnh desktop và mobile.

## 5.4. Xử lý lỗi và các vấn đề kỹ thuật

Các lệnh chạy end-to-end (build, nạp, kiểm chứng, dựng dashboard, tái tạo minh chứng) ở Phụ lục A.

Bảng: Các vấn đề kỹ thuật đã gặp và cách xử lý
| Vấn đề | Nguyên nhân | Cách xử lý |
|---|---|---|
| `COPY`/DDL qua endpoint pooled có thể lỗi | PgBouncer chế độ transaction không giữ phiên | Loader tự đổi sang endpoint direct |
| Superset không kết nối Postgres; script khởi động lỗi `\r` | Image gốc thiếu driver; tệp CRLF từ Windows | Cài `psycopg2-binary`; `sed -i 's/\r$//'` trong Dockerfile |
| Chart tải song song phải xếp hàng | Metadata SQLite khoá ghi toàn cục | Chuyển metadata sang Postgres 16, 4 worker Gunicorn |
| Lần mở dashboard đầu chậm (~{{var:chart_force_median}} ms/chart) | Superset dùng NullPool, mỗi chart mở kết nối TLS mới | Cache kết quả 600 s; endpoint pooled; đề xuất đặt Superset cùng vùng |
| Tổng tiền lệch vài xu / timestamp không hợp lệ | Số thực cho tiền; Arrow lưu nano giây | `NUMERIC(p,s)`; ép timestamp về micro giây |
| Chuỗi rỗng bị hiểu thành NULL; mất cột năm/tháng | CSV không phân biệt; cột phân vùng nằm trong tên thư mục | `quoting_style="all_valid"`; `partitioning="hive"` |
| Bộ lọc thời gian / bản đồ không hoạt động | Thiếu cột DATE; Country Map cần mã ISO | `month_date`; `dim_state.iso_code = 'BR-xx'` |
| Bộ lọc vừa dựng bị ghi đè | Tab trình duyệt đang mở lưu lại trạng thái dashboard cũ | Tải lại trang sau khi chạy `build_dashboard.py` |
| Superset không có tiếng Việt | Bản 4.1.2 không kèm gói `vi` | Tự soạn `messages.po`, biên dịch `.mo`/`.json` khi build image |
| Đổi sang English: menu vẫn tiếng Việt, bị đưa về trang chủ | Nhãn menu dịch lúc khởi động theo locale mặc định; `/lang/<mã>` chuyển hướng theo lịch sử server | Mặc định `en` lúc khởi động, `vi` cho phiên mới; `fetch` `/lang/<mã>` rồi tải lại đúng URL |
| Tiêu đề thẻ KPI chồng số khi lọc | Biểu tượng phễu làm tiêu đề xuống 3–4 dòng | Tiêu đề ngắn 1 dòng, phễu lên góc thẻ; QA đo ở 1440/1280 px |
| Ảnh tab 5 trắng, ảnh lọc nhầm tab | Chụp full-page làm Superset gỡ lưới chart | Chụp theo viewport, kiểm tên chart của tab |
