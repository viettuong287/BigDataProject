# 5.8. Khả năng tái lập

> **Yêu cầu 5.8 (đề bài):** Nộp mã nguồn/cấu hình cần thiết, hướng dẫn chạy, yêu cầu môi trường và dữ liệu mẫu hoặc script sinh dữ liệu để người khác có thể kiểm tra.

**Mã nguồn và cấu hình.** Toàn bộ nằm trong repo `https://github.com/viettuong287/BigDataProject` (nhánh `main`):

Bảng: Vị trí mã nguồn và cấu hình trong repo {w=3.6,12.4}
| Thư mục / tệp | Nội dung |
|---|---|
| `docker-compose.yml` | 5 service: `superset-db` (Postgres 16), `superset` (4.1.2, cổng 8088, 4 worker), `tools` (Python 3.12), `screenshots` (Playwright), `web` (nginx, cổng 8090) |
| `.env.example` | Mẫu biến môi trường: `NEON_DATABASE_URL` (endpoint pooled, `sslmode=require`), `NEON_PROJECT_ID`, `SUPERSET_SECRET_KEY`, `SUPERSET_ADMIN_USER`, `SUPERSET_ADMIN_PASSWORD`; tệp `.env` thật không commit |
| `loader/` | `load_to_neon.py` (nạp 23 bảng), `validate.py` (23 bảng + 19 số neo), `apply_sql.py` (chỉ tạo lại view), `common.py`, `Dockerfile`, `requirements.txt` |
| `sql/` | `10_presentation_views.sql` (tầng ngữ nghĩa), `90_anchor_checks.sql` (19 kiểm tra) |
| `superset/` | `Dockerfile`, `superset_config.py`, `build_dashboard.py` (dựng dashboard qua REST API), `import_dashboard.py` + `export/dashboard_olist_presentation.zip` (dự phòng), `i18n/` (bản dịch tiếng Việt), `branding/`, `dashboard.css` |
| `scripts/` | `measure_latency.py`, `scale_experiment.py`, `neon_inventory.py`, `take_screenshots.py`, `qa_check.py` + `qa_run.ps1`, `export_landing_kpi.py`, `render_diagrams.py` |
| `web/` | Landing page tĩnh + `nginx.conf`; `data/kpi.json` |
| `docs/` | `architecture.md/.png`; `upstream/` – tài liệu bàn giao của nhóm trước |
| `evidence/` | Log, CSV/MD số đo, ảnh minh chứng |

**Yêu cầu môi trường.** Docker Desktop (đã chạy với Docker 29, Compose v2) trên Windows/macOS/Linux; Git; kết nối Internet; một database Neon (gói miễn phí đủ dùng, nhóm em dùng vùng `aws-ap-southeast-1`); khoảng 4 GB RAM trống cho Superset. Không cần cài Python lên máy vì mọi script chạy trong container `tools`.

**Dữ liệu mẫu.** Dữ liệu đầu vào đầy đủ (23 bảng Parquet, 42,88 MB) đã nằm sẵn trong repo ở `data/analytics/` và `data/gold/`, kèm tài liệu bàn giao trong `docs/upstream/`. Nguồn gốc là bộ công khai *Brazilian E-Commerce Public Dataset by Olist* (Kaggle); để tạo lại từ CSV gốc thì dùng repo của nhóm Processing (`https://github.com/NguyenAlpha/big-data`) và Analytics (`Analytics-main`). Dữ liệu cho thí nghiệm ×10 do `scripts/scale_experiment.py` tự sinh trên Neon bằng `generate_series`.

**Hướng dẫn chạy** (PowerShell, từ thư mục gốc repo; giống README mục 5):

```powershell
git clone https://github.com/viettuong287/BigDataProject.git
cd BigDataProject
copy .env.example .env        # điền NEON_DATABASE_URL, SUPERSET_SECRET_KEY, mật khẩu admin

# Bước 1 – nạp dữ liệu vào Neon và kiểm chứng (~5 phút, phụ thuộc băng thông tải lên)
docker compose build tools
docker compose run --rm tools python loader/load_to_neon.py   # schema, COPY 23 bảng, index, view
docker compose run --rm tools python loader/validate.py       # kỳ vọng: 23/23 bảng, 19/19 số neo

# Bước 2 – bật Superset và dựng dashboard từ code (~4 phút lần đầu)
docker compose up -d superset-db superset                     # chờ trạng thái healthy
docker compose run --rm tools python superset/build_dashboard.py
#   mở http://localhost:8088/superset/dashboard/olist-presentation/ (admin / mật khẩu trong .env)
#   dự phòng: docker compose run --rm tools python superset/import_dashboard.py

# Bước 3 – tái tạo minh chứng (tuỳ chọn)
docker compose run --rm tools python scripts/measure_latency.py
docker compose run --rm tools python scripts/scale_experiment.py
docker compose run --rm tools python scripts/neon_inventory.py
docker exec olist-superset bash -c 'rm -rf /app/superset_home/cache/*'
docker compose run --rm screenshots                           # ảnh + thời gian tải cold/cache
powershell -ExecutionPolicy Bypass -File scripts\qa_run.ps1   # 41 ca QA → evidence/qa_test_cases.md

# Bước 4 – landing page (tuỳ chọn)
docker compose run --rm tools python scripts/export_landing_kpi.py
docker compose up -d web                                      # http://localhost:8090
```

**Cách người khác kiểm tra kết quả.** Sau bước 1, `validate.py` phải in 23/23 bảng khớp và 19/19 số neo đạt; sau bước 2, dashboard có 7 tab, 45 biểu đồ, không biểu đồ lỗi; bước 3 sinh lại các tệp trong `evidence/` để so với số trong báo cáo. Loader, view và `build_dashboard.py` đều idempotent nên chạy lại không tạo trùng. Ca QA TC41 đã tự kiểm mọi script/service mà README nhắc tới đều tồn tại và `docker compose config` hợp lệ. Tắt hệ thống: `docker compose down` (thêm `-v` sẽ xoá metadata Superset; dữ liệu trên Neon không bị ảnh hưởng).
