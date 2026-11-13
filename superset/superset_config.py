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
# BABEL_DEFAULT_LOCALE phải là "en": Superset dịch nhãn menu trái (Bảng điều khiển, Biểu đồ...) một lần lúc khởi động
# theo locale mặc định rồi chỉ dịch lại theo msgid; mặc định "vi" làm nhãn kẹt tiếng Việt khi người dùng chọn English.
# Tiếng Việt mặc định được gán cho từng phiên trong FLASK_APP_MUTATOR bên dưới.
BABEL_DEFAULT_LOCALE = "en"
DEFAULT_UI_LOCALE = "vi"


def FLASK_APP_MUTATOR(app):  # noqa: N802
    from flask import request, session

    @app.before_request
    def _default_ui_locale():
        if "locale" not in session and not request.path.startswith(("/static/", "/health")):
            session["locale"] = DEFAULT_UI_LOCALE


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

# ---------------------------------------------------------------------------------------------
# Nhận diện thương hiệu "Olist Insight" – đồng bộ với landing page (web/, http://localhost:8090).
# Logo/favicon nằm trong superset/branding/, Dockerfile chép vào /app/superset/static/assets/images/olist/.
# ---------------------------------------------------------------------------------------------
LANDING_URL = os.environ.get("LANDING_URL", "http://localhost:8090/")

APP_NAME = "Olist Insight"
APP_ICON = "/static/assets/images/olist/olist-insight-logo.svg"
FAVICONS = [
    {"href": "/static/assets/images/olist/olist-insight-favicon.svg", "type": "image/svg+xml"},
    {"href": "/static/assets/images/olist/olist-insight-favicon.png", "sizes": "64x64", "type": "image/png"},
]
LOGO_TARGET_PATH = LANDING_URL
LOGO_TOOLTIP = "Về trang giới thiệu Olist Insight"
LOGO_RIGHT_TEXT = "Phân tích → Trình bày"
# Superset chỉ vẽ link này thành icon ở thanh menu phải; nhãn chữ thêm bằng CSS trong tail_js_custom_extra.html.
DOCUMENTATION_URL = LANDING_URL
DOCUMENTATION_TEXT = "Trang giới thiệu"
DOCUMENTATION_ICON = "fa fa-home"

# Bảng màu giống landing page (web/assets/style.css): xanh ngọc #10b981/#34d399, chàm #6366f1/#818cf8,
# hồng #f472b6, hổ phách #fbbf24, nền xanh đen #0b1024, chữ phụ xám xanh.
THEME_OVERRIDES = {
    "borderRadius": 8,
    "brandIconMaxWidth": 46,  # x gridUnit 4px = 184px, vừa logo ngang 180x36

    "colors": {
        "primary": {"base": "#6366f1", "dark1": "#4f46e5", "dark2": "#4338ca", "light1": "#818cf8",
                    "light2": "#a5b4fc", "light3": "#c7d2fe", "light4": "#e0e7ff", "light5": "#eef2ff"},
        "secondary": {"base": "#10b981", "dark1": "#059669", "dark2": "#047857", "dark3": "#065f46",
                      "light1": "#34d399", "light2": "#6ee7b7", "light3": "#a7f3d0", "light4": "#d1fae5",
                      "light5": "#ecfdf5"},
        "grayscale": {"base": "#64748b", "dark1": "#334155", "dark2": "#0b1024", "light1": "#94a3b8",
                      "light2": "#e2e8f0", "light3": "#f1f5f9", "light4": "#f8fafc", "light5": "#ffffff"},
        "success": {"base": "#10b981"},
        "warning": {"base": "#f59e0b"},
        "error": {"base": "#ef4444"},
    },
    "typography": {
        "families": {"sansSerif": "'Be Vietnam Pro', Inter, 'Segoe UI', Helvetica, Arial, sans-serif"},
    },
}

# Màu phân loại mặc định cho mọi chart: thứ tự giống biểu đồ hero của landing (doanh thu xanh ngọc,
# số đơn chàm), rồi tới màu chú giải RFM (hồng, hổ phách, xanh lơ, tím...).
EXTRA_CATEGORICAL_COLOR_SCHEMES = [{
    "id": "olistInsight",
    "label": "Olist Insight (landing)",
    "description": "Bảng màu của landing page Olist Insight",
    "isDefault": True,
    "colors": ["#10b981", "#6366f1", "#f472b6", "#fbbf24", "#22d3ee", "#a78bfa", "#f87171", "#475569",
               "#34d399", "#818cf8", "#db2777", "#d97706", "#0891b2", "#7c3aed", "#059669", "#94a3b8"],
}]
# Thang liên tục cho bản đồ Brazil và heatmap mùa vụ: xanh ngọc nhạt -> chàm.
EXTRA_SEQUENTIAL_COLOR_SCHEMES = [{
    "id": "olistInsightSeq",
    "label": "Olist Insight · xanh ngọc → chàm",
    "description": "Thang liên tục theo gradient của landing page",
    "isDiverging": False,
    "isDefault": True,
    "colors": ["#ecfdf5", "#a7f3d0", "#34d399", "#10b981", "#0d9488", "#4f46e5", "#3730a3"],
}]
