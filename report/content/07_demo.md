# 7. Kết quả demo

## 7.1. Luồng demo từ đầu vào đến đầu ra

1. **Đầu vào:** `data/analytics/` ({{var:n_tables}} bảng) và `data/gold/` (7 bảng) — Parquet do nhóm Analytics bàn giao.
2. **Nạp:** `docker compose run --rm tools python loader/load_to_neon.py` — log từng bảng, dòng tổng, `analytics.load_log` có `run_id` mới; các view được tạo lại.
3. **Kiểm chứng:** `validate.py` — {{var:val_rows_ok}} bảng khớp số dòng, {{var:val_anchor_ok}} số neo "ĐẠT".
4. **Dashboard:** `docker compose up -d superset-db superset` rồi `build_dashboard.py` — mở `http://localhost:8088/superset/dashboard/olist-presentation/`, đi qua 7 tab, áp dụng bộ lọc.
5. **Đầu ra cho Decision/Action:** truy vấn `v_decision_hints` và `v_seller_watchlist` (Mục 7.4).
6. **Giới thiệu:** `docker compose up -d web` — landing page `http://localhost:8090` (Mục 7.5).

Các ảnh dưới đây được Playwright chụp tự động từ hệ thống đang chạy với giao diện Superset tiếng Việt (toàn bộ 7 tab và 6 kịch bản lọc ở `evidence/`; một số tab ở Phụ lục E); để dễ đọc, báo cáo cắt phần chính của mỗi ảnh.

## 7.2. Dashboard và nội dung phân tích

{{shot:evidence/dashboard_tab1_tong_quan_xu_huong.png|270,170,1590,1200|Tab 1 "Tổng quan & xu hướng": 6 thẻ KPI khung 2017-01 → 2018-08, doanh thu tháng gần nhất, doanh thu & số đơn theo tháng, % trễ vs review, MoM|h=11.5}}

**Tổng quan.** Sáu thẻ KPI tính trên `v_orders`: doanh thu 13.449.530 BRL, 97.905 đơn hợp lệ, 94.703 khách, AOV 160,19 BRL, tỷ lệ trễ 8,13%, review 4,12. Doanh thu tăng từ ~120 nghìn BRL (01/2017) lên đỉnh **1.003.862 BRL vào 11/2017** (Black Friday, MoM +52,06%). Thông điệp cho ban điều hành: **bán nhiều không đồng nghĩa vận hành tốt** — 11/2017 trễ 14,31%, review 3,95; 03/2018 trễ 21,36%, review 3,76; trong khi 04–05/2018 doanh thu gần bằng đỉnh mà trễ chỉ 5–8%.

**Danh mục (tab 2).** `health_beauty` 9,30%, `watches_gifts` 8,88%, `bed_bath_table` 7,70% doanh thu; 17 danh mục lớn nhất mới chiếm 79,7% — "đuôi dài" của sàn đa ngành. Mọi ngành lớn đạt đỉnh tháng 11, nên tồn kho và quảng cáo cần dồn vào quý IV.

{{shot:evidence/dashboard_tab3_dia_ly_logistics.png|270,170,1590,760|Tab 3 "Địa lý & logistics": bản đồ doanh thu theo bang và quan hệ ngày giao – review (kích thước = doanh thu)|h=7}}

**Địa lý.** SP chiếm 38,27% doanh thu, giao 8,7 ngày, trễ 5,89%, review 4,21 — góc "nhanh và hài lòng" vì gần người bán; BA (19,3 ngày, trễ 14,04%, review 3,88) và RJ (15,2 ngày, 13,47%, 3,91) ở góc ngược lại dù giá trị đơn cao hơn. Từ 0–200 km lên trên 1.000 km, phí ship tăng 12,66 → 31,65 BRL, ngày giao 7,0 → 19,0, tỷ lệ trễ 6,34% → 11,69% — ưu tiên kho/người bán theo vùng.

**Khách hàng (tab 4).** 96,96% khách chỉ mua một lần; 2.887 khách (3,04%) mua lại, chi trọn đời 308 so với 161 BRL. Phân khúc theo luật: 251 Champions, 675 Loyal, 1.961 At Risk; K-Means tự tách đúng 2.887 khách mua lại thành một cụm. **Giao trễ (tab 6).** Đơn trễ 2,56 sao so với 4,29; trễ 1–3 ngày còn 3,29 sao, trễ 4–7 ngày còn 2,10 sao với 58,6% một sao — căn cứ cho luật "can thiệp trước mốc 4 ngày".

{{shot:evidence/filter_tab1_thoi_gian_2018_bang_SP.png|0,50,1600,790|Bộ lọc native: khoảng thời gian 2018 + bang SP — thẻ KPI và biểu đồ tháng chỉ còn 8 tháng 2018 của bang SP (doanh thu 2.960.326 BRL, 23.598 đơn, trễ 6,82%)|h=7}}

## 7.3. Cảnh báo người bán và gợi ý quyết định

{{shot:evidence/watchlist_seller_canh_bao.png||Tab 5 "Người bán": bảng "Người bán cần theo dõi (watchlist)" – 153 người bán (số vi phạm, lý do, mức ĐỎ/VÀNG, hành động đề xuất)|h=6.5}}

Chỉ 539/3.053 người bán (17,65%) tạo 80% doanh thu. Bảng watchlist liệt kê 153 người bán thuộc top 10% doanh thu nhưng vận hành kém; 75 người ở mức ĐỎ (vi phạm ≥ 2 tiêu chí) kèm hành động "cảnh cáo + giảm hiển thị; yêu cầu kế hoạch SLA 30 ngày". Ví dụ người bán `b1b39487…` (SP): review 1,81, giao 23,4 ngày, trễ 64,29%.

{{shot:evidence/watchlist_goi_y_quyet_dinh.png||Tab 7: bảng "Gợi ý quyết định (luật + ngưỡng + hành động)" — luật, giá trị hiện tại, ngưỡng và hành động (nguồn v_decision_hints)|h=6.5}}

## 7.4. Đầu ra cho giai đoạn Decision/Action

Giai đoạn sau chỉ cần hai truy vấn để lấy toàn bộ đầu vào:

```sql
SELECT priority, severity, topic, signal, metric_value, threshold, action, source
FROM   presentation.v_decision_hints ORDER BY priority;          -- 7 luật

SELECT seller_id, seller_state, revenue, violations, reasons, recommended_action
FROM   presentation.v_seller_watchlist
WHERE  alert_level = 'ĐỎ' ORDER BY revenue DESC;   -- 75 người bán
```

Kết quả là dữ liệu có cấu trúc mà một rule engine có thể chuyển thành email/Telegram cảnh báo hoặc kích hoạt chăm sóc khách hàng khi đơn có nguy cơ trễ ≥ 4 ngày. Dashboard phục vụ con người, view phục vụ máy — hai kênh dùng chung một tầng ngữ nghĩa nên không mâu thuẫn số liệu.

## 7.5. Landing page giới thiệu hệ thống

Trang tĩnh tiếng Việt tại `http://localhost:8090` (nginx, service `web`) là "cửa vào" cho người xem lần đầu: biểu đồ *live replay* phát lại doanh thu và số đơn 20 tháng (2017-01 → 2018-08) từ `v_kpi_monthly` kèm 5 thẻ KPI cập nhật theo tháng; huy hiệu kiểm chứng (19/19 số neo, 23/23 bảng); insight thật (top danh mục, bang, phân khúc RFM, cảnh báo từ `v_decision_hints`); dải pipeline và nút mở dashboard. Mọi con số lấy từ `web/data/kpi.json` do `export_landing_kpi.py` xuất từ Neon, nên trang khớp dashboard mà không cần backend. Ảnh bản mobile (390 px) ở Phụ lục E.

{{shot:evidence/landing_page_desktop.png|0,0,1440,1000|Landing page tại cổng 8090 (1440 px): hero với biểu đồ live replay doanh thu/đơn hàng và thẻ KPI từ web/data/kpi.json|h=9}}
