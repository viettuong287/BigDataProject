# 3. Bộ câu hỏi vấn đáp dự kiến và gợi ý trả lời

Mỗi câu ghi kèm người nên trả lời chính (trong ngoặc). Câu trả lời viết theo văn nói, xưng "nhóm em"; nên nói ý chính trước, số liệu sau, và chỉ vào bằng chứng (ảnh, tệp) khi có thể.

## 3.1. Tổng quan và pipeline

Q(Tường): Nhóm em làm phần nào trong pipeline, bắt đầu và kết thúc ở đâu?
A: Dạ, nhóm em làm quy trình con Analytics → Presentation. Đầu vào là 16 bảng Parquet do nhóm Analytics tính trên Spark, kèm 7 bảng gold để lọc chéo, tổng 23 bảng, khoảng 505 nghìn dòng. Nhóm em nạp vào Neon Postgres, xây tầng ngữ nghĩa bằng 22 view SQL và trình bày trên dashboard Superset 7 tab, 45 biểu đồ, 7 bộ lọc. Điểm kết thúc là dashboard cho người dùng nghiệp vụ và view `v_decision_hints` để nhóm Decision/Action đọc bằng SQL. Nhóm em không chạy lại Spark và không sửa số của nhóm Analytics.

Q(Tường): Tóm tắt kiến trúc hệ thống trong 30 giây?
A: Dạ, có bốn khối. Một là Data Lake Parquet. Hai là loader Python chạy trong Docker: đọc Parquet bằng pyarrow, nạp bằng lệnh COPY qua TLS vào Neon. Ba là Neon có ba schema: `analytics` và `gold` là bản sao vật lý, `presentation` là tầng ngữ nghĩa. Bốn là Superset kết nối Neon qua SQLAlchemy, mỗi view là một dataset, dashboard được dựng bằng REST API. Sơ đồ ở `docs/architecture.png`.

Q(Phi Long): Dashboard trả lời những câu hỏi nghiệp vụ nào?
A: Dạ, mỗi tab dành cho một nhóm người dùng. Tab Tổng quan cho ban điều hành: doanh thu tăng thế nào, vận hành có theo kịp không. Tab Danh mục: ngành nào tạo 80% doanh thu, mùa vụ ra sao. Tab Địa lý: bang nào giao chậm, review thấp. Tab Khách hàng: bao nhiêu khách quay lại, nên chăm sóc phân khúc nào. Tab Người bán: ai lớn nhưng vận hành kém. Tab Giao trễ: trễ bao nhiêu ngày thì review sụt. Tab cuối là gợi ý quyết định và nguồn dữ liệu.

Q(Hồng Phong): Kết quả phân tích nổi bật nhất dashboard cho thấy là gì?
A: Dạ, có ba ý. Thứ nhất, bán nhiều không đồng nghĩa vận hành tốt: tháng 11/2017 doanh thu đỉnh 1,0 triệu BRL, tăng 52% so với tháng trước, nhưng tỷ lệ trễ lên 14,3% và review rơi còn 3,95. Thứ hai, giao trễ làm review giảm từ 4,29 xuống 2,56 sao, trễ từ 4 ngày trở lên thì đa số khách cho 1 sao. Thứ ba, 97% khách chỉ mua một lần, chỉ 3,04% quay lại, nên CRM phải tập trung vào nhóm nhỏ đó.

## 3.2. Vì sao là Big Data?

Q(Cả nhóm): Tầng của nhóm chỉ có khoảng 500 nghìn dòng, vậy đây có phải Big Data thật không?
A: Dạ, nhóm em xin trả lời thẳng là ở tầng Presentation dữ liệu không còn lớn, và đó là thiết kế đúng của pipeline: khối lượng giảm dần qua từng tầng, từ khoảng 1,55 triệu dòng thô xuống các bảng đã tổng hợp. Phần xử lý phân tán nặng nằm ở Spark của nhóm trước, nhóm em có ảnh Spark UI trong báo cáo. Bài toán của tầng phục vụ là khác: nhiều người dùng đồng thời, độ trễ tương tác, tải không đều, giữ đúng ngữ nghĩa số liệu. Nhóm em chứng minh khả năng mở rộng bằng thí nghiệm nhân dữ liệu lên 10 lần: truy vấn trên dữ liệu thô tăng từ 47 lên 507 ms, còn view đã tổng hợp giữ 1,1 ms. Nghĩa là kiến trúc giữ nguyên khi dữ liệu nguồn lớn lên.

Q(Hồng Phong): Bài toán thể hiện những đặc trưng V nào?
A: Dạ, nhóm em chọn bốn. Volume: nguồn 1,55 triệu dòng, và thí nghiệm đã chạy tới 1,12 triệu dòng trên Neon. Variety: 23 bảng với hơn 10 grain khác nhau, nhiều kiểu dữ liệu, có fact phân vùng theo tháng. Veracity: có cờ chất lượng `dq_*`, tháng thiếu dữ liệu, `customer_id` không phải khách thật, nên nhóm em kiểm 19 số neo. Value: kết quả thành luật quyết định, ví dụ 75 người bán mức cảnh báo đỏ.

Q(Tường): Tại sao không dùng Spark cho tầng Presentation?
A: Dạ, vì Spark là hệ xử lý theo lô, mỗi job tốn hàng chục giây để khởi động và lập kế hoạch, không hợp để trả lời từng cú nhấp của người dùng trong vài trăm mili giây. Phần tính nặng đã được Spark làm xong ở nhóm Analytics; tầng của nhóm em chỉ cần đọc, lọc và cộng lại trên bảng đã cô đọng, việc mà Postgres có chỉ mục làm trong khoảng 1 ms phía server. Đây đúng là mô hình batch layer và serving layer trong kiến trúc Lambda. Ngoài ra, đọc Parquet bằng pyarrow trong loader cũng không cần cụm Spark.

Q(Cả nhóm): Nếu dữ liệu tăng 100 lần thì sao?
A: Dạ, các bảng theo tháng, danh mục, bang gần như không đổi vì số tháng và số danh mục cố định; chỉ bảng cấp khách hàng, người bán và gold tăng tuyến tính. Thí nghiệm ×10 cho thấy truy vấn thô tăng gần tuyến tính còn view tổng hợp không đổi, nên ở ×100 nhóm em sẽ không cho dashboard truy vấn fact thô nữa mà chuyển lớp gold thành bảng tổng hợp nhẹ hoặc materialized view. Neon có thể tăng compute và thêm read replica; Superset mở rộng ngang với Celery và Redis. Nếu cần lọc chéo tự do trên hàng tỷ dòng chi tiết thì chuyển tầng phục vụ sang kho OLAP cột như ClickHouse hoặc Trino; vì tầng ngữ nghĩa là SQL chuẩn nên chủ yếu chỉ phải chuyển view, dashboard giữ nguyên.

## 3.3. Neon Postgres

Q(Tường): Neon "serverless" nghĩa là gì, khác Postgres thường thế nào?
A: Dạ, Neon tách compute và storage. Compute là tiến trình Postgres không giữ dữ liệu, có thể tự tăng giảm hoặc tắt hẳn khi không dùng; storage gồm safekeeper nhận WAL, pageserver dựng lại trang dữ liệu và object storage lưu lâu dài. Vì vậy dữ liệu luôn an toàn dù compute ngủ. Với dashboard, tải rất không đều nên không ai xem thì không tốn compute. Project của nhóm em ở vùng Singapore, PostgreSQL 18, gói miễn phí 0,25 CU.

Q(Tường): Endpoint pooled và direct khác nhau thế nào, nhóm dùng cái nào?
A: Dạ, endpoint pooled có chữ `-pooler` trong hostname, đi qua PgBouncer chế độ transaction, chịu được rất nhiều kết nối ngắn nên Superset và script đo độ trễ dùng nó. Endpoint direct nối thẳng Postgres, giữ phiên ổn định, phù hợp cho DDL và COPY dài; loader tự bỏ `-pooler` để dùng direct. Nếu cho COPY đi qua PgBouncer chế độ transaction thì dễ gặp lỗi vì trạng thái phiên không được giữ.

Q(Tường): Scale-to-zero ảnh hưởng gì đến người dùng? Có đo cold start không?
A: Dạ, khi không có truy vấn một thời gian, compute tạm dừng, truy vấn đầu tiên phải chờ đánh thức. Nhóm em chưa đo tách riêng thời gian đánh thức compute; tài liệu Neon cho biết cỡ vài trăm mili giây. Cái nhóm em đo được là thời gian mở dashboard khi đã xoá cache: trung vị 3,83 giây một tab, trong đó phần lớn do mỗi biểu đồ mở kết nối TLS mới mất khoảng 1,1 giây, chứ không phải do compute. Có cache thì còn 1,51 giây.

Q(Cả nhóm): Sao không dùng Postgres cài trên máy, ClickHouse hay BigQuery?
A: Dạ, Postgres trên máy thì nhanh nhưng dữ liệu nằm trên laptop một bạn, không chia sẻ được cho nhóm, thầy và nhóm Decision. ClickHouse mạnh với hàng tỷ dòng chi tiết, nhưng với nửa triệu dòng đã tổng hợp thì không thấy lợi thế mà lại thêm việc vận hành. BigQuery hay Snowflake tính phí theo truy vấn, cần thẻ thanh toán và khoá vào một nhà cung cấp. Neon cho Postgres chuẩn, miễn phí ở quy mô đồ án, có TLS, mọi công cụ đều kết nối được. Bảng so sánh ở Phụ lục B báo cáo.

Q(Tường): Loader nạp dữ liệu thế nào, chạy lại có bị trùng không?
A: Dạ, loader đọc mỗi bảng bằng `pyarrow.dataset`, đọc được cả thư mục phân vùng Hive, tự sinh câu `CREATE TABLE` từ schema Parquet, chuyển thành CSV trong RAM rồi `COPY FROM STDIN` theo khối 1 MiB. DROP, CREATE và COPY nằm trong một giao dịch nên người dùng chỉ thấy bản cũ hoặc bản mới hoàn chỉnh. Sau đó tạo khoá chính, chỉ mục, ANALYZE, đếm dòng so với Parquet và ghi `analytics.load_log`. Chạy lại bao nhiêu lần cũng ra cùng trạng thái, không trùng dữ liệu.

Q(Tường): Vì sao tiền dùng NUMERIC chứ không dùng float?
A: Dạ, vì số neo doanh thu 13.494.400,74 BRL phải khớp đến từng xu. Kiểu số thực dấu phẩy động cộng hàng chục nghìn giá trị sẽ có sai số làm tròn. Parquet lưu decimal nên nhóm em ánh xạ sang `NUMERIC(p,s)`; kiểm tra số neo cho thấy tổng trên Neon bằng đúng số của Spark.

## 3.4. Superset và dashboard

Q(Phi Long): Vì sao chọn Superset mà không dùng Power BI, Tableau, Grafana hay Metabase?
A: Dạ, Power BI và Tableau là phần mềm thương mại, tệp dashboard nhị phân khó quản lý phiên bản, chia sẻ cần tài khoản trả phí, Power BI Desktop chỉ chạy trên Windows. Grafana mạnh về chuỗi thời gian giám sát nhưng yếu với Pareto, bảng xếp hạng. Metabase dễ dùng nhưng ít loại biểu đồ và bộ lọc hạn chế. Superset mã nguồn mở, chạy bằng Docker, kết nối thẳng Postgres, có bản đồ Brazil, và quan trọng nhất là có REST API để dựng dashboard bằng mã, giúp người khác dựng lại giống hệt.

Q(Phi Long): Tầng ngữ nghĩa là gì, sao không để Superset tự tính?
A: Dạ, tầng ngữ nghĩa là nơi định nghĩa KPI một lần, ở đây là 22 view trong schema `presentation`. Nếu mỗi biểu đồ tự viết SQL thì dễ ra mỗi nơi một số. Đặt trong view thì Superset và nhóm Decision đọc cùng một định nghĩa, có quản lý phiên bản bằng Git. View cũng thêm cột phục vụ trình bày như `month_date` cho bộ lọc thời gian, mã ISO `BR-SP` cho bản đồ, nhãn tiếng Việt, và mã hoá luật cảnh báo.

Q(Phi Long): Tỷ lệ trễ khi lọc nhiều tháng tính thế nào cho đúng?
A: Dạ, đây là độ đo không cộng dồn. Bảng `kpi_monthly` chỉ có tỷ lệ theo tháng, nếu lấy trung bình các tỷ lệ thì sai. Nhóm em làm view cấp đơn `v_orders` từ gold, cột `late_flag` bằng 1 khi trễ, 0 khi đúng hạn, NULL khi chưa giao; `AVG(late_flag)` chính là tỷ lệ trễ đúng định nghĩa với mọi tổ hợp bộ lọc. AOV cũng tính bằng tổng giá trị đơn chia số đơn chứ không lấy trung bình của AOV tháng.

Q(Phi Long): Bộ lọc native hoạt động thế nào, có lọc được mọi biểu đồ không?
A: Dạ, có 7 bộ lọc: khoảng thời gian, bang khách hàng, vùng, danh mục, phân khúc RFM, phương thức thanh toán, bang người bán. Mỗi bộ lọc chỉ gắn vào biểu đồ có cột tương ứng, phạm vi do script tính tự động. Các kết quả phân tích toàn kỳ như Pareto hay K-Means thì không lọc theo tháng được vì đó là kết quả Spark đã chốt, lọc lại sẽ sai nghĩa. Nhóm em kiểm 6 kịch bản lọc, cả 6 đúng; ví dụ lọc năm 2018 và bang SP thì doanh thu từ 13,45 triệu còn 2,96 triệu BRL.

Q(Phi Long): Cache của Superset để làm gì? Metadata lưu ở đâu?
A: Dạ, Superset lưu kết quả truy vấn 600 giây, lần mở lại không phải hỏi Neon: một biểu đồ từ 1.558 ms còn 67 ms, nhanh khoảng 23 lần. Metadata gồm người dùng, biểu đồ, dashboard lưu trong container Postgres 16 riêng. Ban đầu nhóm em dùng SQLite nhưng SQLite khoá ghi toàn cục làm các biểu đồ tải song song phải xếp hàng, nên chuyển sang Postgres và chạy 4 worker.

Q(Phi Long): Nếu xoá container Superset thì dashboard có mất không?
A: Dạ, không mất vì dashboard được dựng bằng mã. Chạy `build_dashboard.py` là tạo lại database, 22 dataset, 45 biểu đồ, 7 tab và 7 bộ lọc; script idempotent nên chạy lại chỉ cập nhật. Dự phòng thêm có tệp ZIP export và `import_dashboard.py`. Dữ liệu nghiệp vụ nằm trên Neon nên cũng không bị ảnh hưởng.

Q(Phi Long): Giao diện tiếng Việt và theme Olist Insight làm thế nào?
A: Dạ, Superset 4.1.2 không có sẵn tiếng Việt nên nhóm em viết bản dịch riêng khoảng 536 chuỗi hay gặp, biên dịch khi build image. Phiên mới mặc định tiếng Việt, vẫn đổi được sang English bằng cờ, và trang tải lại đúng tab, bộ lọc đang mở. Theme dùng logo, màu chàm và xanh ngọc, font Be Vietnam Pro đồng bộ với landing page. Giới hạn là một số màn hình như SQL Lab và màn hình sửa biểu đồ còn tiếng Anh, và Superset 4.1 chưa có dark mode thật cho biểu đồ.

## 3.5. Data contract và kiểm chứng

Q(Tường): Data contract giữa hai nhóm gồm những gì?
A: Dạ, gồm danh sách bảng, grain tức một dòng là gì, khoá, kiểu dữ liệu, ngữ nghĩa từng độ đo, khung thời gian 2017-01 đến 2018-08, và các số neo để đối chiếu. Thêm cột thì loader tự xử lý; đổi tên hay xoá cột là thay đổi phá vỡ phải báo trước. Mỗi bảng trên Neon có COMMENT ghi grain và nguồn. Chi tiết ở mục 3.5 và Phụ lục C báo cáo.

Q(Hồng Phong): Làm sao chứng minh số trên dashboard đúng?
A: Dạ, script `validate.py` kiểm hai lớp. Một là đọc lại từng thư mục Parquet và so với `COUNT(*)` trên Postgres: 23/23 bảng khớp. Hai là chạy 19 truy vấn số neo: tổng doanh thu 13.494.400,74 BRL, tháng đỉnh 2017-11 tăng 52,06%, review 2,56 và 4,29, 2.887 khách mua lại, 153 người bán watchlist — 19/19 đạt. Có cả kiểm tra nhất quán chéo: tổng từ lớp gold bằng đúng tổng của bảng Analytics, chênh lệch 0,00. QA còn đọc trực tiếp dữ liệu trả về của biểu đồ sau khi lọc.

Q(Hồng Phong): Sao tổng doanh thu trên thẻ KPI là 13,45 triệu mà số neo là 13,49 triệu?
A: Dạ, cả hai đều đúng nhưng trả lời hai câu hỏi khác nhau. 13.494.400,74 BRL là doanh thu gold toàn kỳ, kể cả các tháng 2016 và 09/2018 thiếu dữ liệu. Thẻ KPI dùng khung chuẩn 2017-01 đến 2018-08 theo quy tắc bàn giao nên ra 13.449.530 BRL. Thẻ có ghi rõ khung thời gian để người dùng không hiểu nhầm.

Q(Phi Long): Nạp thêm 7 bảng gold có làm "hai sự thật" không?
A: Dạ, nhóm em lo điều đó nên chỉ dùng gold để lọc và cộng lại, còn mọi phân tích như Pareto, RFM, K-Means vẫn lấy nguyên của Analytics. Kiểm tra nhất quán chéo cho thấy tổng doanh thu và số đơn từ `v_orders`, `v_sales_items` bằng đúng tổng của `kpi_monthly`. Nên không có hai con số mâu thuẫn.

## 3.6. Hiệu năng và cách đo

Q(Hồng Phong): Nạp dữ liệu mất bao lâu? Nút thắt ở đâu?
A: Dạ, lần nạp ngày 13/11 nạp 23 bảng, 505.592 dòng, tổng thời gian các bảng 277,8 giây, log tính cả chi phí khởi tạo là 284,7 giây; riêng 16 bảng Analytics mất 66 giây. Pha COPY đạt khoảng 1.972 dòng mỗi giây. Nút thắt là băng thông tải lên từ máy nhà tới Singapore, khoảng 0,42 MB/s, vì CSV gửi đi lớn hơn Parquet khoảng 2,5 lần; ngoài ra mỗi bảng nhỏ tốn khoảng 1–2 giây cho nhiều vòng khứ hồi mạng. Muốn nhanh thì chạy loader cùng vùng với Neon.

Q(Hồng Phong): Độ trễ truy vấn đo thế nào, kết quả ra sao?
A: Dạ, script `measure_latency.py` chạy đúng 21 truy vấn mà các biểu đồ sinh ra, qua endpoint pooled giống Superset, mỗi truy vấn 5 lần sau một lần làm nóng, đo cả phía client và thời gian thực thi phía server bằng EXPLAIN ANALYZE. Trung vị phía client 173 ms nhưng phía server chỉ 1,25 ms; riêng một vòng khứ hồi `SELECT 1` đã 105 ms. Kết luận là mạng chiếm gần hết độ trễ, không phải cơ sở dữ liệu.

Q(Hồng Phong): Mở dashboard mất bao lâu? Vì sao có tab trên 5 giây?
A: Dạ, đo bằng Playwright ngày 13/11: xoá cache rồi mở 7 tab, trung vị 3,83 giây một tab; mở lại khi có cache trung vị 1,51 giây. Có 3/7 tab vượt 5 giây khi cold, chậm nhất là tab Khách hàng & RFM 6,38 giây. Lý do là Superset dùng NullPool, mỗi biểu đồ mở kết nối TLS mới tới Singapore khoảng 1,1 giây và các biểu đồ xếp hàng chờ, chứ truy vấn chỉ khoảng 1 ms. Nhóm em ghi rõ tiêu chí này chưa đạt và đề xuất bật pool kết nối, đặt Superset cùng vùng hoặc làm nóng cache định kỳ.

Q(Hồng Phong): Tại sao đo cache nhanh hơn 23 lần mà tab chỉ nhanh khoảng 2,5 lần?
A: Dạ, con số 23 lần là cho từng biểu đồ qua API: 1.558 ms xuống 67 ms. Thời gian mở một tab còn gồm trình duyệt vẽ biểu đồ ECharts, tải khung trang và chờ biểu đồ chậm nhất trong tab, các phần này cache không rút ngắn được. Vì vậy tab giảm từ 3,83 xuống 1,51 giây.

## 3.7. Khả năng mở rộng (thí nghiệm ×10)

Q(Hồng Phong): Thí nghiệm mở rộng làm thế nào?
A: Dạ, script `scale_experiment.py` nhân bản bảng `gold.fact_order_items` lên 1, 2, 5, 10 lần ngay trên Neon bằng `generate_series`, tới 1,12 triệu dòng, 117,7 MB; sinh dữ liệu khoảng 1 triệu dòng mỗi giây phía server. Với mỗi hệ số, đo ba kiểu truy vấn bằng EXPLAIN ANALYZE, lấy trung vị 3 lần. Xong thì xoá bảng tạm để không vượt giới hạn 1 GiB của gói miễn phí.

Q(Hồng Phong): Kết quả thí nghiệm nói lên điều gì?
A: Dạ, truy vấn tổng hợp tháng × danh mục trên dữ liệu thô tăng gần tuyến tính từ 47 lên 507 ms. Truy vấn có lọc dùng chỉ mục tăng chậm hơn nhiều, từ 2,5 lên 18,5 ms. Còn đọc view đã tổng hợp ở Spark giữ 1,1 ms ở mọi hệ số. Điều này chứng minh thiết kế: tầng Presentation đọc kết quả đã cô đọng nên độ trễ dashboard không tăng theo dữ liệu nguồn; phần tăng được đẩy về Spark vốn mở rộng ngang được.

Q(Tường): Thí nghiệm chỉ tới ×10, vậy có đủ thuyết phục không?
A: Dạ, nhóm em dừng ở ×10 vì gói miễn phí giới hạn 1 GiB mỗi nhánh và compute 0,25 CU. Xu hướng tuyến tính đã rõ qua bốn điểm đo nên có thể ngoại suy, nhưng nhóm em không khẳng định con số chính xác ở ×100. Điều nhóm em khẳng định là đường của view tổng hợp nằm ngang. Với tải thật lớn hơn, cần nâng compute và kiểm chứng lại.

## 3.8. Hạn chế và trung thực

Q(Cả nhóm): Hạn chế lớn nhất của hệ thống là gì?
A: Dạ, có bốn điểm. Một, mở dashboard lần đầu chậm: 3/7 tab cold trên 5 giây do Superset mở kết nối mới cho mỗi biểu đồ. Hai, phụ thuộc mạng Việt Nam – Singapore, cả nạp lẫn truy vấn. Ba, chỉ chạy theo lô, nạp lại toàn bộ, chưa có streaming hay nạp tăng dần. Bốn, gói Neon miễn phí 0,25 CU nên chưa kiểm chứng autoscaling và tải hàng nghìn người dùng.

Q(Tường): Có ảnh chụp Neon Console không?
A: Dạ, không ạ. Neon Console cần đăng nhập tương tác nên nhóm em không chụp tự động được. Thay vào đó, ảnh kiểm kê được sinh từ truy vấn catalog trực tiếp trên database: 25 bảng, 22 view, số dòng, dung lượng 146 MB; thông tin project như vùng, phiên bản, 0,25 CU lấy qua Neon API và lưu ở `neon_project.json`.

Q(Phi Long): Bảng giá trên landing page có thật không?
A: Dạ, không ạ, đó là bảng giá minh hoạ cho kịch bản thương mại hoá, trên trang có ghi rõ. Bản đồ án chạy hoàn toàn trên gói miễn phí của Neon và phần mềm mã nguồn mở.

Q(Phi Long): Superset có chỗ nào chưa Việt hoá hoặc chưa đẹp?
A: Dạ có. Bản dịch 536 chuỗi phủ các màn hình hay dùng, nhưng SQL Lab, màn hình sửa biểu đồ và trang quản trị còn nhiều chữ tiếng Anh; các giá trị dữ liệu như tên danh mục hay "Champions", "At Risk" giữ nguyên gốc. Superset 4.1 chưa có dark mode thật cho biểu đồ, nên thẻ biểu đồ để nền sáng cho dễ đọc. Đây là giới hạn của phiên bản, nhóm em ghi trong README.

## 3.9. Gợi ý quyết định, landing page và tái lập

Q(Phi Long): "Gợi ý quyết định" gồm những gì, nhóm Decision dùng thế nào?
A: Dạ, view `v_decision_hints` có 7 luật, mỗi dòng gồm mức ưu tiên, mức độ, tín hiệu, giá trị hiện tại, ngưỡng và hành động đề xuất. Ví dụ luật 1: 75/153 người bán top doanh thu vi phạm từ hai tiêu chí trở lên thì cảnh cáo, giảm hiển thị, yêu cầu kế hoạch SLA 30 ngày; luật 2: đơn trễ kéo review từ 4,29 xuống 2,56 thì cảnh báo người bán khi đơn trễ 1–3 ngày. Nhóm Decision chỉ cần một câu SELECT để lấy, rồi chuyển thành email hay Telegram. Giá trị tính lại mỗi lần truy vấn nên luật tự cập nhật khi nạp dữ liệu mới.

Q(Hồng Phong): Landing page có vai trò gì trong đồ án?
A: Dạ, landing page ở cổng 8090 là trang giới thiệu hệ thống cho người xem lần đầu: biểu đồ phát lại doanh thu 20 tháng, thẻ KPI, insight, pipeline và huy hiệu kiểm chứng 19/19 số neo. Số liệu là số thật xuất từ Neon bằng `export_landing_kpi.py` thành `kpi.json`; trang tĩnh nên không giữ thông tin kết nối cơ sở dữ liệu. Logo trên Superset dẫn về landing và nút trên landing mở đúng dashboard. Nó không thay thế dashboard, chỉ là cửa vào.

Q(Tường): Người khác muốn chạy lại hệ thống thì làm thế nào?
A: Dạ, chỉ cần Docker, Git và một database Neon. Clone repo, chép `.env.example` thành `.env` và điền chuỗi kết nối; rồi chạy `docker compose run --rm tools python loader/load_to_neon.py` để nạp, `validate.py` để kiểm, `docker compose up -d superset-db superset` và `build_dashboard.py` để dựng dashboard. Dữ liệu Parquet đã có sẵn trong repo. QA đã kiểm mọi lệnh trong README đều chạy được và `docker compose config` hợp lệ.

Q(Hồng Phong): Kiểm thử QA gồm những gì?
A: Dạ, script `qa_check.py` dùng Playwright chạy 41 ca tự động: đăng nhập đúng, sai mật khẩu; 7 tab ở hai độ rộng 1440 và 1280 px kiểm biểu đồ lỗi, lỗi console, thẻ KPI chồng chữ; 6 kịch bản lọc kiểm giá trị trả về; xoá lọc; đổi ngôn ngữ giữ nguyên trang; link logo và landing; xuất nhập ZIP; lệnh README. Kết quả 41/41 PASS, chi tiết trong `qa_test_cases.md`.

## 3.10. Câu hỏi theo từng thành viên

Q(Tường): Em phụ trách phần nào, khó nhất là gì?
A: Dạ, em là nhóm trưởng, phụ trách kiến trúc, Neon, loader, Docker Compose và tích hợp, quản lý repo GitHub. Khó nhất là nạp đúng kiểu dữ liệu: tiền phải là NUMERIC, timestamp phải ép từ nano về micro giây, chuỗi rỗng phải phân biệt với NULL, và bảng fact phân vùng phải đọc được cột năm, tháng từ tên thư mục. Em xử lý bằng cách sinh DDL từ schema Parquet và kiểm 23/23 số dòng sau mỗi lần nạp.

Q(Tường): Nếu loader chết giữa chừng thì dữ liệu có hỏng không?
A: Dạ, không ạ. Mỗi bảng nạp trong một giao dịch, lỗi thì rollback, bảng cũ vẫn nguyên. Chạy lại loader thì nạp lại từ đầu và ra cùng trạng thái. Nếu số dòng lệch, chương trình thoát với mã lỗi để không âm thầm đi tiếp.

Q(Phi Long): Em phụ trách phần nào? Cho ví dụ một view em viết.
A: Dạ, em phụ trách tầng ngữ nghĩa và dashboard. Ví dụ `v_seller_watchlist`: mỗi tiêu chí review dưới 4, giao trên 15 ngày, trễ trên 10% thành một cờ 0/1; cộng lại thành số vi phạm; ghép thành chuỗi lý do; từ hai vi phạm trở lên là mức ĐỎ kèm hành động "cảnh cáo, giảm hiển thị". Kết quả có 75 người bán mức ĐỎ trên 153. Dashboard thì em dựng bằng `build_dashboard.py` qua REST API, gồm 7 tab, 45 biểu đồ và 7 bộ lọc.

Q(Phi Long): Vì sao bản đồ Brazil cần bảng `dim_state`?
A: Dạ, biểu đồ Country Map của Superset nhận diện bang theo mã ISO 3166-2 dạng `BR-SP`, còn dữ liệu chỉ có `SP`. Bảng `dim_state` 27 dòng thêm tên bang, vùng và mã ISO; nhờ cột vùng mới có bộ lọc Vùng, ví dụ lọc Nordeste còn đúng 9 bang.

Q(Hồng Phong): Em phụ trách phần nào? Số liệu em đo có tin được không?
A: Dạ, em phụ trách thực nghiệm, minh chứng, QA và báo cáo. Mọi số đo đều do script sinh ra và lưu thành tệp trong `evidence/`, có ghi thời điểm đo, cách đo, số lần lặp; người khác chạy lại cùng lệnh sẽ ra số cùng bậc, chỉ dao động theo đường truyền. Ví dụ lần đo trước tab cold trung vị 6,64 giây, lần đo 13/11 là 3,83 giây; em ghi cả hai và giải thích dao động chủ yếu do mạng.

## 3.11. Câu hỏi "bẫy"

Q(Cả nhóm): AI làm hết phải không?
A: Dạ, không ạ. Nhóm em có dùng trợ lý AI trong Cursor để gợi ý khung mã, SQL và bản nháp báo cáo, và đã ghi rõ trong Phụ lục H. Nhưng nhóm em tự chạy toàn bộ hệ thống, sửa lỗi thực tế như SQLite khoá ghi, kết nối pooled và direct, đối chiếu mọi số với tệp trong `evidence/`. Các quyết định chọn Neon, Superset, thiết kế schema, định nghĩa KPI và luật là của nhóm. Thầy có thể hỏi bất kỳ phần nào, mỗi bạn giải thích được phần mình làm.

Q(Cả nhóm): Dashboard này khác gì làm bằng Excel?
A: Dạ, khác ở ba điểm. Dữ liệu nằm trên cơ sở dữ liệu dùng chung, nhiều người truy cập đồng thời và luôn cùng một phiên bản số. Định nghĩa KPI nằm trong view có kiểm chứng tự động, không phụ thuộc thao tác tay. Và toàn bộ dựng lại được bằng script, mở rộng được khi dữ liệu lớn lên, điều mà Excel không làm được ở quy mô hàng trăm nghìn tới hàng triệu dòng.

Q(Tường): Có xử lý thời gian thực (streaming) không?
A: Dạ, không ạ. Dữ liệu Olist là dữ liệu lịch sử và nhóm Analytics bàn giao theo lô, nên hệ thống của nhóm em là batch: mỗi lần Analytics chạy lại thì nạp lại. Loader idempotent nên có thể chạy theo lịch, ví dụ mỗi giờ. Nếu cần gần thời gian thực thì phải có nguồn streaming ở các tầng trước và nạp tăng dần, đó là hướng phát triển.

Q(Tường): Dữ liệu trên Neon có an toàn không, mật khẩu để ở đâu?
A: Dạ, kết nối bắt buộc TLS với `sslmode=require`. Chuỗi kết nối và mật khẩu chỉ nằm trong tệp `.env`, tệp này nằm trong `.gitignore` nên không lên GitHub; repo chỉ có `.env.example`. Loader che mật khẩu khi ghi log, và landing page chỉ đọc tệp `kpi.json` tĩnh nên không lộ thông tin kết nối.

Q(Hồng Phong): Nếu Neon hoặc Docker hỏng lúc bảo vệ thì sao?
A: Dạ, nhóm em đã chuẩn bị phương án dự phòng: toàn bộ ảnh chụp 7 tab, 6 bộ lọc, watchlist và landing page có trong `evidence/`, cùng bản PDF báo cáo và các tệp số liệu. Nhóm em sẽ trình bày bằng ảnh và log, và có thể chạy lại phần kiểm chứng sau nếu thầy cần.

Q(Phi Long): Tại sao 97% khách chỉ mua một lần mà vẫn làm phân khúc RFM?
A: Dạ, chính vì vậy nên nhóm Analytics tách luật: chỉ khách mua từ hai lần mới được gọi Champions, Loyal hay At Risk, khách mua một lần chia theo độ mới. Dashboard cho thấy CRM nên tập trung vào 2.887 khách mua lại, đặc biệt 1.961 khách At Risk, thay vì gửi khuyến mãi cho 65 nghìn khách mua một lần đã lâu. K-Means cũng tự tách đúng 2.887 khách mua lại thành một cụm, xác nhận tần suất là trục phân biệt thật.
