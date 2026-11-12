# Độ trễ truy vấn dashboard (Neon Postgres)

Thời điểm đo: 2026-11-12 15:48:26 · Script: `scripts/measure_latency.py` · Endpoint pooled (PgBouncer) như Superset · 5 lần đo/truy vấn sau 1 lần làm nóng.

- Thiết lập kết nối TLS mới: **1134 ms** (Superset mở kết nối mới cho mỗi truy vấn).
- Round-trip mạng `SELECT 1`: **105 ms** (máy local → Neon ap-southeast-1).
- Trung vị 21 truy vấn dashboard: **173 ms** phía client, **1.25 ms** phía server.
- Chậm nhất: Xu hướng danh mục – v_category_monthly – 288 ms (server 1.5 ms).

| Tab | Truy vấn | Số dòng trả về | Client trung vị (ms) | Client max (ms) | Server thực thi (ms) |
|---|---|---:|---:|---:|---:|
| Tổng quan | Thẻ KPI (6 chỉ số) – v_orders | 1 | 244.0 | 427.3 | 167.87 |
| Tổng quan | Thẻ KPI có lọc bang SP + 2018 | 1 | 151.0 | 442.0 | 50.27 |
| Tổng quan | Xu hướng tháng – v_kpi_monthly | 20 | 174.4 | 255.5 | 0.16 |
| Danh mục | Pareto top 25 – v_category_pareto | 25 | 129.6 | 235.5 | 0.24 |
| Danh mục | Heatmap mùa vụ – v_category_seasonality | 144 | 207.5 | 425.4 | 0.48 |
| Danh mục | Xu hướng danh mục – v_category_monthly | 1,246 | 287.6 | 352.6 | 1.48 |
| Danh mục | Doanh thu danh mục × bang (lọc 3 danh mục) – v_sales_items | 81 | 171.0 | 329.4 | 53.0 |
| Địa lý | Bản đồ / bảng bang – v_state_logistics | 27 | 129.8 | 226.0 | 0.22 |
| Địa lý | Khoảng cách – v_insight_distance | 4 | 126.0 | 219.2 | 0.17 |
| Khách hàng | Pie phân khúc RFM – v_rfm_customers (94.983 dòng) | 6 | 189.0 | 301.2 | 95.88 |
| Khách hàng | Cụm K-Means lọc bang RJ + 3 segment | 1 | 173.4 | 226.4 | 1.25 |
| Khách hàng | Bảng segment – v_rfm_segments | 6 | 247.0 | 374.1 | 151.95 |
| Seller | Pareto nhóm seller – v_seller_pareto | 3 | 201.7 | 302.7 | 2.36 |
| Seller | Bubble top 300 seller – v_seller_pareto | 300 | 129.6 | 443.9 | 2.5 |
| Seller | Bảng watchlist – v_seller_watchlist | 153 | 151.7 | 444.3 | 0.51 |
| Review/PTTT | Trễ vs review – v_late_vs_review | 2 | 131.5 | 254.5 | 0.11 |
| Review/PTTT | Ngưỡng ngày trễ – v_delay_vs_review | 5 | 99.7 | 234.0 | 0.11 |
| Review/PTTT | Payment mix – v_payment_mix | 10 | 108.1 | 206.6 | 0.14 |
| Review/PTTT | Pie PTTT – v_orders | 4 | 192.1 | 405.8 | 117.72 |
| Quyết định | Gợi ý quyết định – v_decision_hints | 7 | 189.7 | 282.3 | 108.16 |
| Quyết định | Nhật ký nạp – v_load_log | 23 | 186.4 | 197.8 | 0.18 |
| So sánh | Pareto danh mục tính lại từ gold.fact_order_items (không dùng bảng tổng hợp) | 25 | 171.4 | 337.4 | 66.43 |

Ghi chú: thời gian client = mạng + thực thi; phần lớn là round-trip mạng. Dòng 'So sánh' cho thấy chi phí khi tính lại từ bảng fact thay vì đọc bảng Analytics đã tổng hợp sẵn.
