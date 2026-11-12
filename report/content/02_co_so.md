# 2. Cơ sở và công nghệ liên quan

Chương này chỉ trình bày phần kiến thức Big Data dùng trực tiếp trong đồ án.

## 2.1. Đặc trưng dữ liệu lớn và vai trò tầng trình bày

Dữ liệu lớn được mô tả bằng các chữ V: **Volume** (khối lượng), **Velocity** (tốc độ phát sinh), **Variety** (đa dạng), **Veracity** (độ tin cậy) và **Value** (giá trị). Pipeline gồm Sources → Ingestion → Storage → Processing → Analytics → Presentation → Decision/Action; mỗi giai đoạn giao tiếp qua định dạng dữ liệu thống nhất. Đặc điểm quan trọng là **khối lượng giảm dần theo từng tầng trong khi giá trị trên mỗi byte tăng dần**: triệu dòng thô thành trăm nghìn dòng fact, rồi bảng tổng hợp, cuối cùng là vài chục KPI. Vì vậy thách thức của tầng Presentation không phải quét petabyte, mà là (1) phục vụ **nhiều người dùng đồng thời với độ trễ tương tác**, (2) giữ **nhất quán ngữ nghĩa** giữa số do hệ thống phân tán tính và số người dùng thấy, (3) **co giãn** theo tải truy cập rất không đều.

## 2.2. Data Lake và định dạng cột Apache Parquet

**Data Lake** lưu dữ liệu dạng tệp theo nguyên tắc *schema-on-read*; nhiều công cụ (Spark, pyarrow, DuckDB, Trino) đọc trực tiếp mà không cần máy chủ cơ sở dữ liệu. Các tầng silver, gold, analytics của pipeline Olist đều là thư mục Parquet.

**Apache Parquet** [5] là định dạng hướng cột kế thừa Dremel [6]: tệp chia thành *row group*, trong đó dữ liệu từng cột nằm liền nhau (*column chunk*, chia thành *page*). Lợi ích [7]: chỉ đọc cột cần thiết; nén tốt nhờ mã hoá từ điển, run-length kết hợp Snappy (bảng `customer_segments` 94.983 dòng × 13 cột chỉ khoảng 3,9 MB); thống kê min/max cho phép bỏ qua khối dữ liệu (predicate pushdown); schema tự mô tả với kiểu logic `DECIMAL`, `DATE`, `TIMESTAMP` — nhờ đó loader của nhóm **tự sinh DDL PostgreSQL**. Tuy nhiên Parquet không phải hệ thống phục vụ: không có chỉ mục tra cứu điểm, không kiểm soát truy cập theo người dùng, không phục vụ nhiều client đồng thời — nên cần một tầng phục vụ riêng.

## 2.3. Xử lý phân tán bằng Apache Spark ở giai đoạn trước

Các bảng đầu vào được sinh bởi **Apache Spark** [3], [4] — công cụ xử lý phân tán trong bộ nhớ, kế thừa MapReduce [2] nhưng biểu diễn tính toán thành DAG các phép biến đổi trên dữ liệu phân vùng. *Driver* lập kế hoạch, *executor* trên worker chạy *task* trên từng *partition*; `GROUP BY`, `JOIN`, window function sinh bước *shuffle*; trình tối ưu Catalyst chọn broadcast hoặc sort-merge join.

Nhóm Analytics chạy job trên cụm Docker 1 master + 2 worker (tổng 4 core), Spark 3.5.3, `spark.sql.shuffle.partitions = 16`. Job mất {{var:spark_total_s}} giây (SQL {{var:spark_sql_s}} giây, K-Means {{var:spark_kmeans_s}} giây); bảng KPI nhỏ được `coalesce(1)` thành một tệp. Hai hình dưới là ảnh Spark UI do nhóm Analytics cung cấp, chứng minh job chạy phân tán. Lưu ý cho tầng Presentation: các window toàn cục (Pareto cộng dồn, NTILE của RFM) đã được Spark tính; nếu dashboard tính lại trên dữ liệu đã lọc sẽ ra kết quả khác, nên nhóm coi chúng là **thuộc tính đã chốt**.

{{image:UPSTREAM:evidence/spark-ui-8080.png|Spark Master UI (cổng 8080) của nhóm Analytics: 2 worker ALIVE, 4 core, ứng dụng olist-analytics FINISHED}}

{{image:UPSTREAM:evidence/spark-ui-8081-worker.png|Spark Worker UI (cổng 8081): worker 2 core và executor của ứng dụng Analytics}}

## 2.4. OLAP, bảng tổng hợp và tầng phục vụ

Hệ **OLTP** tối ưu cho giao dịch nhỏ theo dòng; hệ **OLAP** tối ưu cho truy vấn quét nhiều dòng và tổng hợp theo nhiều chiều [11]. Mô hình Kimball [10] tổ chức dữ liệu thành bảng **fact**, **dimension** và **bảng tổng hợp** tính trước theo các tổ hợp chiều thường dùng. Các bảng Analytics chính là bảng tổng hợp ở nhiều *grain*: tháng, danh mục, danh mục × tháng, bang, người bán, khách hàng. Trong kiến trúc Lambda [8], **tầng phục vụ** lập chỉ mục và phục vụ các *batch view* do tầng batch tính ra: ở đây Spark là batch layer, Neon là serving layer.

Khái niệm then chốt là **tính cộng dồn của độ đo** [10]: *cộng dồn được* (doanh thu, số đơn) có thể `SUM` theo mọi chiều; *bán cộng dồn* (số khách duy nhất) cộng theo tháng sẽ đếm trùng; *không cộng dồn* (tỷ lệ, trung bình, % tăng trưởng) không được lấy trung bình của trung bình mà phải tính lại từ tử số và mẫu số. Tầng ngữ nghĩa của nhóm mã hoá các quy tắc này.

## 2.5. PostgreSQL và Neon Serverless Postgres

**PostgreSQL** là hệ quản trị quan hệ mã nguồn mở với SQL đầy đủ, giao dịch ACID, view, window function, chỉ mục và lệnh `COPY` nạp hàng loạt nhanh hơn nhiều lần so với `INSERT` từng dòng [14]; hầu hết công cụ BI đều kết nối được.

**Neon** là Postgres serverless **tách rời compute và storage** [12], tương tự Amazon Aurora [24]. *Compute* là tiến trình Postgres không trạng thái; *storage* gồm Safekeeper (nhân bản WAL bằng đồng thuận Paxos), Pageserver (dựng trang dữ liệu từ WAL, phục vụ compute) và object storage cho lưu trữ dài hạn. Các tính năng dùng trong đồ án [13]: **autoscaling** compute theo Compute Unit (≈ 1 vCPU + 4 GB RAM); **scale-to-zero** tạm dừng compute sau thời gian không hoạt động (mặc định 5 phút), truy vấn kế tiếp chịu độ trễ khởi động; **branching** copy-on-write để thử thay đổi trên dữ liệu thật; **connection pooling** qua hostname `-pooler` chạy PgBouncer chế độ transaction. Mô hình này khớp với **tải không đều** của dashboard: không ai xem thì compute ngủ, nhiều người xem thì compute tự tăng tài nguyên, dữ liệu luôn an toàn trong storage nhân bản.

## 2.6. Tầng ngữ nghĩa và Apache Superset

**Tầng ngữ nghĩa** định nghĩa *một lần* các khái niệm nghiệp vụ (chỉ số, chiều phân tích, tên hiển thị, cách tổng hợp) để mọi dashboard, báo cáo, API cho cùng một con số. Có thể đặt nó trong cơ sở dữ liệu (view), trong công cụ BI (dataset, metric) hoặc công cụ riêng (dbt, Cube). Nhóm đặt phần lõi ở **view SQL trên Neon** vì cả Superset lẫn giai đoạn Decision/Action đều đọc trực tiếp được.

**Apache Superset** [15] là nền tảng BI mã nguồn mở: web server Flask/Gunicorn với giao diện React và REST API; cơ sở dữ liệu metadata (SQLite/PostgreSQL); kết nối **SQLAlchemy** tới hầu hết hệ SQL; bộ nhớ đệm kết quả; tuỳ chọn Celery cho truy vấn bất đồng bộ và báo cáo định kỳ. Khái niệm chính: *Database*, *Dataset* (bảng/view hoặc SQL ảo), *Chart* (chủ yếu Apache ECharts), *Dashboard* (bố cục, tab), *Native filter* và *Cross-filter*. Superset đẩy toàn bộ phép tính xuống cơ sở dữ liệu, nên hiệu năng dashboard phụ thuộc trực tiếp vào tầng phục vụ và cache.

## 2.7. Nguyên tắc thiết kế dashboard

Thiết kế dựa trên nguyên tắc **"overview first, zoom and filter, then details on demand"** của Shneiderman [16] (thẻ KPI → biểu đồ → bộ lọc → bảng chi tiết) và khuyến nghị của Few [17]: xem được trong một màn hình, ưu tiên cột/đường hơn biểu đồ tròn và đồng hồ đo, màu nổi bật chỉ dành cho ngoại lệ. Biểu đồ được chọn theo câu hỏi: xu hướng → đường/cột theo tháng; tập trung 80/20 → Pareto; so sánh địa lý → bản đồ và scatter; xếp hạng → bảng có định dạng điều kiện. Mỗi biểu đồ ghi rõ nguồn (tên view), đơn vị và khoảng thời gian.

## 2.8. Các phương án công nghệ thay thế

Bảng: So sánh công cụ trình bày (BI) cho giai đoạn Presentation
| Tiêu chí | Apache Superset | Power BI | Tableau | Grafana | Metabase |
|---|---|---|---|---|---|
| Giấy phép | Mã nguồn mở (Apache 2.0) | Thương mại (chia sẻ cần Pro) | Thương mại | Mã nguồn mở (AGPL) | Mã nguồn mở / thương mại |
| Triển khai | Docker, tự host | Windows Desktop + cloud | Desktop + Server/Cloud | Docker | Docker |
| Thế mạnh | BI SQL-native, nhiều chart, native filter, REST API | Mô hình DAX, thân thiện | Trực quan hoá linh hoạt | Chuỗi thời gian, giám sát | Dễ dùng |
| Hạn chế | Cấu hình ban đầu phức tạp | Khó tái lập bằng mã | Chi phí bản quyền | Yếu với phân tích theo danh mục | Ít loại biểu đồ, bộ lọc hạn chế |
| Dashboard-as-code | Có (REST API, export YAML) | Hạn chế (.pbix nhị phân) | Hạn chế | Có (JSON) | Một phần |

Bảng: So sánh phương án tầng lưu trữ phục vụ
| Tiêu chí | Neon Serverless Postgres | Postgres cục bộ (Docker) | ClickHouse | Đọc thẳng Parquet (DuckDB) |
|---|---|---|---|---|
| Mô hình lưu trữ | Hàng + chỉ mục | Hàng + chỉ mục | Cột (MergeTree) | Cột (tệp) |
| Phù hợp quy mô | Hàng chục–trăm triệu dòng tổng hợp | Giới hạn một máy | Hàng tỷ dòng chi tiết | Lớn, nhưng không phục vụ đồng thời |
| Chia sẻ cho nhóm/giảng viên | Có, qua Internet + TLS | Không | Cần tự host trên cloud | Phải chia sẻ tệp |
| Vận hành | Được quản lý, autoscaling, scale-to-zero | Tự quản lý | Tự quản lý / trả phí | Không có dịch vụ |
| Tương thích BI | Rất tốt (chuẩn Postgres) | Rất tốt | Tốt (driver riêng) | Trung bình |
