# Bàn giao: Analytics → Presentation

Repo này **chỉ chứa Analytics**. Mọi đường dẫn dưới đây tính từ gốc repo.

## Bạn nhận gì

| Thư mục | Dùng để |
|---|---|
| `data/analytics/*.parquet` | Vẽ dashboard (Power BI: Get Data → Parquet / Folder) |
| `reports/analytics_report.md` | Bảng xem trước, số đối chiếu |
| `docs/03-cau-hoi-va-kpi.md` | Diễn giải 6 chủ đề (copy caption) |

Không cần Spark nếu chỉ vẽ. Cần số mới thì chạy lại theo `README.md`.

## 6 chủ đề → bảng

| Chủ đề | Bảng (trong `data/analytics/`) | 1 dòng = |
|---|---|---|
| 1. Xu hướng | `kpi_monthly` | 1 tháng (2017-01→2018-08) |
| 2. Danh mục | `category_pareto`, `category_seasonality` | 1 ngành / ngành × tháng 2017 |
| 3. Địa lý | `state_logistics`, `insight_distance` | 1 bang / 1 band km |
| 4. Khách hàng | `rfm_scores`, `repeat_profile`, `repeat_categories`, `repeat_states`, `customer_segments`, `cluster_profile` | 1 khách hoặc 1 nhóm |
| 5. Seller | `seller_pareto`, `seller_watchlist` | 1 seller |
| 6. Review / PTTT | `insight_late_vs_review`, `delay_vs_review`, `payment_mix` | 1 nhóm |

Mỗi bảng Spark ghi thành **một file** `part-*.parquet` trong thư mục cùng tên.

## Quy tắc khi vẽ

1. Doanh thu / đơn: các bảng `agg_*` và output Analytics đã lọc đơn hợp lệ. `kpi_monthly` **không** gồm 2016 và 2018-09 (tháng rỗng) — tổng KPI tháng **khác** 13.494.400,74.
2. Đếm khách: `customer_unique_id`.
3. Review: dùng `insight_late_vs_review` / `delay_vs_review` / `kpi_monthly`, **không** trung bình `review_score` trên `fact_order_items`.
4. RFM: ~97% `frequency = 1`. Tách one-shot vs repeat (`repeat_profile`). Nhãn CRM: cột `rfm_segment`. Cột `cluster` là K-Means (xem `cluster_profile` trước khi đặt tên).

## Số neo (lần chạy 2026-10-29)

- Gold `SUM(revenue) = 13.494.400,74` — 4/4 kiểm tra đạt
- Đỉnh doanh thu: 11/2017, MoM +52%
- Đơn trễ vs đúng hạn: review 2,56 vs 4,29
- Repeat: 3,04% khách (2.887 / 94.983)
