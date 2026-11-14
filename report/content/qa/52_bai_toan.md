# 5.2. Bài toán cụ thể và tính chất dữ liệu lớn

> **Yêu cầu 5.2 (đề bài):** Mô tả bài toán thực tế và trả lời: vì sao bài toán cần tiếp cận Big Data? Nhóm phải chỉ ra ít nhất 02 đặc trưng phù hợp trong Volume, Velocity, Variety, Veracity hoặc nhu cầu xử lý phân tán/mở rộng.

**Bài toán thực tế.** Sàn thương mại điện tử Olist (Brazil) có khoảng 100 nghìn đơn hàng giai đoạn 09/2016–10/2018 từ hơn 3.000 người bán và gần 95 nghìn khách. Nhóm Analytics đã trả lời sáu nhóm câu hỏi nghiệp vụ trên Spark, nhưng kết quả chỉ là các tệp Parquet. Bài toán của nhóm em là phục vụ kết quả đó cho người ra quyết định — đúng số, tương tác được, nhiều người dùng cùng lúc — và chuyển thành gợi ý hành động.

Bảng: Người dùng nghiệp vụ và quyết định được hỗ trợ {w=2.8,4.6,8.6}
| Người dùng | Câu hỏi trên dashboard | Quyết định được hỗ trợ (số liệu thật) |
|---|---|---|
| Ban điều hành | Doanh thu tăng thế nào, vận hành có theo kịp? | 11/2017 doanh thu đỉnh 1.003.862 BRL (MoM +52,06%) nhưng trễ 14,31%, review 3,95 → tăng năng lực giao vận trước cao điểm |
| Quản lý ngành hàng | Ngành nào tạo 80% doanh thu, mùa vụ ra sao? | `health_beauty` 9,30%, 17 ngành đầu chiếm 79,7%; mọi ngành lớn đạt đỉnh tháng 11 → dồn tồn kho, quảng cáo vào quý IV |
| Logistics | Bang nào giao chậm, trễ nhiều, review thấp? | SP 8,7 ngày, review 4,21; BA 19,3 ngày, trễ 14,04%, review 3,88 → kho/người bán theo vùng |
| CRM – marketing | Bao nhiêu khách quay lại, chăm sóc ai? | Chỉ 2.887/94.983 khách (3,04%) mua lại; 1.961 khách At Risk → win-back có mục tiêu |
| Quản lý người bán | Ai lớn nhưng vận hành kém? | 539/3.053 người bán tạo 80% doanh thu; 153 người bán watchlist, 75 mức ĐỎ → cảnh cáo, SLA 30 ngày |

**Vì sao cần tiếp cận Big Data.** Nhóm em trả lời trung thực: ở tầng Presentation, khối lượng dữ liệu đã giảm mạnh — đó là thiết kế đúng của pipeline (tính nặng ở tầng batch phân tán, phục vụ nhẹ ở tầng serving). Phần cần Big Data nằm ở chỗ: (1) dữ liệu đến từ một pipeline phân tán và phải giữ đúng ngữ nghĩa khi đi qua nhiều tầng; (2) tầng phục vụ phải chịu nhiều người dùng đồng thời với độ trễ tương tác; (3) kiến trúc phải không đổi khi dữ liệu nguồn tăng. Các đặc trưng cụ thể:

Bảng: Các đặc trưng dữ liệu lớn của bài toán (có số liệu) {w=2.4,5.4,8.2}
| Đặc trưng | Thể hiện cụ thể | Số liệu / bằng chứng |
|---|---|---|
| Volume | Khối lượng giảm qua từng tầng: CSV thô → silver → gold → Analytics → serving | 9 CSV ≈ 1,55 triệu dòng (~120 MB) → silver 569.698 dòng → gold 7 bảng (33,3 MB, Spark 61,72 s) → Analytics 16 bảng (Spark 1 master + 2 worker, 119,71 s) → nhóm em phục vụ 23 bảng, **505.592 dòng**, 42,88 MB Parquet |
| Variety | Nhiều grain, nhiều kiểu, chuyển từ lưu trữ cột (Parquet) sang quan hệ (Postgres) | 23 bảng với hơn 10 grain (tháng, danh mục, danh mục × tháng, bang, band khoảng cách, khách, cụm, cohort, người bán, PTTT × kỳ góp, đơn, dòng sản phẩm); kiểu `decimal`, `date`, `timestamp`, `boolean`, chuỗi băm; fact phân vùng Hive; hai hệ nhãn khách (luật RFM và cụm K-Means) |
| Veracity | Dữ liệu có cờ chất lượng `dq_*`, tháng thiếu dữ liệu, `customer_id` ≠ khách thật; bẫy ngữ nghĩa (tổng 20 tháng 13.449.529,68 < số neo 13.494.400,74 vì đã cắt tháng rỗng) | 23/23 bảng khớp số dòng Parquet ↔ Neon; **19/19 số neo** đạt; kiểm nhất quán chéo gold ↔ Analytics chênh 0,00 (`evidence/validation.md`) |
| Nhu cầu mở rộng / phục vụ đồng thời | Dashboard 45 biểu đồ, mỗi biểu đồ một truy vấn; tải không đều; dữ liệu nguồn có thể tăng | Thí nghiệm ×10 (1.121.010 dòng): truy vấn trên dữ liệu thô 47 → 507 ms, view tổng hợp giữ 1,1 ms; Neon serverless (tách compute/storage, scale-to-zero); Superset 4 worker + cache 600 s |
| Velocity | Theo lô: mỗi lần Analytics chạy lại thì nạp lại; loader idempotent nên chạy theo lịch được | Một lần nạp đầy đủ 23 bảng ≈ 278 s; chưa có streaming (nói rõ là hạn chế) |
