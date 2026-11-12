# 9. Kết luận

Đồ án đã thực hiện giai đoạn **Analytics → Presentation** của pipeline dữ liệu lớn trên bộ dữ liệu Olist. Đối chiếu với mục tiêu ở Chương 1:

- **Nạp đúng và đủ:** {{var:load_tables}} bảng ({{var:n_tables}} Analytics + {{var:n_gold}} gold, {{var:load_total_rows}} dòng) được nạp vào Neon bằng loader tự sinh DDL và `COPY`, có `load_log`; {{var:val_rows_ok}} bảng khớp số dòng, {{var:val_anchor_ok}} kiểm tra số neo/nhất quán đạt.
- **Tầng ngữ nghĩa:** {{var:n_views}} view và bảng `dim_state` định nghĩa KPI thống nhất, xử lý đúng độ đo không cộng dồn qua lớp cấp đơn, bổ sung cột trình bày và mã hoá 7 luật gợi ý quyết định.
- **Dashboard:** Superset nhiều tab cho năm nhóm người dùng, có thẻ KPI, xu hướng, Pareto, bản đồ Brazil, bảng chi tiết, bộ lọc native và khu vực gợi ý quyết định.
- **Đo lường:** nạp toàn bộ trong {{var:load_total_seconds}} giây (16 bảng Analytics trong {{var:load_ana_seconds}} giây), nút thắt là băng thông của client; {{var:latency_queries}} truy vấn dashboard có trung vị {{var:latency_median}} ms phía client nhưng chỉ {{var:latency_server_median}} ms thực thi trên server — mạng chiếm phần lớn độ trễ, còn bảng tổng hợp sẵn nhanh hơn hơn 250 lần so với tính lại từ fact.
- **Tái lập:** Docker Compose, mã nguồn tại {{var:repo_url}}, dashboard dựng bằng REST API, báo cáo sinh bằng script.

Dashboard truyền tải năm thông điệp chính: (1) doanh thu đỉnh không đồng nghĩa vận hành khoẻ (11/2017, 03/2018 trễ cao, review thấp); (2) giao trễ làm mất ~1,7 sao, sau 4 ngày trễ phần lớn khách chấm 1 sao; (3) địa lý quyết định trải nghiệm — SP gần người bán nên nhanh và hài lòng; (4) 97% khách chỉ mua một lần, CRM nên tập trung vào 3% khách mua lại và khách mới; (5) ~18% người bán tạo 80% doanh thu, 153 người bán lớn nhưng vận hành kém là rủi ro lớn nhất phía cung.

**Khả năng tích hợp:** với giai đoạn trước, nhóm giao tiếp qua data contract trên Parquet — Analytics chạy lại thì chỉ cần chạy lại loader. Với giai đoạn sau, `v_decision_hints` và `v_seller_watchlist` là giao diện máy đọc được để kích hoạt cảnh báo, thông báo hoặc điều chỉnh nghiệp vụ mà không phụ thuộc dashboard. Cùng các nhóm khác, đồ án góp phần hình thành pipeline hoàn chỉnh từ dữ liệu thô đến hành động.
