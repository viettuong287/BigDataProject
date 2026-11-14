# 5.4. Output

> **Yêu cầu 5.4 (đề bài):** Mô tả chính xác kết quả đầu ra: dữ liệu đã lưu, bảng dữ liệu đã xử lý, KPI, mô hình, dashboard, API hoặc hành động. Nêu định dạng và ví dụ đầu ra.

**(1) Dữ liệu đã lưu trên Neon** — database `olist_analytics`, PostgreSQL 18.6, tổng **25 bảng + 22 view, 146 MB**:

- `analytics`: 16 bảng bản sao Parquet của Analytics (194.132 dòng) + `analytics.load_log` (mỗi lần nạp thêm 23 dòng: `run_id`, số dòng Postgres/Parquet, cờ khớp, dung lượng, thời gian đọc/COPY/index, thông lượng, thời điểm).
- `gold`: 7 bảng (311.460 dòng), có khoá chính và chỉ mục trên cột lọc (`purchase_date`, `customer_state`, `category`, `seller_id`, `main_payment_type`).
- `presentation`: 22 view ngữ nghĩa + bảng `dim_state` (27 bang: tên, vùng, mã ISO `BR-xx` cho bản đồ).

**(2) Bảng đã xử lý – tầng ngữ nghĩa** (`sql/10_presentation_views.sql`, 22 view + `dim_state`, mỗi view phục vụ một nhóm biểu đồ):

- *Xu hướng:* `v_kpi_monthly` (KPI tháng + `month_date`, `month_label` cho bộ lọc thời gian), `v_kpi_overview` (1 dòng số neo toàn kỳ), `v_orders` (97.905 đơn hợp lệ cấp đơn – nguồn thẻ KPI lọc được theo tháng/bang/PTTT; `late_flag` cho tỷ lệ trễ đúng định nghĩa).
- *Danh mục:* `v_category_pareto` (Pareto + hạng + nhóm A/B/C), `v_category_seasonality` (danh mục × tháng 2017), `v_category_monthly` (doanh thu danh mục theo tháng, từ gold), `v_sales_items` (111.752 dòng sản phẩm hợp lệ, không có cột review).
- *Địa lý:* `v_state_logistics` (27 bang + tên, vùng, mã ISO), `v_insight_distance` (4 band khoảng cách).
- *Khách hàng:* `v_rfm_customers` (94.983 khách, phân khúc, cohort, tên cụm K-Means), `v_rfm_segments` (6 phân khúc + hành động CRM), `v_cluster_profile`, `v_repeat_profile`, `v_repeat_categories`, `v_repeat_states`.
- *Người bán:* `v_seller_pareto` (3.053 người bán, nhóm A/B/C, cờ watchlist), `v_seller_watchlist` (153 người bán: số vi phạm, lý do, mức ĐỎ/VÀNG, hành động).
- *Giao hàng – thanh toán:* `v_late_vs_review`, `v_delay_vs_review`, `v_payment_mix`.
- *Quyết định và nguồn gốc:* `v_decision_hints` (7 luật), `v_load_log` (lần nạp gần nhất của 23 bảng – lineage).

**(3) KPI và mô hình.** Thẻ KPI trên khung 2017-01 → 2018-08 (từ `v_orders`): doanh thu **13.449.530 BRL**, **97.905** đơn hợp lệ, **94.703** khách, AOV **160,19** BRL, tỷ lệ trễ **8,13%**, review **4,12**. Kết quả mô hình K-Means (k = 4) của nhóm Analytics được trình bày qua `v_cluster_profile` với tên nghiệp vụ C0–C3; phân khúc RFM theo luật qua `v_rfm_segments` kèm cột hành động CRM.

**(4) Dashboard Superset** (Superset 4.1.2, giao diện tiếng Việt, thương hiệu Olist Insight; dựng bằng `superset/build_dashboard.py`; bản export `superset/export/dashboard_olist_presentation.zip`):

Bảng: Bảy tab của dashboard {w=4.4,1.8,9.8}
| Tab | Thành phần | Nội dung chính |
|---|---|---|
| 1 · Tổng quan & xu hướng | 11 | 6 thẻ KPI, doanh thu tháng gần nhất, doanh thu & đơn theo tháng, % trễ vs review, MoM, bảng KPI tô màu |
| 2 · Danh mục & mùa vụ | 4 | Pareto top 25, heatmap mùa vụ 2017, phí ship/doanh thu, xu hướng 6 danh mục lớn |
| 3 · Địa lý & logistics | 5 | Bản đồ Brazil, bubble ngày giao vs review, % trễ theo bang, khoảng cách → ship & % trễ, bảng 27 bang |
| 4 · Khách hàng & RFM | 10 | 4 thẻ, donut phân khúc RFM, cụm K-Means, danh mục/bang của khách lặp, bảng hành động CRM |
| 5 · Người bán | 7 | 4 thẻ (3.053; 539 = 80% doanh thu; 17,65%; 153 cần theo dõi), Pareto A/B/C, bubble top 300, bảng watchlist |
| 6 · Giao trễ, đánh giá & thanh toán | 6 | Review trễ vs đúng hạn, ngưỡng ngày trễ vs % 1 sao, cơ cấu thanh toán, AOV theo kỳ góp |
| 7 · Gợi ý quyết định & nguồn dữ liệu | 4 | Bảng 7 luật, giải thích, nhật ký nạp (lineage) |

Tổng **45 biểu đồ** (47 thành phần gồm cả khối markdown), 22 dataset (1 view = 1 dataset). **7 bộ lọc native**: Khoảng thời gian (`month_date`), Bang khách hàng, Vùng, Danh mục, Phân khúc RFM, Phương thức thanh toán, Bang người bán; mỗi bộ lọc chỉ gắn vào biểu đồ có cột tương ứng.

**(5) Hành động / API cho giai đoạn sau.** View `presentation.v_decision_hints` — mỗi dòng một luật:

Bảng: Bảy luật trong v_decision_hints (giá trị lấy từ Neon) {w=0.8,2.0,2.2,5.4,5.6}
| # | Mức | Chủ đề | Tín hiệu | Hành động đề xuất |
|---|---|---|---|---|
| 1 | CAO | Seller | Seller doanh thu top 10% vi phạm ≥ 2 tiêu chí vận hành (75/153) | Gửi cảnh cáo, giảm hiển thị, yêu cầu kế hoạch SLA 30 ngày |
| 2 | CAO | Giao hàng | Đơn trễ kéo review xuống (4,29 → 2,56) | Cảnh báo seller khi đơn trễ 1–3 ngày (review 3,29) trước mốc 4–7 ngày (2,10) |
| 3 | CAO | Vận hành theo tháng | Tháng có tỷ lệ giao trễ > 15% (03/2018: 21,36%; 02/2018: 15,99%) | Tăng năng lực vận chuyển trước cao điểm (T11 Black Friday, T2–T3) |
| 4 | TRUNG BÌNH | Địa lý | Bang trễ > 10% và review < 4 (9 bang) | Seller/kho vùng; hiển thị ngày giao thực tế trước checkout |
| 5 | TRUNG BÌNH | Danh mục | Ngành lớn có phí ship > 20% doanh thu | Không free-ship đại trà; đưa phí ship vào giá/ngưỡng miễn phí |
| 6 | TRUNG BÌNH | Khách hàng | Khách At Risk (≥ 2 lần mua, > 180 ngày chưa quay lại): 1.961 | Chiến dịch win-back có mục tiêu (email/voucher ngành nhà cửa) |
| 7 | THẤP | Seller | Mức tập trung doanh thu seller (17,65%) | Ưu tiên account manager cho nhóm A |

Nhóm Decision lấy bằng `SELECT * FROM presentation.v_decision_hints ORDER BY priority;` hoặc xuất CSV / Chart Data API (`/api/v1/chart/data`) của Superset.

**(6) Phụ trợ.** Landing page tĩnh `web/` (nginx, cổng 8090) đọc `web/data/kpi.json` do `scripts/export_landing_kpi.py` xuất từ Neon; bộ minh chứng trong `evidence/` (log, CSV/MD số đo, ảnh).

**Ví dụ đầu ra thật.**

Bảng: Hai ví dụ dòng đầu ra {w=3.6,12.4}
| Đầu ra | Dòng ví dụ |
|---|---|
| `presentation.v_kpi_monthly` | month_date 2017-11-01, month_label `2017-11`, orders 7.421, customers 7.313, revenue 1.003.862,14, gmv 1.172.191,68, avg_order_value 157,96, avg_review_score 3,95, late_delivery_pct 14,31, revenue_mom_pct 52,06, revenue_rank 1, is_black_friday_month true |
| `presentation.v_decision_hints` | priority 1, severity CAO, topic Seller, signal "Seller doanh thu top 10% vi phạm ≥2 tiêu chí vận hành", metric_value 75, detail "75/153 seller trong watchlist, doanh thu watchlist 4.400.613 BRL", threshold "review < 4 \| giao > 15 ngày \| trễ > 10% (≥2 điều kiện)", action "Gửi cảnh cáo, giảm hiển thị, yêu cầu kế hoạch SLA 30 ngày", source `presentation.v_seller_watchlist` |
