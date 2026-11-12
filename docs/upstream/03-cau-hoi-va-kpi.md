# Câu hỏi nghiệp vụ và kết quả

Số liệu từ lần chạy 2026-10-29 (`reports/analytics_report.md`). Khung thời gian KPI: 2017-01 → 2018-08, trừ khi ghi khác. Đơn vị tiền: BRL.

## 1. Tăng trưởng doanh thu và vận hành

**Bảng:** `kpi_monthly` (20 tháng).

Đỉnh doanh thu là **11/2017 (Black Friday)**: 7.421 đơn, **1.003.862** BRL, MoM **+52,06%**, `revenue_rank = 1`. Cùng tháng `late_delivery_pct = 14,31%` và `avg_review_score = 3,95` — tăng đơn kéo theo quá tải vận chuyển.

Tháng vận hành tệ nhất trong các tháng lớn: **03/2018** trễ **21,36%**, review **3,76** (thấp nhất trong top doanh thu). 02/2018 trễ 15,99%, review 3,86. Cùng mô hình với Black Friday: spike đơn → trễ → sao rớt (chủ đề 6 đo đúng trên `fact_orders`).

AOV không đi cùng quy mô đơn. 11/2017 đơn tăng mạnh nhưng AOV gold ~158 (thấp hơn 04–05/2018 ~167): cao điểm = nhiều giỏ nhỏ, không phải giỏ đắt hơn.

YoY 2018-01 **+687%** là hiệu ứng nền thấp (2017-01 mới 120k BRL), không phải tăng trưởng bền. 2018-08 YoY còn **+49%** — tốc độ chậm lại khi mẫu 2017 đã lớn. Đọc MoM 2018: 02 và 06 giảm ~11–13%.

## 2. Danh mục và mùa vụ

**Bảng:** `category_pareto`, `category_seasonality`.

Top 3: `health_beauty` 9,30% doanh thu, `watches_gifts` 8,88%, `bed_bath_table` 7,70%. Top 10 cộng dồn **62,4%** — chưa tới 80% (74 danh mục, đuôi dài).

`bed_bath_table`: nhiều đơn/món nhất (9.394 đơn, 11.089 món) nhưng `avg_price = 93,38`. `watches_gifts`: ít món hơn, `avg_price = 200,31`, freight/revenue chỉ **8,37%** (rẻ vận chuyển tương đối). Nhóm bình dân vs giá trị cao khác nhau ở **giá và tỷ trọng ship**, không chỉ ở doanh thu.

Freight ăn biên nặng: `furniture_decor` **23,68%**, `housewares` **23,17%**, `garden_tools` 20,52% — hàng cồng kềnh. Marketing những ngành này phải tính ship vào giá, không so margin với đồng hồ.

Mùa vụ 2017 (đủ 12 tháng): cả 6 ngành lớn đều **đỉnh tháng 11** (Black Friday), `watches_gifts` 19,85% doanh thu năm rơi vào T11. Chiến dịch nhập hàng / ads nên dồn trước tháng 11, không rải đều.

## 3. Địa lý, khoảng cách, logistics

**Bảng:** `state_logistics`, `insight_distance`.

SP **38,27%** doanh thu, giao **8,7 ngày**, freight **13,83%** doanh thu, review **4,21**, trễ chỉ 5,89%. Phần lớn seller nằm ở SP (gold_report): khoảng cách ngắn → ship rẻ/nhanh.

Bang xa: BA 19,3 ngày / trễ 14,04% / review **3,88**; RJ 15,2 ngày / trễ 13,47% / review **3,91**; ES trong handover cùng nhóm chậm. Review thấp đi cùng trễ và ngày giao — không cần giả định “khách đông bắc khó tính”.

Khoảng cách (chim bay, đơn delivered, đã lọc `dq_*`):

| Band | Món | Freight TB | Ngày giao | % trễ |
|---|---:|---:|---:|---:|
| 0–200 km | 28.060 | 12,66 | 7,0 | 6,34 |
| 200–500 | 34.572 | 19,07 | 11,9 | 7,04 |
| 500–1000 | 29.361 | 21,08 | 14,2 | 8,29 |
| 1000+ | 17.156 | 31,65 | 19,0 | 11,69 |

Pearson: distance–freight **0,39**, distance–delivery_days **0,39** (tăng tuyến tính vừa). Distance–`delivery_delay_days` **−0,08**: SLA ước lượng đã chèn buffer cho đường dài, nên “số ngày trễ so với hẹn” không tăng theo km, dù **tỷ lệ trễ** và **ngày giao thực** vẫn tăng. Đừng nói “xa thì trễ hạn nhiều ngày hơn”; nói “xa thì giao lâu hơn và dễ trễ hơn”.

## 4. Giữ chân và RFM

**Bảng:** `rfm_scores`, `repeat_profile`, `repeat_categories`, `repeat_states`.

**96,96%** khách (92.096 / 94.983) `frequency = 1`. Olist là marketplace one-shot, không phải subscription. KPI “retention” nếu tính trên toàn bộ khách sẽ gần 0 — phải tách **2.887 người mua lại (3,04%)**.

Nhóm lặp chi **308 BRL** lifetime vs 161 one-shot, tần suất 2,11. Địa lý vẫn lệch SP (1.252), rồi RJ / MG — giống phân bố doanh thu, không phải “chỉ khách nội địa SP mới quay lại”.

Danh mục khách lặp ưa: `bed_bath_table` (595 khách, 97,9k), `furniture_decor`, `sports_leisure` — hàng nhà cửa mua bổ sung, không phải đồng hồ (watches chỉ 202 khách lặp).

Nhãn luật (không dùng NTILE-F cho Champion):

| Segment | Số khách | Ý CRM |
|---|---:|---|
| Champions | 251 | Lặp + mới mua + chi cao — giữ bằng voucher |
| Loyal | 675 | Lặp, recency ≤ 180 ngày |
| At Risk | 1.961 | Đã lặp nhưng > 180 ngày không mua |
| One-shot Recent / Warm / Lost | 91.096 | Đừng gọi Champion; win-back one-shot lost tốn kém |

`f_score` NTILE gần như nhiễu vì hòa `frequency = 1`. Báo cáo giữ cột để đúng mô hình RFM cổ điển, nhưng hành động dựa `rfm_segment` + `frequency >= 2`.

## 5. Hiệu suất seller

**Bảng:** `seller_pareto`, `seller_watchlist`.

3.053 seller. **539 seller (17,65%)** đã chiếm **≤ 80%** doanh thu — tập trung hơn 20/80. Đội seller ops nên ưu tiên nhóm này, không rải đều 3.000 shop.

Watchlist: top 10% doanh thu **và** (review < 4 hoặc giao > 15 ngày hoặc trễ > 10%) → **153 seller**. Ví dụ vận hành kém: `b1b39487…` review 1,81 / 23,4 ngày / trễ 64%; `cf8ab161…` 2,0 sao / 26,3 ngày. Doanh thu cao không miễn trừ; đây là đối tượng cảnh cáo / hạn chế visibility.

`active_months` thấp đi cùng watchlist (3–7 tháng): shop lớn nhanh, quy trình giao chưa ổn. Kết hợp `avg_distance_km` trên `seller_pareto` khi Presentation vẽ scatter.

## 6. Giao trễ, review, thanh toán

**Bảng:** `insight_late_vs_review`, `delay_vs_review`, `payment_mix`.

Đơn trễ: review **2,56** vs đúng hạn **4,29** (kém **1,73 sao**). Sao 1–2: **54,07%** vs **9,20%**. Có bình luận: 55,6% vs 39,2% — khách trễ vừa chấm thấp vừa viết phàn nàn.

Ngưỡng ngày (không “chắc chắn 100% 1 sao”):

| Band | Review TB | % 1 sao | % có comment |
|---|---:|---:|---:|
| Đúng hạn / sớm | 4,29 | 6,6 | 39,2 |
| Trễ 1–3 ngày | 3,29 | 25,1 | 48,4 |
| Trễ 4–7 ngày | 2,10 | 58,6 | 59,8 |
| Trễ 8–14 ngày | **1,67** | **70,6** | 64,7 |
| Trễ ≥ 15 ngày | 1,72 | 68,9 | 66,2 |

Sau ~1 tuần trễ, điểm kịch sàn (~1,7) và ~70% một sao. Ưu tiên cảnh báo seller trước mốc 4–7 ngày, không đợi 15 ngày.

Thanh toán (đơn hợp lệ, 2017-01→2018-08): **credit_card ~75,5% đơn**, boleto ~20%. Trả góp **≥ 7 kỳ**: AOV **334,67** vs trả 1 kỳ thẻ **100,81**. Đây là tương quan (đơn đắt mới trả góp), không chứng minh “bật trả góp sẽ tăng AOV”. Voucher/debit là phần nhỏ.
