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
BABEL_DEFAULT_LOCALE = "en"
