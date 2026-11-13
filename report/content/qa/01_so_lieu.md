# 1. Bảng tra nhanh – số liệu cần nhớ

Số liệu lấy từ `evidence/` và README tại commit fb9a8b1 (lần nạp 13/11/2026). Khi giảng viên hỏi số, trả lời bằng số tròn trước, số chính xác sau (ví dụ "khoảng 500 nghìn dòng, chính xác 505.592").

Bảng: Số liệu cần nhớ khi vấn đáp
| Hạng mục | Số liệu | Nguồn |
|---|---|---|
| Bộ dữ liệu gốc | Olist Brazil, 99.441 đơn, 09/2016–10/2018; 9 tệp CSV ≈ 1,55 triệu dòng, ~120 MB | Mục 3.1 báo cáo |
| Upstream Spark | Gold: 7 bảng, 33,3 MB, 61,72 s; Analytics: cụm 1 master + 2 worker (4 core), 14 SQL + K-Means k = 4, 119,71 s | `docs/upstream/` |
| Đầu vào của nhóm | 16 bảng Analytics (194.132 dòng, ~8 MB) + 7 bảng gold (311.460 dòng, ~35 MB) = **23 bảng, 505.592 dòng, 42,88 MB Parquet** | `load_run.log` |
| Neon | Project `bigdata-olist-presentation`, PostgreSQL 18.6, **aws-ap-southeast-1 (Singapore)**, **0,25 CU**, gói free, 1 GiB/nhánh, CSDL 146 MB (25 bảng + 22 view) | `neon_project.json`, `neon_tables_inventory.png` |
| Nạp dữ liệu (13/11) | 23/23 bảng khớp; tổng thời gian từng bảng **277,82 s** (log cả overhead 284,74 s); COPY 256,43 s → **1.972 dòng/s**; riêng 16 bảng Analytics 66,44 s; CSV truyền 107,4 MB ≈ 0,42 MB/s | `load_log.csv`, `load_run.log` |
| Kiểm chứng | **23/23** bảng khớp số dòng; **19/19** số neo đạt | `validation.md` |
| Số neo nghiệp vụ | Doanh thu **13.494.400,74 BRL**; đỉnh 11/2017 = 1.003.862 BRL, MoM **+52,06%**; review trễ **2,56** vs đúng hạn **4,29**; khách mua lại **2.887/94.983 = 3,04%**; 539/3.053 người bán (17,65%) tạo 80% doanh thu; 153 người bán watchlist (75 mức ĐỎ) | `validation.md`, README |
| Độ trễ truy vấn | RTT `SELECT 1` **105 ms**; kết nối TLS mới **1.134 ms**; 21 truy vấn dashboard: trung vị **173 ms** phía client, **1,25 ms** phía server; p95 lớn nhất 444 ms | `query_latency.md` |
| Bảng tổng hợp vs tính lại | Pareto danh mục: đọc view **0,24 ms** vs tính lại từ fact **66,43 ms** (server) | `query_latency.md` |
| Tải dashboard (13/11) | Trung vị tab **3,83 s cold → 1,51 s có cache**; **3/7 tab cold > 5 s** (chậm nhất 6,38 s – Khách hàng & RFM); tổng 7 tab 31,38 s → 12,42 s | `dashboard_load_latency.md` |
| Chart qua REST API | 44/44 chart: bỏ cache **1.558 ms** vs cache **67 ms** (~23 lần) | `superset_chart_latency.csv` |
| Bộ lọc | 6/6 kịch bản đúng, 2,0–4,9 s mỗi lần; ví dụ 2018 + SP: doanh thu 13.449.530 → 2.960.326 BRL | `dashboard_load_time.csv`, `filter_*.png` |
| Thí nghiệm ×10 | 112.101 → **1.121.010 dòng** (117,7 MB): truy vấn dữ liệu thô **47 → 507 ms**; lọc có index 2,5 → 18,5 ms; **view tổng hợp giữ 1,1 ms** | `scale_experiment.md` |
| Dashboard | **7 tab, 45 chart, 7 bộ lọc native**, 22 dataset (1 view = 1 dataset); Superset 4.1.2, 4 worker, metadata Postgres 16, cache 600 s | README mục 7 |
| Tầng ngữ nghĩa | 22 view + `dim_state`; `v_decision_hints` 7 luật | `sql/10_presentation_views.sql` |
| Kiểm thử QA | **41/41 PASS** (đăng nhập, 7 tab × 2 độ rộng, 6 bộ lọc, đổi ngôn ngữ, landing, export/import, README) | `qa_test_cases.md` |
| Giao diện | Superset tiếng Việt (bản dịch riêng **536 chuỗi**), thương hiệu Olist Insight; landing page nginx **:8090** | README mục 5 |
