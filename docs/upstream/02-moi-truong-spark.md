# Môi trường Spark

## Cụm

Docker Compose: 1 master + 2 worker, image `apache/spark:3.5.3-python3` dựng thêm `numpy` (PySpark ML import numpy khi load `KMeans`). Mọi volume trỏ trong repo (`./data/gold`, `./jobs`, …), không phụ thuộc folder ngoài.

| Thành phần | Cấu hình |
|---|---|
| Image | `analytics-spark:3.5.3` (`Dockerfile`) |
| Worker | 2 × (2 core, 2 GB RAM) → 4 core cụm |
| Volume | `data/gold` (ro), `data/analytics`, `jobs`, `reports` |
| UI | Master http://localhost:8080 — job http://localhost:4040 |

Driver chạy trong container `spark-master` qua `spark-submit --master spark://spark-master:7077`. Không đặt `.master()` trong code.

## Vì sao Docker, không Pandas trên Windows

Đề bài yêu cầu chứng minh xử lý phân tán. Pandas trên Python 3.14 máy host không phải Spark. Image Spark dùng Python 3.8 + Java 11 sẵn có.

`user: "0:0"` để ghi được `reports/` và `data/analytics/` từ container (bind mount Windows).

## Tối ưu nhỏ phù hợp dữ liệu

`spark.sql.shuffle.partitions = 16` — default 200 quá nhiều cho ~100k dòng (nhiều file tí hon, chậm hơn).

Bảng KPI `coalesce(1)` vì vài nghìn dòng; Presentation đọc một file Parquet cho tiện.

`wait_for_executors`: ngay sau `SparkSession`, worker có thể chưa đăng ký; đọc sớm sẽ chia ít partition.

## Numpy

Image gốc không có numpy → `from pyspark.ml.clustering import KMeans` crash. `Dockerfile` cài `numpy==1.24.4` (cp38). Cài trong image, không pip tạm trong container đang chạy (mất khi `compose down`).
