# 5.1. Quy trình được lựa chọn

> **Yêu cầu 5.1 (đề bài):** Nêu rõ nhóm phụ trách giai đoạn nào trong pipeline, ranh giới bắt đầu/kết thúc và quan hệ với các giai đoạn trước/sau.

**Giai đoạn phụ trách.** Nhóm em phụ trách quy trình con **Analytics → Presentation** trong pipeline Sources → Ingestion → Storage → Processing → Analytics → Presentation → Decision/Action. Nhiệm vụ: đưa kết quả phân tích mà nhóm Analytics đã tính trên Spark tới người dùng nghiệp vụ dưới dạng dashboard, và tới giai đoạn Decision/Action dưới dạng dữ liệu máy đọc được.

**Ranh giới bắt đầu (input của nhóm em).**

- 16 bảng Parquet output của nhóm Analytics, nằm trong repo upstream `Analytics-main` ở thư mục `data/analytics/<bảng>/part-00000-*.snappy.parquet` (mỗi bảng một thư mục kiểu Spark); nhóm em sao chép nguyên vẹn vào `data/analytics/` của repo mình.
- 7 bảng gold do nhóm Processing bàn giao (đầu vào của chính nhóm Analytics) trong `data/gold/`, trong đó `fact_orders` và `fact_order_items` phân vùng `purchase_year=YYYY/purchase_month=M/`. Nhóm em chỉ dùng gold để lọc chéo và cộng lại trên dashboard.
- Tài liệu bàn giao: `ANALYTICS_HANDOVER.md`, `HANDOVER.md`, `SCHEMA.md`, `MANIFEST.json`, `analytics_report.md`, `analytics_summary.json` (bản sao trong `docs/upstream/`). Các tài liệu này quy định grain, quy tắc và số neo để đối chiếu, ví dụ tổng doanh thu 13.494.400,74 BRL.

**Ranh giới kết thúc (output của nhóm em).**

- Cơ sở dữ liệu phục vụ trên Neon Postgres (database `olist_analytics`): schema `analytics` (16 bảng + `load_log`), `gold` (7 bảng), `presentation` (22 view + bảng `dim_state`).
- Dashboard Apache Superset "Thương mại điện tử Olist · Phân tích → Trình bày" tại `http://localhost:8088/superset/dashboard/olist-presentation/`: 7 tab, 45 biểu đồ, 7 bộ lọc native.
- View `presentation.v_decision_hints` (7 luật có ngưỡng và hành động) và `presentation.v_seller_watchlist` (153 người bán, mức ĐỎ/VÀNG) — giao diện cho giai đoạn Decision/Action đọc bằng SQL.
- Phụ trợ: landing page giới thiệu `http://localhost:8090` (đọc `web/data/kpi.json` xuất từ Neon) và bộ minh chứng trong `evidence/`.

**Không thuộc phạm vi.** Nhóm em không đọc lại CSV thô, không làm sạch dữ liệu, không chạy lại Spark, không tính lại các phân tích của nhóm Analytics (Pareto, RFM, K-Means, watchlist) và không sửa số liệu của họ. Nhóm em cũng không tự thực thi hành động (gửi email, gọi webhook) — đó là việc của giai đoạn Decision/Action.

**Quan hệ với giai đoạn trước và sau.**

Bảng: Giao diện của nhóm em với giai đoạn trước và sau {w=2.8,6.6,6.6}
| | Giai đoạn trước: Processing → Analytics | Giai đoạn sau: Presentation → Decision/Action |
|---|---|---|
| Nhận / giao | Nhận 16 bảng Analytics + 7 bảng gold (Parquet) | Giao view SQL `v_decision_hints`, `v_seller_watchlist`; dashboard |
| Hình thức hợp đồng | Data contract: tên bảng, grain (1 dòng = gì), khoá, kiểu dữ liệu, quy tắc (khung 2017-01 → 2018-08, đếm `customer_unique_id`, review cấp đơn), số neo | Schema `presentation` ổn định; mỗi luật có `priority`, `severity`, `signal`, `metric_value`, `threshold`, `action`, `source` |
| Kiểm soát | `loader/validate.py`: 23/23 bảng khớp số dòng, 19/19 số neo | Luật tính lại mỗi lần truy vấn nên tự cập nhật sau mỗi lần nạp |
| Khi bên kia thay đổi | Analytics chạy lại → nhóm em chạy lại `load_to_neon.py` (idempotent) | Nhóm Decision chỉ cần chuỗi kết nối chỉ đọc, không phụ thuộc giao diện Superset |
