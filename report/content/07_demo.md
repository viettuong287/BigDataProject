# 7. Kết quả demo

## 7.1. Kịch bản demo từ đầu vào đến đầu ra

1. **Đầu vào:** mở `data/analytics/` ({{var:n_tables}} thư mục bảng Parquet), dùng pyarrow in schema và số dòng của `kpi_monthly`.
2. **Nạp dữ liệu:** chạy loader trong container `tools`; log hiển thị từng bảng, số dòng, thời gian và dòng tổng; `analytics.load_log` có thêm một `run_id`.
3. **Kiểm tra:** chạy `loader/validate.py`; {{var:val_rows_ok}} bảng khớp số dòng, {{var:val_anchor_ok}} kiểm tra số neo "ĐẠT".
4. **Tầng ngữ nghĩa:** trong SQL Lab (hoặc psql) truy vấn `v_kpi_overview`, `v_seller_watchlist`, `v_decision_hints`.
5. **Dashboard:** đi qua từng tab; áp dụng bộ lọc khoảng tháng, bang, danh mục, phân khúc; nhấn một bang trên bản đồ để cross-filter.
6. **Đầu ra cho Decision/Action:** truy vấn view gợi ý quyết định, xuất CSV, minh hoạ một luật hành động.
7. **Serverless:** Neon Console cho thấy compute co giãn và về trạng thái nghỉ sau khi ngừng truy cập.

## 7.2. Nội dung phân tích được trình bày

Các biểu đồ dưới đây do script sinh báo cáo vẽ trực tiếp từ các bảng Parquet đầu vào (cùng nguồn với dashboard), minh hoạ thông điệp của từng tab và kiểm chứng các số neo. Ảnh chụp dashboard thật ở Mục 7.3.

### 7.2.1. Tổng quan: tăng trưởng và sức khoẻ vận hành

{{chart:kpi_trend|Doanh thu, số đơn, tỷ lệ giao trễ và điểm review theo tháng (2017-01 → 2018-08; cột cam = Black Friday)}}

Doanh thu tăng từ ~120 nghìn BRL (01/2017) lên đỉnh **1.003.862 BRL vào 11/2017** (Black Friday, MoM +52,06%, 7.421 đơn), rồi giữ quanh 0,85–1,0 triệu BRL/tháng trong 2018. Thông điệp cho ban điều hành: **bán nhiều không đồng nghĩa vận hành tốt** — 11/2017 tỷ lệ trễ vọt lên 14,31%, review rơi còn 3,95; 03/2018 tệ nhất với 21,36% trễ và review 3,76; trong khi 04–05/2018 doanh thu gần bằng đỉnh mà trễ chỉ 5–8%, review ~4,2. Trước các đợt khuyến mãi phải tăng năng lực giao vận tương ứng.

### 7.2.2. Danh mục: Pareto và mùa vụ

{{chart:category_pareto|Pareto doanh thu theo danh mục: không danh mục nào vượt 10%, top 10 đạt ~62%}}

`health_beauty` dẫn đầu (9,30%), tiếp theo `watches_gifts` (8,88%), `bed_bath_table` (7,70%). 17 danh mục lớn nhất mới chiếm 79,7% doanh thu, đến danh mục thứ 18 mới vượt 80% — "đuôi dài" điển hình của sàn đa ngành. Chiến dịch nên theo cụm ngành; cắt bỏ hàng loạt ngành nhỏ sẽ mất ~38% doanh thu nằm ngoài top 10.

{{chart:category_season|Mùa vụ 2017: tỷ trọng doanh thu từng tháng trong năm của 8 danh mục lớn nhất}}

Cả tám danh mục lớn đều đạt đỉnh tháng 11; `watches_gifts` có gần 20% doanh thu năm rơi vào tháng 11 — tồn kho và ngân sách quảng cáo cần dồn vào quý IV.

### 7.2.3. Địa lý và logistics

{{chart:state_scatter|27 bang theo số ngày giao trung bình và điểm review (kích thước = doanh thu, màu = % giao trễ)}}

SP chiếm 38,27% doanh thu, giao 8,7 ngày, trễ 5,89%, review 4,21 — góc "nhanh và hài lòng" vì phần lớn người bán ở SP. Các bang xa như BA (19,3 ngày, trễ 14,04%, review 3,88) và RJ (15,2 ngày, 13,47%, 3,91) ở góc ngược lại dù giá trị đơn cao hơn (BA 181 BRL so với SP 143 BRL).

{{chart:distance|Phí vận chuyển, thời gian giao và tỷ lệ trễ theo khoảng cách người bán → khách}}

Từ 0–200 km lên trên 1.000 km, phí ship tăng từ 12,66 lên 31,65 BRL, thời gian giao từ 7,0 lên 19,0 ngày, tỷ lệ trễ từ 6,34% lên 11,69%. Hệ số Pearson khoảng cách – phí ship 0,39, khoảng cách – ngày giao 0,39, nhưng khoảng cách – số ngày trễ so với hẹn chỉ −0,08: ngày hẹn đã được nới cho đường dài, vấn đề là thời gian chờ thực tế. Hàm ý: ưu tiên kho/người bán theo vùng thay vì siết hạn hẹn.

### 7.2.4. Khách hàng: giữ chân và phân khúc

{{chart:rfm_segments|Số khách theo phân khúc RFM (thang log): ba phân khúc khách mua lại chỉ chiếm ~3%}}

96,96% khách chỉ mua một lần; **2.887 khách (3,04%) mua lại**, chi trọn đời 308 BRL so với 161 BRL, nhưng giá trị mỗi đơn không cao hơn (146 so với 161 BRL) — họ mua thêm lần chứ không mua đắt hơn. Phân khúc theo luật: 251 Champions, 675 Loyal, 1.961 At Risk; K-Means (k = 4) tự tách đúng 2.887 khách mua lại thành một cụm. Ngân sách CRM nên tập trung vào At Risk và One-shot Recent thay vì 65 nghìn khách One-shot Lost.

### 7.2.5. Người bán

{{chart:seller_pareto|Đường Pareto doanh thu của người bán}}

Chỉ 539/3.053 người bán (17,65%) tạo 80% doanh thu — tập trung hơn quy luật 20/80. Kết hợp điều kiện vận hành kém, `seller_watchlist` chọn ra **153 người bán** thuộc top 10% doanh thu nhưng review < 4, giao > 15 ngày hoặc trễ > 10% — đầu vào trực tiếp cho giai đoạn Decision/Action.

### 7.2.6. Giao trễ, đánh giá và thanh toán

{{chart:delay_review|Điểm review trung bình và tỷ lệ đơn 1 sao theo số ngày giao trễ so với hẹn}}

Đơn trễ chỉ đạt **2,56 sao so với 4,29** (chênh 1,73 sao); 54,07% đơn trễ bị 1–2 sao so với 9,20%. Trễ 1–3 ngày còn 3,29 sao, trễ 4–7 ngày còn 2,10 sao với 58,6% một sao, từ 8 ngày trở đi chạm đáy ~1,7 sao — căn cứ cho luật "can thiệp trước mốc 4 ngày trễ".

Về thanh toán, thẻ tín dụng chiếm ~75% số đơn, boleto ~20%. Đơn trả góp ≥ 7 kỳ có giá trị trung bình ~335 BRL so với ~101 BRL của đơn thẻ trả một lần — tương quan (đơn đắt mới cần trả góp), không chứng minh "bật trả góp sẽ tăng giá trị đơn".

## 7.3. Ảnh chụp hệ thống đang chạy

Các ảnh dưới đây được chèn tự động từ `evidence/` (chụp bằng Playwright hoặc chụp tay), tương ứng các bước của kịch bản ở Mục 7.1.

{{evidence:dashboard|dashboard Superset – tab Tổng quan với thẻ KPI và biểu đồ xu hướng}}

{{evidence:filter|dashboard khi áp dụng bộ lọc native (ví dụ chọn bang SP và khoảng tháng 2018)}}

{{evidence:decision|khu vực gợi ý quyết định: bảng người bán cần theo dõi và tác động giao trễ}}

{{evidence:remaining}}

## 7.4. Đầu ra cho giai đoạn Decision/Action

Giai đoạn Decision/Action chỉ cần hai truy vấn để lấy toàn bộ đầu vào:

```sql
-- 7 luật gợi ý quyết định, sắp theo mức ưu tiên
SELECT priority, severity, topic, signal, metric_value, threshold, action, source
FROM   presentation.v_decision_hints ORDER BY priority;

-- Người bán mức ĐỎ (vi phạm >= 2 tiêu chí), doanh thu lớn nhất trước
SELECT seller_id, seller_state, revenue, violations, reasons, recommended_action
FROM   presentation.v_seller_watchlist
WHERE  alert_level = 'ĐỎ' ORDER BY revenue DESC LIMIT 20;
```

Kết quả là dữ liệu có cấu trúc (luật, giá trị hiện tại, ngưỡng, hành động; mã người bán, lý do, hành động khuyến nghị) mà một rule engine có thể chuyển thành email/Telegram cảnh báo, hoặc kích hoạt chăm sóc khách hàng khi đơn có nguy cơ trễ ≥ 4 ngày. Dashboard phục vụ con người, view phục vụ máy — hai kênh dùng chung một tầng ngữ nghĩa nên không mâu thuẫn số liệu.
