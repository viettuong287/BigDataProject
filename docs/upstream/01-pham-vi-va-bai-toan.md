# Phạm vi và bài toán

## Vai trò nhóm

**Processing → Analytics.** Nhận 7 bảng Parquet gold (Olist Brazil, 09/2016–10/2018), đặt câu hỏi nghiệp vụ, tính KPI / phân khúc trên Spark, đo thời gian, diễn giải, bàn giao bảng cho Presentation.

Không thuộc phạm vi: CSV raw, silver, job `01_profiling` / `02_clean` / `03_gold`, dashboard Power BI (chỉ xuất bảng họ vẽ được).

## Dữ liệu vào

| Bảng | 1 dòng = | Dùng cho |
|---|---|---|
| `fact_orders` | 1 đơn | Review, thanh toán, giao trễ |
| `fact_order_items` | 1 món trong đơn | Khoảng cách, danh mục khách lặp |
| `agg_sales_monthly` | 1 tháng | Xu hướng KPI |
| `agg_category_monthly` | danh mục × tháng | Pareto, mùa vụ |
| `agg_customer_state` | 1 bang | Logistics theo vùng |
| `agg_seller_performance` | 1 seller | 80/20, watchlist |
| `agg_customer_rfm` | 1 khách thật | RFM, K-Means |

Nguồn: đã nằm trong repo tại `data/gold/` kèm `data/HANDOVER.md`. Số neo: `SUM(revenue) = 13.494.400,74`.

## Năm quy tắc (handover + đề Word)

1. Fact: `WHERE is_valid_sale`. Các `agg_*` đã lọc sẵn.
2. Đếm khách bằng `customer_unique_id` (không `customer_id`).
3. Chuỗi thời gian chỉ 2017-01 → 2018-08.
4. Review trên `fact_orders`, không AVG trên `fact_order_items`.
5. Phân tích giao hàng: `order_status = 'delivered' AND NOT dq_carrier_before_purchase AND NOT dq_delivered_without_date`.

## Kết quả giao

- 14 bảng Parquet trong `data/analytics/`
- `reports/analytics_report.md` (tự sinh, 4/4 đối chiếu đạt)
- `docs/` diễn giải 6 chủ đề
- Ảnh Spark UI trong `evidence/`
