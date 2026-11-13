# Thời gian tải dashboard Superset: cold vs cache

Đo ngày 2026-11-13 13:29 bằng `scripts/take_screenshots.py` (Playwright + Chromium headless, viewport 1600×1900), Superset 4.1.2 giao diện tiếng Việt, theme Olist Insight, trong Docker (4 worker gunicorn), dữ liệu trên Neon `aws-ap-southeast-1` (0,25 CU). "Cold" = đã xoá cache Superset trước khi chạy, mọi chart phải truy vấn Neon; "cache" = mở lại ngay sau đó (cache kết quả 600 s). Thời gian render = từ lúc bấm tab tới khi mọi chart trong tab hết spinner.

## 1. Theo tab (`dashboard_load_time.csv`)

| Tab | Số thành phần | Cold (s) | Cache (s) |
|---|---:|---:|---:|
| 1 · Tổng quan & xu hướng | 11 | 5,52 | 1,00 |
| 2 · Danh mục & mùa vụ | 4 | 3,74 | 0,94 |
| 3 · Địa lý & logistics | 5 | 3,83 | 1,51 |
| 4 · Khách hàng & RFM | 10 | 6,38 | 2,61 |
| 5 · Người bán | 7 | 5,55 | 3,39 |
| 6 · Giao trễ, đánh giá & thanh toán | 6 | 3,65 | 1,92 |
| 7 · Gợi ý quyết định & nguồn dữ liệu | 4 | 2,71 | 1,05 |
| **Trung vị** | | **3,83** | **1,51** |
| **Tổng 7 tab** | 47 | **31,38** | **12,42** |

Khung dashboard (HTML + JS) tải trong ~3,9 s. Lỗi chart: 0. Áp dụng bộ lọc native (6 kịch bản, ảnh `filter_*.png`): 2,0–4,9 s mỗi lần, đo từ lúc chuyển sang tab đích (đã áp bộ lọc) tới khi các chart trong tab vẽ xong.

## 2. Theo chart, qua REST API (`superset_chart_latency.csv`)

Replay đúng payload `/api/v1/chart/data` mà trình duyệt gửi, xác thực bằng cookie phiên + header `X-CSRFToken`, 3 lần mỗi chế độ:

- `force=true` (bỏ cache, Superset mở kết nối mới tới Neon và chạy SQL): trung vị **1.558 ms**/chart (1,3–3,2 s).
- Đọc từ cache Superset: trung vị **67 ms**/chart — nhanh hơn ~23 lần.
- 44/44 chart đo thành công (Country Map dùng endpoint legacy `explore_json` nên không nằm trong phép replay).

## 3. Diễn giải

- Thời gian thực thi SQL phía Neon chỉ ~1 ms cho hầu hết view (`query_latency.md`); phần lớn thời gian mỗi chart là bắt tay TLS kết nối mới + các round-trip mạng Việt Nam → Singapore, vì Superset dùng NullPool.
- Tab cold chậm nhất (Khách hàng & RFM, 6,4 s) là do các chart xếp hàng chờ kết nối, không phải do truy vấn nặng.
- So với lần đo trước: tab cold trung vị 6,64 → 3,83 s, có cache 1,19 → 1,51 s; chart bỏ cache 1.880 → 1.558 ms, từ cache 75 → 67 ms (dao động chủ yếu do đường truyền).
- Cache kết quả đưa thời gian mở tab về ~0,9–3,4 s, đủ cho người dùng nghiệp vụ; muốn cold nhanh hơn: đặt Superset cùng region với Neon, bật pool kết nối, hoặc làm nóng cache định kỳ (Celery beat).
