# Thí nghiệm mở rộng trên Neon (0,25 CU)

Nhân bản `gold.fact_order_items` (đơn hợp lệ) ×N bằng `generate_series` ngay trên server, đo truy vấn kiểu dashboard bằng `EXPLAIN ANALYZE` (trung vị 3 lần, chỉ thời gian server). Script: `scripts/scale_experiment.py`.

| ×N | Số dòng | MB | Sinh dữ liệu (s) | Dòng/s (server) | Doanh thu tháng × danh mục trên dữ liệu thô (ms) | Lọc 1 danh mục, có index (ms) | Đọc view tổng hợp sẵn (ms) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 112,101 | 12.7 | 0.18 | 607,063 | 47.0 | 2.5 | 1.1 |
| 2 | 224,202 | 24.2 | 0.25 | 892,497 | 93.5 | 4.8 | 1.1 |
| 5 | 560,505 | 59.2 | 0.57 | 984,986 | 272.9 | 11.3 | 1.1 |
| 10 | 1,121,010 | 117.7 | 1.16 | 968,083 | 506.6 | 18.5 | 1.1 |

- Dữ liệu ×10: truy vấn thô tăng từ 47.0 ms lên 506.6 ms (×10.8), gần tuyến tính theo số dòng.
- Đọc bảng/view đã tổng hợp ở Spark giữ ~1.1 ms bất kể dữ liệu nguồn lớn bao nhiêu: đây là lý do Presentation đọc output Analytics thay vì tính lại từ fact.
- Truy vấn có điều kiện lọc dùng index tăng chậm hơn nhiều so với quét toàn bảng.
