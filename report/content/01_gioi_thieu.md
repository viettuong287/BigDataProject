# 1. Giới thiệu

## 1.1. Bối cảnh

Trong hệ thống dữ liệu lớn, giá trị kinh doanh chỉ xuất hiện khi kết quả phân tích đến được người ra quyết định, đúng lúc và dễ hiểu. Các kiến trúc tham chiếu như Lambda [8] hay Lakehouse [9] đều có một **tầng phục vụ (serving layer)**: dữ liệu sau khi được xử lý phân tán được cô đọng thành bảng tổng hợp, nạp vào hệ thống trả lời truy vấn tương tác với độ trễ thấp, rồi được trình bày qua dashboard hoặc API. Thiếu tầng này, kết quả Spark chỉ là các tệp Parquet trong Data Lake mà người dùng nghiệp vụ không khai thác được.

Bộ dữ liệu dùng xuyên suốt pipeline của lớp là **Brazilian E-Commerce Public Dataset by Olist** [1]: khoảng 100 nghìn đơn hàng trên các sàn thương mại điện tử Brazil từ 09/2016 đến 10/2018. Dữ liệu đã qua các giai đoạn trước: nhóm Storage → Processing dựng tầng gold (7 bảng, đối chiếu 11/11); nhóm Processing → Analytics chạy 14 truy vấn Spark SQL và K-Means trên cụm Spark, bàn giao 16 bảng Parquet kèm tài liệu `ANALYTICS_HANDOVER.md`. Nhóm chúng tôi đưa các kết quả này tới người dùng nghiệp vụ của sàn: ban điều hành, quản lý ngành hàng, vận hành – logistics, CRM – marketing và đội quản lý người bán.

## 1.2. Quy trình được lựa chọn và ranh giới

Nhóm thực hiện quy trình con **Analytics → Presentation** (Mục 4 của đề bài), với ranh giới:

- **Điểm bắt đầu:** {{var:n_tables}} bảng Parquet trong `data/analytics/` cùng tài liệu bàn giao của Analytics; nạp kèm {{var:n_gold}} bảng gold ({{var:gold_rows}} dòng, cũng là đầu vào của Analytics) để dashboard lọc chéo được ở cấp đơn hàng. Nhóm **không** đọc lại CSV thô, **không** chạy lại Spark và **không** tính lại các phân tích phức tạp (K-Means, Pareto, RFM). Mọi chỉ số trên dashboard truy ngược được về một cột của Analytics hoặc gold, và tổng từ gold phải khớp số của Analytics.
- **Điểm kết thúc:** (1) cơ sở dữ liệu phục vụ trên Neon đã nạp và kiểm tra; (2) tầng ngữ nghĩa gồm các view SQL định nghĩa KPI thống nhất; (3) dashboard Superset có KPI, bộ lọc, biểu đồ và nguồn dữ liệu rõ ràng; (4) các view **gợi ý quyết định** cho giai đoạn Presentation → Decision/Action.
- **Giao diện với giai đoạn trước:** *data contract* gồm danh sách bảng, grain, khoá, kiểu dữ liệu và các số neo đối chiếu (Chương 3). **Với giai đoạn sau:** các view ổn định trong schema `presentation`, đọc bằng SQL, không phụ thuộc Superset.

## 1.3. Mục tiêu và phạm vi

Mục tiêu là xây dựng tầng trình bày **đúng số liệu, tương tác được, tái lập được và mở rộng được**:

1. Nạp đầy đủ, chính xác các bảng Parquet vào cơ sở dữ liệu phục vụ trên đám mây, bảo toàn kiểu dữ liệu (đặc biệt tiền tệ `DECIMAL`), có nhật ký nạp và kiểm tra đối chiếu tự động.
2. Xây dựng tầng ngữ nghĩa trong đó mỗi KPI có một định nghĩa và cách tổng hợp đúng (kể cả chỉ số không cộng dồn như tỷ lệ, trung bình).
3. Triển khai dashboard Superset cho năm nhóm người dùng, có bộ lọc native và khu vực gợi ý quyết định.
4. Đo thời gian nạp, thông lượng, độ trễ truy vấn và tác động của scale-to-zero, bộ nhớ đệm.
5. Đóng gói bằng Docker Compose và mã nguồn để người khác chạy lại.

**Ngoài phạm vi:** thu thập, làm sạch, tính toán phân tích (các nhóm trước); thực thi hành động tự động như gửi email, gọi webhook (nhóm Decision/Action). Dữ liệu được xử lý theo lô vì nguồn Olist là dữ liệu lịch sử.

## 1.4. Câu hỏi kỹ thuật

- **RQ1 – Lưu trữ phục vụ:** phục vụ kết quả từ đâu (Parquet trực tiếp, Postgres cục bộ, ClickHouse hay Postgres serverless) để cân bằng độ trễ, chi phí, khả năng chia sẻ và công vận hành? (Chương 2, 4)
- **RQ2 – Tính đúng đắn:** làm sao đảm bảo số trên dashboard khớp tuyệt đối kết quả Spark, kể cả khi người dùng lọc và gộp chỉ số không cộng dồn? (Chương 3, 6)
- **RQ3 – Hiệu năng:** thời gian nạp và độ trễ truy vấn là bao nhiêu; nút thắt nằm ở đâu? (Chương 6)
- **RQ4 – Thiết kế trình bày:** bố cục, biểu đồ, bộ lọc nào giúp từng nhóm người dùng trả lời câu hỏi nhanh nhất? (Chương 4, 7)
- **RQ5 – Mở rộng và tích hợp:** kiến trúc thay đổi ra sao khi dữ liệu tăng 10–100 lần, và giai đoạn sau tiêu thụ kết quả thế nào? (Chương 8, 9)

## 1.5. Cấu trúc báo cáo

Chương 2 trình bày cơ sở và công nghệ; Chương 3 mô tả dữ liệu, đặc trưng Big Data, đầu vào, đầu ra và data contract; Chương 4 trình bày kiến trúc và thiết kế; Chương 5 mô tả cài đặt; Chương 6 thực nghiệm; Chương 7 kết quả demo; Chương 8 thảo luận; Chương 9 kết luận. Phụ lục chứa hướng dẫn chạy, cấu hình, schema, mã SQL, minh chứng chi tiết, mã nguồn, bảng phân công và ghi chú sử dụng AI.
