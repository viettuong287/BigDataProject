# Thời gian tải dashboard Superset: cold vs cache

Đo ngày 2026-11-12 bằng `scripts/take_screenshots.py` (Playwright + Chromium headless, viewport 1600×1900),
Superset 4.1.2 trong Docker (4 worker gunicorn), dữ liệu trên Neon `aws-ap-southeast-1` (0,25 CU).
"Cold" = đã xoá cache Superset trước khi chạy, mọi chart phải truy vấn Neon; "cache" = mở lại ngay sau đó
(cache kết quả 600 s). Thời gian render = từ lúc bấm tab tới khi mọi chart trong tab hết spinner.

## 1. Theo tab (`dashboard_load_time.csv`)

| Tab | Số thành phần | Cold (s) | Cache (s) |
|---|---:|---:|---:|
| 1 · Tổng quan & xu hướng | 11 | 6,39 | 0,91 |
| 2 · Danh mục & mùa vụ | 4 | 2,24 | 0,94 |
| 3 · Địa lý & logistics | 5 | 12,66 | 0,95 |
| 4 · Khách hàng & RFM | 10 | 9,93 | 1,18 |
| 5 · Seller | 7 | 5,16 | 2,08 |
| 6 · Giao trễ, review & thanh toán | 6 | 5,24 | 1,06 |
| 7 · Gợi ý quyết định & nguồn dữ liệu | 4 | 2,51 | 1,04 |
| **Trung vị** | | **5,24** | **1,04** |
| **Tổng 7 tab** | 47 | **44,13** | **8,16** |

Khung dashboard (HTML + JS) tải trong ~3 s. Không chart nào lỗi ở cả hai lượt.
Áp dụng bộ lọc native (6 kịch bản, ảnh `filter_*.png`): 0,9–2,5 s mỗi lần.

## 2. Theo chart, qua REST API (`superset_chart_latency.csv`)

Replay đúng payload `/api/v1/chart/data` mà trình duyệt gửi, xác thực bằng cookie phiên + header `X-CSRFToken`,
3 lần mỗi chế độ:

- `force=true` (bỏ cache, Superset mở kết nối mới tới Neon và chạy SQL): trung vị **741 ms**/chart
  (chart 2 truy vấn như mixed chart ~1,4–1,6 s).
- Đọc từ cache Superset: trung vị **55 ms**/chart — nhanh hơn ~13 lần.
- 44/44 chart đo thành công (Country Map dùng endpoint legacy `explore_json` nên không nằm trong phép replay).

## 3. Diễn giải

- Thời gian thực thi SQL phía Neon chỉ ~1 ms cho hầu hết view (`query_latency.md`); phần lớn ~740 ms/chart là
  bắt tay TLS kết nối mới (~1,1 s đo riêng) + round-trip mạng ~105 ms VN → Singapore, vì Superset dùng NullPool.
- Tab cold chậm nhất (Địa lý, 12,7 s) là do các chart xếp hàng chờ kết nối, không phải do truy vấn nặng.
- Cache kết quả đưa thời gian mở tab về ~1 s, đủ cho người dùng nghiệp vụ; muốn cold nhanh hơn: đặt Superset cùng
  region với Neon, bật pool kết nối, hoặc làm nóng cache định kỳ (Celery beat).
