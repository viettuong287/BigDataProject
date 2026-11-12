# 4. Thiết kế hệ thống

## 4.1. Kiến trúc tổng thể

Hệ thống gồm bốn khối, mỗi khối một trách nhiệm và giao tiếp qua định dạng/giao thức chuẩn (Hình 4.1):

1. **Data Lake (đầu vào):** {{var:n_tables}} bảng Parquet Analytics (8 MB) và {{var:n_gold}} bảng gold (35 MB, fact phân vùng năm/tháng).
2. **Loader (Python trong container `tools`):** pyarrow đọc Parquet → CSV trong bộ nhớ → `COPY FROM STDIN` (psycopg 3) qua endpoint *direct*, tạo khoá chính/chỉ mục, `ANALYZE`, ghi `load_log`, rồi áp dụng tầng ngữ nghĩa; `validate.py` kiểm 19 số neo.
3. **Tầng phục vụ (Neon Postgres 18, aws-ap-southeast-1):** schema `analytics` (16 bảng + `load_log`), `gold` (7 bảng), `presentation` ({{var:n_views}} view + `dim_state`).
4. **Tầng trình bày (Apache Superset 4.1.2 trong Docker, 4 worker Gunicorn):** kết nối Neon qua SQLAlchemy + psycopg2 (endpoint *pooled*); 22 dataset (1 view = 1 dataset), 45 chart, dashboard 7 tab, 7 native filter; metadata lưu trong container Postgres 16 (`superset-db`); cache kết quả 600 s. Dashboard được dựng bằng `build_dashboard.py` qua REST API.

Người dùng nghiệp vụ mở dashboard qua trình duyệt (cổng 8088); giai đoạn Decision/Action đọc trực tiếp view `v_decision_hints` trên Neon.

{{image:PROJECT:docs/architecture.png|Sơ đồ data-flow của hệ thống: Parquet → Loader (COPY, TLS 5432 direct) → Neon (gold, analytics → presentation) → Superset (SQLAlchemy, endpoint pooled) → người dùng; nhánh v_decision_hints → Decision/Action|h=11.5}}

## 4.2. Luồng dữ liệu, định dạng và giao thức

Bảng: Các bước của luồng dữ liệu
| Bước | Từ → Đến | Định dạng / giao thức | Nơi xử lý | Mô tả |
|---|---|---|---|---|
| 1 | Spark → Data Lake | Parquet + Snappy | Cụm Spark (nhóm trước) | 16 bảng Analytics; gold phân vùng Hive năm/tháng |
| 2 | Data Lake → Loader | Arrow (cột) → CSV trong RAM | Container `tools` | `pyarrow.dataset` đọc cả bảng phân vùng; ép timestamp ns → µs |
| 3 | Loader → Neon | Postgres v3, `COPY … FROM STDIN (FORMAT csv)`, TLS, cổng 5432, endpoint direct | Neon compute | DROP/CREATE/COPY trong một giao dịch; PK, index, `ANALYZE`, `load_log` |
| 4 | `analytics`, `gold` → `presentation` | SQL view | Neon compute | Tạo lại schema `presentation` trong một giao dịch |
| 5 | Neon → Superset | SQLAlchemy + psycopg2, TLS, endpoint pooled (PgBouncer) | Superset | Mỗi chart một truy vấn đẩy xuống Neon; cache 600 s |
| 6 | Superset → người dùng | HTTP 8088, JSON + React/ECharts | Trình duyệt | 7 tab, native filter, cross-filter |
| 7 | Neon → Decision/Action | SQL (`v_decision_hints`, `v_seller_watchlist`), CSV, Chart Data API | Giai đoạn sau | Luật, ngưỡng, danh sách người bán cần xử lý |

Nguyên tắc chung là **"tính một lần, đọc nhiều lần"**: phép tính nặng (join fact, window toàn cục, K-Means) đã làm ở Spark; tầng phục vụ chỉ lọc và tổng hợp nhẹ, nên độ trễ chủ yếu do mạng và kết nối (Chương 6).

## 4.3. Thiết kế tầng lưu trữ trên Neon

Bảng: Cấu hình tầng phục vụ Neon (theo `evidence/neon_project.json`)
| Thuộc tính | Giá trị | Lý do |
|---|---|---|
| Project | `bigdata-olist-presentation` ({{var:neon_project_id}}), gói {{var:neon_plan}} | Một project riêng cho giai đoạn Presentation |
| Vùng / phiên bản | `aws-ap-southeast-1` (Singapore), PostgreSQL 18.6 | Vùng gần Việt Nam nhất |
| Compute | {{var:neon_cu}} CU, scale-to-zero khi không hoạt động | Giới hạn gói miễn phí; không tốn compute khi không ai xem |
| Dung lượng | 146 MB (25 bảng + 22 view), giới hạn {{var:neon_branch_gib}} GiB/nhánh | Đủ cho dữ liệu đồ án và thí nghiệm ×10 |
| Database / schema | `olist_analytics`: `analytics`, `gold`, `presentation` | Phân tầng vật lý – ngữ nghĩa |
| Kết nối | Loader: endpoint *direct*; Superset và đo độ trễ: endpoint *pooled* | `COPY`/DDL cần phiên ổn định; BI cần nhiều kết nối ngắn |

Tách ba schema thể hiện nguyên tắc **phân tầng**: `analytics` và `gold` phản ánh cấu trúc do nhóm trước quyết định, còn `presentation` là giao diện ổn định cho người dùng và nhóm sau; khi nhóm trước đổi tên cột, chỉ cần sửa view.

**DDL tự sinh và ánh xạ kiểu.** Loader không chứa `CREATE TABLE` viết tay: DDL được sinh từ schema Arrow; kiểu chưa ánh xạ gây lỗi ngay. **Tiền tệ giữ `NUMERIC(p,s)`** để tổng 13.494.400,74 BRL khớp đến từng xu; **timestamp nano giây ép về micro giây**; **chuỗi rỗng và NULL được phân biệt** bằng cách đặt mọi giá trị hợp lệ trong dấu nháy khi ghi CSV. Mỗi bảng có `COMMENT ON TABLE` ghi grain và nguồn.

**Nạp idempotent, nhật ký, chỉ mục.** Mỗi lần chạy có một `run_id`; với từng bảng, `DROP … CASCADE`, `CREATE`, `COPY` (khối 1 MiB) và `COMMENT` nằm trong **một giao dịch**, nên người dùng luôn thấy bản cũ hoặc bản mới hoàn chỉnh. Sau đó loader tạo khoá chính theo grain của data contract (vi phạm thì lùi về chỉ mục thường), chỉ mục phụ trên cột bộ lọc của bảng lớn (`rfm_segment`, `customer_state`, `cluster`, `seller_state`, `purchase_date`, `category`, `seller_id`, `main_payment_type`), `ANALYZE`, rồi so `count(*)` với Parquet; lệch thì kết thúc với mã lỗi. `analytics.load_log` lưu mỗi bảng mỗi lần nạp một dòng; view `v_load_log` hiển thị độ tươi và nguồn gốc dữ liệu trên dashboard.

## 4.4. Thiết kế tầng ngữ nghĩa

Tầng ngữ nghĩa (`sql/10_presentation_views.sql`) bắt đầu bằng `DROP SCHEMA IF EXISTS presentation CASCADE` rồi tạo lại toàn bộ, nên luôn nhất quán với dữ liệu vừa nạp. Bốn quy tắc: (1) **không tính lại** những gì Spark đã tính (Pareto, NTILE, K-Means), chỉ gắn nhãn và thêm cột dẫn xuất nhẹ; (2) **thêm cột phục vụ trình bày** — `month_date` kiểu DATE cho bộ lọc thời gian, `dim_state` với tên bang, vùng và `iso_code = 'BR-' || customer_state` cho Country Map, nhãn tiếng Việt, tên nghiệp vụ cho 4 cụm K-Means; (3) **giữ quy tắc bàn giao** — khung 2017-01 → 2018-08, đơn hợp lệ, đếm `customer_unique_id`, review chỉ ở cấp đơn; (4) **mã hoá gợi ý quyết định** thành dữ liệu (số vi phạm, lý do, mức ĐỎ/VÀNG, hành động).

Các view được nhóm theo chủ đề: **xu hướng** (`v_kpi_monthly`, `v_kpi_overview`, `v_orders`), **danh mục** (`v_category_pareto`, `v_category_seasonality`, `v_category_monthly`, `v_sales_items`), **địa lý** (`v_state_logistics`, `v_insight_distance`), **khách hàng** (`v_rfm_customers`, `v_rfm_segments`, `v_cluster_profile`, `v_repeat_*`), **người bán** (`v_seller_pareto`, `v_seller_watchlist`), **giao hàng – thanh toán** (`v_late_vs_review`, `v_delay_vs_review`, `v_payment_mix`), **quyết định** (`v_decision_hints`) và **nguồn gốc dữ liệu** (`v_load_log`). Danh mục đầy đủ ở Phụ lục D.

**Hai lớp dữ liệu cho bộ lọc.** Bảng Analytics có grain cố định (`category_pareto` không có tháng, `kpi_monthly` không có bang) nên không lọc chéo được. Lớp **cấp đơn/sản phẩm** (`v_orders`, `v_sales_items`, `v_category_monthly` từ gold) phục vụ thẻ KPI và xu hướng cần lọc tự do theo tháng × bang × danh mục × PTTT; lớp **insight** (view trên `analytics.*`) phục vụ kết quả phân tích toàn kỳ như Pareto, RFM, watchlist. Ví dụ: `AVG(late_flag)` trên `v_orders` cho tỷ lệ trễ đúng định nghĩa trên mọi tổ hợp bộ lọc, thay vì trung bình các tỷ lệ tháng.

## 4.5. Thiết kế dashboard và giao diện với Decision/Action

Dashboard "Olist E-commerce · Analytics → Presentation" gồm bảy tab theo sáu chủ đề của Analytics cộng một tab quyết định; mỗi tab theo mẫu "tổng quan → chi tiết" (thẻ KPI → biểu đồ → bảng).

Bảng: Thiết kế dashboard theo tab và nhóm người dùng
| Tab | Người dùng chính | Câu hỏi nghiệp vụ | Thành phần chính |
|---|---|---|---|
| 1 · Tổng quan & xu hướng | Ban điều hành | Doanh thu tăng thế nào? Vận hành có theo kịp? | 6 thẻ KPI, doanh thu & đơn theo tháng, % trễ vs review, MoM, bảng KPI tô màu |
| 2 · Danh mục & mùa vụ | Quản lý ngành hàng | Ngành nào tạo 80% doanh thu? Mùa vụ? | Pareto top 25, heatmap mùa vụ 2017, ship/doanh thu, xu hướng 6 ngành lớn |
| 3 · Địa lý & logistics | Vận hành – logistics | Bang nào giao chậm, trễ nhiều, review thấp? | Country Map Brazil, bubble ngày giao vs review, % trễ theo bang, band khoảng cách |
| 4 · Khách hàng & RFM | CRM – marketing | Bao nhiêu khách quay lại? Chăm sóc phân khúc nào? | 4 thẻ, donut phân khúc RFM, cụm K-Means, bảng hành động CRM |
| 5 · Seller | Quản lý người bán | Ai tạo 80% doanh thu? Ai lớn nhưng vận hành kém? | Pareto nhóm A/B/C, bubble top 300, bảng watchlist cảnh báo |
| 6 · Giao trễ, review & thanh toán | Vận hành, CSKH, tài chính | Trễ bao nhiêu ngày thì review sụt? | Review trễ vs đúng hạn, ngưỡng ngày trễ vs % 1 sao, payment mix |
| 7 · Gợi ý quyết định & nguồn dữ liệu | Ban điều hành, nhóm Decision | Cần làm gì trước? Dữ liệu nạp lúc nào? | Bảng 7 luật, nhật ký nạp |

Bảy native filter — Khoảng thời gian (`month_date`), Bang khách hàng, Vùng, Danh mục, Phân khúc RFM, Phương thức thanh toán, Bang seller — chỉ gắn vào chart có cột tương ứng (phạm vi do script tính tự động). Màu nổi bật chỉ dành cho ngoại lệ (tháng Black Friday, ô review < 4, trễ > 10%); không dùng biểu đồ tròn cho 74 danh mục hay 27 bang.

**Giao diện với Decision/Action.** View `v_decision_hints` có mỗi dòng là một luật: ưu tiên, mức độ, chủ đề, tín hiệu, giá trị hiện tại, ngưỡng, hành động và view nguồn. Giá trị được tính lại mỗi lần truy vấn nên luật tự cập nhật khi dữ liệu được nạp lại.

Bảng: Bảy luật gợi ý quyết định trong v_decision_hints
| # | Mức | Chủ đề | Tín hiệu / ngưỡng | Hành động khuyến nghị |
|---|---|---|---|---|
| 1 | CAO | Người bán | Top 10% doanh thu vi phạm ≥ 2 tiêu chí (review < 4, giao > 15 ngày, trễ > 10%): 75/153 | Cảnh cáo, giảm hiển thị, kế hoạch SLA 30 ngày |
| 2 | CAO | Giao hàng | Review đúng hạn 4,29 vs trễ 2,56 (chênh > 1 sao) | Cảnh báo người bán khi đơn trễ 1–3 ngày |
| 3 | CAO | Vận hành | Tháng trễ > 15%: 03/2018 (21,36%), 02/2018 (15,99%) | Tăng năng lực vận chuyển trước cao điểm |
| 4 | TRUNG BÌNH | Địa lý | 9 bang trễ > 10% và review < 4 | Kho/người bán vùng; báo ngày giao thực tế |
| 5 | TRUNG BÌNH | Danh mục | Ngành > 100k BRL có phí ship > 20% doanh thu | Không free-ship đại trà |
| 6 | TRUNG BÌNH | Khách hàng | 1.961 khách At Risk | Win-back có mục tiêu |
| 7 | THẤP | Người bán | 17,65% người bán tạo 80% doanh thu | Account manager cho nhóm A |

## 4.6. Lựa chọn công nghệ và lý do

Bảng: Công nghệ sử dụng, vai trò và lý do lựa chọn
| Công nghệ | Vai trò trong kiến trúc | Lý do chọn |
|---|---|---|
| Parquet + pyarrow | Định dạng nhận từ Analytics; đọc cả thư mục phân vùng Hive | Giữ kiểu Spark (decimal, date); không cần Spark để đọc bảng đã cô đọng |
| Python loader + psycopg 3 (`COPY`) trong `python:3.12-slim` | Tạo bảng đúng kiểu, nạp hàng loạt, PK/index, `load_log` | `COPY` nhanh hơn INSERT nhiều lần; máy Windows không cần cài Python; chạy lại được |
| Neon Postgres 18 (serverless) | Serving layer: `analytics`, `gold`, `presentation` | SQL chuẩn, tách compute/storage, scale-to-zero, chia sẻ qua Internet + TLS, không phải tự vận hành |
| View SQL | Semantic layer, luật cảnh báo | KPI định nghĩa một nơi, có version control, dùng chung cho dashboard và Decision |
| Apache Superset 4.1.2 (Docker, 4 worker) | Dashboard, chart, native filter, cache | Mã nguồn mở, REST API để dựng dashboard bằng mã, Country Map Brazil |
| Postgres 16 (`superset-db`) | Metadata của Superset | SQLite khoá ghi toàn cục khiến chart tải song song phải xếp hàng |
| Playwright (Chromium headless) | Chụp ảnh, đo thời gian tải dashboard và từng chart | Tự động, nhất quán, chạy lại được |

**Vì sao Superset?** So với Power BI/Tableau (thương mại, tệp nhị phân khó quản lý phiên bản), Grafana (mạnh về chuỗi thời gian giám sát, yếu với Pareto/xếp hạng) và Metabase (ít loại biểu đồ), Superset chạy bằng Docker, kết nối thẳng Postgres và cho phép **dựng dashboard bằng mã** — then chốt cho yêu cầu tái lập. **Vì sao Neon?** Postgres cục bộ không chia sẻ được cho nhóm, giảng viên và giai đoạn sau; ClickHouse chỉ phát huy ở hàng tỷ dòng chi tiết; DuckDB không có máy chủ phục vụ đồng thời. Neon cho Postgres chuẩn, được quản lý, khớp tải không đều của dashboard. Cấu hình chi tiết (Compose, `superset_config.py`) ở Phụ lục F.
