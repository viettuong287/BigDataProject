# 4. Thiết kế hệ thống

## 4.1. Kiến trúc tổng thể

Hệ thống gồm bốn khối nối tiếp nhau, mỗi khối có một trách nhiệm duy nhất và giao tiếp qua một định dạng/giao thức chuẩn:

1. **Data Lake (đầu vào):** {{var:n_tables}} bảng Parquet do Spark ghi ra (cùng {{var:n_gold}} bảng gold dùng cho lọc chi tiết). Đây là ranh giới với các nhóm trước.
2. **Loader (Python, chạy trong container `tools`):** đọc Parquet bằng pyarrow, tự sinh DDL, chuyển dữ liệu thành CSV trong bộ nhớ và nạp bằng `COPY FROM STDIN` qua psycopg 3, tạo khoá chính/chỉ mục, kiểm tra số dòng, ghi nhật ký, rồi áp dụng tầng ngữ nghĩa.
3. **Tầng phục vụ (Neon Serverless Postgres 18):** schema `analytics` (bản sao trung thực của output Analytics + `load_log`), schema `gold` (fact/aggregate chi tiết) và schema `presentation` (view ngữ nghĩa `v_*` + bảng dimension `dim_state`).
4. **Tầng trình bày (Apache Superset 4.1 trong Docker):** kết nối tới Neon qua SQLAlchemy + psycopg2; mỗi view là một dataset; chart và dashboard được dựng bằng mã thông qua REST API.

Ở đầu ra, người dùng nghiệp vụ truy cập dashboard qua trình duyệt; giai đoạn Decision/Action đọc trực tiếp các view gợi ý quyết định trên Neon. Hình 4.1 là sơ đồ data-flow do script vẽ từ thiết kế; nếu nhóm có sơ đồ vẽ riêng trong `docs/` hoặc `evidence/`, nó được chèn ngay sau.

{{chart:architecture|Sơ đồ kiến trúc và luồng dữ liệu: Parquet → Loader (COPY) → Neon (analytics/gold → presentation) → Superset → người dùng / Decision-Action}}

{{evidence:architecture?}}

## 4.2. Luồng dữ liệu chi tiết

Bảng: Các bước của luồng dữ liệu, định dạng và giao thức
| Bước | Từ → Đến | Định dạng / giao thức | Nơi xử lý | Mô tả |
|---|---|---|---|---|
| 1 | Spark → Data Lake | Parquet + Snappy | Cụm Spark (nhóm trước) | 16 thư mục bảng Analytics; gold phân vùng Hive năm/tháng |
| 2 | Data Lake → Loader | Arrow in-memory (cột) → CSV trong bộ nhớ | Container `tools` | `pyarrow.dataset` đọc cả bảng phân vùng; ép kiểu timestamp ns → µs |
| 3 | Loader → Neon | Giao thức Postgres v3, `COPY ... FROM STDIN (FORMAT csv)`, TLS (`sslmode=require`), cổng 5432, endpoint *direct* | Neon compute | DROP/CREATE/COPY/COMMENT trong một giao dịch; sau đó PK, index, `ANALYZE`, đếm dòng, ghi `load_log` |
| 4 | `analytics`, `gold` → `presentation` | SQL view (`sql/10_presentation_views.sql`) | Neon compute | Tạo lại toàn bộ schema `presentation` trong một giao dịch |
| 5 | Neon → Superset | SQLAlchemy + psycopg2, TLS | Superset (Docker) | Mỗi chart sinh một truy vấn SQL đẩy xuống Neon; kết quả cache 10 phút |
| 6 | Superset → người dùng | HTTP cổng 8088, JSON + React/ECharts | Trình duyệt | Dashboard nhiều tab, native filter, cross-filter |
| 7 | Neon → Decision/Action | SQL (`v_decision_hints`, `v_seller_watchlist`), CSV export, Chart Data API | Giai đoạn sau | Đọc luật, ngưỡng và danh sách người bán cần xử lý |

Luồng được thiết kế theo nguyên tắc **"tính một lần, đọc nhiều lần"**: các phép tính nặng (join fact, window toàn cục, K-Means) đã được Spark làm ở giai đoạn trước; tầng phục vụ chỉ thực hiện lọc và tổng hợp nhẹ trên bảng đã cô đọng hoặc trên bảng fact đã có chỉ mục, nên độ trễ chủ yếu do mạng và khởi động compute chứ không do tính toán.

## 4.3. Thiết kế tầng lưu trữ trên Neon

### 4.3.1. Tổ chức project, database và schema

Bảng: Cấu hình tầng phục vụ Neon
| Thuộc tính | Giá trị | Lý do |
|---|---|---|
| Project | `bigdata-olist-presentation` | Một project riêng cho giai đoạn Presentation |
| Vùng | `aws-ap-southeast-1` (Singapore) | Vùng gần Việt Nam nhất → giảm độ trễ mạng |
| Phiên bản | PostgreSQL 18 (log nạp ghi nhận 18.6, aarch64) | Phiên bản mới nhất Neon hỗ trợ |
| Database | `olist_analytics` | Tách khỏi database mặc định |
| Schema `analytics` | 16 bảng output Analytics + `load_log` | "Hợp đồng vật lý" với nhóm Analytics |
| Schema `gold` | 7 bảng fact/aggregate | Dữ liệu chi tiết cho lọc chéo và kiểm tra nhất quán |
| Schema `presentation` | {{var:n_views}} view + `dim_state` | "Hợp đồng logic" với người dùng và nhóm sau |
| Kết nối loader | Endpoint *direct* (bỏ `-pooler`) | `COPY`/DDL cần phiên ổn định, không qua PgBouncer |
| Kết nối Superset | Endpoint *pooled* (`-pooler`) | Nhiều truy vấn ngắn, nhiều kết nối đồng thời |
| Autoscaling | [[CẬP NHẬT: khoảng CU thực tế, ví dụ 0,25–2 CU]] | Co giãn theo tải dashboard |
| Scale-to-zero | Sau 5 phút không hoạt động (mặc định) | Không tốn compute khi không ai xem |

Việc tách ba schema thể hiện nguyên tắc **phân tầng**: `analytics` và `gold` phản ánh cấu trúc do các nhóm trước quyết định (thay đổi khi họ thay đổi), còn `presentation` là giao diện ổn định cho người dùng (tên cột, nhãn tiếng Việt, định nghĩa KPI). Khi nhóm trước đổi tên một cột, nhóm chỉ cần sửa view; dashboard và giai đoạn Decision/Action không bị ảnh hưởng.

### 4.3.2. Sinh DDL tự động và ánh xạ kiểu

Loader không chứa `CREATE TABLE` viết tay: DDL được sinh từ schema Arrow trong metadata Parquet theo ánh xạ kiểu của data contract (Mục 3.5); kiểu chưa ánh xạ gây lỗi ngay thay vì âm thầm thành `text`. Các quyết định quan trọng: **tiền tệ giữ `NUMERIC(p,s)`** để tổng 13.494.400,74 BRL khớp đến từng xu (số thực dấu phẩy động gây sai số làm tròn); **timestamp nano giây ép về micro giây** vì PostgreSQL chỉ lưu tới micro giây; **phân biệt chuỗi rỗng và NULL** bằng cách đặt mọi giá trị hợp lệ trong dấu nháy kép khi ghi CSV. Mỗi bảng được gắn `COMMENT ON TABLE` ghi grain và nguồn để tra cứu ngay trong cơ sở dữ liệu.

### 4.3.3. Nạp idempotent, nhật ký và chỉ mục

Mỗi lần chạy sinh một `run_id`. Với từng bảng, `DROP … CASCADE`, `CREATE`, `COPY` (khối 1 MiB) và `COMMENT` nằm trong **một giao dịch**, nên người dùng dashboard hoặc thấy bản cũ, hoặc bản mới hoàn chỉnh. Sau commit, loader tạo khoá chính theo grain của data contract (vi phạm thì lùi về chỉ mục thường và ghi cảnh báo), tạo chỉ mục phụ, `ANALYZE`, rồi so `count(*)` với số dòng Parquet; lệch thì chương trình kết thúc với mã lỗi. Chạy lại bao nhiêu lần cũng cho cùng trạng thái (idempotent).

Chỉ mục phụ chỉ tạo trên cột bộ lọc dùng thường xuyên của các bảng lớn: `rfm_segment`, `customer_state`, `cluster` (bảng khách hàng), `seller_state` (người bán), `purchase_date`, `customer_state`, `category`, `seller_id`, `main_payment_type` (fact gold); 18 bảng còn lại (≤ 3.053 dòng) quét tuần tự chỉ vài mili giây nên không cần. Bảng `analytics.load_log` lưu mỗi bảng mỗi lần nạp một dòng (`run_id`, số dòng Postgres/Parquet, cờ khớp, dung lượng Parquet/CSV, thời gian đọc/COPY/chỉ mục/tổng, thông lượng, thời điểm), đồng thời xuất `evidence/load_log.csv`; view `v_load_log` hiển thị lần nạp gần nhất trên dashboard (độ tươi và nguồn gốc dữ liệu).

## 4.4. Thiết kế tầng ngữ nghĩa

Tầng ngữ nghĩa nằm trong tệp `sql/10_presentation_views.sql`, bắt đầu bằng `DROP SCHEMA IF EXISTS presentation CASCADE` rồi tạo lại toàn bộ — nhờ vậy luôn nhất quán với dữ liệu vừa nạp và chạy lại an toàn. Các view tuân theo bốn quy tắc:

- **Không tính lại** những gì Spark đã tính (Pareto cộng dồn, NTILE, cụm K-Means) — chỉ đổi tên, gắn nhãn và bổ sung cột dẫn xuất nhẹ (hạng, nhóm A/B/C).
- **Bổ sung cột phục vụ trình bày:** `month_date` kiểu `DATE` và `month_label` dựng từ năm/tháng để bộ lọc khoảng thời gian của Superset hoạt động; bảng `dim_state` cung cấp tên bang, vùng (Norte, Nordeste, Centro-Oeste, Sudeste, Sul) và `iso_code = 'BR-' || customer_state` cho biểu đồ Country Map Brazil; nhãn tiếng Việt cho band ngày trễ, kỳ trả góp, cohort; tên nghiệp vụ cho cụm K-Means (C0 "One-shot giá trị thấp", C1 "Khách mua lại", C2 "One-shot chi cao", C3 "One-shot lâu không mua").
- **Giữ quy tắc bàn giao:** khung 2017-01 → 2018-08, đơn hợp lệ, đếm khách bằng `customer_unique_id`, review chỉ lấy ở cấp đơn (`v_sales_items` cấp sản phẩm cố ý không có cột review).
- **Mã hoá gợi ý quyết định** thành dữ liệu: số vi phạm, lý do, mức cảnh báo và hành động khuyến nghị.

Các view được nhóm theo sáu chủ đề của Analytics cộng hai nhóm tiện ích: **xu hướng** (`v_kpi_monthly`, `v_kpi_overview`, `v_orders`), **danh mục** (`v_category_pareto`, `v_category_seasonality`, `v_category_monthly`, `v_sales_items`), **địa lý** (`v_state_logistics`, `v_insight_distance`, bảng `dim_state`), **khách hàng** (`v_rfm_customers`, `v_rfm_segments`, `v_cluster_profile`, `v_repeat_*`), **người bán** (`v_seller_pareto`, `v_seller_watchlist`), **giao hàng – review – thanh toán** (`v_late_vs_review`, `v_delay_vs_review`, `v_payment_mix`), **quyết định** (`v_decision_hints`) và **nguồn gốc dữ liệu** (`v_load_log`). Danh mục đầy đủ (nguồn, mục đích) và mã SQL ở Phụ lục D.

Ví dụ: view `v_seller_watchlist` biến danh sách người bán của Analytics thành dữ liệu hành động được — mỗi tiêu chí (review < 4, giao > 15 ngày, trễ > 10%) thành một cờ 0/1, cộng lại thành `violations`, ghép thành chuỗi `reasons`, và `alert_level` là ĐỎ khi vi phạm từ hai tiêu chí trở lên, ngược lại là VÀNG, kèm `recommended_action` tương ứng.

## 4.5. Thiết kế dashboard theo người dùng nghiệp vụ

Dashboard "Olist E-commerce · Analytics → Presentation" (dựng bởi `superset/build_dashboard.py`) gồm bảy tab bám theo sáu chủ đề của Analytics cộng một tab quyết định, mỗi tab phục vụ một nhóm người dùng. Bố cục mỗi tab theo mẫu "tổng quan → chi tiết": hàng thẻ KPI, biểu đồ chính, rồi bảng chi tiết.

Bảng: Thiết kế dashboard theo tab và nhóm người dùng
| Tab | Người dùng chính | Câu hỏi nghiệp vụ | Thành phần chính (view) |
|---|---|---|---|
| Tổng quan & xu hướng | Ban điều hành | Doanh thu tăng thế nào? Vận hành có theo kịp? | Thẻ KPI (`v_orders`, `v_kpi_overview`); doanh thu, số đơn, % trễ, review theo tháng (`v_kpi_monthly`) |
| Danh mục & mùa vụ | Quản lý ngành hàng | Ngành nào tạo 80% doanh thu? Mùa vụ? Ship ăn biên ngành nào? | Pareto (`v_category_pareto`); heatmap (`v_category_seasonality`); xu hướng ngành (`v_category_monthly`, `v_sales_items`) |
| Địa lý & logistics | Vận hành – logistics | Bang nào giao chậm, trễ nhiều, review thấp? Khoảng cách ảnh hưởng ra sao? | Country Map Brazil, bảng bang (`v_state_logistics`); band km (`v_insight_distance`) |
| Khách hàng & RFM | CRM – marketing | Bao nhiêu khách quay lại? Nên chăm sóc phân khúc nào? | Repeat vs one-shot (`v_repeat_profile`); phân khúc + hành động CRM (`v_rfm_segments`); cụm K-Means; danh mục, bang của khách lặp |
| Seller | Quản lý người bán | Ai tạo 80% doanh thu? Ai lớn nhưng vận hành kém? | Pareto, bubble người bán (`v_seller_pareto`); watchlist ĐỎ/VÀNG (`v_seller_watchlist`) |
| Giao trễ, review & thanh toán | Vận hành, CSKH, tài chính | Trễ bao nhiêu ngày thì review sụt? Cơ cấu thanh toán? | `v_late_vs_review`, `v_delay_vs_review`, `v_payment_mix` |
| Gợi ý quyết định & nguồn dữ liệu | Ban điều hành, giai đoạn Decision/Action | Cần làm gì, ưu tiên nào? Dữ liệu nạp lúc nào? | Bảng luật (`v_decision_hints`); nhật ký nạp (`v_load_log`) |

Bảy native filter: **Khoảng thời gian** (cột `month_date`, áp dụng cho `v_kpi_monthly`, `v_orders`, `v_category_monthly`, `v_sales_items`), **Bang khách hàng**, **Vùng**, **Danh mục**, **Phân khúc RFM**, **Phương thức thanh toán** và **Bang seller**; mỗi bộ lọc chỉ gắn vào các chart có cột tương ứng (phạm vi được script tính tự động).

Các quyết định thiết kế đáng chú ý:

- **Màu có chủ đích:** tháng Black Friday (11/2017), người bán mức ĐỎ và các ô vượt ngưỡng (review < 4, trễ > 10%) dùng màu cam/đỏ; còn lại dùng màu trung tính, để mắt người dùng tập trung vào ngoại lệ.
- **Tránh biểu đồ tròn** cho 74 danh mục hoặc 27 bang (không so sánh được góc nhỏ); dùng cột sắp xếp giảm dần và Pareto.
- **Thang log** cho số khách theo phân khúc RFM vì chênh lệch 65.325 ("One-shot Lost") so với 251 ("Champions") làm các nhóm nhỏ biến mất trên thang tuyến tính.
- **Ghi chú nguồn** dưới mỗi chart (tên view, giai đoạn 2017-01 → 2018-08, đơn vị BRL) và bảng `v_load_log` ở cuối dashboard cho biết dữ liệu được nạp lúc nào.

**Hai lớp dữ liệu cho bộ lọc.** Bảng Analytics là bảng tổng hợp ở grain cố định: `category_pareto` không có cột tháng, `kpi_monthly` không có cột bang, nên không thể lọc chéo trực tiếp. Nhóm giải quyết bằng hai lớp: (1) **lớp cấp đơn/sản phẩm** (`v_orders`, `v_sales_items`, `v_category_monthly` từ gold) cho các thẻ KPI và xu hướng cần lọc tự do theo tháng × bang × danh mục × phương thức thanh toán; (2) **lớp insight** (các view trên `analytics.*`) cho những kết quả phân tích cố định trên toàn kỳ như Pareto, RFM, watchlist. Phạm vi (scope) của từng native filter được cấu hình chỉ gồm những chart có cột tương ứng, và tiêu đề chart ghi rõ "toàn kỳ" với các insight không lọc được.

## 4.6. Giao diện với giai đoạn Decision/Action

Giai đoạn Presentation → Decision/Action cần dữ liệu có cấu trúc, ổn định, không phụ thuộc giao diện. Nhóm cung cấp view `presentation.v_decision_hints`, mỗi dòng là **một luật** gồm: mức ưu tiên, mức độ (CAO/TRUNG BÌNH/THẤP), chủ đề, tín hiệu, giá trị đo hiện tại, chi tiết, ngưỡng, hành động khuyến nghị và view nguồn. Bảy luật hiện tại:

Bảng: Các luật gợi ý quyết định trong v_decision_hints
| Ưu tiên | Mức | Chủ đề | Tín hiệu / ngưỡng | Hành động khuyến nghị |
|---|---|---|---|---|
| 1 | CAO | Người bán | Người bán top 10% doanh thu vi phạm ≥ 2 tiêu chí (review < 4, giao > 15 ngày, trễ > 10%) | Cảnh cáo, giảm hiển thị, yêu cầu kế hoạch SLA 30 ngày |
| 2 | CAO | Giao hàng | Chênh lệch review đúng hạn – trễ > 1 sao | Cảnh báo người bán khi đơn trễ 1–3 ngày, trước mốc 4–7 ngày |
| 3 | CAO | Vận hành theo tháng | Tháng có tỷ lệ trễ > 15% | Tăng năng lực vận chuyển trước cao điểm (T11, T2–T3) |
| 4 | TRUNG BÌNH | Địa lý | Bang trễ > 10% và review < 4 | Người bán/kho vùng; hiển thị ngày giao thực tế trước checkout |
| 5 | TRUNG BÌNH | Danh mục | Ngành doanh thu > 100k BRL có phí ship > 20% doanh thu | Không free-ship đại trà; đưa phí ship vào giá |
| 6 | TRUNG BÌNH | Khách hàng | Khách At Risk (≥ 2 đơn, > 180 ngày chưa quay lại) | Win-back có mục tiêu (email/voucher ngành nhà cửa) |
| 7 | THẤP | Người bán | % người bán tạo 80% doanh thu | Ưu tiên account manager cho nhóm A |

Vì giá trị và ngưỡng được tính trực tiếp từ dữ liệu mỗi lần truy vấn, khi Analytics chạy lại và nhóm nạp lại, các luật tự cập nhật mà không cần sửa mã. Kênh truy cập cho nhóm sau: chuỗi kết nối Postgres (khuyến nghị role chỉ đọc trên schema `presentation`), xuất CSV từ Superset, hoặc Chart Data API của Superset (`/api/v1/chart/{id}/data`).

## 4.7. Lựa chọn công nghệ và lý do

Bảng: Công nghệ sử dụng, vai trò và lý do lựa chọn
| Thành phần | Công nghệ | Vai trò trong kiến trúc | Lý do chọn | Phương án đã cân nhắc |
|---|---|---|---|---|
| Đầu vào | Apache Parquet (Snappy) | Định dạng bàn giao từ Analytics | Có schema, kiểu DECIMAL, nén tốt, đọc nhanh theo cột | CSV (mất kiểu, lớn hơn) |
| Đọc dữ liệu | pyarrow (`dataset`, `csv`) | Đọc Parquet (kể cả phân vùng Hive), chuyển CSV | Thư viện chuẩn của Arrow, không cần Spark cho bảng đã cô đọng | Spark (quá nặng), pandas thuần |
| Nạp dữ liệu | psycopg 3 + `COPY` | Nạp hàng loạt vào Postgres | `COPY` nhanh hơn nhiều lần so với INSERT; hỗ trợ stream theo khối | INSERT batch, `to_sql` |
| Tầng phục vụ | Neon Serverless Postgres 18 | Lưu bảng phục vụ + view ngữ nghĩa | Được quản lý, chia sẻ qua Internet, autoscaling, scale-to-zero, branching, chuẩn Postgres | Postgres cục bộ, ClickHouse, DuckDB |
| Tầng ngữ nghĩa | View SQL (schema `presentation`) | Định nghĩa KPI và luật dùng chung | Dùng chung cho Superset và Decision/Action; quản lý được bằng Git | Chỉ metric trong Superset, dbt |
| Trình bày | Apache Superset 4.1.2 | Dashboard, bộ lọc, chart | Mã nguồn mở, SQL-native, native filter, Country Map Brazil, REST API dựng dashboard bằng mã | Power BI, Tableau, Grafana, Metabase |
| Đóng gói | Docker Compose | Chạy Superset, container công cụ, chụp ảnh | Tái lập trên mọi máy; máy Windows không cần cài Python | Cài đặt thủ công |
| Minh chứng | Playwright (headless Chromium) | Chụp ảnh dashboard tự động | Ảnh nhất quán, chạy lại được | Chụp tay |

**Vì sao Superset?** So với Power BI/Tableau (thương mại, tệp dashboard nhị phân khó quản lý phiên bản, chia sẻ cần tài khoản trả phí), Grafana (mạnh về chuỗi thời gian giám sát nhưng yếu với Pareto, xếp hạng, phân tích theo danh mục) và Metabase (dễ dùng nhưng hạn chế loại biểu đồ, bộ lọc), Superset là dự án Apache chạy bằng một lệnh Docker, kết nối thẳng Postgres, có Country Map cho Brazil, native filter và **REST API để dựng dashboard bằng mã** — yếu tố then chốt cho yêu cầu tái lập.

**Vì sao Neon?** Postgres cục bộ không chia sẻ được cho nhóm, giảng viên và giai đoạn sau; ClickHouse chỉ phát huy ở hàng tỷ dòng chi tiết, còn với khoảng nửa triệu dòng thì chỉ tăng chi phí vận hành; DuckDB đọc Parquet không có máy chủ cho nhiều client đồng thời. Neon cho Postgres chuẩn, được quản lý, có TLS, mô hình serverless khớp với tải không đều của dashboard, và branching cho phép thử thay đổi view trên dữ liệu thật mà không ảnh hưởng dashboard đang dùng.

## 4.8. Cấu hình chính

Bí mật (chuỗi kết nối Neon, khoá Superset, mật khẩu quản trị) chỉ nằm trong `.env` không commit; repo chứa `.env.example`, hàm `mask()` che mật khẩu khi ghi log. Cấu hình Superset (`superset/superset_config.py`): metadata lưu SQLite trong volume `superset_home`, tách khỏi dữ liệu nghiệp vụ trên Neon; bật `DASHBOARD_NATIVE_FILTERS`, `DASHBOARD_CROSS_FILTERS`, `ENABLE_TEMPLATE_PROCESSING`; cache kết quả kiểu filesystem 600 giây — lần mở thứ hai trong 10 phút không truy vấn Neon và không đánh thức compute đang ngủ; `ROW_LIMIT = 50000` bảo vệ trình duyệt khi mở view cấp khách hàng/cấp đơn. Toàn văn cấu hình ở Phụ lục B.
