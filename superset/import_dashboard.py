"""Phương án dự phòng: import dashboard từ superset/export/dashboard_olist_presentation.zip.

ZIP đã thay host/user Neon bằng placeholder (không commit thông tin kết nối); script này điền lại
từ NEON_DATABASE_URL trong .env rồi gọi POST /api/v1/dashboard/import/.
Cách chính vẫn là build_dashboard.py (dựng từ code, idempotent).

Chạy: docker compose run --rm tools python superset/import_dashboard.py
"""
import io
import json
import re
import sys
import zipfile
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from superset_client import Superset  # noqa: E402
from build_dashboard import sqlalchemy_uri  # noqa: E402

SRC = Path(__file__).resolve().parent / "export" / "dashboard_olist_presentation.zip"


def main() -> None:
    uri = sqlalchemy_uri()
    password = urlparse(uri).password or ""
    masked = re.sub(r":[^:@/]+@", ":XXXXXXXXXX@", uri, count=1)
    buf, db_file = io.BytesIO(), None
    with zipfile.ZipFile(SRC) as zin, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if "/databases/" in item.filename:
                db_file = item.filename.split("/", 1)[1]
                data = re.sub(r"sqlalchemy_uri: .*", f"sqlalchemy_uri: {masked}", data.decode("utf-8")).encode("utf-8")
            zout.writestr(item.filename, data)
    api = Superset()
    r = api.s.post(f"{api.url}/api/v1/dashboard/import/",
                   files={"formData": ("dashboard.zip", buf.getvalue(), "application/zip")},
                   data={"overwrite": "true", "passwords": json.dumps({db_file: password})})
    print(r.status_code, r.text[:300])
    r.raise_for_status()


if __name__ == "__main__":
    main()
