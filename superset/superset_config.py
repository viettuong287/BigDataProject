"""Cấu hình Superset cho môi trường demo cục bộ (docker compose)."""
import os

SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "change-me-in-.env")

# Metadata (dashboard, chart, user, log) nằm trong container superset-db (Postgres cục bộ).
# SQLite chỉ là phương án dự phòng: nó khoá ghi toàn cục nên các chart tải song song bị xếp hàng.
# Dữ liệu nghiệp vụ nằm ở Neon Postgres, đăng ký qua REST API (superset/build_dashboard.py).
SQLALCHEMY_DATABASE_URI = os.environ.get(
    "SUPERSET_METADATA_URI", "sqlite:////app/superset_home/superset.db?check_same_thread=false"
)

FEATURE_FLAGS = {
    "DASHBOARD_NATIVE_FILTERS": True,
    "DASHBOARD_CROSS_FILTERS": True,
    "ENABLE_TEMPLATE_PROCESSING": True,
}

# Cache kết quả truy vấn chart 10 phút: lần mở dashboard thứ 2 không phải hỏi lại Neon.
DATA_CACHE_CONFIG = {
    "CACHE_TYPE": "FileSystemCache",
    "CACHE_DIR": "/app/superset_home/cache",
    "CACHE_DEFAULT_TIMEOUT": 600,
}

TALISMAN_ENABLED = False
WTF_CSRF_TIME_LIMIT = None
ROW_LIMIT = 50000

# Giao diện tiếng Việt mặc định; bản dịch "vi" do superset/i18n/build_catalog.py biên dịch lúc build image.
# Giữ English trong bộ chọn ngôn ngữ (cờ ở góc phải thanh menu).
BABEL_DEFAULT_LOCALE = "vi"
LANGUAGES = {
    "vi": {"flag": "vn", "name": "Tiếng Việt"},
    "en": {"flag": "us", "name": "English"},
}

# Định dạng số/ngày kiểu Việt Nam cho chart: 13.494.400,74 thay vì 13,494,400.74.
D3_FORMAT = {"decimal": ",", "thousands": ".", "grouping": [3], "currency": ["R$ ", ""]}
D3_TIME_FORMAT = {
    "dateTime": "%X %A, %e/%m/%Y",
    "date": "%d/%m/%Y",
    "time": "%H:%M:%S",
    "periods": ["SA", "CH"],
    "days": ["Chủ nhật", "Thứ hai", "Thứ ba", "Thứ tư", "Thứ năm", "Thứ sáu", "Thứ bảy"],
    "shortDays": ["CN", "T2", "T3", "T4", "T5", "T6", "T7"],
    "months": [f"Tháng {i}" for i in range(1, 13)],
    "shortMonths": [f"Th{i}" for i in range(1, 13)],
}
