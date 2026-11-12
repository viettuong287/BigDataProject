# Thực nghiệm

Lần chạy: **2026-10-29 15:50:47 UTC**, Spark 3.5.3, master `spark://spark-master:7077`, **2 executor / 4 core**.

## Thời gian

| Khối | Thời gian |
|---|---:|
| 14 câu SQL (ghi Parquet) | 51,39 s |
| K-Means k=4 | 26,49 s |
| **Tổng job** | **135,50 s** (~2,3 phút) |

SQL chậm nhất: `insight_distance` 7,61 s (join fact items × orders + lọc delivered). RFM 94.983 dòng: 6,10 s. Các agg nhỏ 2–4 s.

Cảnh báo `WindowExec: No Partition Defined` trên Pareto/NTILE là đúng: window toàn cục phải về 1 partition. 3.053 seller / 74 category — chấp nhận được.

`InstanceBuilder: Failed to load JNIBLAS`: K-Means dùng BLAS thuần Java, không ảnh hưởng kết quả.

## Đối chiếu (4/4 đạt)

| Kiểm tra | Kết quả |
|---|---|
| `SUM(revenue)` gold | 13.494.400,74 |
| Số tháng KPI | 20 |
| Số khách RFM | 94.983 |
| Nhóm late / on_time | 2 |

## Minh chứng cụm

- `evidence/spark-ui-8080.png` — 2 worker ALIVE, 4 core, application `olist-analytics` FINISHED ~2,2 phút
- `evidence/spark-ui-8081-worker.png` — worker 2 core, executor của app đã EXITED
- `reports/analytics_run.log` — log INFO từng bước
- `reports/analytics_summary.json` — số thô

Job UI `:4040` chỉ mở khi application đang chạy; lần sau chụp trong lúc `spark-submit`.

## Lặp lại thí nghiệm

```powershell
docker compose up -d --build
docker compose exec spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 /opt/jobs/01_analytics.py
```

K-Means `seed=42` → cùng centroid. SQL không ngẫu nhiên.
