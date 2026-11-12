# Báo cáo Analytics

> Sinh bởi `jobs/01_analytics.py`. Dưới mỗi bảng: **cột nghĩa gì** → **số nói gì** → **ý nghĩa với sàn** (hành động, không chỉ định nghĩa).

## 1. Lần chạy

| Thuộc tính | Giá trị |
|---|---|
| Thời điểm | 2026-10-29 16:07:30 |
| Master | spark://spark-master:7077 (2 executor, 4 core) |
| Gold SUM(revenue) | 13494400.74 |
| SQL | 44.51 s |
| K-Means | 29.5 s |
| Tổng | 119.71 s |

`Gold SUM(revenue)` phải bằng **13.494.400,74** (handover). Đó là tổng giá sản phẩm trên **mọi tháng** đơn hợp lệ, kể cả tháng rỗng 2016/2018-09. Bảng `kpi_monthly` cắt những tháng đó nên **cộng revenue theo tháng sẽ nhỏ hơn** con số này — không phải job sai.

## 2. Tương quan khoảng cách

| Cặp | Pearson |
|---|---:|
| distance vs freight | 0.3924107915413591 |
| distance vs delivery_days | 0.39398211323178073 |
| distance vs delay_days | -0.07768512927232768 |

Pearson từ −1 đến 1: mức tăng/giảm **cùng chiều tuyến tính**. ~0,39 với cước và ngày giao: xa hơn thì ship đắt hơn và giao lâu hơn, mức vừa (không phải 1-1). Gần 0 với `delivery_delay_days`: số ngày **trễ so với hạn hẹn** gần như không tăng theo km — ước lượng thời gian giao đã chèn buffer cho đường dài. Đừng nhầm “xa thì trễ hạn nhiều ngày”; hãy nói “xa thì giao lâu hơn và **tỷ lệ** trễ cao hơn” (xem `insight_distance`).

**Ý nghĩa:** Bảng giá ship theo vùng **có căn cứ**, không phải bắt khách xa. Vấn đề band xa không nằm ở “hạn trên giấy quá chặt” (trung bình vẫn giao trước hạn) mà ở **chờ 19 ngày** và **nhiều ca trễ hơn** — đúng thứ kéo 1 sao ở mục 5.

## 3. Bảng kết quả

| Bảng | 1 dòng = | Số dòng | Thời gian (s) |
|---|---|---:|---:|
| `kpi_monthly` | 1 tháng | 20 | 4.14 |
| `category_pareto` | 1 danh mục | 74 | 3.11 |
| `category_seasonality` | 1 danh mục × 1 tháng (2017) | 715 | 2.85 |
| `state_logistics` | 1 bang | 27 | 3.27 |
| `insight_distance` | 1 band km | 4 | 6.32 |
| `rfm_scores` | 1 khách | 94,983 | 5.5 |
| `repeat_profile` | one_shot vs repeat | 2 | 2.89 |
| `repeat_categories` | 1 danh mục của khách lặp | 70 | 3.11 |
| `repeat_states` | 1 bang của khách lặp | 27 | 2.05 |
| `seller_pareto` | 1 seller | 3,053 | 1.77 |
| `seller_watchlist` | seller doanh thu cao / ops kém | 153 | 1.57 |
| `insight_late_vs_review` | late vs on_time | 2 | 2.98 |
| `delay_vs_review` | 1 band ngày trễ | 5 | 2.34 |
| `payment_mix` | PTTT × kỳ trả góp | 10 | 2.41 |

## 4. Đối chiếu

| Kiểm tra | Được | Kỳ vọng | Kết quả |
|---|---:|---:|---|
| Gold SUM(revenue) | 13494400.74 | 13494400.74 | ĐẠT |
| kpi_monthly số tháng | 20 | 20 | ĐẠT |
| rfm_scores số khách | 94,983 | 94,983 | ĐẠT |
| late vs review có 2 nhóm | 2 | 2 | ĐẠT |

ĐẠT = đọc đúng gold và SQL không nuốt tháng / khách / nhóm giao hàng.

## 5. Xem trước

### KPI tháng (đỉnh + Black Friday)

| purchase_year | purchase_month | orders | revenue | revenue_mom_pct | late_delivery_pct | avg_review_score | is_black_friday_month | revenue_rank |
|---|---|---|---|---|---|---|---|---|
| 2017 | 11 | 7421 | 1003862.14 | 52.06 | 14.31 | 3.95 | True | 1 |
| 2018 | 4 | 6919 | 993592.98 | 1.28 | 5.31 | 4.17 | False | 2 |
| 2018 | 5 | 6833 | 992871.75 | -0.07 | 8.24 | 4.21 | False | 3 |
| 2018 | 3 | 7168 | 981051.06 | 17.09 | 21.36 | 3.76 | False | 4 |
| 2018 | 1 | 7187 | 945456.29 | 27.39 | 6.56 | 4.07 | False | 5 |

**Bảng `kpi_monthly`:** 1 dòng = 1 tháng trong 2017-01→2018-08 (đã cắt tháng rỗng). `revenue` = tổng giá sản phẩm (chưa gồm ship); `revenue_mom_pct` = % tăng/giảm so với tháng trước (NULL ở tháng đầu); `late_delivery_pct` = % đơn đã giao bị trễ; `avg_review_score` = sao trung bình cấp đơn; `revenue_rank` 1 = tháng doanh thu cao nhất; `is_black_friday_month` = tháng 11/2017.

**Đọc số:** 11/2017 vừa đỉnh doanh thu vừa MoM +52% vừa trễ 14,3% và review 3,95 — cao điểm Black Friday kèm quá tải vận chuyển. 03/2018 trễ 21,4% / review 3,76: tháng vận hành tệ nhất trong nhóm doanh thu lớn.

**Ý nghĩa:** Sàn **bán được nhiều hơn không đồng nghĩa vận hành ổn**. Tăng ads tháng 11 mà không tăng năng lực giao = đổi doanh thu đỉnh lấy uy tín. 04–05/2018 gần bằng doanh thu T11 nhưng trễ thấp và review ~4,2 — đó mới là tháng “khỏe” để nhân rộng, không phải Black Friday.

### Top 10 danh mục

| category | orders | items | revenue | freight | avg_price | freight_to_revenue_pct | revenue_share_pct | cumulative_share_pct |
|---|---|---|---|---|---|---|---|---|
| health_beauty | 8757 | 9585 | 1251145.54 | 181067.84 | 130.53 | 14.47 | 9.30 | 9.30 |
| watches_gifts | 5599 | 5965 | 1194824.97 | 99999.46 | 200.31 | 8.37 | 8.88 | 18.19 |
| bed_bath_table | 9394 | 11089 | 1035485.07 | 204294.48 | 93.38 | 19.73 | 7.70 | 25.89 |
| sports_leisure | 7656 | 8573 | 977728.77 | 167025.10 | 114.05 | 17.08 | 7.27 | 33.15 |
| computers_accessories | 6636 | 7760 | 902922.70 | 146278.79 | 116.36 | 16.20 | 6.71 | 39.87 |
| furniture_decor | 6373 | 8229 | 721584.27 | 170853.26 | 87.69 | 23.68 | 5.37 | 45.23 |
| housewares | 5838 | 6903 | 625538.73 | 144953.87 | 90.62 | 23.17 | 4.65 | 49.88 |
| cool_stuff | 3609 | 3772 | 619724.39 | 83124.97 | 164.30 | 13.41 | 4.61 | 54.49 |
| auto | 3863 | 4195 | 585177.48 | 91676.70 | 139.49 | 15.67 | 4.35 | 58.84 |
| garden_tools | 3500 | 4323 | 479650.06 | 98409.95 | 110.95 | 20.52 | 3.57 | 62.41 |

**Bảng `category_pareto`:** 1 dòng = 1 ngành (cộng 2017-01→2018-08). `avg_price` = revenue/items; `freight_to_revenue_pct` = ship / doanh thu (càng cao càng ăn biên); `revenue_share_pct` = % trên tổng sàn; `cumulative_share_pct` = cộng dồn từ ngành lớn nhất (Pareto).

**Đọc số:** `health_beauty` dẫn 9,3%. `watches_gifts` giá TB 200 vs `bed_bath_table` 93 (ít món đắt vs nhiều món rẻ). `furniture_decor` / `housewares` ship ~23% doanh thu. Top 10 mới ~62% — đuôi dài, chưa tới 80%.

**Ý nghĩa:** Không ngành nào >10% — campaign nên theo cụm (làm đẹp + đồng hồ + nhà cửa), không all-in một SKU. Đồng hồ là hàng margin (ship chỉ 8%); chăn ga là hàng volume (đừng so AOV). Nội thất/gia dụng: mỗi 100 BRL hàng mất ~23 BRL ship — “free ship” sẽ lỗ. Top 10 chưa 80% nghĩa là đuôi 64 ngành vẫn góp ~38%: cắt ngành nhỏ ồ ạt có thể mất doanh thu.

### Bang (top 8)

| customer_state | orders | customers | revenue | gmv | avg_order_value | avg_freight | freight_pct_of_revenue | avg_delivery_days | late_delivery_pct | avg_review_score | revenue_share_pct | revenue_rank |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SP | 41125 | 39747 | 5163867.22 | 5878132.06 | 142.93 | 17.37 | 13.83 | 8.7 | 5.89 | 4.21 | 38.27 | 1 |
| RJ | 12697 | 12241 | 1811623.42 | 2115667.56 | 166.63 | 23.95 | 16.78 | 15.2 | 13.47 | 3.91 | 13.43 | 2 |
| MG | 11496 | 11134 | 1573508.20 | 1843074.43 | 160.32 | 23.45 | 17.13 | 11.9 | 5.61 | 4.16 | 11.66 | 3 |
| RS | 5415 | 5233 | 742559.78 | 877290.59 | 162.01 | 24.88 | 18.14 | 15.2 | 7.15 | 4.15 | 5.50 | 4 |
| PR | 4982 | 4824 | 676883.06 | 794196.61 | 159.41 | 23.55 | 17.33 | 11.9 | 5.0 | 4.21 | 5.02 | 5 |
| SC | 3599 | 3501 | 518578.28 | 608023.70 | 168.94 | 24.85 | 17.25 | 14.9 | 9.76 | 4.1 | 3.84 | 6 |
| BA | 3344 | 3244 | 507108.83 | 606908.66 | 181.49 | 29.84 | 19.68 | 19.3 | 14.04 | 3.88 | 3.76 | 7 |
| DF | 2120 | 2057 | 300886.45 | 351327.21 | 165.72 | 23.79 | 16.76 | 12.9 | 7.07 | 4.09 | 2.23 | 8 |

**Bảng `state_logistics`:** 1 dòng = 1 bang khách. `gmv` = revenue + freight; `avg_order_value` = GMV/đơn; `freight_pct_of_revenue` = tỷ trọng ship; `avg_delivery_days` / `late_delivery_pct` / `avg_review_score` đo trải nghiệm giao.

**Đọc số:** SP ~38% doanh thu, giao 8,7 ngày, ship 13,8%, review 4,21. BA/RJ xa hơn: 15–19 ngày, trễ 13–14%, review ~3,9. Cùng lúc xa + trễ + sao thấp.

**Ý nghĩa:** SP vừa lớn vừa **dễ làm hài lòng** vì gần seller. BA/RJ **trả AOV cao hơn** (BA 181 vs SP 143) nhưng trải nghiệm tệ — copy playbook SP sang toàn quốc sẽ thất bại. Mở vùng phải kèm SLA/seller local hoặc báo ngày giao thật trước checkout.

### Khoảng cách

| distance_band | band_order | items | avg_freight | avg_delivery_days | avg_delay_days | late_pct |
|---|---|---|---|---|---|---|
| 0-200km | 1 | 28060 | 12.66 | 7.0 | -10.0 | 6.34 |
| 200-500km | 2 | 34572 | 19.07 | 11.9 | -12.4 | 7.04 |
| 500-1000km | 3 | 29361 | 21.08 | 14.2 | -12.8 | 8.29 |
| 1000km+ | 4 | 17156 | 31.65 | 19.0 | -12.9 | 11.69 |

**Bảng `insight_distance`:** 1 dòng = 1 band đường chim bay seller→khách (đơn delivered, đã lọc `dq_*`). `avg_freight` = cước TB; `avg_delivery_days` = ngày mua→nhận; `avg_delay_days` = nhận − hẹn (**âm = sớm hơn hẹn**); `late_pct` = % món trễ.

**Đọc số:** 0–200 km ship 12,7 / 7 ngày / trễ 6%; 1000km+ ship 31,7 / 19 ngày / trễ 12%. Cột delay âm (~−10 đến −13) nghĩa là **trung bình vẫn giao trước hạn**, nhưng `late_pct` vẫn tăng theo km (nhiều ca trễ hơn, kéo đuôi phân phối).

**Ý nghĩa:** Logistics có **cấu trúc địa lý**, không phải nhiễu. Gốc rễ band xa là chờ thực tế 19 ngày + 12% ca trễ (đủ để 1 sao), không phải deadline trên giấy. Ưu tiên gần hóa hàng (kho/seller vùng) hơn siết hạn hẹn hệ thống.

### Repeat vs one-shot

| cohort | customers | pct | avg_recency | avg_frequency | avg_monetary | avg_aov |
|---|---|---|---|---|---|---|
| repeat | 2887 | 3.04 | 270.4 | 2.114 | 308.35 | 145.83 |
| one_shot | 92096 | 96.96 | 287.9 | 1.0 | 161.19 | 161.19 |

**Bảng `repeat_profile`:** 1 dòng = một cohort. `frequency>=2` = repeat, còn lại one-shot. `pct` = % trên 94.983 khách RFM; `monetary` = lifetime GMV; `avg_aov` = giá trị đơn TB.

**Đọc số:** 96,96% chỉ mua 1 lần. 3,04% lặp chi lifetime gấp đôi (308 vs 161) nhưng AOV không cao hơn (145 vs 161) — họ quay lại, không phải mỗi đơn đắt hơn.

**Ý nghĩa:** Olist là **marketplace one-shot**, không phải subscription. KPI “retention 95k khách” sẽ gần 0 và vô dụng — chỉ 2.887 người đã lặp mới đáng CRM. Họ không mua đơn đắt hơn; họ mua **thêm lần**. Đốt budget win-back 92k one-shot sẽ loãng.

### RFM segment

| rfm_segment | customers |
|---|---|
| One-shot Lost | 65325 |
| One-shot Warm | 17615 |
| One-shot Recent | 9156 |
| At Risk | 1961 |
| Loyal | 675 |
| Champions | 251 |

**Bảng `rfm_scores` (cột `rfm_segment`):** Champion/Loyal/At Risk **chỉ** khi đã mua ≥2 lần. One-shot tách theo recency (Recent ≤90 ngày, Warm ≤180, Lost còn lại). Không gọi Champion cho khách mua một lần dù R và M cao.

**Đọc số:** CRM cổ điển rất nhỏ (251 Champions, 675 Loyal, 1.961 At Risk). Phần lớn là One-shot Lost — win-back toàn sàn kém ROI hơn giữ 3% đã lặp.

**Ý nghĩa:** Sách “Champions 20%” **không áp** được (chỉ 251 người). At Risk 1.961 người đáng gọi lại hơn 65k One-shot Lost. One-shot Recent (9k) còn cửa lần 2 trong 90 ngày (ngành nhà cửa); One-shot Lost gần như chi phí chìm.

### Giao trễ vs review

| delivery | orders | avg_review | pct_score_1_2 | pct_has_comment |
|---|---|---|---|---|
| late | 7655 | 2.56 | 54.07 | 55.56 |
| on_time | 87741 | 4.29 | 9.20 | 39.17 |

**Bảng `insight_late_vs_review`:** 1 dòng = late hoặc on_time. Chỉ đơn delivered, có review, đã lọc cờ `dq_*`. `avg_review` = sao TB cấp đơn; `pct_score_1_2` = % cho 1–2 sao; `pct_has_comment` = % có viết lời.

**Đọc số:** Trễ 2,56 sao vs đúng hạn 4,29 (kém 1,73). Hơn nửa đơn trễ cho 1–2 sao (54% vs 9%).

**Ý nghĩa:** Giao trễ **đổi 4,3 sao (rất tốt) thành 2,6 (gần thất bại trên storefront)**. Review 1–2 sao kèm comment là đòn **công khai kéo listing**, không phải “khách hơi bực”. Cải thiện on-time trên ~7.600 đơn trễ có đòn bẩy sao rõ hơn tăng ads.

### Ngưỡng ngày trễ

| delay_band | band_order | orders | avg_review | pct_1_star | pct_has_comment |
|---|---|---|---|---|---|
| on_time_or_early | 0 | 89020 | 4.29 | 6.60 | 39.17 |
| late_1_3d | 1 | 1850 | 3.29 | 25.14 | 48.38 |
| late_4_7d | 2 | 1747 | 2.1 | 58.56 | 59.76 |
| late_8_14d | 3 | 1446 | 1.67 | 70.61 | 64.73 |
| late_15d_plus | 4 | 1333 | 1.72 | 68.94 | 66.17 |

**Bảng `delay_vs_review`:** chia theo `delivery_delay_days` (âm = sớm). `pct_1_star` = % cho đúng 1 sao — dùng để tìm ngưỡng “khách giận”.

**Đọc số:** Đúng hạn 6,6% một sao. Trễ 4–7 ngày: review 2,1 và 59% một sao. Trễ 8–14 ngày kịch sàn (~1,67 sao, ~71% một sao). Sau ~1 tuần thêm ngày trễ gần như không làm tệ hơn.

**Ý nghĩa:** Không “chắc chắn 100% 1 sao”, nhưng sau **4 ngày trễ** đa số đã phạt nặng; sau **1 tuần** điểm kịch sàn. Ops phải can thiệp ở mốc 1–3 ngày (review còn 3,3), đừng đợi 15 ngày. Hứa giao sát thực tế (band xa ~19 ngày) còn hơn hứa 2 tuần rồi trễ 4 ngày.

## 6. K-Means profile (đặt tên cụm sau khi đọc bảng này)

| cluster | customers | avg_recency | avg_frequency | avg_monetary | champions | loyal | at_risk |
|---|---|---|---|---|---|---|---|
| 0 | 36442 | 196.2 | 1.0 | 69.56 | 0 | 0 | 0 |
| 1 | 2887 | 270.4 | 2.114 | 308.35 | 251 | 675 | 1961 |
| 2 | 28220 | 224.0 | 1.0 | 320.35 | 0 | 0 | 0 |
| 3 | 27434 | 475.3 | 1.0 | 119.20 | 0 | 0 | 0 |

**Cách đọc:** `cluster` là nhãn K-Means (k=4, seed=42) trên (recency, frequency, log1p(monetary)) đã scale — **không** phải tên CRM. Frequency TB ≈ 1 ở cụm 0/2/3 vì ~97% khách one-shot.

| Cụm | Đặt tên sau khi xem số | Vì sao |
|---|---|---|
| 0 | One-shot giá trị thấp | F=1, monetary ~70, recency ~196 (còn tương đối mới) |
| 1 | Khách mua lại | F=2,11; đúng 2.887 người; chứa hết Champions/Loyal/At Risk |
| 2 | One-shot chi cao | F=1, monetary ~320 |
| 3 | One-shot lost | F=1, recency ~475 ngày (lâu không mua) |

**Ý nghĩa:** Model **tự tìm ra** đúng 2.887 người lặp (cụm 1) — frequency là trục thật, K-Means không hỏng. Nó không tách nổi Champion vs At Risk trong 3% đó (N quá nhỏ). Dùng cụm 0 vs 2 cho one-shot: 0 (giỏ ~70) đừng tốn voucher lớn; 2 (giỏ ~320) còn cửa mời lần 2. Cụm 3 (~475 ngày) gần như chi phí chìm.

## 7. Các bảng không có trong mục xem trước — ý nghĩa kết quả

| Bảng | Kết quả | Ý nghĩa với sàn |
|---|---|---|
| `category_seasonality` | Mọi ngành lớn **đỉnh tháng 11** (~15–20% doanh thu năm). | Nhập hàng / ads / CSKH dồn trước Black Friday; rải đều 12 tháng sẽ thiếu hàng lúc cầu cao và thừa lúc cầu thấp. |
| `repeat_categories` | Khách lặp mua `bed_bath_table`, nội thất, thể thao — không phải đồng hồ. | Lần 2 là **bổ sung nhà cửa**, không phải upsell đồng hồ. Email/voucher lần 2 nên theo ngành này. |
| `repeat_states` | Lặp nhiều ở SP rồi RJ, MG — giống bản đồ doanh thu. | Không phải “chỉ dân SP mới trung thành”. Repeat đi theo mật độ đơn, không phải văn hóa vùng. |
| `seller_pareto` | ~18% seller nắm ~80% doanh thu. | Tập trung QC/ops vào vài trăm shop lớn; rải 3.000 shop sẽ loãng. |
| `seller_watchlist` | 153 shop vừa to vừa (sao thấp / giao chậm / trễ nhiều). | Rủi ro **uy tín × doanh thu**: ẩn/cảnh cáo sớm hơn shop nhỏ. Doanh thu cao không được miễn SLA. |
| `payment_mix` | Thẻ ~75% đơn; trả góp ≥7 kỳ AOV ~335 vs 1 kỳ ~101. | Trả góp là **kênh đơn đắt**, không phải nút “bật góp là tăng AOV”. Giữ góp cho đơn lớn; boleto (~20%) vẫn cần cho khách không thẻ. |
| `customer_segments` / `cluster_profile` | K-Means tách đúng 2.887 người lặp thành 1 cụm. | Model xác nhận frequency là trục thật. Luật CRM cho Champion/At Risk; cụm 0 vs 2 tách one-shot rẻ / đắt. |

## 8. Từ điển chỉ số (dùng chung)

| Chỉ số | Nghĩa |
|---|---|
| `revenue` | Tổng **giá sản phẩm**, chưa gồm vận chuyển (BRL). |
| `freight` / `freight_value` | Phí vận chuyển. |
| `gmv` / `order_value` | `revenue` + ship = số khách trả cho hàng. |
| `avg_order_value` (AOV) | GMV trung bình mỗi đơn. |
| `orders` / `customers` / `items` | Số đơn / khách thật (`customer_unique_id`) / món. |
| `late_delivery_pct` / `late_pct` | % đơn (hoặc món) **đã giao** nhận sau ngày hẹn. |
| `avg_delivery_days` | Ngày từ mua đến khách nhận. NULL nếu chưa giao. |
| `delivery_delay_days` / `avg_delay_days` | Ngày nhận − ngày hẹn. **Âm = sớm**, dương = trễ. |
| `avg_review_score` | Sao 1–5 **cấp đơn**, không nhân theo số món. |
| `freight_to_revenue_pct` | Ship / revenue × 100. Cao = hàng cồng kềnh ăn biên. |
| `revenue_share_pct` | Tỷ trọng trên tổng đang xét. |
| `cumulative_share_pct` | Cộng dồn từ lớn đến nhỏ (đường Pareto). |
| `revenue_mom_pct` | (tháng này − tháng trước) / tháng trước × 100. |
| `revenue_yoy_pct` | So với cùng tháng năm trước (`LAG` 12). Tháng 2017 = NULL. |
| `recency_days` | Ngày từ lần mua cuối đến 2018-10-17 (neo gold). |
| `frequency` | Số đơn hợp lệ của khách. |
| `monetary` | Tổng GMV lifetime của khách. |
| `r_score` / `f_score` / `m_score` | NTILE 5. F gần như nhiễu vì 97% frequency = 1. |
| Pearson | −1…1. 0,39 = tăng cùng chiều vừa; gần 0 = gần như không tuyến tính. |

## 9. Kết luận ngắn (kết quả này nói gì về sàn)

1. **Doanh thu đỉnh ≠ sức khỏe:** Black Friday và 03/2018 bán mạnh nhưng trễ và sao rớt — phải tăng năng lực giao trước khi tăng ads.
2. **Giao trễ là đòn bẩy sao:** trễ mất ~1,7 sao; sau 4–7 ngày đa số đã 1 sao. Can thiệp sớm, hứa ngày giao sát thực tế.
3. **Địa lý quyết định trải nghiệm:** SP dễ tính vì gần seller; BA/RJ trả AOV cao hơn nhưng review thấp — mở vùng phải kèm SLA.
4. **Khách không quay lại là mặc định:** 97% one-shot. CRM chỉ đáng tiền trên ~3% đã lặp + one-shot recent; đừng làm loyalty cho cả 95k người.
5. **Seller lệch Pareto:** ~18% shop = 80% doanh thu. Watchlist 153 shop to mà ops kém là rủi ro lớn nhất phía cung.

Diễn giải dài: `docs/03-cau-hoi-va-kpi.md`.
