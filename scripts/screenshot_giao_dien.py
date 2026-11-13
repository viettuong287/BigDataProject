"""Chụp ảnh minh chứng giao diện Superset đồng bộ với landing page (thương hiệu Olist Insight, theme, CSS dashboard).

Chạy (Superset + web đang chạy):
    docker compose run --rm screenshots python scripts/screenshot_giao_dien.py
Kết quả: evidence/superset_giao_dien_dong_bo_*.png (đăng nhập, 7 tab, so sánh landing ↔ dashboard).
Biến OUT_DIR đổi thư mục lưu ảnh (vd. khi chỉnh CSS thử).
"""
from __future__ import annotations

import base64
import os
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("OUT_DIR", ROOT / "evidence"))
PREFIX = "superset_giao_dien_dong_bo_"
URL = os.environ.get("SUPERSET_URL", "http://localhost:8088").rstrip("/")
LANDING = os.environ.get("LANDING_URL_INTERNAL", "http://web").rstrip("/")
USER = os.environ.get("SUPERSET_ADMIN_USER", "admin")
PWD = os.environ.get("SUPERSET_ADMIN_PASSWORD", "admin")
DASH = f"{URL}/superset/dashboard/olist-presentation/"

TABS = ["tab1_tong_quan", "tab2_danh_muc", "tab3_dia_ly", "tab4_khach_hang_rfm", "tab5_nguoi_ban",
        "tab6_giao_tre_thanh_toan", "tab7_goi_y_quyet_dinh"]
TAB_MARK = ["Doanh thu tháng gần nhất & xu hướng", "Pareto danh mục", "Bản đồ doanh thu theo bang",
            "Phân bố khách theo phân khúc RFM", "Pareto người bán", "Điểm đánh giá TB: giao trễ và đúng hạn",
            "Gợi ý quyết định (luật"]
STATE_JS = """() => {
    const hs = [...document.querySelectorAll('.dashboard-component-chart-holder')]
        .filter(h => h.offsetParent !== null && h.getBoundingClientRect().width > 0);
    const busy = hs.filter(h => /Waiting on|Loading|Đang chờ|Đang tải/.test(h.innerText)).length;
    const errors = hs.filter(h => h.querySelector('.ant-alert-error, .alert-danger') || /Unexpected error|Lỗi không mong đợi/.test(h.innerText))
                     .map(h => (h.innerText || '').split('\\n')[0]);
    return {n: hs.length, busy, errors, text: hs.map(h => h.innerText || '').join('\\n'),
            font: document.fonts.check('16px "Be Vietnam Pro"')};
}"""


def wait_rendered(page, timeout_s: float = 180) -> dict:
    t0, stable, st = time.perf_counter(), 0, {}
    while time.perf_counter() - t0 < timeout_s and stable < 4:
        st = page.evaluate(STATE_JS)
        stable = stable + 1 if st["n"] > 0 and st["busy"] == 0 else 0
        time.sleep(0.4)
    page.wait_for_timeout(1500)
    return st


def open_tab(page, idx: int) -> dict:
    # Bấm lại tab đang chọn không có tác dụng: đi qua một tab khác nếu nội dung chưa đúng.
    for _ in range(3):
        page.locator('[role="tab"]').nth(idx).click()
        st = wait_rendered(page)
        if TAB_MARK[idx] in st["text"]:
            return st
        page.locator('[role="tab"]').nth(1 if idx == 0 else 0).click()
        wait_rendered(page)
    raise RuntimeError(f"tab {idx + 1} không hiển thị đúng nội dung")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1600, "height": 1900}, locale="vi-VN")
        page = ctx.new_page()

        page.set_viewport_size({"width": 1600, "height": 1000})
        page.goto(f"{URL}/login/")
        page.wait_for_selector("#username")
        page.wait_for_timeout(1200)
        page.screenshot(path=str(OUT / f"{PREFIX}dang_nhap.png"))
        page.fill("#username", USER)
        page.fill("#password", PWD)
        page.keyboard.press("Enter")
        page.wait_for_url("**/superset/welcome/**", timeout=60000)

        page.set_viewport_size({"width": 1600, "height": 1900})
        page.goto(DASH, wait_until="domcontentloaded")
        page.wait_for_selector('[role="tab"]', timeout=120000)
        for i, slug in enumerate(TABS):
            st = open_tab(page, i)
            page.screenshot(path=str(OUT / f"{PREFIX}{slug}.png"))
            print(f"tab {i + 1} {slug:<26} {st['n']:>2} thành phần  lỗi={st['errors']}  font Be Vietnam Pro={st['font']}",
                  flush=True)

        # Ảnh so sánh: phần đầu landing page ↔ phần đầu dashboard (cùng khung 1440x900).
        page.set_viewport_size({"width": 1440, "height": 900})
        open_tab(page, 0)
        dash_png = page.screenshot()
        landing = ctx.new_page()
        landing.set_viewport_size({"width": 1440, "height": 900})
        landing.goto(f"{LANDING}/", wait_until="networkidle")
        landing.wait_for_timeout(4000)
        land_png = landing.screenshot()
        b64 = lambda b: base64.b64encode(b).decode()  # noqa: E731
        cmp = ctx.new_page()
        cmp.set_viewport_size({"width": 1480, "height": 520})
        cmp.set_content(f"""<html><body style="margin:0;background:#070b1a;font-family:'Segoe UI',Arial,sans-serif;color:#e8ecf8">
          <div style="display:flex;gap:16px;padding:16px">
            <figure style="margin:0;flex:1"><figcaption style="margin:0 0 8px;font-weight:700">Landing page · :8090</figcaption>
              <img style="width:100%;border-radius:12px;border:1px solid rgba(255,255,255,.15)" src="data:image/png;base64,{b64(land_png)}"></figure>
            <figure style="margin:0;flex:1"><figcaption style="margin:0 0 8px;font-weight:700">Dashboard Superset · :8088</figcaption>
              <img style="width:100%;border-radius:12px;border:1px solid rgba(255,255,255,.15)" src="data:image/png;base64,{b64(dash_png)}"></figure>
          </div></body></html>""")
        cmp.wait_for_timeout(500)
        cmp.screenshot(path=str(OUT / f"{PREFIX}so_sanh_landing.png"), full_page=True)
        browser.close()
    print(f"Đã lưu {OUT}/{PREFIX}*.png")


if __name__ == "__main__":
    main()
