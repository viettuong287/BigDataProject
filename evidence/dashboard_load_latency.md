# Thời gian tải dashboard Superset: cold vs cache

Đo ngày 2026-11-13 bằng `scripts/take_screenshots.py` (Playwright + Chromium headless, viewport 1600×1900),
Superset 4.1.2 giao diện tiếng Việt trong Docker (4 worker gunicorn), dữ liệu trên Neon `aws-ap-southeast-1` (0,25 CU).
"Cold" = đã xoá cache Superset trước khi chạy, mọi chart phải truy vấn Neon; "cache" = mở lại ngay sau đó
(cache kết quả 600 s). Thời gian render = từ lúc bấm tab tới khi mọi chart trong tab hết spinner.

## 1. Theo tab (`dashboard_load_time.csv`)

| Tab | Số thành phần | Cold (s) | Cache (s) |
|---|---:|---:|---:|
| 1 · Tổng quan & xu hướng | 11 | 6,64 | 0,98 |
| 2 · Danh mục & mùa vụ | 4 | 3,98 | 1,13 |
| 3 · Địa lý & logistics | 5 | 4,02 | 1,10 |
| 4 · Khách hàng & RFM | 10 | 8,38 | 2,50 |
| 5 · Người bán | 7 | 12,18 | 2,46 |
| 6 · Giao trễ, đánh giá & thanh toán | 6 | 7,72 | 1,35 |
| 7 · Gợi ý quyết định & nguồn dữ liệu | 4 | 2,42 | 1,19 |
| **Trung vị** | | **6,64** | **1,19** |
| **Tổng 7 tab** | 47 | **45,34** | **10,71** |

Khung dashboard (HTML + JS) tải trong ~2,1 s. Không chart nào lỗi ở cả hai lượt.
Áp dụng bộ lọc native (6 kịch bản, ảnh `filter_*.png`): 2,1–4,7 s mỗi lần, đo từ lúc chuyển sang tab đích
(đã áp bộ lọc) tới khi các chart trong tab vẽ xong.

## 2. Theo chart, qua REST API (`superset_chart_latency.csv`)

Replay đúng payload `/api/v1/chart/data` mà trình duyệt gửi, xác thực bằng cookie phiên + header `X-CSRFToken`,
3 lần mỗi chế độ:

- `force=true` (bỏ cache, Superset mở kết nối mới tới Neon và chạy SQL): trung vị **1.880 ms**/chart
  (1,4–5,1 s; các mixed chart chạy 2 truy vấn mất 3,0–5,1 s).
- Đọc từ cache Superset: trung vị **75 ms**/chart — nhanh hơn ~25 lần.
- 44/44 chart đo thành công (Country Map dùng endpoint legacy `explore_json` nên không nằm trong phép replay).

## 3. Diễn giải

- Thời gian thực thi SQL phía Neon chỉ ~1 ms cho hầu hết view (`query_latency.md`); phần lớn thời gian mỗi chart là
  bắt tay TLS kết nối mới (~1,1 s đo riêng) + các round-trip mạng ~105 ms VN → Singapore, vì Superset dùng NullPool.
- So với lần đo 2026-11-12 (trung vị 741 ms/chart, tab cold 5,24 s), lần này chậm hơn ở phần không cache do đường
  truyền tới Singapore lúc đo; phần có cache gần như không đổi (55 → 75 ms/chart, 1,04 → 1,19 s/tab).
- Tab cold chậm nhất (Người bán, 12,2 s) là do các chart xếp hàng chờ kết nối, không phải do truy vấn nặng.
- Cache kết quả đưa thời gian mở tab về ~1–2,5 s, đủ cho người dùng nghiệp vụ; muốn cold nhanh hơn: đặt Superset cùng
  region với Neon, bật pool kết nối, hoặc làm nóng cache định kỳ (Celery beat).
