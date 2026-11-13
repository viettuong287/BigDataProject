"""Kiểm thử QA tự động (Playwright): đăng nhập, 7 tab dashboard, 6 kịch bản bộ lọc native + xoá lọc, đổi ngôn ngữ
vi↔en tại chỗ, link logo/"Trang giới thiệu", landing page, ZIP export, lệnh README.

Chạy toàn bộ (gồm kiểm tra phía host: docker compose config, import ZIP):
    powershell -ExecutionPolicy Bypass -File scripts\\qa_run.ps1
Chỉ phần trình duyệt:
    docker compose run --rm screenshots python scripts/qa_check.py
Kết quả: evidence/qa_test_cases.md (bảng ID, ca kiểm thử, bước, kỳ vọng, kết quả, ghi chú) + evidence/qa_results.json.
"""
from __future__ import annotations

import json
import os
import re
import time
import traceback
import zipfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / "evidence"
URL = os.environ.get("SUPERSET_URL", "http://localhost:8088").rstrip("/")
LANDING = os.environ.get("LANDING_URL", "http://web").rstrip("/")
PUBLIC_LANDING = "http://localhost:8090"  # URL người dùng thấy (logo, nút "Trang giới thiệu")
PUBLIC_DASH = "http://localhost:8088/superset/dashboard/olist-presentation/"  # nút "Mở dashboard" của landing
GITHUB = "https://github.com/viettuong287/BigDataProject"
USER = os.environ.get("SUPERSET_ADMIN_USER", "admin")
PWD = os.environ.get("SUPERSET_ADMIN_PASSWORD", "admin")
INFO = json.loads((ROOT / "superset" / "export" / "build_info.json").read_text(encoding="utf-8"))
DASH = f"{URL}/superset/dashboard/{INFO['dashboard_id']}/"
CH = INFO["charts"]  # key -> chart id
F = {fid.split("-")[1][2:]: fid for fid in INFO["filters"]}

TAB_NAMES = ["Tổng quan & xu hướng", "Danh mục & mùa vụ", "Địa lý & logistics", "Khách hàng & RFM", "Người bán",
             "Giao trễ, đánh giá & thanh toán", "Gợi ý quyết định & nguồn dữ liệu"]
TAB_MARK = ["Doanh thu tháng gần nhất & xu hướng", "Pareto danh mục", "Bản đồ doanh thu theo bang",
            "Phân bố khách theo phân khúc RFM", "Pareto người bán", "Điểm đánh giá TB: giao trễ và đúng hạn",
            "Gợi ý quyết định (luật"]
TAB_COMPONENTS = [11, 4, 5, 10, 7, 6, 4]  # chart + markdown của mỗi tab (build_dashboard.py)

# Lỗi console đã biết là vô hại – được liệt kê trong báo cáo nhưng không làm ca kiểm thử FAIL.
BENIGN = [
    (r"scarf\.sh", "pixel thống kê ẩn danh của Superset (apachesuperset.gateway.scarf.sh), không ảnh hưởng chức năng"),
    (r"fonts\.g(oogleapis|static)\.com", "tải font Google chậm/bị chặn: trình duyệt dùng font dự phòng"),
]

STATE_JS = """() => {
    const hs = [...document.querySelectorAll('.dashboard-component-chart-holder')]
        .filter(h => h.offsetParent !== null && h.getBoundingClientRect().width > 0);
    const busy = hs.filter(h => /Waiting on|Loading|Đang chờ|Đang tải/.test(h.innerText)).length;
    const errors = hs.filter(h => h.querySelector('.ant-alert-error, .alert-danger')
                              || /Unexpected error|Lỗi không mong đợi|An error occurred|Đã xảy ra lỗi|Kh\\u00f4ng t\\u1ea3i \\u0111\\u01b0\\u1ee3c/.test(h.innerText))
                     .map(h => (h.innerText || '').split('\\n')[0]);
    const nodata = hs.filter(h => /No results|Không có kết quả|Không có dữ liệu|No data/.test(h.innerText))
                     .map(h => (h.innerText || '').split('\\n')[0]);
    return {n: hs.length, busy, errors, nodata, text: hs.map(h => h.innerText || '').join('\\n')};
}"""

KPI_JS = """() => [...document.querySelectorAll('.dashboard-component-chart-holder')]
  .filter(h => h.offsetParent !== null && h.querySelector('[data-test-viz-type^="big_number"]'))
  .map(h => {
    const q = s => h.querySelector(s), R = e => e ? e.getBoundingClientRect() : null;
    const t = q('.header-title'), v = q('.header-line'), s = q('.subheader-line');
    const hr = R(h), tr = R(t), vr = R(v), sr = R(s), issues = [];
    if (tr && vr && tr.bottom > vr.top + 1) issues.push('tiêu đề chồng lên số');
    if (vr && (vr.right > hr.right + 1 || vr.left < hr.left - 1)) issues.push('số tràn khỏi thẻ');
    if (v && v.scrollWidth > v.clientWidth + 2) issues.push('số bị cắt');
    if (sr && vr && sr.top < vr.bottom - 2) issues.push('dòng phụ chồng lên số');
    if (sr && sr.bottom > hr.bottom + 1) issues.push('dòng phụ ra ngoài thẻ');
    if (tr && tr.bottom > hr.bottom) issues.push('tiêu đề ra ngoài thẻ');
    if (t && t.scrollWidth > t.clientWidth + 1) issues.push('tiêu đề bị cắt');
    return {title: t ? t.innerText.trim() : '', value: v ? v.innerText.trim() : '', issues};
  })"""

BOOT_LOCALE_JS = "() => { try { return JSON.parse(document.getElementById('app').dataset.bootstrap).common.locale } catch (e) { return null } }"

results: list[dict] = []
console_seen: dict[str, str] = {}


def record(tid: str, case: str, steps: str, expected: str, ok: bool | None, note: str = "") -> None:
    res = "PASS" if ok else ("KNOWN" if ok is None else "FAIL")
    results.append({"id": tid, "case": case, "steps": steps, "expected": expected, "result": res, "note": note})
    print(f"[{res:<5}] {tid} {case} {('– ' + note) if note else ''}", flush=True)


def run(tid: str, case: str, steps: str, expected: str, fn) -> None:
    try:
        out = fn()
        ok, note = out if isinstance(out, tuple) else (bool(out), "")
        record(tid, case, steps, expected, ok, note)
    except Exception as e:  # noqa: BLE001
        record(tid, case, steps, expected, False, f"ngoại lệ: {type(e).__name__}: {str(e)[:200]}")
        traceback.print_exc()


class Console:
    """Thu lỗi console + pageerror của một trang; tách lỗi vô hại theo BENIGN."""

    def __init__(self, page):
        self.items: list[str] = []
        page.on("console", lambda m: m.type == "error" and self.items.append(m.text))
        page.on("pageerror", lambda e: self.items.append(f"pageerror: {e}"))

    def take(self) -> tuple[list[str], list[str]]:
        bad, benign = [], []
        for msg in self.items:
            why = next((w for rx, w in BENIGN if re.search(rx, msg)), None)
            if why:
                benign.append(msg)
                console_seen.setdefault(msg[:160], why)
            else:
                bad.append(msg[:200])
        self.items.clear()
        return bad, benign


class ChartData:
    """Ghi lại response /api/v1/chart/data theo slice_id (đọc JSON bên ngoài event handler)."""

    def __init__(self, page):
        self.pending = []
        page.on("response", lambda r: "/api/v1/chart/data" in r.url and r.request.method == "POST" and self.pending.append(r))

    def reset(self) -> None:
        self.pending.clear()

    def rows(self, key: str) -> list[dict] | None:
        sid, found = CH[key], None
        for r in self.pending:
            try:
                if (r.request.post_data_json or {}).get("form_data", {}).get("slice_id") == sid and r.ok:
                    found = r.json()["result"][0]["data"]
            except Exception:  # noqa: BLE001
                continue
        return found


def num(text: str) -> float:
    t = re.sub(r"[^\d,.\-]", "", text or "").replace(".", "").replace(",", ".")
    return float(t) if t not in ("", "-", ".") else float("nan")


def wait_rendered(page, timeout_s: float = 180) -> dict:
    t0, stable, st = time.perf_counter(), 0, {}
    while time.perf_counter() - t0 < timeout_s and stable < 4:
        st = page.evaluate(STATE_JS)
        stable = stable + 1 if st["n"] > 0 and st["busy"] == 0 else 0
        time.sleep(0.4)
    page.wait_for_timeout(1200)
    return page.evaluate(STATE_JS)


def open_tab(page, idx: int) -> dict:
    for _ in range(3):
        page.locator('[role="tab"]').nth(idx).click()
        st = wait_rendered(page)
        if TAB_MARK[idx] in st["text"]:
            return st
        page.locator('[role="tab"]').nth(1 if idx == 0 else 0).click()
        wait_rendered(page)
    raise RuntimeError(f"tab {idx + 1} không hiển thị đúng nội dung")


def goto_dash(page, url: str = DASH) -> None:
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_selector('[role="tab"]', timeout=120000)


def kpi_value(page, title: str) -> str:
    for k in page.evaluate(KPI_JS):
        if k["title"] == title:
            return k["value"]
    return ""


def login(page) -> None:
    page.goto(f"{URL}/login/")
    page.fill("#username", USER)
    page.fill("#password", PWD)
    page.keyboard.press("Enter")
    page.wait_for_url("**/superset/welcome/**", timeout=60000)


def permalink(ctx, headers, mask: dict, tab: int) -> str:
    r = ctx.request.post(f"{URL}/api/v1/dashboard/{INFO['dashboard_id']}/permalink",
                         data={"dataMask": mask, "activeTabs": [f"TAB-t{tab + 1}"], "urlParams": []}, headers=headers)
    return f"{URL}/superset/dashboard/p/{r.json()['key']}/"


def select(key: str, col: str, values: list[str]) -> dict:
    fid = F[key]
    return {fid: {"id": fid, "extraFormData": {"filters": [{"col": col, "op": "IN", "val": values}]},
                  "filterState": {"value": values, "label": ", ".join(values)}, "ownState": {}}}


def time_range(rng: str) -> dict:
    fid = F["monthdate"]
    return {fid: {"id": fid, "extraFormData": {"time_range": rng}, "filterState": {"value": rng}, "ownState": {}}}


def switch_lang(page, code: str, keyboard: bool = False) -> None:
    """Mở menu cờ, chọn ngôn ngữ (chuột hoặc bàn phím); script trong tail_js_custom_extra.html tải lại trang."""
    page.locator('#main-menu li[aria-label="Languages"]').hover()
    link = page.locator(f'.ant-menu-submenu-popup a[href="/lang/{code}"]')
    link.wait_for(state="visible", timeout=10000)
    with page.expect_navigation(timeout=60000):
        if keyboard:
            link.focus()
            page.keyboard.press("Enter")
        else:
            link.click()
    page.wait_for_load_state("domcontentloaded")


# ---------------------------------------------------------------------------------------------
def main() -> None:
    EVID.mkdir(exist_ok=True)
    host = {}
    hc = EVID / "qa_host_checks.json"
    if hc.exists():
        host = json.loads(hc.read_text(encoding="utf-8-sig"))

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ---------------- Đăng nhập ----------------
        ctx0 = browser.new_context(viewport={"width": 1440, "height": 900}, locale="vi-VN")
        pg = ctx0.new_page()
        con0 = Console(pg)

        def t_login_page():
            pg.goto(f"{URL}/login/")
            pg.wait_for_selector("#username")
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(800)
            title = pg.title()
            logo = pg.locator('#main-menu a.navbar-brand img').get_attribute("src") or ""
            icon = pg.evaluate("() => [...document.querySelectorAll('link[rel=icon]')].map(l => l.getAttribute('href')).join(' ')")
            font = pg.evaluate("() => document.fonts.check('16px \"Be Vietnam Pro\"')")
            bad, _ = con0.take()
            ok = title.strip() == "Olist Insight" and "olist-insight-logo.svg" in logo and "olist-insight-favicon" in icon and font and not bad
            return ok, f"title={title.strip()!r}, logo={logo.rsplit('/', 1)[-1]}, font Be Vietnam Pro={font}, lỗi console={bad or 0}"

        run("TC01", "Trang đăng nhập hiển thị thương hiệu Olist Insight", "Mở /login/",
            "Tiêu đề 'Olist Insight', logo + favicon Olist Insight, font Be Vietnam Pro, không lỗi console", t_login_page)

        def t_wrong_pwd():
            pg.fill("#username", USER)
            pg.fill("#password", "sai-mat-khau-qa")
            pg.keyboard.press("Enter")
            pg.wait_for_load_state("domcontentloaded")
            pg.wait_for_timeout(800)
            alert = pg.locator(".alert").all_inner_texts()
            txt = " ".join(alert)
            return ("/login" in pg.url and bool(re.search(r"không hợp lệ|Invalid login", txt)), f"thông báo: {txt.strip()[:80]!r}")

        run("TC02", "Sai mật khẩu bị từ chối", "Nhập admin / mật khẩu sai → Đăng nhập",
            "Ở lại /login/, hiện thông báo 'Đăng nhập không hợp lệ'", t_wrong_pwd)

        def t_login_ok():
            pg.fill("#username", USER)
            pg.fill("#password", PWD)
            pg.keyboard.press("Enter")
            pg.wait_for_url("**/superset/welcome/**", timeout=60000)
            pg.wait_for_selector("#main-menu", timeout=60000)
            pg.wait_for_timeout(1500)
            loc = pg.evaluate(BOOT_LOCALE_JS)
            vi_menu = pg.locator("#main-menu >> text=Bảng điều khiển").count() > 0
            bad, _ = con0.take()
            return ("/superset/welcome/" in pg.url and loc == "vi" and vi_menu and not bad,
                    f"→ {pg.url.replace(URL, '')}; phiên mới mặc định locale={loc}, menu 'Bảng điều khiển'={vi_menu}; lỗi console={bad or 0}")

        run("TC03", "Đăng nhập admin thành công, mặc định tiếng Việt", "Phiên mới: nhập admin / mật khẩu đúng (.env)",
            "Chuyển tới /superset/welcome/, giao diện tiếng Việt (locale vi)", t_login_ok)
        ctx0.close()

        # ---------------- Dashboard: 7 tab × 2 độ rộng ----------------
        ctx = browser.new_context(viewport={"width": 1440, "height": 1600}, locale="vi-VN")
        page = ctx.new_page()
        con = Console(page)
        data = ChartData(page)
        login(page)
        csrf = ctx.request.get(f"{URL}/api/v1/security/csrf_token/").json()["result"]
        headers = {"X-CSRFToken": csrf, "Referer": URL, "Content-Type": "application/json"}
        baseline: dict[str, str] = {}

        for width in (1440, 1280):
            page.set_viewport_size({"width": width, "height": 1600})
            goto_dash(page)
            con.take()
            for i in range(7):
                tid = f"TC{4 + i:02d}" if width == 1440 else f"TC{11 + i:02d}"

                def t_tab(i=i, width=width):
                    st = open_tab(page, i)
                    kpis = page.evaluate(KPI_JS)
                    if width == 1440:
                        baseline.update({k["title"]: k["value"] for k in kpis})
                    over = [f"{k['title']}: {', '.join(k['issues'])}" for k in kpis if k["issues"]]
                    nav_h = page.evaluate("() => document.getElementById('main-menu').offsetHeight")
                    bad, benign = con.take()
                    ok = (st["n"] == TAB_COMPONENTS[i] and not st["errors"] and not st["nodata"] and not over and not bad
                          and nav_h <= 64)
                    note = (f"{st['n']}/{TAB_COMPONENTS[i]} thành phần, thanh menu cao {nav_h}px, lỗi chart={st['errors'] or 0}, "
                            f"không dữ liệu={st['nodata'] or 0}, thẻ KPI={len(kpis)} chồng chữ={over or 0}, "
                            f"lỗi console={bad or 0}" + (f", bỏ qua {len(benign)} lỗi vô hại" if benign else ""))
                    return ok, note

                run(tid, f"Tab {i + 1} · {TAB_NAMES[i]} @ {width}px", f"Mở dashboard ({width}px), bấm tab {i + 1}",
                    "Mọi chart/markdown hiển thị, không trạng thái lỗi/'Lỗi', không 'không có dữ liệu', không lỗi console, "
                    "thẻ KPI không chồng chữ", t_tab)
        page.set_viewport_size({"width": 1440, "height": 1600})

        # ---------------- 6 kịch bản bộ lọc native (permalink) ----------------
        def scenario(tid, case, steps, expected, mask, tab, check, widths=(1440, 1280)):
            def fn():
                notes, ok_all = [], True
                for w in widths:
                    page.set_viewport_size({"width": w, "height": 1600})
                    data.reset()
                    goto_dash(page, permalink(ctx, headers, mask, tab))
                    st = wait_rendered(page) if tab == 0 else open_tab(page, tab)
                    if tab == 0 and TAB_MARK[0] not in st["text"]:
                        st = open_tab(page, 0)
                    kpis = page.evaluate(KPI_JS)
                    over = [k["title"] for k in kpis if k["issues"]]
                    bad, _ = con.take()
                    ok, note = check(st, kpis)
                    ok = ok and not st["errors"] and not over and not bad
                    ok_all &= ok
                    notes.append(f"@{w}px: {note}; lỗi chart={st['errors'] or 0}, KPI chồng chữ={over or 0}, lỗi console={bad or 0}")
                    if w == 1280 and tab == 0:
                        page.screenshot(path=str(EVID / "qa_kpi_loc_1280.png"), clip={"x": 0, "y": 0, "width": 1280, "height": 420})
                page.set_viewport_size({"width": 1440, "height": 1600})
                return ok_all, " | ".join(notes)
            run(tid, case, steps, expected, fn)

        def chk1(st, kpis):
            rev = next((k["value"] for k in kpis if k["title"] == "Doanh thu"), "")
            rows = data.rows("kpi_table") or []
            months = sorted({r.get("month_label", "") for r in rows})
            ok = 0 < num(rev) < num(baseline.get("Doanh thu", "0")) and months and all(m.startswith("2018") for m in months)
            return ok, f"doanh thu {baseline.get('Doanh thu')} → {rev}; bảng KPI {len(months)} tháng {months[:1]}…{months[-1:]}"

        scenario("TC18", "Lọc Khoảng thời gian 2018 + Bang khách hàng SP (tab 1)",
                 "Permalink: time_range 2018-01-01:2018-09-01, customer_state=SP; mở tab 1 ở 1440 và 1280 px",
                 "Thẻ doanh thu giảm so với không lọc; bảng KPI chỉ còn tháng 2018; thẻ KPI không chồng chữ",
                 {**time_range("2018-01-01 : 2018-09-01"), **select("customerst", "customer_state", ["SP"])}, 0, chk1)

        cats = ["bed_bath_table", "health_beauty", "watches_gifts"]

        def chk2(st, kpis):
            rows = data.rows("cat_trend") or []
            s = json.dumps(rows, ensure_ascii=False)
            found = sorted({c for c in cats if c in s})
            ok = bool(rows) and found == sorted(cats) and "sports_leisure" not in s and "furniture_decor" not in s
            return ok, f"chart xu hướng danh mục có {found}, không còn danh mục khác"

        scenario("TC19", "Lọc Danh mục (3 danh mục, tab 2)", "Permalink: category ∈ {bed_bath_table, health_beauty, watches_gifts}; mở tab 2",
                 "Chart 'Doanh thu theo tháng của 6 danh mục' chỉ còn 3 danh mục đã chọn", select("category", "category", cats), 1, chk2,
                 widths=(1440,))

        def chk3(st, kpis):
            rows = data.rows("geo_table") or []
            regions = sorted({r.get("region") for r in rows})
            return regions == ["Nordeste"] and len(rows) == 9, f"bảng logistics {len(rows)} bang, vùng={regions}"

        scenario("TC20", "Lọc Vùng Nordeste (tab 3)", "Permalink: region=Nordeste; mở tab 3",
                 "Bảng logistics chỉ còn 9 bang vùng Nordeste", select("region", "region", ["Nordeste"]), 2, chk3, widths=(1440,))

        segs = ["Champions", "Loyal", "At Risk"]

        def chk4(st, kpis):
            tot = next((k["value"] for k in kpis if k["title"] == "Khách hàng (RFM)"), "")
            rows = data.rows("rfm_pie") or []
            got = sorted({r.get("rfm_segment") for r in rows})
            ok = 0 < num(tot) < num(baseline.get("Khách hàng (RFM)", "0")) and set(got) <= set(segs) and got
            return ok, f"khách RFM {baseline.get('Khách hàng (RFM)')} → {tot}; donut phân khúc={got}"

        scenario("TC21", "Lọc Phân khúc RFM (Champions/Loyal/At Risk) + bang RJ (tab 4)",
                 "Permalink: rfm_segment ∈ {Champions, Loyal, At Risk}, customer_state=RJ; mở tab 4 ở 1440 và 1280 px",
                 "Thẻ 'Khách hàng (RFM)' giảm; donut chỉ còn 3 phân khúc; thẻ KPI không chồng chữ",
                 {**select("rfmsegment", "rfm_segment", segs), **select("customerst", "customer_state", ["RJ"])}, 3, chk4)

        def chk5(st, kpis):
            tot = next((k["value"] for k in kpis if k["title"] == "Số người bán"), "")
            rows = data.rows("sel_watch_table") or []
            states = sorted({r.get("seller_state") for r in rows})
            ok = 0 < num(tot) < num(baseline.get("Số người bán", "0")) and states == ["SP"]
            return ok, f"số người bán {baseline.get('Số người bán')} → {tot}; watchlist bang={states} ({len(rows)} dòng)"

        scenario("TC22", "Lọc Bang người bán SP (tab 5)", "Permalink: seller_state=SP; mở tab 5 ở 1440 và 1280 px",
                 "Thẻ 'Số người bán' giảm; bảng watchlist chỉ còn người bán bang SP; thẻ KPI không chồng chữ",
                 select("sellerstat", "seller_state", ["SP"]), 4, chk5)

        def chk6(st, kpis):
            pie = sorted({r.get("main_payment_type") for r in (data.rows("pay_pie") or [])})
            tab = sorted({r.get("main_payment_type") for r in (data.rows("pay_table") or [])})
            return pie == ["boleto"] and tab == ["boleto"], f"donut PTTT={pie}, bảng cơ cấu={tab}"

        scenario("TC23", "Lọc Phương thức thanh toán boleto (tab 6)", "Permalink: main_payment_type=boleto; mở tab 6",
                 "Donut và bảng cơ cấu thanh toán chỉ còn boleto", select("mainpaymen", "main_payment_type", ["boleto"]), 5, chk6,
                 widths=(1440,))

        def t_clear():
            data.reset()
            goto_dash(page, permalink(ctx, headers, {**time_range("2018-01-01 : 2018-09-01"),
                                                    **select("customerst", "customer_state", ["SP"])}, 0))
            wait_rendered(page)
            before = kpi_value(page, "Doanh thu")
            page.locator(".filter-clear-all-button").click()
            page.wait_for_timeout(800)
            btn = page.locator(".filter-apply-button")
            if btn.is_enabled():
                btn.click()
            wait_rendered(page)
            after = kpi_value(page, "Doanh thu")
            con.take()
            return after == baseline.get("Doanh thu"), f"doanh thu {before} → bấm 'Xoá tất cả' + 'Áp dụng' → {after} (gốc {baseline.get('Doanh thu')})"

        run("TC24", "Xoá bộ lọc khôi phục số liệu gốc", "Mở permalink TC18 → 'Xoá tất cả' → 'Áp dụng bộ lọc'",
            "Thẻ doanh thu trở về giá trị không lọc", t_clear)

        # ---------------- Bộ lọc qua giao diện + đổi ngôn ngữ trên dashboard ----------------
        state = {}

        def t_ui_filter():
            goto_dash(page)
            open_tab(page, 2)
            data.reset()
            ctl = page.locator('form:has-text("Bang khách hàng") .ant-select-selector').first
            ctl.click()
            page.keyboard.type("SP")
            page.wait_for_timeout(1500)
            page.keyboard.press("Enter")
            page.keyboard.press("Escape")
            page.locator(".filter-apply-button").click()
            st = wait_rendered(page)
            rows = data.rows("geo_table") or []
            states = sorted({r.get("customer_state") for r in rows})
            state["url"] = page.url
            con.take()
            ok = states == ["SP"] and "native_filters_key=" in page.url and not st["errors"]
            return ok, f"bảng logistics bang={states}; URL có native_filters_key={'native_filters_key=' in page.url}"

        run("TC25", "Chọn bộ lọc trên thanh bộ lọc (giao diện)", "Tab 3 → ô 'Bang khách hàng' gõ SP, Enter → 'Áp dụng bộ lọc'",
            "Bảng logistics chỉ còn SP; URL có native_filters_key", t_ui_filter)

        def selected_tab():
            return page.evaluate("() => (document.querySelector('[role=tab][aria-selected=true]') || {}).id")

        def t_lang_dash():
            url0, tab0 = page.url, selected_tab()
            data.reset()
            switch_lang(page, "en")
            page.wait_for_function(f"() => (document.querySelector('[role=tab][aria-selected=true]') || {{}}).id === '{tab0}'",
                                   timeout=60000)
            st = wait_rendered(page)
            loc = page.evaluate(BOOT_LOCALE_JS)
            en_ui = page.locator("text=Apply filters").count() > 0 and page.locator("#main-menu >> text=Dashboards").count() > 0
            rows = data.rows("geo_table") or []
            states = sorted({r.get("customer_state") for r in rows})
            ok1 = page.url == url0 and selected_tab() == tab0 and loc == "en" and en_ui and states == ["SP"] and not st["errors"]
            n1 = f"vi→en: URL giữ nguyên={page.url == url0}, tab={selected_tab()}, locale={loc}, chữ 'Apply filters'/'Dashboards'={en_ui}, bộ lọc SP còn={states == ['SP']}"
            data.reset()
            switch_lang(page, "vi", keyboard=True)
            page.wait_for_function(f"() => (document.querySelector('[role=tab][aria-selected=true]') || {{}}).id === '{tab0}'",
                                   timeout=60000)
            st = wait_rendered(page)
            loc = page.evaluate(BOOT_LOCALE_JS)
            vi_ui = page.locator("text=Áp dụng bộ lọc").count() > 0 and page.locator("#main-menu >> text=Bảng điều khiển").count() > 0
            ok2 = page.url == url0 and selected_tab() == tab0 and loc == "vi" and vi_ui and not st["errors"]
            bad, _ = con.take()
            n2 = f"en→vi (bàn phím Enter): URL giữ nguyên={page.url == url0}, tab={selected_tab()}, locale={loc}, chữ tiếng Việt={vi_ui}"
            return ok1 and ok2 and not bad, f"{n1} | {n2}; lỗi console={bad or 0}"

        run("TC26", "Đổi ngôn ngữ trên dashboard giữ nguyên trang, tab và bộ lọc",
            "Sau TC25 (tab 3, lọc SP): menu cờ → English (chuột); rồi → Tiếng Việt (bàn phím: focus + Enter)",
            "Tải lại đúng URL (native_filters_key), vẫn tab 3, bộ lọc SP còn; giao diện đổi en rồi vi", t_lang_dash)

        pages = [("TC27", "Trang chủ", "/superset/welcome/", "Home", "Trang chủ"),
                 ("TC28", "Danh sách biểu đồ", "/chart/list/", "Charts", "Biểu đồ"),
                 ("TC29", "Danh sách tập dữ liệu", "/tablemodelview/list/", "Datasets", "Tập dữ liệu"),
                 ("TC30", "SQL Lab", "/sqllab/", "Dashboards", "Bảng điều khiển")]
        for tid, name, path, en_word, vi_word in pages:
            def t_lang_page(path=path, en_word=en_word, vi_word=vi_word):
                page.goto(URL + path, wait_until="domcontentloaded")
                page.wait_for_selector("#main-menu", timeout=60000)
                page.wait_for_timeout(2500)
                url0 = page.url
                switch_lang(page, "en")
                page.wait_for_selector("#main-menu", timeout=60000)
                page.wait_for_timeout(2000)
                l1, u1 = page.evaluate(BOOT_LOCALE_JS), page.url
                en_ok = page.locator(f"#app >> text={en_word}").count() > 0 or page.locator(f"text={en_word}").count() > 0
                switch_lang(page, "vi")
                page.wait_for_selector("#main-menu", timeout=60000)
                page.wait_for_timeout(2000)
                l2, u2 = page.evaluate(BOOT_LOCALE_JS), page.url
                vi_ok = page.locator(f"text={vi_word}").count() > 0
                bad, _ = con.take()
                ok = u1 == url0 and u2 == url0 and l1 == "en" and l2 == "vi" and en_ok and vi_ok and not bad
                return ok, f"URL {path} giữ nguyên ({u1 == url0}/{u2 == url0}), locale {l1}→{l2}, '{en_word}'={en_ok}, '{vi_word}'={vi_ok}, lỗi console={bad or 0}"

            run(tid, f"Đổi ngôn ngữ vi→en→vi tại {name}", f"Mở {path} → English → Tiếng Việt",
                f"Ở nguyên {path}; chữ giao diện đổi ('{en_word}' rồi '{vi_word}')", t_lang_page)

        # ---------------- Link về landing page ----------------
        def to_web(route):
            resp = ctx.request.get(route.request.url.replace(PUBLIC_LANDING, LANDING))
            route.fulfill(response=resp)

        ctx.route(f"{PUBLIC_LANDING}/**", to_web)

        def t_logo():
            goto_dash(page)
            a = page.locator("#main-menu a.navbar-brand")
            href = a.get_attribute("href")
            with page.expect_navigation(timeout=30000):
                a.click()
            page.wait_for_load_state("domcontentloaded")
            ok = href == f"{PUBLIC_LANDING}/" and page.url.startswith(PUBLIC_LANDING) and "Olist Insight" in page.title()
            return ok, f"href={href}, sau khi bấm: {page.url} ({page.title()[:40]!r})"

        run("TC31", "Logo → landing page", "Trên dashboard bấm logo Olist Insight",
            "Mở http://localhost:8090/ (landing Olist Insight)", t_logo)

        def t_home_btn():
            goto_dash(page)
            a = page.locator('#main-menu a[title="Trang giới thiệu"]')
            href, label = a.get_attribute("href"), a.evaluate("e => getComputedStyle(e, '::after').content")
            with ctx.expect_page(timeout=30000) as pop:
                a.click()
            np = pop.value
            np.wait_for_load_state("domcontentloaded")
            ok = href == f"{PUBLIC_LANDING}/" and np.url.startswith(PUBLIC_LANDING) and "Olist Insight" in np.title() and "Trang giới thiệu" in label
            note = f"href={href}, nhãn={label}, tab mới: {np.url}"
            np.close()
            return ok, note

        run("TC32", "Nút 'Trang giới thiệu' → landing page", "Bấm nút 'Trang giới thiệu' ở thanh menu phải",
            "Mở landing ở tab mới", t_home_btn)
        ctx.close()

        # ---------------- Landing page ----------------
        lctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="vi-VN")
        lp = lctx.new_page()
        lcon = Console(lp)
        kpi_resp = {}
        lp.on("response", lambda r: r.url.endswith("data/kpi.json") and kpi_resp.setdefault("r", r))

        def t_landing_load():
            r = lp.goto(f"{LANDING}/", wait_until="networkidle")
            lp.wait_for_function("document.querySelectorAll('#ins-cat li').length > 0", timeout=20000)
            lp.wait_for_timeout(1500)
            bad, benign = lcon.take()
            return (r.ok and "Olist Insight" in lp.title() and not bad,
                    f"HTTP {r.status}, title={lp.title()[:50]!r}, lỗi console={bad or 0}" + (f", vô hại={len(benign)}" if benign else ""))

        run("TC33", "Landing page tải được, không lỗi JS", f"Mở {PUBLIC_LANDING}/ (trong Docker: {LANDING}/)",
            "HTTP 200, tiêu đề Olist Insight, không lỗi console/pageerror", t_landing_load)

        def t_kpi_json():
            r = kpi_resp.get("r")
            js = r.json() if r else {}
            n = lp.locator("#ins-cat li").count()
            return (bool(r) and r.ok and bool(js) and n > 0, f"kpi.json HTTP {r.status if r else '-'}, {len(json.dumps(js))} byte, {n} dòng top danh mục")

        run("TC34", "Landing tải data/kpi.json", "Theo dõi request data/kpi.json khi mở trang",
            "HTTP 200, JSON hợp lệ, phần Insight được điền số liệu", t_kpi_json)

        def t_hero_anim():
            t1 = lp.locator("#ticker").inner_text()
            b1 = lp.locator("#chart .bar").count()
            lp.wait_for_timeout(3500)
            t2 = lp.locator("#ticker").inner_text()
            b2 = lp.locator("#chart .bar").count()
            return (t1 != t2 and b2 >= b1 and b2 > 0, f"ticker {t1[:28]!r} → {t2[:28]!r}; số cột {b1} → {b2}")

        run("TC35", "Biểu đồ hero 'live replay' chạy", "Đọc dòng ticker + số cột SVG, chờ 3,5 s, đọc lại",
            "Ticker đổi tháng, số cột tăng/không giảm", t_hero_anim)

        def t_dash_link():
            hrefs = lp.eval_on_selector_all('a:has-text("dashboard")', "els => els.map(e => e.href)")
            ok_href = bool(hrefs) and all(h == PUBLIC_DASH for h in hrefs)
            sctx = browser.new_context(viewport={"width": 1440, "height": 900})
            sp = sctx.new_page()
            login(sp)
            sp.goto(PUBLIC_DASH.replace("http://localhost:8088", URL), wait_until="domcontentloaded")
            sp.wait_for_selector('[role="tab"]', timeout=120000)
            ok_dash = "olist-presentation" in sp.url and sp.locator('[role="tab"]').count() == 7
            sctx.close()
            return ok_href and ok_dash, f"{len(hrefs)} link 'dashboard' → {sorted(set(hrefs))}; mở link (đã đăng nhập) thấy 7 tab={ok_dash}"

        run("TC36", "Nút 'Mở dashboard' mở đúng dashboard Superset", "Đọc href các nút dashboard, mở URL đó với phiên đã đăng nhập",
            f"href = {PUBLIC_DASH}; trang dashboard 7 tab hiển thị", t_dash_link)

        def t_github():
            hrefs = sorted(set(lp.eval_on_selector_all('a[href*="github.com"]', "els => els.map(e => e.href)")))
            try:
                st = lctx.request.get(GITHUB, timeout=20000).status
            except Exception as e:  # noqa: BLE001
                st = f"không truy cập được ({type(e).__name__})"
            return hrefs == [GITHUB] and st == 200, f"href={hrefs}, GET {GITHUB} → {st}"

        run("TC37", "Link GitHub đúng", "Đọc mọi link github.com trên landing, GET thử", f"Mọi link = {GITHUB}, HTTP 200", t_github)
        lctx.close()

        def t_mobile():
            mctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
            mp = mctx.new_page()
            mcon = Console(mp)
            mp.goto(f"{LANDING}/", wait_until="networkidle")
            mp.wait_for_timeout(1500)
            sw, iw = mp.evaluate("() => [document.documentElement.scrollWidth, window.innerWidth]")
            bad, _ = mcon.take()
            mctx.close()
            return sw <= iw and not bad, f"scrollWidth={sw}, innerWidth={iw}, lỗi console={bad or 0}"

        run("TC38", "Landing responsive 390 px", "Mở landing với viewport 390×844 (mobile)",
            "Không cuộn ngang (scrollWidth ≤ 390), không lỗi JS", t_mobile)
        browser.close()

    # ---------------- Export / import, lệnh README (kiểm tra phía host + tệp) ----------------
    def t_export_zip():
        z = zipfile.ZipFile(ROOT / "superset" / "export" / "dashboard_olist_presentation.zip")
        names = z.namelist()
        charts = [n for n in names if "/charts/" in n]
        dash = [n for n in names if "/dashboards/" in n]
        css_ok = bool(dash) and "css: \"/* Olist Insight" in z.read(dash[0]).decode("utf-8", "ignore")
        return len(charts) == 45 and len(dash) == 1 and css_ok, f"{len(charts)} chart, {len(dash)} dashboard, css Olist Insight trong YAML={css_ok}"

    run("TC39", "ZIP export dashboard đầy đủ", "Đọc superset/export/dashboard_olist_presentation.zip",
        "1 dashboard (có CSS) + 45 chart", t_export_zip)

    imp = host.get("import")
    if imp:
        record("TC40", "Import dashboard từ ZIP (import_dashboard.py)",
               "docker compose run --rm tools python superset/import_dashboard.py", "HTTP 200, rồi dashboard vẫn chạy (TC04–TC30 chạy sau import)",
               imp.get("exit") == 0 and str(imp.get("output", "")).startswith("200"), str(imp.get("output", ""))[:120])
    else:
        record("TC40", "Import dashboard từ ZIP (import_dashboard.py)", "chạy qua scripts/qa_run.ps1", "HTTP 200", False,
               "chưa có evidence/qa_host_checks.json (chạy scripts/qa_run.ps1)")

    def t_readme():
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        scripts = sorted(set(re.findall(r"python ((?:loader|superset|scripts)/[\w./]+\.py)", text)))
        missing = [s for s in scripts if not (ROOT / s).exists()]
        used = set(re.findall(r"docker compose run --rm (?:-e \S+ )*([\w-]+)", text))
        used |= {w for s in re.findall(r"docker compose (?:up -d|build) ([\w -]+)", text) for w in s.split()}
        known = set(host.get("services", []))
        unknown = sorted(u for u in used if known and u not in known and not u.endswith(".py"))
        cfg = host.get("compose_config", {})
        ok = not missing and cfg.get("exit") == 0 and cfg.get("exit_all_profiles") == 0 and known and not unknown
        return ok, (f"{len(scripts)} script được README nhắc đều tồn tại{'' if not missing else ', thiếu ' + str(missing)}; "
                    f"docker compose config: {cfg.get('exit')}/{cfg.get('exit_all_profiles')} (0 = hợp lệ); "
                    f"service: {sorted(used & known)}{', lạ: ' + str(unknown) if unknown else ''}")

    run("TC41", "Lệnh chạy trong README hợp lệ", "Kiểm script/service README nhắc tới; docker compose config -q (mọi profile)",
        "Mọi tệp tồn tại, service có trong compose, config hợp lệ", t_readme)

    write_report()


def write_report() -> None:
    cnt = {k: sum(r["result"] == k for r in results) for k in ("PASS", "FAIL", "KNOWN")}
    esc = lambda s: str(s).replace("|", "\\|").replace("\n", " ")  # noqa: E731
    lines = [
        "# Kết quả kiểm thử QA (tự động)",
        "",
        f"Chạy lúc {time.strftime('%d/%m/%Y %H:%M')} bằng `scripts/qa_run.ps1` (Playwright Chromium trong service "
        "`screenshots` + kiểm tra phía host). Superset 4.1.2 tại `:8088`, landing page tại `:8090`.",
        "",
        f"**Tổng: {len(results)} ca – PASS {cnt['PASS']}, FAIL {cnt['FAIL']}, KNOWN {cnt['KNOWN']}.**",
        "",
        "| ID | Ca kiểm thử | Bước | Kỳ vọng | Kết quả | Ghi chú |",
        "|---|---|---|---|---|---|",
    ]
    lines += [f"| {r['id']} | {esc(r['case'])} | {esc(r['steps'])} | {esc(r['expected'])} | **{r['result']}** | {esc(r['note'])} |"
              for r in results]
    lines += ["", "## Lỗi console được bỏ qua (vô hại)", ""]
    if console_seen:
        lines += [f"- `{esc(m)}` – {why}" for m, why in console_seen.items()]
    else:
        lines += ["- Không có: mọi trang đã kiểm không phát sinh lỗi console nào."]
    lines += ["", "Ảnh kèm: `evidence/qa_kpi_loc_1280.png` (thẻ KPI tab 1 khi lọc 2018 + SP ở 1280 px).", ""]
    (EVID / "qa_test_cases.md").write_text("\n".join(lines), encoding="utf-8")
    (EVID / "qa_results.json").write_text(json.dumps({"summary": cnt, "results": results, "benign_console": console_seen},
                                                     ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(cnt))


if __name__ == "__main__":
    main()
