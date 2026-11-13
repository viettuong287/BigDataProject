# 6. Thực nghiệm và đánh giá

## 6.1. Kịch bản, môi trường và tiêu chí

Thực nghiệm trả lời RQ2 (tính đúng đắn), RQ3 (hiệu năng) và cung cấp số liệu cho RQ5 (mở rộng).

Bảng: Các kịch bản thực nghiệm
| Mã | Kịch bản | Cách thực hiện | Đại lượng đo |
|---|---|---|---|
| E1 | Đối chiếu Parquet ↔ Neon | `validate.py`: đếm dòng 23 bảng; 19 truy vấn số neo/nhất quán | Số kiểm tra đạt |
| E2 | Hiệu năng nạp | `load_to_neon.py` ghi thời gian từng pha mỗi bảng | Giây, dòng/s, MB/s |
| E3 | Độ trễ truy vấn | `measure_latency.py`: 21 truy vấn của dashboard qua endpoint pooled, 5 lần sau 1 lần làm nóng | Trung vị, p95 client; thời gian server |
| E4 | Thời gian tải dashboard | Playwright mở 7 tab sau khi xoá cache (cold) và mở lại (cache); replay 44 chart qua REST API | Giây/tab, ms/chart |
| E5 | Bộ lọc native | 6 kịch bản lọc trên 6 tab, chụp ảnh và đo thời gian | Đạt/không, giây |
| E6 | Mở rộng ×1 → ×10 | `scale_experiment.py`: nhân bản `fact_order_items` trên Neon, `EXPLAIN ANALYZE` | ms server theo hệ số |
| E7 | Kiểm thử QA chức năng | `qa_run.ps1` + `qa_check.py` (Playwright): {{var:qa_total}} ca tự động | PASS / FAIL / KNOWN |

**Môi trường.** Client là các container Docker trên máy Windows 11 tại Việt Nam; Neon ở Singapore với {{var:neon_cu}} CU (gói miễn phí). Mọi số đo phía client gồm cả độ trễ mạng (RTT `SELECT 1` ≈ {{var:latency_rtt_ms}} ms).

**Tiêu chí đạt:** đúng đắn 100%; nạp 16 bảng Analytics < 120 s; truy vấn dashboard trung vị < 300 ms, p95 < 500 ms; tab dashboard < 5 s khi cold, < 2 s khi có cache; 100% kịch bản lọc đúng; view tổng hợp không chậm đi khi dữ liệu nguồn tăng; 100% ca QA đạt.

## 6.2. E1 – Đối chiếu dữ liệu

`validate.py` cho kết quả **{{var:val_rows_ok}} bảng khớp số dòng** và **{{var:val_anchor_ok}} kiểm tra số neo/nhất quán đạt**. Ba nhóm kiểm tra: (1) **số neo bàn giao** — tổng doanh thu gold 13.494.400,74 BRL (tính cả từ `agg_sales_monthly` lẫn `fact_order_items`), tháng đỉnh 2017-11 với MoM 52,06%, review 2,56/4,29, 2.887 khách mua lại (3,04%), 153 người bán watchlist, 539 người bán tạo 80% doanh thu; (2) **nhất quán chéo** — tổng doanh thu và số đơn của `v_orders`, tổng doanh thu của `v_sales_items` (từ gold) bằng đúng tổng của `kpi_monthly` (từ Analytics), chênh lệch 0,00; (3) **toàn vẹn tầng ngữ nghĩa** — tổng khách theo phân khúc bằng 94.983, `v_decision_hints` đủ 7 luật. Nhóm (2) cho thấy lớp gold để lọc chéo không tạo ra "hai sự thật". Tổng 20 tháng của `kpi_monthly` (13.449.529,68 BRL) nhỏ hơn số neo vì đã loại 2016 và 09/2018. Chi tiết ở Phụ lục E.

## 6.3. E2 – Hiệu năng nạp dữ liệu

Lần chạy `{{var:load_run_id}}` nạp {{var:load_tables}} bảng, {{var:load_total_rows}} dòng ({{var:load_parquet_mb}} MB Parquet) trong {{var:load_total_seconds}} giây (pha COPY {{var:load_copy_seconds}} giây), thông lượng đầu-cuối {{var:load_throughput}} dòng/s. Riêng {{var:load_ana_tables}} bảng Analytics mất {{var:load_ana_seconds}} giây; {{var:load_gold_tables}} bảng gold mất {{var:load_gold_seconds}} giây (~{{var:load_gold_share}}%). Ba quan sát: (1) **chi phí cố định mỗi bảng** — {{var:load_small_tables}} bảng dưới 1.000 dòng mất trung bình {{var:load_small_avg_s}} giây mỗi bảng do nhiều vòng khứ hồi tới Singapore (DDL, COPY, commit, PK, ANALYZE, đếm), nên cần gộp giao dịch hoặc nạp song song; (2) **bảng lớn bị giới hạn bởi băng thông tải lên** — CSV truyền đi lớn hơn Parquet 2,5–3 lần ({{var:load_csv_mb}} MB so với {{var:load_parquet_mb}} MB) với tốc độ ~{{var:load_copy_mbps}} MB/s, không phải giới hạn của Postgres; (3) **lớp gold chiếm phần lớn thời gian** — chi phí của khả năng lọc chéo; nên chạy loader cùng vùng với Neon. Bảng từng bảng ở Phụ lục E.

## 6.4. E3 – Độ trễ truy vấn

Bảng: Tóm tắt độ trễ truy vấn (`query_latency.md`, `superset_chart_latency.csv`)
| Đại lượng | Giá trị |
|---|---|
| RTT mạng `SELECT 1` (Việt Nam → Singapore) | {{var:latency_rtt_ms}} ms |
| Thiết lập kết nối TLS mới tới Neon | {{var:latency_connect_ms}} ms |
| {{var:latency_queries}} truy vấn dashboard – trung vị phía client / p95 lớn nhất | {{var:latency_median}} ms / {{var:latency_p95_max}} ms |
| {{var:latency_queries}} truy vấn dashboard – trung vị thực thi trên server | {{var:latency_server_median}} ms |
| Pareto danh mục: đọc view tổng hợp / tính lại từ `fact_order_items` (server) | 0,24 ms / 66,43 ms |
| Chart qua Superset API ({{var:charts_ok}} chart): bỏ cache / từ cache (trung vị) | {{var:chart_force_median}} ms / {{var:chart_cache_median}} ms |

Ba kết luận: (1) **mạng chiếm gần như toàn bộ độ trễ** — Postgres thực thi view insight dưới 3 ms; view cấp đơn/khách hàng (`v_orders`, `v_rfm_segments`, `v_decision_hints`) tốn 50–170 ms server, vẫn dưới ngưỡng; (2) **bảng tổng hợp sẵn của tầng Big Data trả giá trị rõ rệt** — đọc Pareto đã tính ở Spark nhanh hơn tính lại từ fact hơn 250 lần; (3) **chi phí kết nối lớn hơn chi phí truy vấn** — Superset dùng NullPool nên mỗi chart mở kết nối TLS mới, khiến một chart không cache mất ~{{var:chart_force_median}} ms; cache đưa con số này về ~{{var:chart_cache_median}} ms (nhanh ~{{var:chart_speedup}} lần). Bảng 22 truy vấn ở Phụ lục E.

## 6.5. E4, E5 – Thời gian tải dashboard và bộ lọc

{{dashload:tabs}}

Khung dashboard (HTML + JS) tải trong ~{{var:dash_shell_cold}} giây; không chart nào lỗi ở cả hai lượt. Khi cold, trung vị một tab là {{var:dash_tab_cold_median}} giây; tab "{{var:dash_cold_max_tab}}" chậm nhất ({{var:dash_cold_max}} s) vì các chart xếp hàng chờ kết nối mới chứ không vì truy vấn nặng. Khi có cache, trung vị còn {{var:dash_tab_warm_median}} giây. Thời gian đánh thức compute Neon (scale-to-zero) không đo tách riêng; theo [13] chỉ cỡ vài trăm mili giây, nhỏ so với chi phí kết nối.

{{dashload:filters}}

Cả {{var:filter_ok}} kịch bản lọc đúng: chart trong phạm vi được tính lại (lọc 2018 + SP: doanh thu 13.449.530 → 2.960.326 BRL, đơn 97.905 → 23.598, Hình 7.3), chart ngoài phạm vi giữ nguyên; áp dụng trong {{var:filter_min}}–{{var:filter_max}} giây.

## 6.6. E6 – Thí nghiệm mở rộng

{{scale}}

Khi dữ liệu tăng từ ×1 lên ×{{var:scale_max}} ({{var:scale_rows}} dòng), truy vấn tổng hợp tháng × danh mục trên dữ liệu thô tăng gần tuyến tính từ {{var:scale_raw_lo}} lên {{var:scale_raw_hi}} ms; truy vấn có lọc dùng chỉ mục tăng chậm hơn nhiều (tới {{var:scale_idx_hi}} ms); còn đọc view đã tổng hợp ở Spark giữ **{{var:scale_view}} ms bất kể kích thước nguồn**. Presentation đọc output Analytics thay vì tính lại từ fact, nên độ trễ dashboard không tăng theo dữ liệu nguồn. Thí nghiệm dừng ở ×10 do giới hạn {{var:neon_branch_gib}} GiB/nhánh gói miễn phí; bảng tạm được xoá sau khi đo.

## 6.7. E7 – Kiểm thử QA chức năng

`qa_check.py` kiểm cả giao diện lẫn dữ liệu: đọc response `/api/v1/chart/data` để kiểm giá trị sau lọc, đo hình học thẻ KPI ở 1440/1280 px, ghi lỗi console, kiểm đổi ngôn ngữ giữ URL, tab, bộ lọc; `qa_run.ps1` thêm `docker compose config` và import lại ZIP. Kết quả **{{var:qa_pass}}/{{var:qa_total}} PASS**, {{var:qa_fail}} FAIL, {{var:qa_known}} KNOWN sau khi sửa các lỗi lượt đầu (menu không sang English, tiêu đề KPI chồng/bị cắt khi lọc, menu xuống hai hàng ở 1280 px; Mục 5.4). Bảng đủ ở Phụ lục E.5.

{{qa:summary}}

## 6.8. Đánh giá tổng hợp

Bảng: Đánh giá mức đạt theo tiêu chí
| Tiêu chí | Ngưỡng | Kết quả | Đánh giá |
|---|---|---|---|
| Đúng đắn dữ liệu | 100% | {{var:val_rows_ok}} bảng; {{var:val_anchor_ok}} kiểm tra | Đạt |
| Nạp 16 bảng Analytics | < 120 s | {{var:load_ana_seconds}} s | Đạt |
| Truy vấn dashboard: trung vị / p95 | < 300 / 500 ms | {{var:latency_median}} / {{var:latency_p95_max}} ms | Đạt |
| Tab dashboard cold (trung vị) | < 5 s | {{var:dash_tab_cold_median}} s; {{var:dash_cold_over5}} tab vượt 5 s, chậm nhất {{var:dash_cold_max}} s | {{var:dash_cold_verdict}} |
| Tab dashboard có cache (trung vị) | < 2 s | {{var:dash_tab_warm_median}} s | Đạt |
| Bộ lọc native | 100% | {{var:filter_ok}} kịch bản | Đạt |
| View tổng hợp khi dữ liệu ×10 | Không tăng | {{var:scale_view}} ms ở mọi hệ số | Đạt |
| Kiểm thử QA chức năng | 100% PASS | {{var:qa_pass}}/{{var:qa_total}} PASS, {{var:qa_fail}} FAIL | {{var:qa_verdict}} |

RQ2: tầng phục vụ tái tạo chính xác kết quả Spark. RQ3: nạp và độ trễ bị chi phối bởi mạng và kết nối, không bởi cơ sở dữ liệu; {{var:dash_cold_over5}} tab cold vượt 5 s do kết nối TLS mới mỗi chart, cache khắc phục; cải tiến ở Mục 8.3.
