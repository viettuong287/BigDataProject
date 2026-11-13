"""Chụp ảnh dashboard Superset + đo thời gian tải (cold vs cache) + đo độ trễ từng chart qua API.

Chạy (Superset đang chạy, nên xoá cache trước để đo cold):
    docker exec olist-superset bash -c 'rm -rf /app/superset_home/cache/*'
    docker compose run --rm screenshots

Kết quả trong evidence/:
    dashboard_tab*.png, filter_*.png, watchlist_*.png    ảnh minh chứng
    dashboard_load_time.csv                               thời gian render từng tab: cold vs cache
    superset_chart_latency.csv                            độ trễ /api/v1/chart/data từng chart: force (bỏ cache) vs cache
"""
from __future__ import annotations

import csv
import json
import os
import statistics
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / "evidence"
URL = os.environ.get("SUPERSET_URL", "http://localhost:8088").rstrip("/")
USER = os.environ.get("SUPERSET_ADMIN_USER", "admin")
PWD = os.environ.get("SUPERSET_ADMIN_PASSWORD", "admin")
INFO = json.loads((ROOT / "superset" / "export" / "build_info.json").read_text(encoding="utf-8"))
DASH = f"{URL}/superset/dashboard/{INFO['dashboard_id']}/"
F = {fid.split("-")[1][2:]: fid for fid in INFO["filters"]}  # 'customerst' -> NATIVE_FILTER-02customerst

TABS = ["tong_quan_xu_huong", "danh_muc_mua_vu", "dia_ly_logistics", "khach_hang_rfm", "seller",
        "giao_tre_review_thanh_toan", "goi_y_quyet_dinh_nguon_du_lieu"]

STATE_JS = """() => {
    const hs = [...document.querySelectorAll('.dashboard-component-chart-holder')]
        .filter(h => h.offsetParent !== null && h.getBoundingClientRect().width > 0);
    const busy = hs.filter(h => /Waiting on|Loading|Đang chờ|Đang tải/.test(h.innerText)).length;
    const errors = hs.filter(h => h.querySelector('.ant-alert-error, .alert-danger') || /Unexpected error|Lỗi không mong đợi/.test(h.innerText))
                     .map(h => (h.innerText || '').split('\\n')[0]);
    return {n: hs.length, busy, errors};
}"""


def select(key: str, col: str, values: list[str]) -> dict:
    fid = F[key]
    return {fid: {"id": fid, "extraFormData": {"filters": [{"col": col, "op": "IN", "val": values}]},
                  "filterState": {"value": values, "label": ", ".join(values)}, "ownState": {}}}


def time_range(rng: str) -> dict:
    fid = F["monthdate"]
    return {fid: {"id": fid, "extraFormData": {"time_range": rng}, "filterState": {"value": rng}, "ownState": {}}}


FILTERS = [
    ("filter_tab1_thoi_gian_2018_bang_SP", 0,
     {**time_range("2018-01-01 : 2018-09-01"), **select("customerst", "customer_state", ["SP"])}),
    ("filter_tab2_danh_muc_bed_bath_health_watches", 1,
     select("category", "category", ["bed_bath_table", "health_beauty", "watches_gifts"])),
    ("filter_tab3_vung_nordeste", 2, select("region", "region", ["Nordeste"])),
    ("filter_tab4_rfm_khach_mua_lai_bang_RJ", 3,
     {**select("rfmsegment", "rfm_segment", ["Champions", "Loyal", "At Risk"]),
      **select("customerst", "customer_state", ["RJ"])}),
    ("filter_tab5_bang_seller_SP", 4, select("sellerstat", "seller_state", ["SP"])),
    ("filter_tab6_pttt_boleto", 5, select("mainpaymen", "main_payment_type", ["boleto"])),
]


def wait_rendered(page, timeout_s: float = 180) -> tuple[float, dict]:
    t0 = time.perf_counter()
    stable, st = 0, {}
    while time.perf_counter() - t0 < timeout_s:
        st = page.evaluate(STATE_JS)
        ready = st["n"] > 0 and st["busy"] == 0 and time.perf_counter() - t0 > 0.8
        stable = stable + 1 if ready else 0
        if stable >= 4:
            return time.perf_counter() - t0 - 0.75, st
        time.sleep(0.25)
    return time.perf_counter() - t0, st


def open_tab(page, idx: int) -> tuple[float, dict]:
    page.locator('[role="tab"]').nth(idx).click()
    return wait_rendered(page)


def main() -> None:
    captured: dict[int, dict] = {}  # slice_id -> payload của request chart/data do trình duyệt gửi

    def on_request(req):
        if req.method == "POST" and "/api/v1/chart/data" in req.url:
            try:
                body = req.post_data_json
                sid = body.get("form_data", {}).get("slice_id")
                if sid and sid not in captured:
                    captured[sid] = body
            except Exception:
                pass

    load_rows, lat_rows = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1600, "height": 1900}, locale="vi-VN")
        page = ctx.new_page()
        page.on("request", on_request)
        page.goto(f"{URL}/login/")
        page.fill("#username", USER)
        page.fill("#password", PWD)
        page.keyboard.press("Enter")
        page.wait_for_url("**/superset/welcome/**", timeout=60000)
        csrf = ctx.request.get(f"{URL}/api/v1/security/csrf_token/").json()["result"]
        headers = {"X-CSRFToken": csrf, "Referer": URL, "Content-Type": "application/json"}

        # ---- Lượt 1 (cold) + chụp ảnh; lượt 2 (cache) chỉ đo ----
        timings: dict[int, dict] = {}
        for run in ("cold", "warm"):
            t0 = time.perf_counter()
            page.goto(DASH, wait_until="domcontentloaded")
            page.wait_for_selector('[role="tab"]', timeout=120000)
            shell = time.perf_counter() - t0
            for i, slug in enumerate(TABS):
                secs, st = open_tab(page, i)
                rec = timings.setdefault(i, {"tab": f"{i + 1} · {slug}", "components": st["n"]})
                rec[f"{run}_s"] = round(secs, 2)
                rec[f"{run}_errors"] = len(st["errors"])
                if run == "cold":
                    page.wait_for_timeout(1500)
                    page.screenshot(path=str(EVID / f"dashboard_tab{i + 1}_{slug}.png"), full_page=True)
                    if slug == "seller":
                        page.locator(".dashboard-component-chart-holder", has_text="Người bán cần theo dõi (watchlist)").first \
                            .screenshot(path=str(EVID / "watchlist_seller_canh_bao.png"))
                    if slug.startswith("goi_y"):
                        page.locator(".dashboard-component-chart-holder", has_text="Gợi ý quyết định (luật").first \
                            .screenshot(path=str(EVID / "watchlist_goi_y_quyet_dinh.png"))
                print(f"[{run}] tab {i + 1} {slug:<32} {st['n']:>2} thành phần  {secs:6.2f}s  lỗi={st['errors']}", flush=True)
            timings.setdefault("shell", {})[run] = round(shell, 2)
        shell = timings.pop("shell")
        for rec in timings.values():
            load_rows.append({"kind": "tab", "scenario": rec["tab"], "components": rec["components"],
                              "cold_s": rec["cold_s"], "warm_s": rec["warm_s"],
                              "errors": rec["cold_errors"] + rec["warm_errors"]})

        # ---- Kịch bản bộ lọc native (permalink lưu trạng thái bộ lọc) ----
        for name, idx, mask in FILTERS:
            r = ctx.request.post(f"{URL}/api/v1/dashboard/{INFO['dashboard_id']}/permalink",
                                 data={"dataMask": mask, "activeTabs": [f"TAB-t{idx + 1}"], "urlParams": []},
                                 headers=headers)
            page.goto(f"{URL}/superset/dashboard/p/{r.json()['key']}/", wait_until="domcontentloaded")
            page.wait_for_selector('[role="tab"]', timeout=120000)
            secs, st = open_tab(page, idx)
            page.wait_for_timeout(1500)
            page.screenshot(path=str(EVID / f"{name}.png"), full_page=True)
            load_rows.append({"kind": "filter", "scenario": name, "components": st["n"], "cold_s": round(secs, 2),
                              "warm_s": "", "errors": len(st["errors"])})
            print(f"[filter] {name:<45} {secs:6.2f}s  lỗi={st['errors']}", flush=True)

        # ---- Độ trễ từng chart qua REST API (cookie phiên + CSRF), replay đúng payload trình duyệt gửi ----
        names = {cid: key for key, cid in INFO["charts"].items()}
        for sid, body in sorted(captured.items()):
            res = {}
            for mode, force in (("force", True), ("cache", False)):
                samples, status, nrows = [], "ok", None
                for _ in range(3):
                    payload = {**body, "force": force}
                    t = time.perf_counter()
                    r = ctx.request.post(f"{URL}/api/v1/chart/data", data=json.dumps(payload), headers=headers)
                    samples.append((time.perf_counter() - t) * 1000)
                    if not r.ok:
                        status = f"HTTP {r.status}: {r.text()[:120]}"
                        break
                    nrows = sum(q.get("rowcount", 0) for q in r.json().get("result", []))
                res[mode] = (round(statistics.median(samples), 1), status, nrows)
            lat_rows.append({"chart_id": sid, "key": names.get(sid, ""),
                             "viz_type": body.get("form_data", {}).get("viz_type", ""),
                             "rows": res["force"][2], "force_median_ms": res["force"][0],
                             "cache_median_ms": res["cache"][0],
                             "status": res["force"][1] if res["force"][1] != "ok" else res["cache"][1]})
            print(f"[api] chart {sid:>3} {names.get(sid, ''):<18} force {res['force'][0]:7.1f} ms  cache {res['cache'][0]:6.1f} ms  {lat_rows[-1]['status']}", flush=True)
        browser.close()

    with (EVID / "dashboard_load_time.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(load_rows[0]))
        w.writeheader()
        w.writerows(load_rows)
    with (EVID / "superset_chart_latency.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(lat_rows[0]))
        w.writeheader()
        w.writerows(lat_rows)

    tabs = [r for r in load_rows if r["kind"] == "tab"]
    ok = [r for r in lat_rows if r["status"] == "ok"]
    summary = {
        "dashboard_shell_s": shell,
        "tabs_cold_total_s": round(sum(r["cold_s"] for r in tabs), 2),
        "tabs_warm_total_s": round(sum(r["warm_s"] for r in tabs), 2),
        "tab_cold_median_s": statistics.median(r["cold_s"] for r in tabs),
        "tab_warm_median_s": statistics.median(r["warm_s"] for r in tabs),
        "charts_measured": len(lat_rows), "charts_ok": len(ok),
        "chart_force_median_ms": statistics.median(r["force_median_ms"] for r in ok) if ok else None,
        "chart_cache_median_ms": statistics.median(r["cache_median_ms"] for r in ok) if ok else None,
    }
    (EVID / "dashboard_load_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
