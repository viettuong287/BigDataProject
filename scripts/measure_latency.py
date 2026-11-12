"""Đo độ trễ các truy vấn mà dashboard gửi xuống Neon (qua endpoint pooled giống Superset).

Mỗi truy vấn: 1 lần làm nóng + N lần đo phía client (gồm mạng VN → Singapore),
và EXPLAIN (ANALYZE) để lấy thời gian thực thi phía server.
Kết quả: evidence/query_latency.csv, evidence/query_latency.md

Chạy: docker compose run --rm tools python scripts/measure_latency.py
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "loader"))
from common import EVIDENCE_DIR, connect  # noqa: E402

N = 5
P = "presentation"
QUERIES = [
    ("Tổng quan", "Thẻ KPI (6 chỉ số) – v_orders",
     f"SELECT SUM(revenue), COUNT(*), COUNT(DISTINCT customer_unique_id), AVG(order_value), AVG(late_flag), AVG(review_score) FROM {P}.v_orders"),
    ("Tổng quan", "Thẻ KPI có lọc bang SP + 2018",
     f"SELECT SUM(revenue), COUNT(*), COUNT(DISTINCT customer_unique_id), AVG(order_value), AVG(late_flag), AVG(review_score) FROM {P}.v_orders "
     "WHERE customer_state IN ('SP') AND month_date >= '2018-01-01' AND month_date < '2018-09-01'"),
    ("Tổng quan", "Xu hướng tháng – v_kpi_monthly", f"SELECT * FROM {P}.v_kpi_monthly ORDER BY month_date"),
    ("Danh mục", "Pareto top 25 – v_category_pareto",
     f"SELECT category, SUM(revenue), MAX(cumulative_share_pct) FROM {P}.v_category_pareto WHERE revenue_rank <= 25 GROUP BY category ORDER BY 2 DESC"),
    ("Danh mục", "Heatmap mùa vụ – v_category_seasonality",
     f"SELECT purchase_month, category, SUM(pct_of_category_year) FROM {P}.v_category_seasonality WHERE revenue_rank <= 12 GROUP BY 1, 2"),
    ("Danh mục", "Xu hướng danh mục – v_category_monthly",
     f"SELECT month_date, category, SUM(revenue) FROM {P}.v_category_monthly GROUP BY 1, 2"),
    ("Danh mục", "Doanh thu danh mục × bang (lọc 3 danh mục) – v_sales_items",
     f"SELECT category, customer_state, SUM(revenue) FROM {P}.v_sales_items "
     "WHERE category IN ('bed_bath_table','health_beauty','watches_gifts') GROUP BY 1, 2"),
    ("Địa lý", "Bản đồ / bảng bang – v_state_logistics", f"SELECT * FROM {P}.v_state_logistics"),
    ("Địa lý", "Khoảng cách – v_insight_distance", f"SELECT * FROM {P}.v_insight_distance ORDER BY band_label"),
    ("Khách hàng", "Pie phân khúc RFM – v_rfm_customers (94.983 dòng)",
     f"SELECT rfm_segment, COUNT(*) FROM {P}.v_rfm_customers GROUP BY 1"),
    ("Khách hàng", "Cụm K-Means lọc bang RJ + 3 segment",
     f"SELECT cluster_name, COUNT(*) FROM {P}.v_rfm_customers WHERE customer_state IN ('RJ') "
     "AND rfm_segment IN ('Champions','Loyal','At Risk') GROUP BY 1"),
    ("Khách hàng", "Bảng segment – v_rfm_segments", f"SELECT * FROM {P}.v_rfm_segments ORDER BY segment_order"),
    ("Seller", "Pareto nhóm seller – v_seller_pareto",
     f"SELECT pareto_group, COUNT(*), SUM(revenue_share_pct) FROM {P}.v_seller_pareto GROUP BY 1"),
    ("Seller", "Bubble top 300 seller – v_seller_pareto",
     f"SELECT seller_short, watchlist_label, MAX(avg_delivery_days), MAX(avg_review_score), SUM(revenue) "
     f"FROM {P}.v_seller_pareto WHERE revenue_rank <= 300 GROUP BY 1, 2"),
    ("Seller", "Bảng watchlist – v_seller_watchlist", f"SELECT * FROM {P}.v_seller_watchlist ORDER BY violations DESC, revenue DESC"),
    ("Review/PTTT", "Trễ vs review – v_late_vs_review", f"SELECT * FROM {P}.v_late_vs_review"),
    ("Review/PTTT", "Ngưỡng ngày trễ – v_delay_vs_review", f"SELECT * FROM {P}.v_delay_vs_review"),
    ("Review/PTTT", "Payment mix – v_payment_mix", f"SELECT * FROM {P}.v_payment_mix"),
    ("Review/PTTT", "Pie PTTT – v_orders", f"SELECT main_payment_type, COUNT(*) FROM {P}.v_orders GROUP BY 1"),
    ("Quyết định", "Gợi ý quyết định – v_decision_hints", f"SELECT * FROM {P}.v_decision_hints ORDER BY priority"),
    ("Quyết định", "Nhật ký nạp – v_load_log", f"SELECT * FROM {P}.v_load_log"),
    # So sánh: tính Pareto danh mục trực tiếp từ fact thay vì dùng bảng Analytics đã tổng hợp sẵn.
    ("So sánh", "Pareto danh mục tính lại từ gold.fact_order_items (không dùng bảng tổng hợp)",
     "SELECT category, SUM(price) AS revenue, ROUND(100.0 * SUM(SUM(price)) OVER (ORDER BY SUM(price) DESC) / SUM(SUM(price)) OVER (), 2) "
     "FROM gold.fact_order_items WHERE is_valid_sale AND purchase_date >= '2017-01-01' AND purchase_date < '2018-09-01' "
     "GROUP BY category ORDER BY 2 DESC LIMIT 25"),
]


def server_ms(conn, sql: str) -> float:
    plan = conn.execute(f"EXPLAIN (ANALYZE, FORMAT JSON) {sql}").fetchone()[0]
    plan = plan if isinstance(plan, list) else json.loads(plan)
    return plan[0]["Execution Time"] + plan[0].get("Planning Time", 0)


def main() -> None:
    t = time.perf_counter()
    conn = connect(direct=False)
    connect_ms = (time.perf_counter() - t) * 1000
    rows = []
    for tab, name, sql in QUERIES:
        cur = conn.execute(sql)
        nrows = len(cur.fetchall())
        samples = []
        for _ in range(N):
            t = time.perf_counter()
            conn.execute(sql).fetchall()
            samples.append((time.perf_counter() - t) * 1000)
        srv = server_ms(conn, sql)
        rows.append({"tab": tab, "query": name, "rows_returned": nrows,
                     "client_median_ms": round(statistics.median(samples), 1),
                     "client_p95_ms": round(sorted(samples)[-1], 1),
                     "server_exec_ms": round(srv, 2)})
        print(f"{tab:<12} {name[:60]:<60} {rows[-1]['client_median_ms']:7.1f} ms (server {srv:6.2f} ms)")
    rtt = []
    for _ in range(N):
        t = time.perf_counter()
        conn.execute("SELECT 1").fetchall()
        rtt.append((time.perf_counter() - t) * 1000)
    conn.close()

    with (EVIDENCE_DIR / "query_latency.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    dash = [r for r in rows if r["tab"] != "So sánh"]
    med = statistics.median(r["client_median_ms"] for r in dash)
    mx = max(dash, key=lambda r: r["client_median_ms"])
    srv_med = statistics.median(r["server_exec_ms"] for r in dash)
    lines = [
        "# Độ trễ truy vấn dashboard (Neon Postgres)",
        "",
        f"Thời điểm đo: {datetime.now():%Y-%m-%d %H:%M:%S} · Script: `scripts/measure_latency.py` · "
        f"Endpoint pooled (PgBouncer) như Superset · {N} lần đo/truy vấn sau 1 lần làm nóng.",
        "",
        f"- Thiết lập kết nối TLS mới: **{connect_ms:.0f} ms** (Superset mở kết nối mới cho mỗi truy vấn).",
        f"- Round-trip mạng `SELECT 1`: **{statistics.median(rtt):.0f} ms** (máy local → Neon ap-southeast-1).",
        f"- Trung vị {len(dash)} truy vấn dashboard: **{med:.0f} ms** phía client, **{srv_med:.2f} ms** phía server.",
        f"- Chậm nhất: {mx['query']} – {mx['client_median_ms']:.0f} ms (server {mx['server_exec_ms']:.1f} ms).",
        "",
        "| Tab | Truy vấn | Số dòng trả về | Client trung vị (ms) | Client max (ms) | Server thực thi (ms) |",
        "|---|---|---:|---:|---:|---:|",
    ]
    lines += [f"| {r['tab']} | {r['query']} | {r['rows_returned']:,} | {r['client_median_ms']} | {r['client_p95_ms']} | {r['server_exec_ms']} |"
              for r in rows]
    lines += ["", "Ghi chú: thời gian client = mạng + thực thi; phần lớn là round-trip mạng. "
              "Dòng 'So sánh' cho thấy chi phí khi tính lại từ bảng fact thay vì đọc bảng Analytics đã tổng hợp sẵn."]
    (EVIDENCE_DIR / "query_latency.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[4:8]))


if __name__ == "__main__":
    main()
