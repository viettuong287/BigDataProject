# Kiểm chứng dữ liệu đã nạp vào Neon

Thời điểm: 2026-11-12 15:12:34 · Script: `loader/validate.py`

## 1. Số dòng Parquet vs Postgres — 23/23 khớp

| Bảng | Parquet | Postgres | Kết quả |
|---|---:|---:|---|
| `analytics.kpi_monthly` | 20 | 20 | ĐẠT |
| `analytics.category_pareto` | 74 | 74 | ĐẠT |
| `analytics.category_seasonality` | 715 | 715 | ĐẠT |
| `analytics.state_logistics` | 27 | 27 | ĐẠT |
| `analytics.insight_distance` | 4 | 4 | ĐẠT |
| `analytics.rfm_scores` | 94,983 | 94,983 | ĐẠT |
| `analytics.repeat_profile` | 2 | 2 | ĐẠT |
| `analytics.repeat_categories` | 70 | 70 | ĐẠT |
| `analytics.repeat_states` | 27 | 27 | ĐẠT |
| `analytics.customer_segments` | 94,983 | 94,983 | ĐẠT |
| `analytics.cluster_profile` | 4 | 4 | ĐẠT |
| `analytics.seller_pareto` | 3,053 | 3,053 | ĐẠT |
| `analytics.seller_watchlist` | 153 | 153 | ĐẠT |
| `analytics.insight_late_vs_review` | 2 | 2 | ĐẠT |
| `analytics.delay_vs_review` | 5 | 5 | ĐẠT |
| `analytics.payment_mix` | 10 | 10 | ĐẠT |
| `gold.fact_orders` | 99,441 | 99,441 | ĐẠT |
| `gold.fact_order_items` | 112,650 | 112,650 | ĐẠT |
| `gold.agg_sales_monthly` | 24 | 24 | ĐẠT |
| `gold.agg_category_monthly` | 1,282 | 1,282 | ĐẠT |
| `gold.agg_customer_state` | 27 | 27 | ĐẠT |
| `gold.agg_seller_performance` | 3,053 | 3,053 | ĐẠT |
| `gold.agg_customer_rfm` | 94,983 | 94,983 | ĐẠT |

Tổng: 505,592 dòng.

## 2. Số neo bàn giao Analytics — 19/19 đạt

SQL nằm trong `sql/90_anchor_checks.sql`.

| Kiểm tra | Kỳ vọng | Thực tế (Neon) | Kết quả | Thời gian truy vấn (ms) |
|---|---:|---:|---|---:|
| Gold SUM(revenue) – agg_sales_monthly | 13494400.74 | 13,494,400.74 | ĐẠT | 82.2 |
| Gold SUM(price) – fact_order_items (is_valid_sale) | 13494400.74 | 13,494,400.74 | ĐẠT | 296.3 |
| kpi_monthly có 20 tháng | 20 | 20 | ĐẠT | 76.2 |
| kpi_monthly không chứa 2016 và 2018-09 | 0 | 0 | ĐẠT | 100.7 |
| Tổng revenue kpi_monthly (nhỏ hơn gold vì cắt tháng rỗng) | info | 13,449,529.68 | INFO | 100.9 |
| Tháng đỉnh doanh thu | 2017-11 | 2017-11 | ĐẠT | 122.4 |
| MoM tháng đỉnh (%) | 52.06 | 52.06 | ĐẠT | 111.0 |
| Review đơn trễ | 2.56 | 2.56 | ĐẠT | 117.8 |
| Review đơn đúng hạn | 4.29 | 4.29 | ĐẠT | 84.3 |
| Số khách mua lại (frequency ≥ 2) | 2887 | 2,887 | ĐẠT | 169.8 |
| Tổng khách thật (customer_unique_id) | 94983 | 94,983 | ĐẠT | 226.8 |
| Tỷ lệ khách mua lại (%) | 3.04 | 3.04 | ĐẠT | 109.3 |
| Tỷ lệ frequency = 1 (%) | 96.96 | 96.96 | ĐẠT | 184.8 |
| Seller watchlist | 153 | 153 | ĐẠT | 100.8 |
| Số seller tạo ≤80% doanh thu | 539 | 539 | ĐẠT | 186.5 |
| Nhất quán: SUM(revenue) v_orders = SUM(revenue) kpi_monthly | 0 | 0 | ĐẠT | 349.1 |
| Nhất quán: COUNT đơn v_orders = SUM(orders) kpi_monthly | 0 | 0 | ĐẠT | 131.9 |
| Nhất quán: SUM(revenue) v_sales_items = SUM(revenue) kpi_monthly | 0 | 0 | ĐẠT | 166.4 |
| Nhất quán: tổng khách theo segment = tổng khách RFM | 94983 | 94,983 | ĐẠT | 186.6 |
| Số dòng gợi ý quyết định | 7 | 7 | ĐẠT | 160.1 |
