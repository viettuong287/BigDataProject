# 5.7. Kết quả demo/thực nghiệm

> **Yêu cầu 5.7 (đề bài):** Có bằng chứng quy trình hoạt động: log, ảnh chụp, dashboard, dữ liệu trước/sau, số liệu throughput/latency/thời gian xử lý, kết quả truy vấn hoặc kết quả phân tích phù hợp.

Bảng: Kết quả chính và tệp minh chứng {w=3.0,9.0,4.0}
| Hạng mục | Kết quả | Tệp minh chứng |
|---|---|---|
| Nạp dữ liệu (13/11/2026, run `20261113-073946-65395d`) | 23 bảng, **505.592 dòng**, 42,88 MB Parquet; tổng thời gian các bảng **277,8 s** (log tính cả khởi tạo 284,7 s) → **~1.820 dòng/s**; riêng pha COPY 256,4 s → 1.972 dòng/s; 16 bảng Analytics 66,4 s; CSV truyền 107,4 MB ≈ 0,42 MB/s (nút thắt: băng thông tải lên Việt Nam → Singapore) | `evidence/load_run.log`, `evidence/load_log.csv`, bảng `analytics.load_log` |
| Dữ liệu trước/sau | Parquet (trước) và Postgres (sau): **23/23 bảng khớp số dòng**; tổng doanh thu 13.494.400,74 BRL giống nhau tới từng xu | `evidence/validation.md` |
| Số neo nghiệp vụ | **19/19 đạt**: đỉnh 2017-11 MoM +52,06%; review trễ 2,56 vs đúng hạn 4,29; khách mua lại 2.887/94.983 = 3,04%; 153 người bán watchlist; 539 người bán tạo 80% doanh thu; nhất quán chéo `v_orders`/`v_sales_items` (gold) = `kpi_monthly` (Analytics), chênh 0,00 | `evidence/validation.json`, `sql/90_anchor_checks.sql` |
| Độ trễ truy vấn | 21 truy vấn của dashboard (endpoint pooled, 5 lần/truy vấn): trung vị **173 ms phía client** nhưng **1,25 ms phía server**; RTT `SELECT 1` = **105 ms**; mở kết nối TLS mới 1.134 ms; Pareto đọc view 0,24 ms vs tính lại từ fact 66,43 ms | `evidence/query_latency.md` |
| Tải dashboard (Playwright) | 7 tab, cache trống (cold) → có cache: Tổng quan 5,52 → 1,00 s; Danh mục 3,74 → 0,94; Địa lý 3,83 → 1,51; Khách hàng & RFM 6,38 → 2,61; Người bán 5,55 → 3,39; Giao trễ 3,65 → 1,92; Gợi ý quyết định 2,71 → 1,05; trung vị **3,83 s → 1,51 s**; biểu đồ qua API: 1.558 ms → 67 ms (44/44 biểu đồ, nhanh ~23 lần); 0 biểu đồ lỗi | `evidence/dashboard_load_latency.md`, `superset_chart_latency.csv` |
| Bộ lọc | 6/6 kịch bản đúng; ví dụ 2018 + bang SP: doanh thu 13.449.530 → 2.960.326 BRL, đơn 97.905 → 23.598 | `evidence/filter_*.png`, `dashboard_load_time.csv` |
| Thí nghiệm ×10 | 112.101 → 1.121.010 dòng: tổng hợp trên dữ liệu thô **47 → 507 ms**; lọc có index 2,5 → 18,5 ms; **view tổng hợp giữ 1,1 ms** | `evidence/scale_experiment.md` |
| Kiểm thử QA | **41/41 PASS** (đăng nhập, 7 tab × 2 độ rộng, 6 bộ lọc kiểm giá trị trả về, đổi ngôn ngữ, landing, export/import ZIP, lệnh README) | `evidence/qa_test_cases.md`, `qa_results.json` |

**Kết quả phân tích được trình bày** (ảnh thật từ hệ thống đang chạy, chụp bằng Playwright ngày 13/11/2026):

{{shot:evidence/dashboard_tab1_tong_quan_xu_huong.png|260,50,1600,820|Tab 1 "Tổng quan & xu hướng": 6 thẻ KPI (13.449.530 BRL, 97.905 đơn, 94.703 khách, AOV 160,19, trễ 8,13%, review 4,12) và doanh thu theo tháng – đỉnh 11/2017|h=8.5}}

{{shot:evidence/filter_tab1_thoi_gian_2018_bang_SP.png|0,50,1600,820|Bộ lọc native "Khoảng thời gian = 2018" + "Bang khách hàng = SP": thẻ KPI còn 2.960.326 BRL, 23.598 đơn; biểu đồ chỉ còn 8 tháng 2018|h=7.5}}

{{shot:evidence/watchlist_goi_y_quyet_dinh.png||Tab 7: bảng gợi ý quyết định – dữ liệu từ presentation.v_decision_hints|h=6}}

**Điểm chưa đạt (nhóm em nêu trung thực).** (1) Khi cache trống, **3/7 tab mở quá 5 giây** (5,52 s; 6,38 s; 5,55 s) vì Superset dùng NullPool, mỗi biểu đồ mở một kết nối TLS mới tới Singapore (~1,1 s) và các biểu đồ xếp hàng chờ — truy vấn thực chỉ ~1 ms; có cache thì mọi tab dưới 3,4 s. Hướng khắc phục: bật pool kết nối, đặt Superset cùng vùng với Neon, làm nóng cache định kỳ. (2) Thời gian đánh thức compute Neon sau scale-to-zero chưa được đo tách riêng. (3) Tốc độ nạp bị giới hạn bởi đường truyền tải lên của máy cá nhân. (4) Chỉ xử lý theo lô, chưa có streaming; gói Neon miễn phí 0,25 CU nên chưa kiểm chứng autoscaling nhiều CU. (5) Neon Console cần đăng nhập tương tác nên ảnh kiểm kê Neon (`neon_tables_inventory.png`) được sinh từ catalog database, không phải ảnh chụp Console.
