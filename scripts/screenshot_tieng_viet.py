"""Chụp ảnh minh chứng giao diện Superset tiếng Việt: trang đăng nhập, dashboard (menu + bộ lọc), menu biểu đồ.

Chạy (Superset đang chạy):
    docker compose run --rm screenshots python scripts/screenshot_tieng_viet.py
Kết quả: evidence/superset_tieng_viet_*.png
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / "evidence"
URL = os.environ.get("SUPERSET_URL", "http://localhost:8088").rstrip("/")
USER = os.environ.get("SUPERSET_ADMIN_USER", "admin")
PWD = os.environ.get("SUPERSET_ADMIN_PASSWORD", "admin")
DASH = f"{URL}/superset/dashboard/olist-presentation/"

BUSY_JS = """() => [...document.querySelectorAll('.dashboard-component-chart-holder')]
    .filter(h => h.offsetParent !== null && /Đang chờ|Đang tải|Waiting on|Loading/.test(h.innerText)).length"""


def wait_charts(page, timeout_s: float = 180) -> None:
    t0, stable = time.perf_counter(), 0
    while time.perf_counter() - t0 < timeout_s and stable < 4:
        stable = stable + 1 if page.evaluate(BUSY_JS) == 0 else 0
        time.sleep(0.5)
    page.wait_for_timeout(1500)


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width": 1600, "height": 1000}, locale="vi-VN").new_page()

        page.goto(f"{URL}/login/")
        page.wait_for_selector("#username")
        page.screenshot(path=str(EVID / "superset_tieng_viet_dang_nhap.png"))

        page.fill("#username", USER)
        page.fill("#password", PWD)
        page.keyboard.press("Enter")
        page.wait_for_url("**/superset/welcome/**", timeout=60000)

        page.goto(DASH, wait_until="domcontentloaded")
        page.wait_for_selector('[role="tab"]', timeout=120000)
        wait_charts(page)
        page.screenshot(path=str(EVID / "superset_tieng_viet_dashboard.png"))

        # Menu "..." của một biểu đồ (Làm mới, Toàn màn hình, Xem truy vấn, Tải xuống...).
        holder = page.locator(".dashboard-component-chart-holder").nth(6)
        holder.hover()
        holder.locator('[id$="-controls"][role="button"]').first.click()
        page.wait_for_timeout(800)
        page.screenshot(path=str(EVID / "superset_tieng_viet_menu_bieu_do.png"))
        page.keyboard.press("Escape")

        # Tab Người bán: nhãn cột (verbose_name) trong bảng, ô tìm kiếm, phân trang.
        page.locator('[role="tab"]').nth(4).click()
        wait_charts(page)
        page.locator(".dashboard-component-chart-holder", has_text="Người bán cần theo dõi (watchlist)").first \
            .screenshot(path=str(EVID / "superset_tieng_viet_bang_nguoi_ban.png"))
        browser.close()
    print("Đã lưu evidence/superset_tieng_viet_*.png")


if __name__ == "__main__":
    main()
