# 5. Cài đặt và triển khai

## 5.1. Môi trường và cấu trúc mã nguồn

Bảng: Môi trường cài đặt và triển khai
| Thành phần | Phiên bản / cấu hình |
|---|---|
| Máy chạy | Windows 11, PowerShell, Docker Desktop (Docker 29, Compose v2); mạng Internet tại Việt Nam → Neon Singapore (RTT ~{{var:latency_rtt_ms}} ms) |
| Container `tools` | `python:3.12-slim` + pyarrow 17, pandas 2.2, psycopg 3.2, SQLAlchemy 2.0, requests |
| Superset | `apache/superset:4.1.2` + `psycopg2-binary`, 4 worker Gunicorn, cache filesystem 600 s, locale mặc định `vi` |
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

**Giao diện tiếng Việt.** Superset 4.1.2 không có gói ngôn ngữ `vi`, nên nhóm tự soạn `superset/i18n/vi/LC_MESSAGES/messages.po` gồm 536 chuỗi hay gặp (menu, đăng nhập, trang chủ, thanh tiêu đề và menu dashboard, thanh bộ lọc, bộ chọn thời gian, menu "⋮" của chart, nút chung). Khi build image, `build_catalog.py` biên dịch thành `messages.mo` (backend) và `messages.json` (frontend); `superset_config.py` đặt `BABEL_DEFAULT_LOCALE = "vi"`, giữ English trong bộ chọn ngôn ngữ và dùng định dạng số/ngày Việt Nam. Phần còn tiếng Anh: chuỗi chưa dịch ở SQL Lab, màn hình sửa chart, trang quản trị; nút "All/Inv" của chú giải ECharts, chữ "… ago", ô "153 record" của bảng và giá trị dữ liệu gốc (tên danh mục, phân khúc *Champions*, *At Risk*).

**Landing page.** `docker compose up -d web` chạy nginx phục vụ `web/` ở cổng 8090; sau mỗi lần nạp, `scripts/export_landing_kpi.py` (container `tools`) xuất lại `web/data/kpi.json` từ Neon, `scripts/screenshot_landing.py` chụp ảnh desktop và mobile.

## 5.4. Xử lý lỗi và các vấn đề kỹ thuật

Bảng: Các vấn đề kỹ thuật đã gặp và cách xử lý
| Vấn đề | Nguyên nhân | Cách xử lý |
|---|---|---|
| Máy Windows không có Python | Môi trường không đồng nhất | Container `tools` chạy mọi script |
| `COPY`/DDL qua endpoint pooled có thể lỗi | PgBouncer chế độ transaction không giữ phiên | Loader tự đổi sang endpoint direct |
| Superset không kết nối được Postgres | Image gốc không có driver | Cài `psycopg2-binary` trong Dockerfile |
| Script khởi động lỗi `\r` | Tệp soạn trên Windows dùng CRLF | `sed -i 's/\r$//'` trong Dockerfile |
| Chart tải song song phải xếp hàng | Metadata SQLite khoá ghi toàn cục | Chuyển metadata sang Postgres 16, 4 worker Gunicorn |
| Lần mở dashboard đầu chậm (~{{var:chart_force_median}} ms/chart) | Superset dùng NullPool, mỗi chart mở kết nối TLS mới | Cache kết quả 600 s; endpoint pooled; đề xuất đặt Superset cùng vùng |
| Tổng tiền lệch vài xu / timestamp không hợp lệ | Số thực cho tiền; Arrow lưu nano giây | `NUMERIC(p,s)`; ép timestamp về micro giây |
| Chuỗi rỗng bị hiểu thành NULL; mất cột năm/tháng | CSV không phân biệt; cột phân vùng nằm trong tên thư mục | `quoting_style="all_valid"`; `partitioning="hive"` |
| Bộ lọc thời gian / bản đồ không hoạt động | Thiếu cột DATE; Country Map cần mã ISO | `month_date`; `dim_state.iso_code = 'BR-xx'` |
| Bộ lọc vừa dựng bị ghi đè | Tab trình duyệt đang mở lưu lại trạng thái dashboard cũ | Tải lại trang sau khi chạy `build_dashboard.py` |
| Superset không có tiếng Việt | Bản 4.1.2 không kèm gói `vi` | Tự soạn `messages.po`, biên dịch `.mo`/`.json` khi build image |
| Ảnh tab 5 trắng; ảnh bộ lọc hiện nhầm tab 1 | Chụp full-page làm viewport đổi kích thước, Superset gỡ lưới chart; permalink chỉ tô tiêu đề tab | Chụp theo viewport, chuyển tab rồi quay lại, kiểm tra tên chart của tab trước khi lưu ảnh |

Các lệnh chạy end-to-end (build, nạp, kiểm chứng, dựng dashboard, tái tạo minh chứng) ở Phụ lục A.
