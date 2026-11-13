"""Chụp ảnh landing page (desktop + mobile) làm minh chứng.

Chạy (service web đang chạy):
    docker compose up -d web
    docker compose run --rm screenshots python scripts/screenshot_landing.py

Ảnh được chụp khi phần phát lại dữ liệu đã qua tháng Black Friday (11/2017) và tạm dừng ở đó,
để ảnh luôn có cùng trạng thái giữa các lần chạy.
"""
from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / "evidence"
URL = os.environ.get("LANDING_URL", "http://web/")

SHOTS = [
    ("landing_page_desktop.png", {"viewport": {"width": 1440, "height": 900}, "device_scale_factor": 1}),
    ("landing_page_mobile.png", {"viewport": {"width": 390, "height": 844}, "device_scale_factor": 2,
                                 "is_mobile": True, "has_touch": True}),
]


def capture(browser, name: str, ctx_args: dict) -> None:
    ctx = browser.new_context(locale="vi-VN", timezone_id="Asia/Ho_Chi_Minh", **ctx_args)
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))

    page.goto(URL, wait_until="networkidle")
    page.wait_for_function("document.querySelectorAll('#ins-cat li').length > 0", timeout=15000)
    page.wait_for_function("document.getElementById('ticker').innerText.includes('Tháng 12/2017')", timeout=60000)
    page.wait_for_timeout(500)
    page.click("#btn-play")

    # html có scroll-behavior: smooth, nên phải cuộn kiểu "instant" để ảnh không bị chụp giữa chừng.
    page.evaluate("document.getElementById('insight').scrollIntoView({behavior: 'instant'})")
    page.wait_for_timeout(1500)
    page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
    page.wait_for_function("window.scrollY === 0")
    page.wait_for_timeout(300)

    out = EVID / name
    page.screenshot(path=str(out), full_page=True)
    print(f"{out.relative_to(ROOT)}  {ctx_args['viewport']['width']}px  lỗi JS: {errors or 'không'}")
    ctx.close()


def main() -> None:
    EVID.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, args in SHOTS:
            capture(browser, name, args)
        browser.close()


if __name__ == "__main__":
    main()
