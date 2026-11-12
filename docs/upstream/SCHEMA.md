# Schema các bảng gold

Sinh tự động từ lần chạy `03_gold.py` lúc 2026-10-28 08:08:47.

## `fact_order_items` (112,650 dòng; 1 dòng = 1 sản phẩm trong 1 đơn hàng)

| Cột | Kiểu |
|---|---|
| `order_id` | string |
| `order_item_id` | int |
| `product_id` | string |
| `seller_id` | string |
| `customer_id` | string |
| `customer_unique_id` | string |
| `order_status` | string |
| `is_valid_sale` | boolean |
| `order_purchase_timestamp` | timestamp |
| `purchase_date` | date |
| `category` | string |
| `price` | decimal(12,2) |
| `freight_value` | decimal(12,2) |
| `item_total` | decimal(12,2) |
| `customer_state` | string |
| `customer_city` | string |
| `seller_state` | string |
| `seller_city` | string |
| `distance_km` | double |
| `delivery_days` | int |
| `delivery_delay_days` | int |
| `is_late` | boolean |
| `review_score` | int |
| `main_payment_type` | string |
| `max_installments` | int |
| `purchase_year` | int |
| `purchase_month` | int |

## `fact_orders` (99,441 dòng; 1 dòng = 1 đơn hàng)

| Cột | Kiểu |
|---|---|
| `order_id` | string |
| `customer_id` | string |
| `customer_unique_id` | string |
| `order_status` | string |
| `is_valid_sale` | boolean |
| `order_purchase_timestamp` | timestamp |
| `purchase_date` | date |
| `customer_state` | string |
| `customer_city` | string |
| `items` | bigint |
| `sellers` | bigint |
| `items_value` | decimal(22,2) |
| `freight_value` | decimal(22,2) |
| `order_value` | decimal(23,2) |
| `payment_total` | decimal(22,2) |
| `payment_count` | bigint |
| `main_payment_type` | string |
| `max_installments` | int |
| `delivery_days` | int |
| `delivery_delay_days` | int |
| `is_late` | boolean |
| `review_score` | int |
| `review_has_comment` | boolean |
| `dq_delivered_without_date` | boolean |
| `dq_carrier_before_purchase` | boolean |
| `dq_no_items` | boolean |
| `dq_no_payment` | boolean |
| `purchase_year` | int |
| `purchase_month` | int |

## `agg_sales_monthly` (24 dòng; 1 dòng = 1 tháng)

| Cột | Kiểu |
|---|---|
| `purchase_year` | int |
| `purchase_month` | int |
| `orders` | bigint |
| `customers` | bigint |
| `items` | bigint |
| `revenue` | decimal(32,2) |
| `freight` | decimal(32,2) |
| `gmv` | decimal(33,2) |
| `avg_order_value` | decimal(24,2) |
| `avg_review_score` | double |
| `avg_delivery_days` | double |
| `late_delivery_pct` | double |

## `agg_category_monthly` (1,282 dòng; 1 dòng = 1 danh mục x 1 tháng)

| Cột | Kiểu |
|---|---|
| `purchase_year` | int |
| `purchase_month` | int |
| `category` | string |
| `orders` | bigint |
| `items` | bigint |
| `revenue` | decimal(22,2) |
| `freight` | decimal(22,2) |
| `avg_price` | decimal(13,2) |
| `avg_review_score` | double |

## `agg_customer_state` (27 dòng; 1 dòng = 1 bang của khách hàng)

| Cột | Kiểu |
|---|---|
| `customer_state` | string |
| `orders` | bigint |
| `customers` | bigint |
| `revenue` | decimal(32,2) |
| `gmv` | decimal(33,2) |
| `avg_order_value` | decimal(24,2) |
| `avg_freight` | decimal(23,2) |
| `freight_pct_of_revenue` | decimal(35,2) |
| `avg_delivery_days` | double |
| `late_delivery_pct` | double |
| `avg_review_score` | double |

## `agg_seller_performance` (3,053 dòng; 1 dòng = 1 người bán)

| Cột | Kiểu |
|---|---|
| `seller_id` | string |
| `seller_state` | string |
| `seller_city` | string |
| `orders` | bigint |
| `items` | bigint |
| `customers` | bigint |
| `revenue` | decimal(22,2) |
| `avg_price` | decimal(13,2) |
| `avg_review_score` | double |
| `avg_delivery_days` | double |
| `late_delivery_pct` | double |
| `avg_distance_km` | double |
| `first_sale_date` | date |
| `last_sale_date` | date |
| `active_months` | bigint |

## `agg_customer_rfm` (94,983 dòng; 1 dòng = 1 khách hàng thật)

| Cột | Kiểu |
|---|---|
| `customer_unique_id` | string |
| `customer_state` | string |
| `first_purchase_date` | date |
| `last_purchase_date` | date |
| `recency_days` | int |
| `frequency` | bigint |
| `monetary` | decimal(33,2) |
| `avg_order_value` | decimal(24,2) |
| `avg_review_score` | double |

