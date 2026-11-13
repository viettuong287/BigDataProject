# Phụ lục A. Hướng dẫn chạy

**Yêu cầu:** Docker Desktop (đã thử với Docker 29), Git, Internet, một database Neon (gói miễn phí đủ dùng). Không cần cài Python trên máy host.

```powershell
git clone https://github.com/viettuong287/BigDataProject.git
cd BigDataProject
copy .env.example .env      # điền NEON_DATABASE_URL (endpoint pooled), SUPERSET_SECRET_KEY, mật khẩu admin

# 1. Nạp dữ liệu vào Neon (~5–6 phút, phụ thuộc băng thông tải lên) và kiểm chứng
docker compose build tools
docker compose run --rm tools python loader/load_to_neon.py   # schema, COPY 23 bảng, index, view
docker compose run --rm tools python loader/validate.py       # 23 bảng + 19 số neo
docker compose run --rm tools python loader/apply_sql.py      # (tuỳ chọn) chỉ tạo lại view

# 2. Bật Superset (metadata Postgres 16) và dựng dashboard từ code (~4 phút lần đầu)
docker compose up -d superset-db superset
docker compose run --rm tools python superset/build_dashboard.py
#    mở http://localhost:8088/superset/dashboard/olist-presentation/  (admin / mật khẩu trong .env)
#    dự phòng: docker compose run --rm tools python superset/import_dashboard.py

# 3. Tái tạo minh chứng (tuỳ chọn)
docker compose run --rm tools python scripts/measure_latency.py
docker compose run --rm tools python scripts/scale_experiment.py
docker compose run --rm tools python scripts/neon_inventory.py
docker exec olist-superset bash -c 'rm -rf /app/superset_home/cache/*'
docker compose run --rm screenshots                       # ảnh + thời gian tải cold/cache
docker compose run --rm screenshots python scripts/render_diagrams.py

# 4. Landing page (tuỳ chọn): xuất số liệu từ Neon rồi mở http://localhost:8090
docker compose run --rm tools python scripts/export_landing_kpi.py
docker compose up -d web
docker compose run --rm screenshots python scripts/screenshot_landing.py

# 5. Sinh lại báo cáo (Python 3.12 trên máy hoặc trong Docker)
python -m venv report\.venv; report\.venv\Scripts\python -m pip install -r report\requirements.txt
report\.venv\Scripts\python report\build_report.py
powershell -ExecutionPolicy Bypass -File report\tools\word_stats.ps1 -Pdf   # cập nhật mục lục, xuất PDF
```

Tắt hệ thống: `docker compose down` (thêm `-v` sẽ xoá metadata Superset; dữ liệu trên Neon không bị ảnh hưởng). Nếu đang mở dashboard trong trình duyệt khi chạy lại `build_dashboard.py`, hãy tải lại trang để tránh ghi đè cấu hình bộ lọc. Trong Word, nhấn Ctrl+A rồi F9 để cập nhật mục lục và danh mục hình/bảng.

# Phụ lục B. So sánh phương án công nghệ

Bảng: So sánh công cụ trình bày (BI) cho giai đoạn Presentation
| Tiêu chí | Apache Superset | Power BI | Tableau | Grafana | Metabase |
|---|---|---|---|---|---|
| Giấy phép | Mã nguồn mở (Apache 2.0) | Thương mại (chia sẻ cần Pro) | Thương mại | Mã nguồn mở (AGPL) | Mã nguồn mở / thương mại |
| Triển khai | Docker, tự host | Windows Desktop + cloud | Desktop + Server/Cloud | Docker | Docker |
| Thế mạnh | BI SQL-native, nhiều chart, native filter, REST API | Mô hình DAX, thân thiện | Trực quan hoá linh hoạt | Chuỗi thời gian, giám sát | Dễ dùng |
| Hạn chế | Cấu hình ban đầu phức tạp | Khó tái lập bằng mã | Chi phí bản quyền | Yếu với phân tích theo danh mục | Ít loại biểu đồ, bộ lọc hạn chế |
| Dashboard-as-code | Có (REST API, export YAML) | Hạn chế (.pbix nhị phân) | Hạn chế | Có (JSON) | Một phần |

Bảng: So sánh phương án tầng lưu trữ phục vụ
| Tiêu chí | Neon Serverless Postgres | Postgres cục bộ (Docker) | ClickHouse | Đọc thẳng Parquet (DuckDB) |
|---|---|---|---|---|
| Mô hình lưu trữ | Hàng + chỉ mục | Hàng + chỉ mục | Cột (MergeTree) | Cột (tệp) |
| Phù hợp quy mô | Hàng chục–trăm triệu dòng tổng hợp | Giới hạn một máy | Hàng tỷ dòng chi tiết | Lớn, nhưng không phục vụ đồng thời |
| Chia sẻ cho nhóm/giảng viên | Có, qua Internet + TLS | Không | Cần tự host trên cloud | Phải chia sẻ tệp |
| Vận hành | Được quản lý, scale-to-zero | Tự quản lý | Tự quản lý / trả phí | Không có dịch vụ |
| Tương thích BI | Rất tốt (chuẩn Postgres) | Rất tốt | Tốt (driver riêng) | Trung bình |

# Phụ lục C. Data contract chi tiết

{{type_mapping}}

{{gold_table}}

{{schema_compact}}

# Phụ lục D. Danh mục đối tượng tầng ngữ nghĩa

Mã SQL đầy đủ: `sql/10_presentation_views.sql` (tầng ngữ nghĩa) và `sql/90_anchor_checks.sql` (19 kiểm tra số neo) trong repo.

{{views}}

# Phụ lục E. Minh chứng thực nghiệm chi tiết

## E.1. Kết quả nạp từng bảng

{{load_log}}

## E.2. Kiểm tra số neo và nhất quán

{{validation:anchors}}

## E.3. Độ trễ 22 truy vấn dashboard

{{latency:query_latency}}

## E.4. Ảnh chụp bổ sung

{{shot:evidence/dashboard_tab2_danh_muc_mua_vu.png|270,170,1590,1200|Tab 2 "Danh mục & mùa vụ": Pareto top 25, heatmap mùa vụ 2017, tỷ lệ ship/doanh thu|h=10}}

{{shot:evidence/dashboard_tab4_khach_hang_rfm.png|270,170,1590,1200|Tab 4 "Khách hàng & RFM": thẻ khách hàng, phân khúc RFM, cụm K-Means|h=10}}

{{shot:evidence/landing_page_mobile.png|0,0,780,1600|Landing page trên điện thoại (390 px): hero, biểu đồ live replay và thẻ KPI xếp một cột|h=9}}

{{shot:evidence/neon_tables_inventory.png||Kiểm kê Neon sinh từ catalog database: 25 bảng, 22 view, số dòng, dung lượng, 0,25 CU, PostgreSQL 18|h=13}}

## E.5. Kiểm thử QA chức năng

{{qa:full}}

## E.6. Danh sách tệp minh chứng

{{evidence_files}}

# Phụ lục F. Mã nguồn và cấu hình

- Kho mã nguồn của nhóm: {{var:repo_url}}
- Đầu vào upstream: repo `Analytics-main` do nhóm Analytics cung cấp (tài liệu bàn giao sao chép trong `docs/upstream/`); repo Processing: https://github.com/NguyenAlpha/big-data
- `docker-compose.yml` gồm các dịch vụ `superset-db` (Postgres 16, metadata), `superset` (4.1.2, cổng 8088, 4 worker), `tools` (Python 3.12: loader, kiểm chứng, dựng dashboard, đo đạc, xuất `kpi.json`), `screenshots` (Playwright) và `web` (nginx 1.27, landing page, cổng 8090).

{{source_tree}}

{{file:superset/superset_config.py|python|40}}

Biến môi trường (`.env.example`, tệp `.env` thật không được commit): `NEON_DATABASE_URL` (endpoint pooled, `sslmode=require`), `NEON_PROJECT_ID`, `SUPERSET_SECRET_KEY`, `SUPERSET_ADMIN_USER`, `SUPERSET_ADMIN_PASSWORD`.

# Phụ lục G. Bảng phân công và đóng góp

{{team_table}}

Bảng: Ma trận đóng góp theo sản phẩm bàn giao (C = chính, H = hỗ trợ)
| Sản phẩm | Võ Việt Tường | Nguyễn Hoàng Phi Long | Mai Hồng Phong |
|---|---|---|---|
| Kiến trúc, ranh giới, data contract | C | H | H |
| Project Neon, loader, `load_log`, `validate.py` | C | H | |
| Tầng ngữ nghĩa: 22 view, KPI, luật quyết định | H | C | |
| Superset Docker, dashboard 7 tab, 7 bộ lọc | H | C | H |
| Đo độ trễ, tải dashboard, thí nghiệm ×10 | H | | C |
| Ảnh minh chứng, kiểm thử bộ lọc, kiểm kê Neon | | H | C |
| Báo cáo, README, tài liệu tham khảo | H | H | C |
| Tích hợp Docker Compose, GitHub | C | | H |
| **Mức đóng góp** | **100%** | **100%** | **100%** |

# Phụ lục H. Ghi chú sử dụng công cụ AI

Theo Mục 8 của yêu cầu đồ án, nhóm xin cam kết như sau. Trong quá trình thực hiện, nhóm có sử dụng trợ lý lập trình AI (các agent trong trình soạn thảo Cursor) để hỗ trợ: gợi ý khung mã cho loader, script dựng dashboard qua REST API, script đo đạc và Dockerfile; gợi ý câu lệnh SQL cho tầng ngữ nghĩa; dựng script sinh báo cáo và bản nháp nội dung báo cáo từ tài liệu bàn giao và các tệp minh chứng.

Nhóm đã tự chạy toàn bộ hệ thống, đọc và chỉnh sửa mã, kiểm tra lại số liệu: mọi con số trong báo cáo được lấy trực tiếp từ tệp Parquet, log và tệp đo trong `evidence/` (không do AI tự tạo), được đối chiếu với 19 số neo của nhóm Analytics và với ảnh chụp dashboard. Các quyết định kỹ thuật — chọn Neon và Superset, thiết kế schema, định nghĩa KPI, luật gợi ý quyết định và tiêu chí đánh giá — do nhóm thảo luận và có lập luận ở Chương 2, 4 và 6. Nhóm chịu trách nhiệm hoàn toàn về nội dung nộp và có thể giải thích từng thành phần của hệ thống.
