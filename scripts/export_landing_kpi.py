"""Xuất số liệu thật từ Neon (schema presentation/analytics) ra web/data/kpi.json cho landing page.

Chạy:
    docker compose run --rm tools python scripts/export_landing_kpi.py

Landing page (web/) là trang tĩnh nên chỉ đọc file JSON này; chạy lại script để cập nhật số liệu sau mỗi lần nạp.
Các số đo hiệu năng (latency, scale, thời gian tải) lấy từ evidence/ do các script đo khác sinh ra.
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "loader"))
from common import EVIDENCE_DIR, ROOT, connect  # noqa: E402

OUT = ROOT / "web" / "data" / "kpi.json"


def plain(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    return v


def rows(cur, sql: str) -> list[dict]:
    cur.execute(sql)
    cols = [d.name for d in cur.description]
    return [{c: plain(v) for c, v in zip(cols, r)} for r in cur.fetchall()]


def read_json(name: str):
    p = EVIDENCE_DIR / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def read_csv(name: str) -> list[dict]:
    p = EVIDENCE_DIR / name
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    with connect(direct=False) as conn, conn.cursor() as cur:
        monthly = rows(cur, """
            SELECT month_label AS month, orders, customers, revenue, freight, avg_order_value,
                   avg_review_score, avg_delivery_days, late_delivery_pct, revenue_mom_pct,
                   is_black_friday_month
            FROM presentation.v_kpi_monthly ORDER BY month_date""")
        overview = rows(cur, "SELECT * FROM presentation.v_kpi_overview")[0]
        categories = rows(cur, """
            SELECT category, revenue, orders, revenue_share_pct, cumulative_share_pct
            FROM analytics.category_pareto ORDER BY revenue DESC LIMIT 6""")
        states = rows(cur, """
            SELECT customer_state, state_name, region, revenue, orders, revenue_share_pct,
                   late_delivery_pct, avg_review_score
            FROM presentation.v_state_logistics ORDER BY revenue DESC LIMIT 6""")
        segments = rows(cur, """
            SELECT rfm_segment, customers, pct_customers, crm_action
            FROM presentation.v_rfm_segments ORDER BY segment_order""")
        hints = rows(cur, """
            SELECT priority, severity, topic, signal, action
            FROM presentation.v_decision_hints ORDER BY priority""")
        watch = rows(cur, """
            SELECT COUNT(*) AS sellers, COUNT(*) FILTER (WHERE alert_level = 'ĐỎ') AS red
            FROM presentation.v_seller_watchlist""")[0]
        load = rows(cur, """
            SELECT run_id, MAX(loaded_at) AS loaded_at, COUNT(*) AS tables, SUM(rows) AS rows,
                   SUM(parquet_bytes) AS parquet_bytes, BOOL_AND(row_count_ok) AS all_ok
            FROM analytics.load_log GROUP BY run_id ORDER BY MAX(loaded_at) DESC LIMIT 1""")
        inventory = rows(cur, """
            SELECT COUNT(*) FILTER (WHERE table_type = 'BASE TABLE') AS tables,
                   COUNT(*) FILTER (WHERE table_type = 'VIEW')       AS views
            FROM information_schema.tables
            WHERE table_schema IN ('analytics', 'gold', 'presentation')""")[0]

    validation = read_json("validation.json") or {}
    anchors = [a for a in validation.get("anchors", []) if a.get("status") != "INFO"]
    row_counts = validation.get("row_counts", [])
    latency = read_csv("query_latency.csv")
    scale = read_csv("scale_experiment.csv")
    load_summary = read_json("dashboard_load_summary.json") or {}

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "Neon Postgres – presentation.v_kpi_monthly, v_kpi_overview, v_state_logistics, "
                  "v_rfm_segments, v_decision_hints, v_seller_watchlist; analytics.category_pareto, load_log",
        "monthly": monthly,
        "totals": {
            "revenue": sum(m["revenue"] for m in monthly),
            "orders": sum(m["orders"] for m in monthly),
            "months": len(monthly),
        },
        "overview": overview,
        "top_categories": categories,
        "top_states": states,
        "rfm_segments": segments,
        "decision_hints": hints,
        "watchlist": watch,
        "load": load[0] if load else None,
        "inventory": inventory,
        "quality": {
            "anchors_total": len(anchors),
            "anchors_passed": sum(a.get("status") == "ĐẠT" for a in anchors),
            "tables_total": len(row_counts),
            "tables_matched": sum(bool(r.get("ok")) for r in row_counts),
        },
        "performance": {
            "query_client_median_ms": round(statistics.median(float(r["client_median_ms"]) for r in latency), 1)
            if latency else None,
            "query_server_median_ms": round(statistics.median(float(r["server_exec_ms"]) for r in latency), 2)
            if latency else None,
            "tab_cold_median_s": load_summary.get("tab_cold_median_s"),
            "tab_warm_median_s": load_summary.get("tab_warm_median_s"),
            "chart_cache_median_ms": load_summary.get("chart_cache_median_ms"),
            "scale": [{k: float(v) for k, v in r.items()} for r in scale],
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Đã ghi {OUT.relative_to(ROOT)}: {len(monthly)} tháng, doanh thu {payload['totals']['revenue']:,.2f}, "
          f"{len(hints)} gợi ý quyết định, {payload['quality']['anchors_passed']}/{payload['quality']['anchors_total']} số neo")


if __name__ == "__main__":
    main()
