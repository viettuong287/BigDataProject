# Phụ lục A. Hướng dẫn chạy

## A.1. Yêu cầu hệ thống

- Docker Desktop (Windows/macOS) hoặc Docker Engine + Compose v2 (Linux); khoảng 4 GB RAM trống cho Superset.
- Tài khoản Neon (gói miễn phí) và chuỗi kết nối tới database `olist_analytics`.
- Mã nguồn: `git clone {{var:repo_url}}`. Dữ liệu đầu vào đã nằm trong `data/analytics/` (sao chép từ repo Analytics); nếu thiếu, sao chép thư mục `data/analytics/` của repo Analytics vào cùng vị trí.
- Không cần cài Python trên máy host (mọi script chạy trong container `tools`).

## A.2. Các bước chạy

```powershell
# 1. Cấu hình
Copy-Item .env.example .env
#    điền NEON_DATABASE_URL (endpoint pooled, sslmode=require), SUPERSET_SECRET_KEY, mật khẩu admin

# 2. Dựng image, khởi động Superset
docker compose build
docker compose up -d superset
docker compose ps                     # superset ở trạng thái healthy
```

{{run_commands}}

Mở `http://localhost:8088`, đăng nhập bằng `SUPERSET_ADMIN_USER` / `SUPERSET_ADMIN_PASSWORD`. Dừng hệ thống: `docker compose down` (giữ volume metadata) — chỉ dùng `docker compose down -v` khi muốn xoá cả metadata Superset.

## A.3. Sinh lại báo cáo này

```powershell
# Cách 1: Python trên máy (đã cài Python 3.12)
python -m venv report\.venv
report\.venv\Scripts\python -m pip install -r report\requirements.txt
report\.venv\Scripts\python report\build_report.py

# Cách 2: không cài Python, dùng Docker
docker run --rm -v "${PWD}:/work" -v "D:\Analytics-main:/upstream:ro" -e ANALYTICS_REPO=/upstream `
  -w /work python:3.12-slim sh -c "pip install -q -r report/requirements.txt && python report/build_report.py"
```

Mở tệp `report/BaoCao_DoAn_BigData.docx` bằng Word, nhấn **Ctrl+A rồi F9** để cập nhật mục lục, danh mục hình và danh mục bảng (Word cũng hỏi cập nhật trường khi mở tệp). Ảnh đặt vào `evidence/` hoặc `docs/` sẽ được tự động chèn vào đúng chương theo từ khoá trong tên tệp (`dashboard`, `filter`, `neon`, `load`, `latency`, `sql`, `watchlist`, `architecture`…); chú thích có thể ghi đè trong `report/content/captions.json`.

## A.4. Xử lý sự cố thường gặp

Bảng: Sự cố thường gặp khi chạy lại hệ thống
| Hiện tượng | Cách xử lý |
|---|---|
| `docker` không được nhận trong PowerShell | Thêm `%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin` vào `PATH` hoặc mở lại terminal sau khi khởi động Docker Desktop |
| Loader báo "Thiếu NEON_DATABASE_URL" | Kiểm tra tệp `.env` ở thư mục gốc và tên biến |
| Kết nối Neon timeout lần đầu | Compute đang ngủ (scale-to-zero); chạy lại hoặc tăng `connect_timeout` |
| Superset không lên (unhealthy) | `docker compose logs superset`; kiểm tra `SUPERSET_SECRET_KEY` đã đặt |
| Dashboard trống sau khi nạp lại | Chạy lại script tạo view (view bị xoá theo `DROP ... CASCADE`) |

# Phụ lục B. Cấu hình

Các tệp cấu hình dưới đây được trích nguyên văn từ repo tại thời điểm sinh báo cáo. Tệp `.env` chứa bí mật nên **không** được đưa vào báo cáo; chỉ trích `.env.example`.

{{file:.env.example|ini|40}}

{{file:docker-compose.yml|yaml|80}}

{{file:superset/superset_config.py|python|60}}

{{file:superset/Dockerfile|docker|30}}

{{file:loader/Dockerfile|docker|30}}

{{file:loader/requirements.txt|text|20}}

{{file:loader/load_to_neon.py|python|120}}

# Phụ lục C. Schema dữ liệu

## C.1. Ánh xạ kiểu và ví dụ bản ghi

{{type_mapping}}

Ví dụ bản ghi thực tế đọc từ Parquet (một dòng của ba bảng tiêu biểu):

{{sample_records}}

## C.2. Quy mô các bảng đầu vào

{{size_table}}

{{chart:table_sizes|Số dòng của từng bảng Analytics (thang log): hai bảng cấp khách hàng chiếm gần như toàn bộ khối lượng}}

{{gold_table}}

## C.3. Schema 16 bảng Analytics

Schema chi tiết của {{var:n_tables}} bảng Parquet đầu vào và kiểu PostgreSQL tương ứng trong schema `analytics` (sinh tự động bằng pyarrow khi tạo báo cáo).

{{schema_appendix}}

# Phụ lục D. Tầng ngữ nghĩa: danh mục view và mã SQL

{{views}}

{{sql_files}}

# Phụ lục E. Minh chứng thực nghiệm chi tiết

## E.1. Kết quả và log nạp dữ liệu

{{load_log}}

{{file:evidence/load_run.log|text|40}}

## E.2. Log áp dụng tầng ngữ nghĩa

{{file:evidence/apply_sql.log|text|40}}

## E.3. Đối chiếu số dòng và giá trị kỳ vọng

{{validation:rows}}

{{expected_checks}}

## E.4. Danh sách tệp minh chứng

{{evidence_files}}

# Phụ lục F. Mã nguồn

- Kho mã nguồn của nhóm: {{var:repo_url}}
- Repo giai đoạn trước (Analytics): [[CẬP NHẬT: URL repo Analytics]]; repo Processing: https://github.com/NguyenAlpha/big-data
- Thư mục dữ liệu đầu vào được dùng khi sinh báo cáo: `{{var:analytics_dir}}`

{{source_tree}}

Bảng: Vị trí các thành phần trong repo
| Thành phần | Đường dẫn |
|---|---|
| Loader Parquet → Neon | `loader/` |
| Mã SQL tầng ngữ nghĩa | `sql/` |
| Cấu hình và script Superset | `superset/` |
| Script tiện ích (đo latency, chụp ảnh, kiểm tra) | `scripts/` |
| Minh chứng (log, số đo, ảnh) | `evidence/` |
| Tài liệu, sơ đồ, tài liệu bàn giao upstream | `docs/` |
| Báo cáo (script sinh, nội dung, hình) | `report/` |

# Phụ lục G. Bảng phân công và đóng góp

{{team_table}}

Bảng: Ma trận đóng góp theo sản phẩm bàn giao (C = chính, H = hỗ trợ)
| Sản phẩm | TV1 | TV2 | TV3 | TV4 | TV5 |
|---|---|---|---|---|---|
| Project Neon, loader, load_log | C | H | | H | |
| View ngữ nghĩa, định nghĩa KPI | H | C | H | | |
| Superset Docker, dashboard, bộ lọc | | H | C | H | |
| Đo hiệu năng, kiểm thử, ảnh minh chứng | H | | H | C | |
| Báo cáo, sơ đồ, README | | H | | H | C |

[[CẬP NHẬT: điều chỉnh ma trận theo phân công thực tế và tỷ lệ % đóng góp đã thống nhất trong nhóm]]

# Phụ lục H. Ghi chú sử dụng công cụ AI

Theo Mục 8 của yêu cầu đồ án, nhóm ghi nhận việc sử dụng AI tạo sinh như sau:

Bảng: Ghi nhận sử dụng công cụ AI
| Công cụ | Mục đích sử dụng | Phần nhóm đã kiểm tra / chỉnh sửa |
|---|---|---|
| Trợ lý lập trình AI trong Cursor | Gợi ý cấu trúc mã loader, script dựng dashboard qua REST API, Dockerfile | [[CẬP NHẬT: thành viên kiểm tra, nội dung đã sửa]] |
| Trợ lý lập trình AI trong Cursor | Sinh script `report/build_report.py`, biểu đồ matplotlib và bản nháp nội dung báo cáo từ tài liệu bàn giao | [[CẬP NHẬT: thành viên kiểm tra số liệu, đã đối chiếu với analytics_report.md]] |
| [[CẬP NHẬT: công cụ khác nếu có]] | [[CẬP NHẬT]] | [[CẬP NHẬT]] |

Mọi số liệu trong báo cáo được lấy trực tiếp từ tệp Parquet, log và tệp đo của hệ thống (không do AI tự tạo); các quyết định kỹ thuật (chọn Neon, Superset, thiết kế schema, định nghĩa KPI, tiêu chí đánh giá) đã được nhóm thảo luận và có lập luận ở Chương 2, 4 và 6. Nhóm chịu trách nhiệm hoàn toàn về nội dung nộp và có thể giải thích từng thành phần của hệ thống.
