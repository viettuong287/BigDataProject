<!-- Trang bìa, tóm tắt, mục lục. Directive {{...}} do build_report.py xử lý. -->
{{cover}}

{{section:front}}

# Tóm tắt

Đồ án thực hiện giai đoạn **Analytics → Presentation** của pipeline dữ liệu lớn trên bộ dữ liệu thương mại điện tử Olist (Brazil, khoảng 100 nghìn đơn hàng 2016–2018, 1,55 triệu dòng thô). Đầu vào là {{var:n_tables}} bảng Parquet ({{var:total_rows}} dòng) do nhóm Analytics tính trên cụm Apache Spark, bao phủ sáu chủ đề: xu hướng KPI, danh mục, địa lý – logistics, phân khúc khách hàng RFM/K-Means, người bán, giao trễ – đánh giá – thanh toán. Nhóm xây dựng tầng phục vụ gồm: loader Python (pyarrow + COPY) nạp dữ liệu vào **Neon Serverless Postgres** (tách compute/storage, scale-to-zero), kèm 7 bảng gold để lọc chéo; tầng ngữ nghĩa {{var:n_views}} view SQL chuẩn hoá KPI; dashboard **Apache Superset** (Docker) 7 tab, 45 chart, 7 bộ lọc native và khu vực gợi ý quyết định (7 luật có ngưỡng, 153 người bán cần theo dõi) cho giai đoạn Decision/Action. Kết quả: {{var:load_total_rows}} dòng ({{var:load_tables}} bảng) nạp trong {{var:load_total_seconds}} giây, {{var:load_ok}} bảng khớp số dòng, {{var:val_anchor_ok}} kiểm tra số neo đạt (doanh thu 13.494.400,74 BRL; đỉnh 11/2017 tăng 52,06%; đơn trễ 2,56 sao so với 4,29; 3,04% khách mua lại). Truy vấn dashboard có trung vị {{var:latency_median}} ms (server {{var:latency_server_median}} ms); một tab mở trong {{var:dash_tab_warm_median}} giây khi có cache; thí nghiệm ×10 cho thấy view tổng hợp giữ {{var:scale_view}} ms trong khi truy vấn dữ liệu thô tăng lên {{var:scale_raw_hi}} ms. Hệ thống tái lập được bằng Docker Compose và mã nguồn công khai.

**Từ khoá:** Big Data, Parquet, Apache Spark, serving layer, Neon, serverless PostgreSQL, semantic layer, Apache Superset, dashboard, Olist.

# Thông tin nhóm

| Hạng mục | Thông tin |
|---|---|
| Học phần / lớp | Nhập môn Dữ liệu lớn – DCT123C5, Trường Đại học Sài Gòn |
| Giảng viên | Vũ Ngọc Thanh Sang |
| Thành viên | Võ Việt Tường (3123411334, nhóm trưởng); Nguyễn Hoàng Phi Long (3123411180); Mai Hồng Phong (3123411225) |
| Quy trình phụ trách | Analytics → Presentation |
| Đầu vào | 16 bảng Parquet của nhóm Analytics + 7 bảng gold, tài liệu `ANALYTICS_HANDOVER.md` |
| Đầu ra cho giai đoạn sau | View `presentation.v_decision_hints`, `v_seller_watchlist` trên Neon; dashboard Superset |
| Kho mã nguồn | {{var:repo_url}} |

Phân công thực tế và mức đóng góp của từng thành viên ở Phụ lục G.

{{toc}}

{{list_figures}}

{{list_tables}}

# Danh mục từ viết tắt

| Viết tắt | Diễn giải |
|---|---|
| AOV | Average Order Value – giá trị đơn hàng trung bình |
| BI | Business Intelligence |
| BRL | Real Brazil (đơn vị tiền tệ) |
| CU | Compute Unit của Neon (≈ 1 vCPU + 4 GB RAM) |
| GMV | Gross Merchandise Value = doanh thu hàng + phí vận chuyển |
| KPI | Key Performance Indicator |
| MoM | Month-over-Month |
| OLAP / OLTP | Online Analytical / Transaction Processing |
| PTTT | Phương thức thanh toán |
| RFM | Recency – Frequency – Monetary |
| RTT | Round-trip time – thời gian khứ hồi mạng |
| TLS | Transport Layer Security |

{{section:body}}
