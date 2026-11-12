# 5. Cài đặt và triển khai

## 5.1. Môi trường

Bảng: Môi trường cài đặt và triển khai
| Thành phần | Phiên bản / cấu hình | Ghi chú |
|---|---|---|
| Máy phát triển | Windows 11, PowerShell | Không cần cài Python trên máy host |
| Docker Desktop | Docker Engine + Compose v2 | Chạy Superset, container công cụ, Playwright |
| Container công cụ `tools` | `python:3.12-slim` + pyarrow 17, pandas 2.2, psycopg 3.2, SQLAlchemy 2.0, requests | Loader, kiểm tra, dựng dashboard, đo độ trễ |
| Superset | `apache/superset:4.1.2` + `psycopg2-binary` 2.9.10 | Metadata SQLite trong volume `superset_home` |
| Chụp ảnh | `mcr.microsoft.com/playwright/python:v1.48.0-jammy` | Chromium headless |
| Tầng phục vụ | Neon, PostgreSQL 18, vùng `aws-ap-southeast-1` | Gói miễn phí |
| Đầu vào | {{var:n_tables}} bảng Analytics ({{var:total_rows}} dòng) + {{var:n_gold}} bảng gold ({{var:gold_rows}} dòng) | `data/analytics/`, `data/gold/` |

Lý do dùng container công cụ thay vì cài Python trên máy: mọi thành viên (và giảng viên) có cùng phiên bản thư viện, không xung đột với Python khác trên máy, và lệnh chạy giống nhau trên Windows, macOS, Linux.

## 5.2. Cấu trúc mã nguồn

Repo được tổ chức theo thành phần của kiến trúc: `data/` (Parquet đầu vào: `analytics/`, `gold/`), `loader/` (nạp, áp dụng SQL, kiểm chứng; Dockerfile của container `tools`), `sql/` (tầng ngữ nghĩa và truy vấn kiểm tra), `superset/` (Dockerfile, cấu hình, script khởi tạo và dựng dashboard), `scripts/` (tiện ích: đo độ trễ, chụp ảnh), `evidence/` (log, số đo, ảnh), `docs/` (tài liệu, tài liệu bàn giao của nhóm trước) và `report/` (script sinh báo cáo này). Cây thư mục đầy đủ, quét tự động từ repo, ở Phụ lục F.

## 5.3. Khởi tạo Neon

Các bước khởi tạo tầng phục vụ:

1. Tạo project `bigdata-olist-presentation` trên Neon Console, chọn PostgreSQL 18 và vùng AWS Singapore (`aws-ap-southeast-1`).
2. Tạo database `olist_analytics` trên nhánh mặc định; ba schema `analytics`, `gold`, `presentation` do loader tự tạo (`CREATE SCHEMA IF NOT EXISTS`).
3. Lấy chuỗi kết nối dạng *pooled* (hostname chứa `-pooler`) và ghi vào biến `NEON_DATABASE_URL` trong `.env`. Module `loader/common.py` tự bỏ hậu tố `-pooler` để có endpoint *direct* cho `COPY`/DDL, còn Superset dùng endpoint pooled.
4. Cấu hình autoscaling và scale-to-zero cho compute (Mục 4.3.1).

{{evidence:neon|ảnh Neon Console: project bigdata-olist-presentation, database olist_analytics, compute/autoscaling}}

## 5.4. Loader Parquet → Neon

Loader (`loader/load_to_neon.py`) được viết bằng Python, chạy trong container `tools`. Danh sách bảng cần nạp được khai báo tường minh trong từ điển `TABLES` cùng khoá chính, chỉ mục phụ và grain của từng bảng. Luồng xử lý của một lần chạy:

1. Sinh `run_id`, mở kết nối direct tới Neon (timeout 30 giây để chịu được cold start khi compute đang ngủ), ghi phiên bản Postgres và chuỗi kết nối đã che mật khẩu vào `evidence/load_run.log`.
2. Tạo các schema `analytics`, `gold`, `presentation` và bảng `analytics.load_log` nếu chưa có.
3. Với mỗi bảng: `pyarrow.dataset` đọc thư mục Parquet (tự nhận phân vùng Hive), ép kiểu timestamp, sinh DDL, chuyển bảng Arrow thành CSV trong bộ nhớ.
4. Trong một giao dịch: `DROP TABLE … CASCADE`, `CREATE TABLE`, `COPY … FROM STDIN (FORMAT csv)` truyền từng khối 1 MiB, `COMMENT ON TABLE` ghi grain và nguồn.
5. Tạo khoá chính và chỉ mục phụ, `ANALYZE`, đếm dòng, ghi một dòng vào `analytics.load_log` và một dòng log (lớp `Tee` ghi đồng thời ra màn hình và tệp).
6. Áp dụng các tệp `sql/[0-8]*.sql` để tạo lại tầng ngữ nghĩa (vì `DROP … CASCADE` ở bước 4 có thể xoá view phụ thuộc).
7. In dòng tổng (số bảng, số dòng, dung lượng, thời gian, thông lượng, số bảng khớp), xuất `evidence/load_log.csv`; thoát với mã lỗi nếu có bảng lệch số dòng.

Đoạn mã trích từ hàm `load_one` của loader, phần nạp trong giao dịch:

```python
table, nfiles, nbytes = read_table(src)          # pyarrow.dataset, partitioning="hive"
cols_ddl = ",\n    ".join(f"{f.name} {pg_type(f.type)}" for f in table.schema)
payload = to_csv_bytes(table)                     # pyarrow.csv, quoting_style="all_valid"
with conn.transaction():
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {fq} CASCADE")
        cur.execute(f"CREATE TABLE {fq} (\n    {cols_ddl}\n)")
        with cur.copy(f"COPY {fq} ({collist}) FROM STDIN WITH (FORMAT csv)") as cp:
            view = memoryview(payload)
            for i in range(0, len(view), 1 << 20):   # khối 1 MiB
                cp.write(view[i : i + (1 << 20)])
        cur.execute(sql.SQL("COMMENT ON TABLE {} IS {}").format(sql.SQL(fq), comment))
```

Chuyển sang CSV bằng `pyarrow.csv` (mã C++) thay vì ghi từng dòng Python giúp phần chuẩn bị dữ liệu chỉ tốn vài phần trăm giây cho mỗi bảng (giá trị `read=` trong log nạp), để thời gian còn lại dành cho truyền dữ liệu. Toàn văn loader ở Phụ lục B, log đầy đủ của lần chạy ở Phụ lục E.

## 5.5. Tạo tầng ngữ nghĩa

Các tệp SQL trong `sql/` được đặt tên theo thứ tự chạy: `10_presentation_views.sql` tạo tầng ngữ nghĩa, `90_anchor_checks.sql` chứa các truy vấn kiểm tra số neo (mỗi truy vấn kèm chú thích `-- check: tên | expected: giá trị | tol: sai số`). Loader tự áp dụng các tệp `[0-8]*.sql` sau khi nạp; khi chỉ sửa view mà không cần nạp lại dữ liệu, chạy `loader/apply_sql.py`. Tệp view bắt đầu bằng `DROP SCHEMA IF EXISTS presentation CASCADE` và chạy trong một giao dịch, nên hoặc toàn bộ tầng ngữ nghĩa được tạo mới, hoặc giữ nguyên bản cũ. Log áp dụng (Phụ lục E) cho thấy {{var:n_views}} view và bảng `dim_state` được tạo trong chưa đến một giây. Sau đó `loader/validate.py` đọc lại Parquet để so số dòng với Postgres và chạy các truy vấn trong `90_anchor_checks.sql`, xuất `evidence/validation.md` và `evidence/validation.json` (kết quả ở Mục 6.4).

{{evidence:sql?}}

## 5.6. Triển khai Apache Superset

Superset được đóng gói bằng `superset/Dockerfile` từ image `apache/superset:4.1.2`, cài thêm `psycopg2-binary` (image gốc không kèm driver Postgres). Script `docker-init.sh` chạy `superset db upgrade`, `superset fab create-admin` (từ biến môi trường, bỏ qua nếu đã có), `superset init` rồi khởi động web server — mọi bước idempotent nên container khởi động lại bất kỳ lúc nào. Dashboard được dựng bằng script gọi **REST API** (dashboard-as-code): lấy access/CSRF token, tạo *Database* trỏ tới Neon, đăng ký mỗi view `presentation.v_*` thành *Dataset*, tạo *Chart* (loại biểu đồ, metric, nhóm theo, định dạng), tạo *Dashboard* có tab, gắn native filter và phạm vi. Nhờ vậy dashboard dựng lại giống hệt trên máy khác bằng một lệnh và được quản lý bằng Git.

{{evidence:superset_setup?}}

{{evidence:docker?}}

{{dashboard_log}}

## 5.7. Xử lý lỗi và các vấn đề kỹ thuật

Bảng: Các vấn đề kỹ thuật và cách xử lý
| Vấn đề | Nguyên nhân | Cách xử lý |
|---|---|---|
| Máy Windows không có Python | Môi trường không đồng nhất giữa thành viên | Container `tools` (`python:3.12-slim`) chạy mọi script |
| `COPY`/DDL qua endpoint pooled có thể lỗi | PgBouncer ở chế độ transaction không giữ trạng thái phiên | Loader tự đổi sang endpoint direct (bỏ `-pooler`) |
| Superset không kết nối được Postgres | Image gốc không có driver | Cài `psycopg2-binary` trong Dockerfile |
| Script khởi động lỗi `\r` trên Linux | Tệp soạn trên Windows có kết thúc dòng CRLF | `sed -i 's/\r$//'` trong Dockerfile |
| Truy vấn đầu tiên chậm hoặc timeout | Compute Neon đang ở trạng thái scale-to-zero | `connect_timeout=30`; cache Superset 600 s; mở trước dashboard khi demo |
| Tổng doanh thu lệch vài xu | Dùng kiểu số thực cho tiền | Ánh xạ `DECIMAL` → `NUMERIC(p,s)` |
| Giá trị timestamp không hợp lệ khi COPY | Arrow lưu nano giây, Postgres chỉ tới micro giây | Ép `timestamp[ns]` → `timestamp[us]` trước khi ghi CSV |
| Chuỗi rỗng bị hiểu thành NULL | CSV không phân biệt ô trống và chuỗi rỗng | `quoting_style="all_valid"`: chuỗi luôn có dấu nháy, ô trống là NULL |
| Mất cột năm/tháng của bảng fact | Bảng gold phân vùng Hive, cột phân vùng nằm trong tên thư mục | `pyarrow.dataset(..., partitioning="hive")` |
| Không tạo được khoá chính | Dữ liệu có NULL hoặc trùng khoá | Bắt lỗi trong giao dịch con, lùi về chỉ mục thường và ghi cảnh báo |
| Bộ lọc thời gian không hoạt động | Bảng chỉ có cột năm, tháng số nguyên | View thêm cột `month_date` kiểu DATE |
| Bản đồ Brazil không hiển thị bang | Country Map cần mã ISO 3166-2 | Bảng `dim_state` với `iso_code = 'BR-' \|\| customer_state` |
| View bị xoá khi nạp lại bảng | `DROP TABLE ... CASCADE` xoá view phụ thuộc | Loader tự áp dụng lại `sql/[0-8]*.sql` sau khi nạp |
| Lộ mật khẩu trong log/repo | Chuỗi kết nối chứa mật khẩu | `.env` trong `.gitignore`; hàm `mask()` che mật khẩu khi log |

[[CẬP NHẬT: bổ sung các lỗi thực tế nhóm gặp khi triển khai (thông báo lỗi, nguyên nhân, cách sửa) nếu khác bảng trên]]

## 5.8. Cách chạy các job và dịch vụ

Trình tự chạy đầy đủ (từ thư mục gốc repo, PowerShell). Các lệnh chạy script Python được liệt kê tự động từ mã nguồn hiện có:

```powershell
# 0. Cấu hình bí mật
Copy-Item .env.example .env      # rồi điền NEON_DATABASE_URL, SUPERSET_SECRET_KEY, ...

# 1. Dựng image và khởi động Superset (http://localhost:8088)
docker compose build
docker compose up -d superset
```

{{run_commands}}

Sau khi chạy xong, mở `http://localhost:8088`, đăng nhập bằng tài khoản quản trị trong `.env` và chọn dashboard của nhóm. Hướng dẫn chi tiết hơn (yêu cầu hệ thống, xử lý sự cố) ở Phụ lục A.
