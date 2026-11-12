<!-- Trang bìa, tóm tắt, mục lục. Directive {{...}} do build_report.py xử lý. -->
{{cover}}

{{section:front}}

# Tóm tắt

Đồ án thực hiện giai đoạn **Analytics → Presentation** của pipeline dữ liệu lớn trên bộ dữ liệu thương mại điện tử Olist (Brazil, khoảng 100 nghìn đơn hàng 2016–2018, 1,55 triệu dòng thô). Đầu vào là {{var:n_tables}} bảng Parquet ({{var:total_rows}} dòng) do nhóm Analytics tính trên cụm Apache Spark, bao phủ sáu chủ đề: xu hướng KPI, danh mục, địa lý – logistics, phân khúc khách hàng RFM/K-Means, người bán, giao trễ – đánh giá – thanh toán. Nhóm xây dựng tầng phục vụ gồm: loader Python (pyarrow + COPY) nạp dữ liệu vào **Neon Serverless Postgres** (tách compute/storage, tự co giãn, scale-to-zero), kèm 7 bảng gold để lọc chéo; tầng ngữ nghĩa {{var:n_views}} view SQL chuẩn hoá định nghĩa KPI; dashboard **Apache Superset** (Docker) với thẻ KPI, xu hướng, Pareto, bản đồ bang, bộ lọc native và khu vực gợi ý quyết định (7 luật có ngưỡng, danh sách người bán cần theo dõi) cho giai đoạn Decision/Action. Kết quả: {{var:load_total_rows}} dòng ({{var:load_tables}} bảng) được nạp trong {{var:load_total_seconds}} giây, {{var:load_ok}} bảng khớp số dòng; {{var:val_anchor_ok}} kiểm tra số neo đạt (doanh thu 13.494.400,74 BRL; đỉnh 11/2017 tăng 52,06%; đơn trễ 2,56 sao so với 4,29; 3,04% khách mua lại); trung vị độ trễ truy vấn dashboard {{var:latency_median}} ms (thực thi trên server {{var:latency_server_median}} ms). Hệ thống tái lập được bằng Docker Compose và mã nguồn công khai.

**Từ khoá:** Big Data, Parquet, Apache Spark, serving layer, Neon, serverless PostgreSQL, semantic layer, Apache Superset, dashboard, Olist.

# Thông tin nhóm

Nhóm gồm năm thành viên, phụ trách quy trình con **Analytics → Presentation** (Mục 4 của đề bài). Danh sách thành viên và vai trò chính được trình bày trên trang bìa; bảng phân công chi tiết theo nhiệm vụ thực tế và mức đóng góp của từng người nằm ở Phụ lục G. Mã nguồn, cấu hình và minh chứng được lưu tại kho {{var:repo_url}}.

| Hạng mục | Thông tin |
|---|---|
| Học phần | Nhập môn Dữ liệu lớn |
| Quy trình phụ trách | Analytics → Presentation |
| Giai đoạn trước (đầu vào) | Processing → Analytics: 16 bảng Parquet + `ANALYTICS_HANDOVER.md` (kèm 7 bảng gold chi tiết) |
| Giai đoạn sau (đầu ra) | Presentation → Decision/Action: view `presentation.v_decision_hints`, `v_seller_watchlist` trên Neon |
| Kho mã nguồn | {{var:repo_url}} |
| Ngày sinh báo cáo | {{var:build_date}} |

{{toc}}

{{list_figures}}

{{list_tables}}

# Danh mục từ viết tắt

| Viết tắt | Diễn giải |
|---|---|
| AOV | Average Order Value – giá trị đơn hàng trung bình |
| BI | Business Intelligence – trí tuệ doanh nghiệp |
| BRL | Real Brazil (đơn vị tiền tệ) |
| CU | Compute Unit của Neon (≈ 1 vCPU + 4 GB RAM) |
| DDL | Data Definition Language (CREATE/ALTER/DROP) |
| ETL/ELT | Extract – Transform – Load |
| GMV | Gross Merchandise Value = doanh thu hàng + phí vận chuyển |
| KPI | Key Performance Indicator – chỉ số hiệu suất chính |
| MoM / YoY | Month-over-Month / Year-over-Year |
| OLAP / OLTP | Online Analytical / Transaction Processing |
| PTTT | Phương thức thanh toán |
| RFM | Recency – Frequency – Monetary |
| SLA | Service Level Agreement – cam kết mức dịch vụ |
| TLS | Transport Layer Security |

{{section:body}}
