# 3. Dữ liệu và yêu cầu

## 3.1. Nguồn dữ liệu và dòng dõi

Nguồn gốc là bộ **Brazilian E-Commerce Public Dataset by Olist** [1] trên Kaggle: 9 tệp CSV gồm đơn hàng (99.441 dòng), chi tiết đơn (112.650), thanh toán (103.886), đánh giá (99.224), khách hàng (99.441), người bán (3.095), sản phẩm (32.951), toạ độ mã bưu chính (1.000.163) và bảng dịch danh mục (71) — khoảng **1,55 triệu dòng, ~120 MB CSV**, đã ẩn danh hoá.

Bảng: Dòng dõi dữ liệu từ nguồn đến tầng phục vụ
| Tầng | Nhóm phụ trách | Nội dung | Quy mô |
|---|---|---|---|
| Raw (CSV) | Sources → Ingestion | 9 tệp CSV Olist | ~1,55 triệu dòng, ~120 MB |
| Silver (Parquet) | Storage → Processing | Làm sạch, chuẩn hoá kiểu, khử trùng lặp | 569.698 dòng, 40,37 MB |
| Gold (Parquet) | Storage → Processing | 2 bảng fact + 5 bảng aggregate, đối chiếu 11/11 | 7 bảng, 33,3 MB, 61,72 s Spark |
| Analytics (Parquet) | Processing → Analytics | 14 truy vấn Spark SQL + K-Means k = 4 | {{var:n_tables}} bảng, {{var:total_rows}} dòng, {{var:spark_total_s}} s Spark |
| Serving (Neon) | **Analytics → Presentation** | Schema `analytics`, `gold`, `presentation` | {{var:serving_tables}} bảng ({{var:serving_rows}} dòng) + {{var:n_views}} view |
| Dashboard | **Analytics → Presentation** | Superset: KPI, biểu đồ, bộ lọc, gợi ý quyết định | Nhiều tab theo nhóm người dùng |

Năm quy tắc nghiệp vụ từ tầng gold phải được giữ nguyên khi trình bày: (1) doanh thu chỉ tính trên đơn hợp lệ `is_valid_sale` (98.199/99.441 đơn); (2) đếm khách bằng `customer_unique_id` (99.441 `customer_id` nhưng chỉ 96.096 khách thật); (3) chuỗi thời gian chỉ dùng 2017-01 → 2018-08; (4) điểm review ở cấp đơn, không lấy trung bình theo dòng sản phẩm; (5) phân tích giao hàng loại đơn có cờ chất lượng `dq_*`.

## 3.2. Đặc trưng Big Data của bài toán

Đầu vào trực tiếp của nhóm ở mức trăm nghìn dòng, nhưng bài toán vẫn mang đặc trưng dữ liệu lớn và kiến trúc được thiết kế để giữ nguyên khi quy mô tăng:

- **Volume:** dữ liệu nguồn ~1,55 triệu dòng; nhóm Processing có sẵn kịch bản nhân bản ×5, ×10, ×20. Với một sàn thực tế (hàng chục triệu đơn/năm), bảng cấp khách hàng và người bán tăng tuyến tính lên hàng chục triệu dòng; tầng phục vụ phải chịu được mức này mà không đổi kiến trúc (Mục 8.3).
- **Variety:** {{var:n_tables}} bảng với 10 grain khác nhau (tháng, danh mục, danh mục × tháng, bang, khoảng cách, khách hàng, cụm, cohort, người bán, nhóm thanh toán), nhiều kiểu dữ liệu, hai hệ nhãn khách hàng song song (luật RFM và cụm K-Means), cộng thêm bảng fact gold phân vùng Hive.
- **Veracity:** cờ chất lượng `dq_*`, tháng không đầy đủ và các bẫy ngữ nghĩa — tổng 20 tháng của `kpi_monthly` *nhỏ hơn* số neo 13.494.400,74 BRL vì đã cắt tháng rỗng; `f_score` gần như nhiễu vì 97% khách chỉ mua một lần. Nhóm phải kiểm tra đối chiếu tự động để chứng minh số trên dashboard đúng.
- **Value:** kết quả phải chuyển thành hành động — 153 người bán cần theo dõi, ngưỡng 4 ngày trễ làm review sụt mạnh.
- **Nhu cầu phục vụ ở quy mô lớn:** nhiều người dùng, nhiều nơi, tải không đều → chọn dịch vụ serverless tự co giãn thay vì máy chủ cố định.

Velocity không phải đặc trưng chính: dữ liệu được làm mới theo lô mỗi khi Analytics chạy lại; loader idempotent cho phép tăng tần suất làm mới mà không đổi kiến trúc.

## 3.3. Input

**Nguồn và cách thu thập:** các bảng do nhóm Analytics bàn giao được sao chép nguyên vẹn vào `data/analytics/` của repo nhóm. **Định dạng:** Parquet nén Snappy, mỗi bảng một thư mục kiểu Spark (`part-00000-*.snappy.parquet`, kèm `_SUCCESS`). **Tốc độ phát sinh:** theo lô (lần chạy Analytics hiện tại: 29/10/2026). **Quy mô:** {{var:n_tables}} bảng, {{var:total_rows}} dòng, {{var:total_cols}} cột, {{var:total_kb}} KB nén; phân bố rất lệch — hai bảng cấp khách hàng (`rfm_scores`, `customer_segments`, mỗi bảng 94.983 dòng) và `seller_pareto` (3.053 dòng) chiếm hơn 99% số dòng, 13 bảng còn lại chỉ 2–715 dòng. Danh sách bảng, grain, khoá ở Mục 3.5; schema từng cột, quy mô chi tiết và ví dụ bản ghi ở Phụ lục C. Ví dụ rút gọn một dòng của `kpi_monthly`: `{purchase_year: 2017, purchase_month: 11, orders: 7421, revenue: 1003862.14, avg_order_value: 157.96, late_delivery_pct: 14.31, avg_review_score: 3.95, revenue_mom_pct: 52.06, revenue_rank: 1, is_black_friday_month: true}`.

**Đầu vào bổ sung – tầng gold.** Bảng Analytics có grain cố định nên không trả lời được câu hỏi lọc chéo như "AOV và % trễ của bang SP trong quý I/2018 với khách trả bằng boleto". Vì vậy nhóm nạp thêm {{var:n_gold}} bảng gold ({{var:gold_rows}} dòng, đầu vào của Analytics, đã đối chiếu 11/11). Hai bảng fact phân vùng Hive theo `purchase_year=YYYY/purchase_month=M/`; loader đọc bằng `pyarrow.dataset(..., partitioning="hive")` để khôi phục cột phân vùng. Gold chỉ dùng để **lọc và cộng lại**; mọi KPI phân tích (Pareto, RFM, K-Means, watchlist) vẫn lấy nguyên từ Analytics, và bộ kiểm tra nhất quán (Mục 6.2) chứng minh tổng từ gold khớp tổng của `kpi_monthly`.

## 3.4. Output

Bảng: Các thành phần đầu ra của giai đoạn Presentation
| Đầu ra | Định dạng / vị trí | Người dùng | Ví dụ |
|---|---|---|---|
| Bảng phục vụ | PostgreSQL 18 trên Neon: `analytics` ({{var:n_tables}} bảng + `load_log`), `gold` ({{var:n_gold}} bảng) | Superset, Decision/Action | `analytics.kpi_monthly` 20 dòng |
| Tầng ngữ nghĩa | {{var:n_views}} view + bảng `dim_state` trong schema `presentation` | Superset, Decision/Action | `v_kpi_monthly` có `month_date` kiểu DATE |
| Dashboard | Apache Superset (HTTP cổng 8088), nhiều tab | Người dùng nghiệp vụ | Thẻ "Doanh thu", Pareto, bản đồ bang |
| Gợi ý quyết định | `v_decision_hints` (7 luật), `v_seller_watchlist` (ĐỎ/VÀNG) | Giai đoạn Decision/Action | 153 người bán kèm lý do, hành động |
| Minh chứng | `evidence/`: log nạp, đối chiếu, độ trễ, ảnh | Giảng viên, nhóm | `load_log.csv`, `validation.json` |

Ví dụ một dòng của `v_decision_hints`: *ưu tiên 2, mức CAO, chủ đề Giao hàng, tín hiệu "Đơn trễ kéo review xuống", giá trị 1,73, ngưỡng "chênh lệch > 1 sao", hành động "Cảnh báo seller khi đơn trễ 1–3 ngày"*.

## 3.5. Data contract giữa Analytics và Presentation

Data contract là thoả thuận ràng buộc giữa bên sản xuất (Analytics) và bên tiêu thụ (Presentation) về **cấu trúc, ngữ nghĩa và chất lượng** dữ liệu bàn giao. Nhóm hình thức hoá `ANALYTICS_HANDOVER.md` thành bảng dưới đây (sinh tự động từ Parquet) và bộ kiểm tra tự động.

{{contract_table}}

Các điều khoản:

1. **Schema:** tên bảng, cột, kiểu như Phụ lục C. Thêm cột được chấp nhận (loader tự sinh DDL); đổi tên hoặc xoá cột là thay đổi phá vỡ, phải báo trước.
2. **Grain và khoá:** khoá ở cột "Khoá" là duy nhất — loader khai báo thành khoá chính, nên vi phạm grain bị phát hiện khi nạp.
3. **Ngữ nghĩa độ đo:** `revenue` = tổng giá sản phẩm chưa gồm ship; `gmv` = `revenue` + ship; `avg_review_score` cấp đơn; `late_delivery_pct` tính trên đơn đã giao; `delivery_delay_days` âm là giao sớm; tiền BRL 2 chữ số thập phân.
4. **Phạm vi thời gian:** 2017-01 → 2018-08; `category_seasonality` chỉ năm 2017.
5. **Số neo đối chiếu:** doanh thu gold 13.494.400,74 BRL; `kpi_monthly` 20 tháng; 94.983 khách; đỉnh 11/2017 với MoM +52,06%; review trễ/đúng hạn 2,56/4,29; khách mua lại 2.887 (3,04%).
6. **Làm mới:** Analytics chạy lại thì toàn bộ thư mục được thay thế; Presentation nạp lại toàn bộ và ghi `run_id` vào `load_log`.
7. **Ánh xạ kiểu:** `decimal(p,s)` → `NUMERIC(p,s)`, `int32` → `INTEGER`, `int64` → `BIGINT`, `double` → `DOUBLE PRECISION`, `bool` → `BOOLEAN`, `date32` → `DATE`, `timestamp` → `TIMESTAMP`, `string` → `TEXT`.

## 3.6. Yêu cầu chức năng và phi chức năng

**Chức năng:** (F1) nạp toàn bộ bảng vào tầng phục vụ đúng kiểu dữ liệu; (F2) ghi nhật ký mỗi lần nạp; (F3) định nghĩa KPI thống nhất, tổng hợp đúng; (F4) dashboard có thẻ KPI, xu hướng, Pareto, bản đồ, bảng chi tiết và bộ lọc theo tháng, bang, danh mục, phân khúc; (F5) cung cấp gợi ý quyết định cho giai đoạn sau. **Phi chức năng:** (N1) đúng đắn 100% so với Parquet và số neo; (N2) truy vấn dashboard trung vị < 300 ms, p95 < 500 ms; (N3) tái lập bằng Docker Compose và script; (N4) TLS bắt buộc, bí mật chỉ trong `.env`; (N5) nằm trong gói miễn phí Neon và không đổi kiến trúc khi dữ liệu ×10. Mức đáp ứng được đánh giá ở Mục 6.8.

## 3.7. Định nghĩa KPI

Bảng: Định nghĩa KPI và quy tắc tổng hợp trên dashboard
| KPI | Định nghĩa | Nguồn | Tổng hợp khi lọc nhiều phần tử |
|---|---|---|---|
| Doanh thu (BRL) | Tổng `price` đơn hợp lệ, chưa gồm ship | `kpi_monthly`, `v_orders` | `SUM(revenue)` |
| Số đơn | Số đơn hợp lệ | `kpi_monthly`, `v_orders` | `SUM(orders)` / `COUNT(*)` |
| AOV (BRL) | GMV / số đơn | `v_orders` | `SUM(order_value) / COUNT(*)` — không AVG của AOV tháng |
| Tăng trưởng MoM (%) | (t − (t−1)) / (t−1) × 100 | `kpi_monthly` | Không tổng hợp; hiển thị theo tháng |
| % đơn giao trễ | Đơn trễ / đơn đã giao × 100 | `v_orders.late_flag` (1/0/NULL) | `AVG(late_flag) × 100` — NULL (chưa giao) tự bị loại |
| Điểm review TB | Trung bình sao 1–5 cấp đơn | `v_orders.review_score` | `AVG(review_score)` cấp đơn |
| Tỷ trọng / % cộng dồn Pareto | Phần tử / tổng; cộng dồn giảm dần | `category_pareto`, `seller_pareto` | Tính sẵn trên toàn kỳ (window của Spark) |
| Phí ship / doanh thu (%) | `freight / revenue × 100` | `category_pareto`, `state_logistics` | `SUM(freight) / SUM(revenue)` |
| % khách mua lại | Khách `frequency ≥ 2` / tổng khách | `repeat_profile` | Trên toàn bộ 94.983 khách |
| Chênh lệch review | review đúng hạn − review trễ | `insight_late_vs_review` | 4,29 − 2,56 = 1,73 sao |
| Người bán cần theo dõi | Top 10% doanh thu **và** (review < 4 hoặc giao > 15 ngày hoặc trễ > 10%) | `seller_watchlist` | `COUNT(*)` = 153 |

Một lựa chọn thiết kế đáng chú ý: `kpi_monthly` chỉ có **tỷ lệ** % trễ và review theo tháng, không có mẫu số; nếu thẻ KPI lấy trung bình các tỷ lệ tháng khi người dùng chọn nhiều tháng thì sai (trung bình của trung bình). Nhóm giải quyết bằng view cấp đơn `v_orders` từ gold: `late_flag` nhận 1, 0 hoặc NULL (chưa giao), nên `AVG(late_flag)` đúng định nghĩa trên mọi tổ hợp bộ lọc. Biểu đồ xu hướng theo tháng vẫn lấy nguyên số của `kpi_monthly`, và bộ kiểm tra nhất quán đảm bảo hai nguồn khớp nhau.
