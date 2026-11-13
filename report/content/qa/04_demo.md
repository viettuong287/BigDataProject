# 4. Kịch bản demo 5–7 phút

## 4.1. Chuẩn bị trước buổi bảo vệ (30 phút trước)

1. Bật Docker Desktop, chạy `docker compose up -d superset-db superset web` và chờ trạng thái `healthy` (`docker compose ps`).
2. Đánh thức Neon và làm nóng cache: đăng nhập `http://localhost:8088`, mở dashboard `olist-presentation`, bấm lần lượt 7 tab (lần mở đầu tab chậm 3–6 s, các lần sau ~1,5 s).
3. Mở sẵn các tab trình duyệt: landing `http://localhost:8090`, dashboard (tab 1), thư mục `evidence/`, `report/BaoCao_DoAn_BigData.pdf`, và một cửa sổ PowerShell ở thư mục repo.
4. Kiểm nhanh: `docker compose run --rm tools python loader/validate.py` phải ra 23/23 bảng và 19/19 số neo (chạy trước, không chạy lúc demo vì cần thời gian).
5. Chuẩn bị bản dự phòng: ảnh trong `evidence/`, PDF báo cáo, tài liệu này in sẵn.

## 4.2. Kịch bản từng bước

Bảng: Kịch bản demo (tổng khoảng 6 phút)
| Thời gian | Người | Thao tác | Lời nói gợi ý |
|---|---|---|---|
| 0:00–0:45 | Tường | Mở `docs/architecture.png` (hoặc Hình 4.1 trong PDF) | "Nhóm em làm Analytics → Presentation: nhận 23 bảng Parquet, nạp vào Neon bằng COPY, 22 view ngữ nghĩa, Superset 7 tab, và view gợi ý quyết định cho nhóm Decision." |
| 0:45–1:30 | Tường | Mở `evidence/load_run.log` và `validation.md` | "Lần nạp 13/11: 23 bảng, 505.592 dòng, 23/23 khớp số dòng; 19/19 số neo, ví dụ doanh thu 13.494.400,74 BRL khớp tới từng xu." |
| 1:30–2:00 | Hồng Phong | Mở landing `:8090`, cho xem biểu đồ phát lại và huy hiệu kiểm chứng; bấm "Mở dashboard" | "Landing là cửa vào, số liệu thật xuất từ Neon; nút này mở đúng dashboard." |
| 2:00–3:00 | Phi Long | Dashboard tab 1: chỉ 6 thẻ KPI, cột tháng 11/2017, đường % trễ vs review | "Tháng 11/2017 doanh thu đỉnh, tăng 52% nhưng trễ lên 14% và review rơi còn 3,95 — bán nhiều không đồng nghĩa vận hành tốt." |
| 3:00–3:45 | Phi Long | Thanh bộ lọc: Khoảng thời gian = 2018, Bang khách hàng = SP → Áp dụng | "Thẻ doanh thu từ 13,45 triệu còn 2,96 triệu; bảng KPI chỉ còn 8 tháng 2018. Bộ lọc chỉ gắn vào biểu đồ có cột tương ứng." Sau đó bấm "Xoá tất cả". |
| 3:45–4:30 | Phi Long | Tab 3 Địa lý (bản đồ Brazil, bubble) rồi tab 6 Giao trễ | "SP giao 8,7 ngày, review 4,21; các bang xa giao 15–19 ngày, review dưới 4. Trễ từ 4 ngày trở lên đa số khách cho 1 sao." |
| 4:30–5:15 | Phi Long | Tab 5 Người bán → bảng watchlist; tab 7 → bảng gợi ý quyết định | "153 người bán cần theo dõi, 75 mức đỏ kèm lý do và hành động; tab 7 là 7 luật mà nhóm Decision đọc bằng một câu SQL." |
| 5:15–6:00 | Hồng Phong | Mở `dashboard_load_latency.md`, `query_latency.md`, `scale_experiment.md` | "Truy vấn chỉ 1,25 ms phía server, 173 ms phía client do mạng; tab cold 3,83 s, có cache 1,51 s. Dữ liệu ×10 thì truy vấn thô 47 → 507 ms còn view tổng hợp giữ 1,1 ms." |
| 6:00–6:30 | Hồng Phong | Mở `qa_test_cases.md` | "41/41 ca kiểm thử tự động PASS; mọi lệnh trong README chạy được, người khác dựng lại bằng Docker Compose." |

Nếu thầy yêu cầu chứng minh tái lập tại chỗ: chạy `docker compose run --rm tools python loader/apply_sql.py` (tạo lại 22 view trong vài giây) rồi tải lại dashboard; không chạy nạp lại toàn bộ (mất ~5 phút).

## 4.3. Phương án dự phòng

Bảng: Xử lý sự cố khi demo
| Sự cố | Dấu hiệu | Cách xử lý |
|---|---|---|
| Docker Desktop không chạy / Superset không lên | `docker compose ps` không healthy, trang 8088 không mở | Chuyển sang ảnh: `evidence/dashboard_tab1…7_*.png`, `filter_*.png`, `watchlist_*.png`, `superset_giao_dien_dong_bo_*.png`; trình bày theo đúng thứ tự kịch bản trên |
| Neon chậm hoặc mất mạng | Biểu đồ quay lâu, báo lỗi kết nối | Nếu cache đã làm nóng thì dashboard vẫn hiện trong 10 phút; nếu không, dùng ảnh và nói rõ "dữ liệu trên Neon Singapore, đang mất kết nối" |
| Biểu đồ đầu tiên chậm 3–6 s | Spinner lâu ở lần mở đầu | Giải thích ngay: mỗi biểu đồ mở kết nối TLS mới (~1,1 s), không phải truy vấn chậm; mở lại tab sẽ ~1,5 s |
| Máy chiếu không mở được trình duyệt | — | Mở `report/BaoCao_DoAn_BigData.pdf`: Hình 4.1 (kiến trúc), chương 6 (số đo), chương 7 (ảnh dashboard) |
| Bộ lọc bị ghi đè sau khi chạy lại `build_dashboard.py` | Bộ lọc không như mong đợi | Tải lại trang (Superset 4.1 lưu trạng thái của tab trình duyệt cũ) |

## 4.4. Lưu ý khi trả lời

- Nói số tròn trước rồi số chính xác; luôn kèm nguồn ("trong `validation.md`", "Hình 4.1").
- Điều chưa làm thì nói thẳng là chưa làm và nêu hướng làm (streaming, autoscaling nhiều CU, đo riêng cold start compute, Neon Console screenshot).
- Phân vai trả lời theo mục 3.10: Tường – Neon, loader, tích hợp; Phi Long – view SQL, dashboard, bộ lọc; Hồng Phong – thực nghiệm, QA, báo cáo. Câu hỏi chung thì nhóm trưởng mở đầu, thành viên liên quan bổ sung.
