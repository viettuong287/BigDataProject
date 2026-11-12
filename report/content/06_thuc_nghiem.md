# 6. Thực nghiệm và đánh giá

## 6.1. Mục tiêu và kịch bản thực nghiệm

Thực nghiệm nhằm trả lời các câu hỏi kỹ thuật RQ2 (tính đúng đắn) và RQ3 (hiệu năng) đặt ra ở Chương 1, đồng thời cung cấp số liệu cho thảo luận về khả năng mở rộng (RQ5). Nhóm thiết kế sáu kịch bản:

Bảng: Các kịch bản thực nghiệm
| Mã | Kịch bản | Cách thực hiện | Đại lượng đo |
|---|---|---|---|
| E1 | Đối chiếu dữ liệu Parquet ↔ Neon | `loader/validate.py`: đọc lại Parquet, đếm dòng trên Postgres; chạy `sql/90_anchor_checks.sql` | Số kiểm tra đạt / tổng số |
| E2 | Hiệu năng nạp dữ liệu | `loader/load_to_neon.py` nạp toàn bộ, ghi thời gian từng pha của từng bảng | Thời gian (s), thông lượng (dòng/s, MB/s) |
| E3 | Độ trễ truy vấn (compute đang chạy – warm) | Đo thời gian mỗi truy vấn kiểm tra và truy vấn view từ máy client | min, trung vị, p95, max (ms) |
| E4 | Độ trễ khi compute thức dậy (cold start) | Đợi compute scale-to-zero, gửi truy vấn đầu tiên | Thời gian truy vấn đầu tiên (ms) |
| E5 | Hiệu quả cache Superset | Mở dashboard hai lần liên tiếp trong 10 phút | Thời gian tải dashboard (s) |
| E6 | Kiểm thử chức năng bộ lọc | Áp dụng từng native filter, kiểm tra chart trong phạm vi thay đổi đúng | Đạt / không đạt |

## 6.2. Dữ liệu và môi trường thử nghiệm

Dữ liệu thử nghiệm là toàn bộ {{var:n_tables}} bảng Analytics ({{var:total_rows}} dòng) cộng {{var:n_gold}} bảng gold ({{var:gold_rows}} dòng): tổng {{var:load_tables}} bảng, {{var:load_total_rows}} dòng, {{var:load_parquet_mb}} MB Parquet. Client là container `tools` chạy trên máy Windows của nhóm tại Việt Nam, kết nối Internet tới Neon vùng Singapore (PostgreSQL 18.6, kiến trúc aarch64). Vì vậy mọi số đo đều bao gồm **độ trễ mạng khứ hồi** và **băng thông tải lên** của đường truyền gia đình/ký túc xá — đúng với kịch bản thực tế của nhóm. [[CẬP NHẬT: cấu hình máy client (CPU, RAM, băng thông đo được) và kích thước compute Neon lúc đo]]

## 6.3. Tiêu chí đánh giá

Ngưỡng đạt được đặt theo trải nghiệm người dùng dashboard: **đúng đắn 100%** (dashboard sai số thì vô giá trị); **nạp 16 bảng Analytics dưới 120 giây** để làm mới được nhiều lần trong ngày; **độ trễ truy vấn khi compute đang chạy có trung vị dưới 300 ms và lớn nhất dưới 500 ms** (mỗi chart một truy vấn, dashboard 10–15 chart chạy song song); **cold start dưới 5 giây** cho lần mở đầu tiên trong ngày; **dashboard có cache dưới 2 giây**; **100% chart trong phạm vi bộ lọc phản hồi đúng**. Bảng tổng hợp mức đạt ở Mục 6.9.

## 6.4. Kết quả E1 – Đối chiếu dữ liệu

`loader/validate.py` đọc lại từng thư mục Parquet và so với `COUNT(*)` trên Postgres cho cả {{var:load_tables}} bảng (bảng chi tiết ở Phụ lục E), sau đó chạy các truy vấn kiểm tra số neo. Ngoài số dòng, nhóm kiểm tra các tổng tiền vì lỗi ánh xạ kiểu (ví dụ cắt mất phần thập phân) sẽ không làm thay đổi số dòng nhưng làm lệch tổng. Script sinh báo cáo cũng tính độc lập các giá trị kỳ vọng từ Parquet (Phụ lục E) để đối chiếu chéo.

{{validation:anchors}}

Kết quả: **{{var:val_rows_ok}} bảng khớp số dòng** và **{{var:val_anchor_ok}} kiểm tra số neo/nhất quán đạt** (một dòng INFO chỉ để hiển thị tổng doanh thu khung 20 tháng). Các kiểm tra chia thành ba nhóm: (1) số neo bàn giao của Analytics — tổng doanh thu gold 13.494.400,74 BRL, tháng đỉnh 2017-11 với MoM 52,06%, review 2,56/4,29, 2.887 khách mua lại (3,04%), 153 người bán watchlist, 539 người bán tạo 80% doanh thu; (2) **nhất quán chéo giữa hai lớp dữ liệu** — tổng doanh thu và số đơn của view cấp đơn `v_orders`, tổng doanh thu của `v_sales_items` (từ gold) bằng đúng tổng của `kpi_monthly` (từ Analytics), chênh lệch 0,00; (3) tính toàn vẹn của tầng ngữ nghĩa — tổng khách theo phân khúc bằng 94.983, `v_decision_hints` có đủ 7 luật.

Nhóm kiểm tra nhất quán chéo đặc biệt quan trọng: nó chứng minh việc bổ sung lớp gold để lọc chéo **không tạo ra "hai sự thật"** trên dashboard. Đồng thời, tổng 20 tháng của `kpi_monthly` (13.449.529,68 BRL) nhỏ hơn số neo gold vì đã loại các tháng 2016 và 09/2018 — hai con số đều đúng nhưng trả lời hai câu hỏi khác nhau, nên thẻ KPI trên dashboard ghi rõ phạm vi thời gian.

## 6.5. Kết quả E2 – Hiệu năng nạp dữ liệu

Kết quả nạp từng bảng (số dòng, dung lượng Parquet/CSV, thời gian COPY, tạo chỉ mục, tổng, tốc độ truyền) được trích tự động từ `evidence/load_log.csv` ở Phụ lục E.

{{evidence:load?}}

**Tổng hợp.** Lần chạy `{{var:load_run_id}}` nạp {{var:load_tables}} bảng, {{var:load_total_rows}} dòng trong {{var:load_total_seconds}} giây (riêng pha COPY {{var:load_copy_seconds}} giây), thông lượng đầu-cuối {{var:load_throughput}} dòng/s. Riêng {{var:load_ana_tables}} bảng Analytics ({{var:load_ana_rows}} dòng) mất {{var:load_ana_seconds}} giây, còn {{var:load_gold_tables}} bảng gold ({{var:load_gold_rows}} dòng) mất {{var:load_gold_seconds}} giây, tức khoảng {{var:load_gold_share}}% tổng thời gian.

**Phân tích.** Ba quan sát rút ra từ số liệu:

1. **Chi phí cố định mỗi bảng chiếm ưu thế ở bảng nhỏ.** {{var:load_small_tables}} bảng dưới 1.000 dòng mất trung bình {{var:load_small_avg_s}} giây mỗi bảng dù dữ liệu chỉ vài KB: thời gian này là tổng của nhiều vòng khứ hồi mạng tới Singapore (DROP, CREATE, COPY, COMMENT, commit, tạo khoá chính, ANALYZE, đếm dòng, ghi log). Thông lượng "dòng/giây" của các bảng này vì vậy không có ý nghĩa; cách tối ưu là giảm số vòng khứ hồi (gộp nhiều bảng nhỏ trong một giao dịch, nạp song song) chứ không phải tăng tốc truyền.
2. **Bảng lớn bị giới hạn bởi băng thông tải lên.** Với các bảng cấp khách hàng và bảng fact, phần lớn thời gian nằm ở pha COPY. Dữ liệu được truyền dưới dạng CSV văn bản, lớn hơn Parquet nén khoảng 2,5–3 lần ({{var:load_csv_mb}} MB CSV so với {{var:load_parquet_mb}} MB Parquet), với tốc độ trung bình khoảng {{var:load_copy_mbps}} MB/s — tương ứng vài Mbit/s, phù hợp với băng thông tải lên của kết nối Internet thông thường hơn là giới hạn của Postgres. Điều này giải thích vì sao `agg_customer_rfm` (9 cột) nạp nhanh hơn rõ rệt so với `customer_segments` (13 cột) dù cùng 94.983 dòng.
3. **Bảng gold chiếm phần lớn thời gian** vì có số cột lớn (27–29 cột) và nhiều dòng nhất. Đây là chi phí của quyết định bổ sung lớp lọc chéo; nếu chỉ cần dashboard insight, 16 bảng Analytics nạp trong {{var:load_ana_seconds}} giây.

Từ đó, hướng tối ưu hợp lý nhất là **chạy loader gần Neon** (máy ảo cùng vùng AWS hoặc trong pipeline CI) để loại bỏ giới hạn băng thông tải lên, và chỉ nạp lại các bảng thay đổi. Điều này được thảo luận ở Mục 8.3.

## 6.6. Kết quả E3, E4 – Độ trễ truy vấn

Script `scripts/measure_latency.py` chạy đúng các truy vấn mà các chart trên dashboard sinh ra, qua endpoint *pooled* (PgBouncer) giống Superset, mỗi truy vấn {{var:latency_runs}} lần sau một lần làm nóng; ghi nhận thời gian phía client (mạng + thực thi) và thời gian thực thi phía server (`EXPLAIN ANALYZE`). Kết quả (đo lúc {{var:latency_measured_at}}):

{{latency}}

{{evidence:latency?}}

**Phân tích.** Trên {{var:latency_queries}} truy vấn dashboard, trung vị phía client là **{{var:latency_median}} ms** (nhỏ nhất {{var:latency_min}} ms, lớn nhất {{var:latency_max}} ms; p95 lớn nhất {{var:latency_p95_max}} ms), trong khi trung vị thời gian **thực thi trên server chỉ {{var:latency_server_median}} ms**. Riêng một vòng khứ hồi mạng `SELECT 1` từ máy nhóm tới Neon Singapore đã mất {{var:latency_rtt_ms}} ms. Ba kết luận:

1. **Mạng chiếm gần như toàn bộ độ trễ.** Với các view trên bảng Analytics đã tổng hợp, Postgres thực thi dưới 3 ms; phần còn lại là đường truyền. Tối ưu SQL ở quy mô này gần như không cải thiện trải nghiệm — đặt Superset cùng vùng với Neon hoặc dùng cache mới có tác dụng.
2. **Bảng tổng hợp sẵn của tầng Big Data trả giá trị rõ rệt.** Dòng "So sánh" tính lại Pareto danh mục trực tiếp từ `gold.fact_order_items` tốn khoảng 66 ms thực thi, so với 0,24 ms khi đọc `v_category_pareto` do Spark tính sẵn — chênh hơn 250 lần. Các truy vấn trên lớp cấp đơn/khách hàng (`v_orders`, `v_rfm_customers`, `v_rfm_segments`, `v_decision_hints`: 50–170 ms server) cũng chậm hơn hẳn lớp insight. Ở quy mô ×100, chênh lệch này quyết định dashboard có tương tác được hay không — minh chứng cho nguyên tắc "tính nặng ở batch layer".
3. **Chi phí mở kết nối lớn hơn chi phí truy vấn.** Thiết lập một kết nối TLS mới tới Neon mất khoảng {{var:latency_connect_ms}} ms, gấp nhiều lần thời gian truy vấn; Superset mặc định mở kết nối mới cho mỗi truy vấn. Endpoint pooled của Neon và cache 10 phút của Superset giảm đáng kể chi phí này; đây cũng là lý do cache ở tầng BI quan trọng hơn tối ưu SQL.

Bộ kiểm tra E1 cho kết quả cùng bậc: {{var:anchor_n}} truy vấn kiểm tra có trung vị {{var:anchor_ms_median}} ms, lớn nhất {{var:anchor_ms_max}} ms. Truy vấn đầu tiên sau khi compute ngủ còn chịu thêm thời gian khởi động compute và nạp lại cache trang từ pageserver — cái giá của scale-to-zero, chấp nhận được với dashboard nội bộ vì đổi lại không tốn compute ngoài giờ làm việc. [[CẬP NHẬT: số đo cold start thực tế (ms) sau khi compute ở trạng thái Idle]]

## 6.7. Kết quả E5, E6 – Dashboard và bộ lọc

Bảng: Kết quả kiểm thử dashboard và bộ lọc
| Kiểm thử | Kỳ vọng | Kết quả |
|---|---|---|
| Mở dashboard lần đầu (cache trống) | < 5 s | [[CẬP NHẬT: số giây]] |
| Mở lại trong 10 phút (có cache) | < 2 s | [[CẬP NHẬT: số giây]] |
| Bộ lọc khoảng tháng | Thẻ KPI (`v_orders`) và chart theo tháng chỉ tính các tháng đã chọn | [[CẬP NHẬT: Đạt/Không]] |
| Bộ lọc bang | Thẻ KPI, bản đồ, scatter, phân khúc khách theo bang thay đổi | [[CẬP NHẬT: Đạt/Không]] |
| Bộ lọc danh mục | Xu hướng ngành (`v_category_monthly`), doanh thu theo danh mục thay đổi | [[CẬP NHẬT: Đạt/Không]] |
| Bộ lọc phân khúc RFM | Biểu đồ và bảng khách hàng thay đổi | [[CẬP NHẬT: Đạt/Không]] |
| Cross-filter (nhấn vào bang trên bản đồ) | Các chart cùng dataset lọc theo bang | [[CẬP NHẬT: Đạt/Không]] |

## 6.8. Tham chiếu hiệu năng giai đoạn trước

Để đặt số liệu của nhóm trong bối cảnh toàn pipeline, bảng dưới đây so sánh thời gian xử lý giữa các giai đoạn. Giai đoạn Processing và Analytics phải quét và join dữ liệu chi tiết trên cụm Spark; giai đoạn Presentation chủ yếu truyền dữ liệu qua mạng một lần, sau đó phục vụ mỗi truy vấn trong vài trăm mili giây. Đây là minh hoạ trực tiếp cho nguyên tắc "tính nặng ở batch layer, phục vụ nhẹ ở serving layer".

Bảng: Thời gian xử lý theo giai đoạn của pipeline
| Giai đoạn | Công việc | Dữ liệu | Thời gian |
|---|---|---|---|
| Storage → Processing | Silver → gold (7 bảng, 11 đối chiếu) trên Spark 4 core | 569.698 dòng vào | 61,72 s |
| Processing → Analytics | 14 SQL + K-Means trên Spark 4 core | 7 bảng gold, 311.460 dòng | {{var:spark_total_s}} s |
| Analytics → Presentation (nạp 16 bảng Analytics) | Parquet → Neon bằng COPY qua Internet | {{var:load_ana_rows}} dòng | {{var:load_ana_seconds}} s |
| Analytics → Presentation (nạp 7 bảng gold) | Parquet → Neon bằng COPY qua Internet | {{var:load_gold_rows}} dòng | {{var:load_gold_seconds}} s |
| Analytics → Presentation (truy vấn) | Một truy vấn phục vụ một chart | Bảng đã cô đọng / có chỉ mục | trung vị {{var:latency_median}} ms client, {{var:latency_server_median}} ms server |

## 6.9. Đánh giá tổng hợp

Bảng: Đánh giá mức đạt theo tiêu chí
| Tiêu chí | Ngưỡng | Kết quả | Đánh giá |
|---|---|---|---|
| Đúng đắn dữ liệu | 100% | {{var:val_rows_ok}} bảng; {{var:val_anchor_ok}} kiểm tra | Đạt |
| Thời gian nạp 16 bảng Analytics | < 120 s | {{var:load_ana_seconds}} s | Đạt |
| Độ trễ truy vấn dashboard, trung vị (client) | < 300 ms | {{var:latency_median}} ms (server {{var:latency_server_median}} ms) | Đạt |
| Độ trễ truy vấn dashboard, p95 lớn nhất | < 500 ms | {{var:latency_p95_max}} ms | Đạt |
| Cold start | < 5 s | [[CẬP NHẬT: ms]] | [[CẬP NHẬT]] |
| Dashboard có cache | < 2 s | [[CẬP NHẬT: s]] | [[CẬP NHẬT]] |
| Bộ lọc | 100% | [[CẬP NHẬT]] | [[CẬP NHẬT]] |

Về câu hỏi RQ2, kết quả E1 cho thấy tầng phục vụ tái tạo chính xác tuyệt đối kết quả của Spark, kể cả các số thập phân tiền tệ, và hai lớp dữ liệu (Analytics, gold) nhất quán với nhau. Về RQ3, cả thời gian nạp lẫn độ trễ truy vấn đều bị chi phối bởi mạng chứ không bởi cơ sở dữ liệu (server thực thi trung vị {{var:latency_server_median}} ms), và độ trễ truy vấn dashboard nằm trong ngưỡng tương tác.
