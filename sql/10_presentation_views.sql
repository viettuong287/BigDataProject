-- =====================================================================
-- Tầng ngữ nghĩa (semantic layer) cho dashboard Superset.
-- Đầu vào : schema analytics (16 bảng output Analytics) + gold (fact/agg).
-- Đầu ra  : schema presentation, mỗi view phục vụ 1 nhóm biểu đồ.
-- Idempotent: chạy lại bao nhiêu lần cũng được (loader tự chạy sau khi nạp).
-- Quy tắc bàn giao được giữ nguyên:
--   * chuỗi thời gian 2017-01 → 2018-08 (kpi_monthly đã cắt 2016 và 2018-09)
--   * đếm khách bằng customer_unique_id
--   * review lấy ở cấp đơn (fact_orders / insight_* / kpi_monthly), KHÔNG từ fact_order_items
-- =====================================================================

DROP SCHEMA IF EXISTS presentation CASCADE;
CREATE SCHEMA presentation;

-- ---------------------------------------------------------------------
-- Dimension bang Brazil: tên, vùng, mã ISO 3166-2 (khớp geojson Country Map của Superset)
-- ---------------------------------------------------------------------
CREATE TABLE presentation.dim_state (
    customer_state char(2) PRIMARY KEY,
    state_name     text NOT NULL,
    region         text NOT NULL,
    iso_code       text NOT NULL
);
INSERT INTO presentation.dim_state (customer_state, state_name, region, iso_code)
SELECT s, n, r, 'BR-' || s
FROM (VALUES
    ('AC','Acre','Norte'), ('AL','Alagoas','Nordeste'), ('AP','Amapá','Norte'),
    ('AM','Amazonas','Norte'), ('BA','Bahia','Nordeste'), ('CE','Ceará','Nordeste'),
    ('DF','Distrito Federal','Centro-Oeste'), ('ES','Espírito Santo','Sudeste'),
    ('GO','Goiás','Centro-Oeste'), ('MA','Maranhão','Nordeste'), ('MT','Mato Grosso','Centro-Oeste'),
    ('MS','Mato Grosso do Sul','Centro-Oeste'), ('MG','Minas Gerais','Sudeste'), ('PA','Pará','Norte'),
    ('PB','Paraíba','Nordeste'), ('PR','Paraná','Sul'), ('PE','Pernambuco','Nordeste'),
    ('PI','Piauí','Nordeste'), ('RJ','Rio de Janeiro','Sudeste'), ('RN','Rio Grande do Norte','Nordeste'),
    ('RS','Rio Grande do Sul','Sul'), ('RO','Rondônia','Norte'), ('RR','Roraima','Norte'),
    ('SC','Santa Catarina','Sul'), ('SP','São Paulo','Sudeste'), ('SE','Sergipe','Nordeste'),
    ('TO','Tocantins','Norte')
) AS t(s, n, r);

-- =====================================================================
-- Chủ đề 1. Tăng trưởng & vận hành
-- =====================================================================
CREATE VIEW presentation.v_kpi_monthly AS
SELECT make_date(k.purchase_year, k.purchase_month, 1)                    AS month_date,
       to_char(make_date(k.purchase_year, k.purchase_month, 1), 'YYYY-MM') AS month_label,
       k.purchase_year, k.purchase_month,
       k.orders, k.customers, k.items, k.revenue, k.freight, k.gmv,
       k.avg_order_value, k.avg_review_score, k.avg_delivery_days, k.late_delivery_pct,
       k.revenue_mom_pct, k.orders_mom_pct, k.revenue_yoy_pct, k.revenue_rank,
       k.is_black_friday_month
FROM analytics.kpi_monthly k;

-- Đơn hợp lệ (cấp đơn) trong khung KPI: nguồn cho thẻ KPI có bộ lọc tháng/bang/PTTT.
CREATE VIEW presentation.v_orders AS
SELECT o.order_id,
       o.customer_unique_id,
       o.purchase_date,
       date_trunc('month', o.purchase_date)::date             AS month_date,
       o.customer_state,
       s.region,
       o.order_status,
       COALESCE(o.main_payment_type, 'unknown')               AS main_payment_type,
       o.max_installments,
       o.items,
       o.items_value                                          AS revenue,
       o.freight_value                                        AS freight,
       o.order_value,
       o.delivery_days,
       o.delivery_delay_days,
       CASE WHEN o.is_late THEN 1 WHEN NOT o.is_late THEN 0 END AS late_flag,
       o.review_score
FROM gold.fact_orders o
LEFT JOIN presentation.dim_state s USING (customer_state)
WHERE o.is_valid_sale
  AND o.purchase_date >= DATE '2017-01-01'
  AND o.purchase_date <  DATE '2018-09-01';

-- Thẻ KPI "toàn kỳ" và số neo (1 dòng).
CREATE VIEW presentation.v_kpi_overview AS
SELECT (SELECT SUM(revenue) FROM gold.agg_sales_monthly)                       AS gold_revenue_total,
       (SELECT SUM(orders)  FROM gold.agg_sales_monthly)                       AS gold_valid_orders,
       (SELECT SUM(revenue) FROM analytics.kpi_monthly)                        AS kpi_window_revenue,
       (SELECT COUNT(*)     FROM analytics.kpi_monthly)                        AS kpi_months,
       (SELECT COUNT(*)     FROM analytics.rfm_scores)                         AS customers,
       (SELECT customers FROM analytics.repeat_profile WHERE cohort = 'repeat') AS repeat_customers,
       (SELECT pct       FROM analytics.repeat_profile WHERE cohort = 'repeat') AS repeat_pct,
       (SELECT month_label FROM presentation.v_kpi_monthly ORDER BY revenue DESC LIMIT 1)     AS peak_month,
       (SELECT revenue_mom_pct FROM presentation.v_kpi_monthly ORDER BY revenue DESC LIMIT 1) AS peak_mom_pct,
       (SELECT avg_review FROM analytics.insight_late_vs_review WHERE delivery = 'late')    AS late_review,
       (SELECT avg_review FROM analytics.insight_late_vs_review WHERE delivery = 'on_time') AS on_time_review,
       (SELECT COUNT(*) FROM analytics.seller_pareto)                          AS sellers,
       (SELECT COUNT(*) FROM analytics.seller_pareto WHERE cumulative_share_pct <= 80) AS sellers_80pct_revenue,
       (SELECT COUNT(*) FROM analytics.seller_watchlist)                       AS watchlist_sellers;

-- =====================================================================
-- Chủ đề 2. Danh mục & mùa vụ
-- =====================================================================
-- category_label có tiền tố hạng ("01 health_beauty") để trục X của chart Pareto sắp đúng thứ tự doanh thu.
CREATE VIEW presentation.v_category_pareto AS
SELECT c.*,
       ROW_NUMBER() OVER (ORDER BY c.revenue DESC) AS revenue_rank,
       lpad((ROW_NUMBER() OVER (ORDER BY c.revenue DESC))::text, 2, '0') || ' ' || c.category AS category_label,
       CASE WHEN c.cumulative_share_pct <= 80 THEN 'A (≤80% doanh thu)'
            WHEN c.cumulative_share_pct <= 95 THEN 'B (80–95%)'
            ELSE 'C (đuôi dài)' END                AS pareto_class
FROM analytics.category_pareto c;

-- revenue_rank lấy từ Pareto để chart lọc top N mà không cần sub-query (Superset chặn sub-query trong filter).
CREATE VIEW presentation.v_category_seasonality AS
SELECT make_date(2017, s.purchase_month, 1) AS month_date,
       s.category, s.purchase_month, s.revenue, s.orders, s.pct_of_category_year,
       p.revenue_rank
FROM analytics.category_seasonality s
LEFT JOIN presentation.v_category_pareto p USING (category);

-- Doanh thu danh mục theo tháng (gold agg, 1.282 dòng) cho biểu đồ xu hướng có bộ lọc danh mục.
CREATE VIEW presentation.v_category_monthly AS
SELECT make_date(a.purchase_year, a.purchase_month, 1) AS month_date,
       a.category, a.orders, a.items, a.revenue, a.freight, a.avg_price
FROM gold.agg_category_monthly a
WHERE make_date(a.purchase_year, a.purchase_month, 1) BETWEEN DATE '2017-01-01' AND DATE '2018-08-01';

-- Dòng sản phẩm hợp lệ (doanh thu/ship theo danh mục × bang × tháng). Không chứa review (quy tắc 3).
CREATE VIEW presentation.v_sales_items AS
SELECT i.order_id,
       i.order_item_id,
       date_trunc('month', i.purchase_date)::date AS month_date,
       i.category,
       i.customer_state,
       s.region,
       i.seller_id,
       i.seller_state,
       i.price         AS revenue,
       i.freight_value AS freight,
       i.distance_km
FROM gold.fact_order_items i
LEFT JOIN presentation.dim_state s USING (customer_state)
WHERE i.is_valid_sale
  AND i.purchase_date >= DATE '2017-01-01'
  AND i.purchase_date <  DATE '2018-09-01';

-- =====================================================================
-- Chủ đề 3. Địa lý & logistics
-- =====================================================================
CREATE VIEW presentation.v_state_logistics AS
SELECT l.customer_state, d.state_name, d.region, d.iso_code,
       l.orders, l.customers, l.revenue, l.gmv, l.avg_order_value, l.avg_freight,
       l.freight_pct_of_revenue, l.avg_delivery_days, l.late_delivery_pct, l.avg_review_score,
       l.revenue_share_pct, l.revenue_rank
FROM analytics.state_logistics l
JOIN presentation.dim_state d USING (customer_state);

CREATE VIEW presentation.v_insight_distance AS
SELECT band_order || '. ' || distance_band AS band_label,
       distance_band, band_order, items, avg_freight, avg_delivery_days, avg_delay_days, late_pct
FROM analytics.insight_distance;

-- =====================================================================
-- Chủ đề 4. Khách hàng, RFM, giữ chân
-- =====================================================================
CREATE VIEW presentation.v_rfm_customers AS
SELECT c.customer_unique_id, c.customer_state, d.region,
       c.recency_days, c.frequency, c.monetary, c.avg_order_value,
       c.r_score, c.f_score, c.m_score, c.rfm_segment,
       CASE c.rfm_segment WHEN 'Champions' THEN 1 WHEN 'Loyal' THEN 2 WHEN 'At Risk' THEN 3
            WHEN 'One-shot Recent' THEN 4 WHEN 'One-shot Warm' THEN 5 ELSE 6 END AS segment_order,
       CASE WHEN c.frequency >= 2 THEN 'repeat' ELSE 'one_shot' END            AS cohort,
       c.cluster,
       CASE c.cluster WHEN 0 THEN 'C0 · One-shot giá trị thấp' WHEN 1 THEN 'C1 · Khách mua lại'
            WHEN 2 THEN 'C2 · One-shot chi cao' WHEN 3 THEN 'C3 · One-shot lâu không mua' END AS cluster_name
FROM analytics.customer_segments c
LEFT JOIN presentation.dim_state d USING (customer_state);

CREATE VIEW presentation.v_rfm_segments AS
SELECT rfm_segment,
       MIN(segment_order)                                       AS segment_order,
       COUNT(*)                                                 AS customers,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)       AS pct_customers,
       ROUND(AVG(recency_days), 1)                              AS avg_recency_days,
       ROUND(AVG(frequency), 3)                                 AS avg_frequency,
       ROUND(AVG(monetary), 2)                                  AS avg_monetary,
       CASE rfm_segment
            WHEN 'Champions'       THEN 'Giữ chân bằng voucher/ưu đãi VIP'
            WHEN 'Loyal'           THEN 'Gợi ý mua bổ sung (nhà cửa, thể thao)'
            WHEN 'At Risk'         THEN 'Win-back có mục tiêu: đã mua ≥2 lần, >180 ngày chưa quay lại'
            WHEN 'One-shot Recent' THEN 'Mời mua lần 2 trong 90 ngày'
            WHEN 'One-shot Warm'   THEN 'Nhắc nhẹ, chi phí thấp'
            ELSE 'Không ưu tiên ngân sách (chi phí chìm)' END   AS crm_action
FROM presentation.v_rfm_customers
GROUP BY rfm_segment;

CREATE VIEW presentation.v_cluster_profile AS
SELECT p.cluster,
       CASE p.cluster WHEN 0 THEN 'C0 · One-shot giá trị thấp' WHEN 1 THEN 'C1 · Khách mua lại'
            WHEN 2 THEN 'C2 · One-shot chi cao' WHEN 3 THEN 'C3 · One-shot lâu không mua' END AS cluster_name,
       p.customers, p.avg_recency, p.avg_frequency, p.avg_monetary, p.champions, p.loyal, p.at_risk
FROM analytics.cluster_profile p;

CREATE VIEW presentation.v_repeat_profile AS
SELECT CASE cohort WHEN 'repeat' THEN 'Mua lại (≥2 đơn)' ELSE 'Mua 1 lần' END AS cohort_label,
       cohort, customers, pct, avg_recency, avg_frequency, avg_monetary, avg_aov
FROM analytics.repeat_profile;

CREATE VIEW presentation.v_repeat_categories AS
SELECT category, repeat_customers, items, revenue FROM analytics.repeat_categories;

CREATE VIEW presentation.v_repeat_states AS
SELECT r.customer_state, d.state_name, d.region, r.repeat_customers, r.avg_frequency, r.avg_monetary, r.avg_aov
FROM analytics.repeat_states r
LEFT JOIN presentation.dim_state d USING (customer_state);

-- =====================================================================
-- Chủ đề 5. Seller
-- =====================================================================
CREATE VIEW presentation.v_seller_pareto AS
SELECT p.seller_id,
       left(p.seller_id, 8) || '…'                              AS seller_short,
       p.seller_state, p.orders, p.revenue, p.avg_review_score, p.avg_delivery_days,
       p.late_delivery_pct, p.avg_distance_km, p.active_months,
       p.revenue_share_pct, p.cumulative_share_pct,
       ROW_NUMBER() OVER (ORDER BY p.revenue DESC)              AS revenue_rank,
       CASE WHEN p.cumulative_share_pct <= 80 THEN 'A · nhóm tạo 80% doanh thu'
            WHEN p.cumulative_share_pct <= 95 THEN 'B · 80–95%'
            ELSE 'C · đuôi dài' END                             AS pareto_group,
       (w.seller_id IS NOT NULL)                                AS is_watchlist,
       CASE WHEN w.seller_id IS NOT NULL THEN 'Watchlist' ELSE 'Bình thường' END AS watchlist_label
FROM analytics.seller_pareto p
LEFT JOIN analytics.seller_watchlist w USING (seller_id);

CREATE VIEW presentation.v_seller_watchlist AS
WITH f AS (
    SELECT w.*,
           (w.avg_review_score < 4.0)::int  AS v_review,
           (w.avg_delivery_days > 15)::int  AS v_delivery,
           (w.late_delivery_pct > 10)::int  AS v_late
    FROM analytics.seller_watchlist w
)
SELECT seller_id,
       left(seller_id, 8) || '…'                    AS seller_short,
       seller_state, orders, revenue, avg_review_score, avg_delivery_days, late_delivery_pct,
       avg_distance_km, active_months, ROUND(revenue_pctile::numeric, 4) AS revenue_pctile,
       v_review + v_delivery + v_late               AS violations,
       concat_ws(', ',
           CASE WHEN v_review = 1   THEN 'review < 4' END,
           CASE WHEN v_delivery = 1 THEN 'giao > 15 ngày' END,
           CASE WHEN v_late = 1     THEN 'trễ > 10%' END) AS reasons,
       CASE WHEN v_review + v_delivery + v_late >= 2 THEN 'ĐỎ' ELSE 'VÀNG' END AS alert_level,
       CASE WHEN v_review + v_delivery + v_late >= 2
            THEN 'Cảnh cáo + giảm hiển thị; yêu cầu kế hoạch SLA 30 ngày'
            ELSE 'Nhắc nhở, theo dõi tháng kế tiếp' END AS recommended_action
FROM f;

-- =====================================================================
-- Chủ đề 6. Giao trễ, review, thanh toán
-- =====================================================================
CREATE VIEW presentation.v_late_vs_review AS
SELECT CASE delivery WHEN 'late' THEN 'Giao trễ' ELSE 'Đúng hạn' END AS delivery_label,
       delivery, orders, avg_review, pct_score_1_2, pct_has_comment
FROM analytics.insight_late_vs_review;

CREATE VIEW presentation.v_delay_vs_review AS
SELECT band_order,
       CASE delay_band WHEN 'on_time_or_early' THEN '0. Đúng hạn/sớm' WHEN 'late_1_3d' THEN '1. Trễ 1–3 ngày'
            WHEN 'late_4_7d' THEN '2. Trễ 4–7 ngày' WHEN 'late_8_14d' THEN '3. Trễ 8–14 ngày'
            ELSE '4. Trễ ≥15 ngày' END AS delay_label,
       delay_band, orders, avg_review, pct_1_star, pct_has_comment
FROM analytics.delay_vs_review;

CREATE VIEW presentation.v_payment_mix AS
SELECT main_payment_type,
       installment_band,
       CASE installment_band WHEN '1_or_none' THEN '1 kỳ / không' WHEN '2_3' THEN '2–3 kỳ'
            WHEN '4_6' THEN '4–6 kỳ' ELSE '≥7 kỳ' END AS installment_label,
       orders, gmv, avg_order_value,
       ROUND(100.0 * orders / SUM(orders) OVER (), 2) AS pct_orders
FROM analytics.payment_mix;

-- =====================================================================
-- Gợi ý quyết định (cầu nối sang giai đoạn Decision / Action).
-- Mỗi dòng = 1 luật có ngưỡng, giá trị tính trực tiếp từ dữ liệu -> nhóm sau có thể đọc bằng SQL/API.
-- =====================================================================
CREATE VIEW presentation.v_decision_hints AS
WITH wl AS (
    SELECT COUNT(*) AS n,
           COUNT(*) FILTER (WHERE alert_level = 'ĐỎ') AS n_red,
           SUM(revenue) AS rev
    FROM presentation.v_seller_watchlist
), lr AS (
    SELECT MAX(avg_review) FILTER (WHERE delivery = 'on_time') AS on_time,
           MAX(avg_review) FILTER (WHERE delivery = 'late')    AS late,
           MAX(orders)     FILTER (WHERE delivery = 'late')    AS late_orders
    FROM analytics.insight_late_vs_review
), hot_months AS (
    SELECT COUNT(*) AS n, string_agg(month_label || ' (' || late_delivery_pct || '%)', ', ' ORDER BY late_delivery_pct DESC) AS lst
    FROM presentation.v_kpi_monthly WHERE late_delivery_pct > 15
), bad_states AS (
    SELECT COUNT(*) AS n, string_agg(customer_state || ' ' || late_delivery_pct || '%/' || avg_review_score, ', ' ORDER BY late_delivery_pct DESC) AS lst
    FROM analytics.state_logistics WHERE late_delivery_pct > 10 AND avg_review_score < 4
), freight AS (
    SELECT COUNT(*) AS n, string_agg(category || ' ' || freight_to_revenue_pct || '%', ', ' ORDER BY freight_to_revenue_pct DESC) AS lst
    FROM analytics.category_pareto WHERE freight_to_revenue_pct > 20 AND revenue > 100000
), sel AS (
    SELECT COUNT(*) FILTER (WHERE cumulative_share_pct <= 80) AS top, COUNT(*) AS total
    FROM analytics.seller_pareto
), atrisk AS (
    SELECT customers, avg_monetary FROM presentation.v_rfm_segments WHERE rfm_segment = 'At Risk'
)
SELECT 1 AS priority, 'CAO' AS severity, 'Seller' AS topic,
       'Seller doanh thu top 10% vi phạm ≥2 tiêu chí vận hành' AS signal,
       wl.n_red::numeric AS metric_value,
       wl.n_red || '/' || wl.n || ' seller trong watchlist, doanh thu watchlist ' || to_char(wl.rev, 'FM999G999G999') || ' BRL' AS detail,
       'review < 4 | giao > 15 ngày | trễ > 10% (≥2 điều kiện)' AS threshold,
       'Gửi cảnh cáo, giảm hiển thị, yêu cầu kế hoạch SLA 30 ngày' AS action,
       'presentation.v_seller_watchlist' AS source
FROM wl
UNION ALL
SELECT 2, 'CAO', 'Giao hàng',
       'Đơn trễ kéo review xuống',
       ROUND((lr.on_time - lr.late)::numeric, 2),
       'Review đúng hạn ' || lr.on_time || ' vs trễ ' || lr.late || ' (' || lr.late_orders || ' đơn trễ)',
       'chênh lệch > 1 sao',
       'Cảnh báo seller khi đơn trễ 1–3 ngày (review 3,29) trước mốc 4–7 ngày (2,10)',
       'analytics.insight_late_vs_review, analytics.delay_vs_review'
FROM lr
UNION ALL
SELECT 3, 'CAO', 'Vận hành theo tháng',
       'Tháng có tỷ lệ giao trễ > 15%',
       hot_months.n::numeric, hot_months.lst, 'late_delivery_pct > 15%',
       'Tăng năng lực vận chuyển trước cao điểm (T11 Black Friday, T2–T3)',
       'presentation.v_kpi_monthly'
FROM hot_months
UNION ALL
SELECT 4, 'TRUNG BÌNH', 'Địa lý',
       'Bang trễ > 10% và review < 4',
       bad_states.n::numeric, bad_states.lst, 'late_delivery_pct > 10% và avg_review_score < 4',
       'Seller/kho vùng; hiển thị ngày giao thực tế trước checkout',
       'presentation.v_state_logistics'
FROM bad_states
UNION ALL
SELECT 5, 'TRUNG BÌNH', 'Danh mục',
       'Ngành lớn có phí ship > 20% doanh thu',
       freight.n::numeric, freight.lst, 'freight_to_revenue_pct > 20% và doanh thu > 100k BRL',
       'Không free-ship đại trà; đưa phí ship vào giá/ngưỡng miễn phí',
       'presentation.v_category_pareto'
FROM freight
UNION ALL
SELECT 6, 'TRUNG BÌNH', 'Khách hàng',
       'Khách At Risk (đã mua ≥2 lần, >180 ngày chưa quay lại)',
       atrisk.customers::numeric,
       atrisk.customers || ' khách, chi TB ' || atrisk.avg_monetary || ' BRL',
       'frequency ≥ 2 và recency > 180 ngày',
       'Chiến dịch win-back có mục tiêu (email/voucher ngành nhà cửa)',
       'presentation.v_rfm_segments'
FROM atrisk
UNION ALL
SELECT 7, 'THẤP', 'Seller',
       'Mức tập trung doanh thu seller',
       ROUND(100.0 * sel.top / sel.total, 2),
       sel.top || '/' || sel.total || ' seller tạo 80% doanh thu',
       '% seller tạo 80% doanh thu',
       'Ưu tiên account manager cho nhóm A',
       'presentation.v_seller_pareto'
FROM sel;

-- =====================================================================
-- Nguồn dữ liệu: lần nạp gần nhất của mỗi bảng (data lineage trên dashboard).
-- =====================================================================
CREATE VIEW presentation.v_load_log AS
SELECT DISTINCT ON (schema_name, table_name)
       schema_name || '.' || table_name AS table_fq,
       schema_name, table_name, rows, parquet_rows, row_count_ok, parquet_files,
       ROUND(parquet_bytes / 1048576.0, 2) AS parquet_mb,
       seconds, rows_per_sec, source_path, run_id, loaded_at
FROM analytics.load_log
ORDER BY schema_name, table_name, loaded_at DESC;
