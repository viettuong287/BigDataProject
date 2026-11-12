# 8. Thảo luận

## 8.1. Điểm mạnh

- **Ranh giới rõ ràng, data contract tường minh:** nhóm phục vụ chứ không tính lại phân tích của Analytics; mọi con số truy ngược được về một cột Parquet và được đối chiếu tự động. Nhóm trước đổi thuật toán, nhóm sau chỉ cần nạp lại.
- **Tách tầng vật lý và ngữ nghĩa:** `analytics`/`gold` phản ánh Parquet, `presentation` phản ánh nghiệp vụ; định nghĩa KPI nằm ở một nơi, dùng chung cho dashboard và Decision/Action.
- **Độ đo không cộng dồn và lọc chéo nhất quán:** AOV, % trễ, review trên thẻ KPI tính lại từ `v_orders` thay vì trung bình của tỷ lệ tháng; kiểm tra nhất quán chéo chứng minh tổng từ gold bằng đúng tổng của Analytics.
- **Đầu ra máy đọc được:** `v_decision_hints` chứa luật, ngưỡng, giá trị và hành động — giai đoạn sau dùng ngay bằng SQL.
- **Tái lập bằng mã:** Docker Compose, DDL tự sinh, dashboard dựng qua REST API, ảnh chụp tự động, báo cáo này cũng sinh bằng script.
- **Chi phí gần bằng không khi không dùng:** scale-to-zero cộng cache 10 phút của Superset.

## 8.2. Hạn chế

- **Insight phân tích không lọc chéo được:** Pareto, RFM, K-Means, watchlist là kết quả toàn kỳ của Spark; lọc theo tháng/bang đòi hỏi tính lại phân tích, vượt phạm vi nhóm. Phạm vi từng bộ lọc phải được cấu hình và giải thích cẩn thận.
- **Chi phí lớp gold:** 7 bảng gold chiếm khoảng {{var:load_gold_share}}% thời gian nạp chỉ để phục vụ lọc chéo cho một số thẻ KPI và xu hướng.
- **Thời gian nạp phụ thuộc đường truyền client:** thông lượng COPY (~{{var:load_copy_mbps}} MB/s) bị giới hạn bởi băng thông tải lên, không phải bởi Neon.
- **Quy mô vừa phải:** {{var:load_total_rows}} dòng chưa đủ để thấy giới hạn của Postgres; nhận định về mở rộng dựa trên lập luận kiến trúc và số đo hiện có, chưa phải tải thật của hàng nghìn người dùng.
- **Full refresh, chưa nạp tăng dần;** metadata Superset dùng SQLite và cache filesystem, chưa phù hợp chạy nhiều bản Superset; bảo mật mức cơ bản (chưa row-level security, tài khoản quản trị dùng cho demo). [[CẬP NHẬT: bổ sung hạn chế thực tế khác nếu có]]

## 8.3. Khả năng mở rộng

Khi dữ liệu nguồn tăng 10–100 lần (1–10 triệu đơn):

- **Bảng Analytics tăng không đều:** bảng theo tháng, danh mục, bang, band khoảng cách gần như không đổi; chỉ bảng cấp khách hàng và người bán tăng tuyến tính (10 triệu đơn → `customer_segments` cỡ 10 triệu dòng), vẫn trong khả năng PostgreSQL với chỉ mục. Đây là lợi ích cốt lõi của việc đặt tầng phục vụ *sau* tầng xử lý phân tán: khối lượng đã được Spark cô đọng. Lớp gold chi tiết thì tăng tuyến tính và là ứng viên đầu tiên cần thay bằng bảng tổng hợp nhẹ hoặc materialized view.
- **Nạp dữ liệu:** nút thắt hiện tại là mạng client → Neon. Bước đầu là chạy loader cùng vùng mạng với Neon (máy ảo AWS Singapore hoặc job CI), nơi `COPY` thường đạt hàng chục đến hàng trăm nghìn dòng/giây; sau đó nạp song song nhiều bảng, nạp tăng dần theo phân vùng tháng, và với bảng rất lớn thì dùng declarative partitioning, nạp vào bảng tạm rồi hoán đổi để không khoá người đọc.
- **Truy vấn:** Neon autoscaling tăng tài nguyên theo chiều dọc; *read replica* tách tải BI khỏi tải nạp; view nặng chuyển thành *materialized view* làm mới sau mỗi lần nạp.
- **Superset:** mở rộng theo chiều ngang — nhiều web server sau cân bằng tải, metadata PostgreSQL, cache Redis, Celery worker cho truy vấn bất đồng bộ và báo cáo định kỳ.
- **Khi nào đổi công nghệ?** Nếu phải lọc chéo tự do trên fact hàng tỷ dòng, kho OLAP cột (ClickHouse, Druid, Pinot) hoặc Trino trên Iceberg/Delta phù hợp hơn. Nhờ SQLAlchemy và tầng ngữ nghĩa SQL chuẩn, việc thay tầng phục vụ chủ yếu là chuyển các view, không làm lại dashboard.

## 8.4. Bài học kỹ thuật và hướng cải tiến

**Bài học:** (1) tầng trình bày không chỉ "vẽ biểu đồ" — rủi ro lớn nhất nằm ở ngữ nghĩa số liệu (grain, độ đo không cộng dồn, phạm vi thời gian), nên data contract và đối chiếu tự động là bắt buộc; (2) với dịch vụ serverless, độ trễ người dùng cảm nhận chủ yếu đến từ mạng và cold start, cache ở tầng BI có tác dụng lớn hơn tối ưu SQL ở quy mô này; (3) PgBouncer chế độ transaction hợp với truy vấn ngắn của BI nhưng không hợp với DDL/COPY — phải phân biệt endpoint pooled và direct; (4) dashboard-as-code tốn công ban đầu nhưng trả lại bằng khả năng tái lập và quản lý phiên bản.

**Hướng cải tiến:**

- Đề xuất Analytics bổ sung cột tử số/mẫu số (đơn đã giao, đơn trễ, đơn có review) và bảng tổng hợp tháng × bang × danh mục × PTTT, để bỏ lớp gold chi tiết mà vẫn lọc chéo được.
- Nạp tăng dần theo `run_id`/phân vùng tháng, lưu lịch sử nhiều lần chạy để so sánh phiên bản phân tích.
- Điều phối toàn pipeline bằng Airflow/Dagster (Analytics xong → nạp → kiểm tra → làm mới view → làm nóng cache); quản lý tầng ngữ nghĩa bằng dbt.
- Bật Alerts & Reports của Superset (Celery + Redis) để gửi cảnh báo khi KPI vượt ngưỡng — cầu nối tự nhiên sang Decision/Action; thêm row-level security, role chỉ đọc, SSO.
