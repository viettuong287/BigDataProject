-- Kiểm tra số neo của ANALYTICS_HANDOVER.md trên dữ liệu ĐÃ NẠP vào Neon.
-- Định dạng: mỗi khối bắt đầu bằng "-- check: <tên> | expected: <giá trị|info> | tol: <sai số>"
-- Chạy bằng: docker compose run --rm tools python loader/validate.py

-- check: Gold SUM(revenue) – agg_sales_monthly | expected: 13494400.74 | tol: 0.005
SELECT SUM(revenue) FROM gold.agg_sales_monthly;

-- check: Gold SUM(price) – fact_order_items (is_valid_sale) | expected: 13494400.74 | tol: 0.005
SELECT SUM(price) FROM gold.fact_order_items WHERE is_valid_sale;

-- check: kpi_monthly có 20 tháng | expected: 20 | tol: 0
SELECT COUNT(*) FROM analytics.kpi_monthly;

-- check: kpi_monthly không chứa 2016 và 2018-09 | expected: 0 | tol: 0
SELECT COUNT(*) FROM analytics.kpi_monthly
WHERE purchase_year = 2016 OR (purchase_year = 2018 AND purchase_month >= 9);

-- check: Tổng revenue kpi_monthly (nhỏ hơn gold vì cắt tháng rỗng) | expected: info | tol: 0
SELECT SUM(revenue) FROM analytics.kpi_monthly;

-- check: Tháng đỉnh doanh thu | expected: 2017-11 | tol: 0
SELECT month_label FROM presentation.v_kpi_monthly ORDER BY revenue DESC LIMIT 1;

-- check: MoM tháng đỉnh (%) | expected: 52.06 | tol: 0.005
SELECT revenue_mom_pct FROM presentation.v_kpi_monthly ORDER BY revenue DESC LIMIT 1;

-- check: Review đơn trễ | expected: 2.56 | tol: 0.005
SELECT avg_review FROM analytics.insight_late_vs_review WHERE delivery = 'late';

-- check: Review đơn đúng hạn | expected: 4.29 | tol: 0.005
SELECT avg_review FROM analytics.insight_late_vs_review WHERE delivery = 'on_time';

-- check: Số khách mua lại (frequency ≥ 2) | expected: 2887 | tol: 0
SELECT COUNT(*) FROM analytics.rfm_scores WHERE frequency >= 2;

-- check: Tổng khách thật (customer_unique_id) | expected: 94983 | tol: 0
SELECT COUNT(DISTINCT customer_unique_id) FROM analytics.rfm_scores;

-- check: Tỷ lệ khách mua lại (%) | expected: 3.04 | tol: 0.005
SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE frequency >= 2) / COUNT(*), 2) FROM analytics.rfm_scores;

-- check: Tỷ lệ frequency = 1 (%) | expected: 96.96 | tol: 0.005
SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE frequency = 1) / COUNT(*), 2) FROM analytics.rfm_scores;

-- check: Seller watchlist | expected: 153 | tol: 0
SELECT COUNT(*) FROM analytics.seller_watchlist;

-- check: Số seller tạo ≤80% doanh thu | expected: 539 | tol: 0
SELECT COUNT(*) FROM analytics.seller_pareto WHERE cumulative_share_pct <= 80;

-- check: Nhất quán: SUM(revenue) v_orders = SUM(revenue) kpi_monthly | expected: 0 | tol: 0.005
SELECT (SELECT SUM(revenue) FROM presentation.v_orders) - (SELECT SUM(revenue) FROM analytics.kpi_monthly);

-- check: Nhất quán: COUNT đơn v_orders = SUM(orders) kpi_monthly | expected: 0 | tol: 0
SELECT (SELECT COUNT(*) FROM presentation.v_orders) - (SELECT SUM(orders) FROM analytics.kpi_monthly);

-- check: Nhất quán: SUM(revenue) v_sales_items = SUM(revenue) kpi_monthly | expected: 0 | tol: 0.005
SELECT (SELECT SUM(revenue) FROM presentation.v_sales_items) - (SELECT SUM(revenue) FROM analytics.kpi_monthly);

-- check: Nhất quán: tổng khách theo segment = tổng khách RFM | expected: 94983 | tol: 0
SELECT SUM(customers) FROM presentation.v_rfm_segments;

-- check: Số dòng gợi ý quyết định | expected: 7 | tol: 0
SELECT COUNT(*) FROM presentation.v_decision_hints;
