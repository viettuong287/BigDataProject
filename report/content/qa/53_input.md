# 5.3. Input

> **Yêu cầu 5.3 (đề bài):** Mô tả nguồn dữ liệu, cách thu thập, định dạng, schema, số lượng bản ghi/khối lượng dữ liệu, tốc độ phát sinh (nếu có), các trường dữ liệu chính và ví dụ bản ghi.

**Nguồn và cách thu thập.** Dữ liệu gốc là bộ công khai *Brazilian E-Commerce Public Dataset by Olist* trên Kaggle. Nhóm em không tự thu thập từ nguồn mà nhận bàn giao từ giai đoạn trước: 16 bảng output của nhóm Analytics (repo upstream `Analytics-main`, thư mục `data/analytics/`) và 7 bảng gold của nhóm Processing (`data/gold/`), kèm tài liệu bàn giao trong `docs/upstream/`. Bản sao đầy đủ nằm sẵn trong repo của nhóm, nên người kiểm tra không cần repo khác.

**Định dạng.** Apache Parquet nén Snappy, mỗi bảng một thư mục kiểu Spark (`part-00000-*.snappy.parquet` + `_SUCCESS`); mỗi bảng Analytics được Spark `coalesce(1)` thành đúng một tệp; `fact_orders` (25 tệp) và `fact_order_items` (24 tệp) phân vùng Hive theo `purchase_year/purchase_month`. Loader đọc bằng `pyarrow.dataset(..., partitioning="hive")`.

**Khối lượng và tốc độ phát sinh.** 23 bảng, **505.592 dòng**, **42,88 MB** Parquet (16 bảng Analytics {{var:total_rows}} dòng, ~8 MB; 7 bảng gold 311.460 dòng, ~35 MB). Dữ liệu phát sinh theo lô: mỗi lần nhóm Analytics chạy lại job (lần hiện tại 29/10/2026) thì nhóm em nạp lại toàn bộ; dữ liệu nghiệp vụ là lịch sử 09/2016–10/2018, không có luồng thời gian thực.

{{contract_table}}

Bảy bảng gold (schema `gold`): `fact_orders` (99.441 dòng, 1 đơn, khoá `order_id`), `fact_order_items` (112.650 dòng, 1 sản phẩm trong đơn, khoá `order_id, order_item_id`), `agg_sales_monthly` (24 dòng, 1 tháng kể cả 2016 và 09/2018), `agg_category_monthly` (1.282 dòng, danh mục × tháng), `agg_customer_state` (27, bang), `agg_seller_performance` (3.053, người bán), `agg_customer_rfm` (94.983, khách thật) — tổng 311.460 dòng.

**Schema các bảng chính** (kiểu PostgreSQL do loader sinh từ kiểu Arrow; đầy đủ trong Phụ lục C báo cáo và `evidence/parquet_schema_inspect.txt`):

Bảng: Schema ba bảng đầu vào chính {w=3.6,12.4}
| Bảng | Cột (kiểu) |
|---|---|
| `analytics.kpi_monthly` (20 dòng, khoá `purchase_year, purchase_month`) | purchase_year, purchase_month (INTEGER); orders, customers, items (BIGINT); revenue, freight (NUMERIC(32,2)); gmv (NUMERIC(33,2)); avg_order_value (NUMERIC(24,2)); avg_review_score, avg_delivery_days, late_delivery_pct (DOUBLE PRECISION); revenue_mom_pct, orders_mom_pct, revenue_yoy_pct (NUMERIC); revenue_rank (INTEGER); is_black_friday_month (BOOLEAN) |
| `analytics.customer_segments` (94.983 dòng, khoá `customer_unique_id`) | customer_unique_id, customer_state (TEXT); first_purchase_date, last_purchase_date (DATE); recency_days (INTEGER); frequency (BIGINT); monetary (NUMERIC(33,2)); avg_order_value (NUMERIC(24,2)); r_score, f_score, m_score (INTEGER); rfm_segment (TEXT); cluster (INTEGER) |
| `gold.fact_orders` (99.441 dòng, khoá `order_id`) | order_id, customer_id, customer_unique_id, order_status (TEXT); is_valid_sale (BOOLEAN); order_purchase_timestamp (TIMESTAMP); purchase_date (DATE); customer_state, customer_city (TEXT); items, sellers (BIGINT); items_value, freight_value, order_value, payment_total (NUMERIC); payment_count (BIGINT); main_payment_type (TEXT); max_installments, delivery_days, delivery_delay_days (INTEGER); is_late (BOOLEAN); review_score (INTEGER); review_has_comment, dq_* (BOOLEAN); purchase_year, purchase_month (INTEGER) |

**Ví dụ bản ghi thật** (đọc trực tiếp từ Parquet):

Bảng: Ví dụ bản ghi đầu vào {w=3.2,12.8}
| Bảng | Bản ghi |
|---|---|
| `kpi_monthly` (tháng Black Friday) | purchase_year 2017, purchase_month 11, orders 7.421, customers 7.313, items 8.626, revenue 1.003.862,14, freight 168.329,54, gmv 1.172.191,68, avg_order_value 157,96, avg_review_score 3,95, avg_delivery_days 15,1, late_delivery_pct 14,31, revenue_mom_pct 52,06, orders_mom_pct 63,21, revenue_rank 1, is_black_friday_month true |
| `customer_segments` | customer_unique_id `031e19fc…f41675c3`, customer_state SP, first/last_purchase_date 2018-07-04, recency_days 105, frequency 2, monetary 35,94, avg_order_value 17,97, r/f/m_score 5/5/1, rfm_segment Loyal, cluster 1 |
| `gold.fact_orders` | order_id `c776863a…04b21413`, order_status delivered, is_valid_sale true, purchase_date 2016-10-10, customer_state MA, items 1, items_value 176,97, freight_value 87,11, order_value 264,08, main_payment_type credit_card, max_installments 3, delivery_days 65, is_late true, review_score NULL, dq_* false |

**Các trường dữ liệu chính và quy tắc đi kèm.** `revenue` = tổng giá sản phẩm của đơn hợp lệ (`is_valid_sale`), chưa gồm phí ship; `gmv` = revenue + phí ship; đếm khách bằng `customer_unique_id` (99.441 `customer_id` nhưng chỉ 96.096 khách thật); `avg_review_score` ở cấp đơn; `late_delivery_pct` tính trên đơn đã giao; chuỗi thời gian dùng khung 2017-01 → 2018-08; tiền là BRL, 2 chữ số thập phân.
