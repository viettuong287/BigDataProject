# Phân cụm RFM và K-Means

## Hai lớp nhãn

1. **Luật** (`rfm_segment` trong SQL): Champion / Loyal / At Risk chỉ khi `frequency >= 2`. One-shot tách theo recency. Phù hợp CRM.
2. **K-Means k=4** trên `(recency_days, frequency, log1p(monetary))` đã `StandardScaler` (mean=0, std=1), `seed=42`.

`log1p(monetary)`: tiền lệch phải; không log thì cụm chỉ chia giàu/nghèo. Scale: recency ~0–700, frequency ~1–16 — Euclid không scale thì recency nuốt hết.

Không đặt tên “Champions” cho `prediction` trước khi đọc centroid.

## Centroid (không gian đã scale)

| Cluster | Centroid (R, F, log M) | Khách | Recency TB | Freq TB | Monetary TB | Ý nghĩa |
|---|---|---:|---:|---:|---:|---|
| 0 | −0,60, −0,16, −0,70 | 36.442 | 196 | 1,00 | 70 | One-shot, giá trị thấp, còn tương đối mới |
| 1 | −0,11, **+5,12**, +0,91 | **2.887** | 270 | **2,11** | 308 | **Toàn bộ khách mua lại** |
| 2 | −0,41, −0,16, +1,00 | 28.220 | 224 | 1,00 | 320 | One-shot chi cao |
| 3 | **+1,23**, −0,16, −0,19 | 27.434 | **475** | 1,00 | 119 | One-shot cũ (lost) |

Cluster 1 chứa đúng 251 Champions + 675 Loyal + 1.961 At Risk. K-Means **tự tách được nhóm 3% lặp** nhờ frequency; không tách nổi Champion vs At Risk bên trong nhóm đó vì N quá nhỏ so với 97% one-shot.

Cluster 0 vs 2: cùng F=1, khác monetary — hữu ích cho campaign “đơn giá cao lần đầu”. Cluster 3: win-back kém ROI.

## Thảo luận

Frequency gần như hằng số 1 → K-Means trên 3 chiều RFM **không** cho 4 persona CRM đẹp như sách giáo khoa. Đó là đặc trưng Olist, không phải model hỏng. Báo cáo nêu rõ: hành động CRM dựa luật `frequency >= 2`; K-Means là lớp kiểm chứng và tách one-shot rẻ / đắt / mất.

Thử k=3 sẽ gộp 0+2 hoặc nuốt lost; k=5 dễ xé one-shot thành nhiễu. k=4 đủ để demo và khớp dữ liệu.
