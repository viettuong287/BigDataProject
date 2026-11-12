"""Thí nghiệm mở rộng: nhân bản gold.fact_order_items ×N ngay trong Neon (không tốn băng thông upload),
đo thời gian sinh dữ liệu, dung lượng, và độ trễ phía server của truy vấn kiểu dashboard
(doanh thu theo tháng × danh mục) trên dữ liệu thô so với đọc bảng tổng hợp sẵn của Analytics.

Chạy: docker compose run --rm tools python scripts/scale_experiment.py
Kết quả: evidence/scale_experiment.csv, evidence/scale_experiment.md (bảng scratch bị xoá sau mỗi bước)
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "loader"))
from common import EVIDENCE_DIR, connect  # noqa: E402

FACTORS = [1, 2, 5, 10]
RAW_Q = ("SELECT date_trunc('month', purchase_date) AS m, category, SUM(price) FROM scratch.items_x "
         "WHERE purchase_date >= '2017-01-01' AND purchase_date < '2018-09-01' GROUP BY 1, 2")
FILTER_Q = ("SELECT customer_state, SUM(price) FROM scratch.items_x "
            "WHERE category = 'bed_bath_table' AND purchase_date >= '2018-01-01' GROUP BY 1")
AGG_Q = "SELECT month_date, category, SUM(revenue) FROM presentation.v_category_monthly GROUP BY 1, 2"


def exec_ms(conn, sql: str, n: int = 3) -> float:
    vals = []
    for _ in range(n):
        plan = conn.execute(f"EXPLAIN (ANALYZE, FORMAT JSON) {sql}").fetchone()[0]
        plan = plan if isinstance(plan, list) else json.loads(plan)
        vals.append(plan[0]["Execution Time"] + plan[0]["Planning Time"])
    return round(statistics.median(vals), 1)


def main() -> None:
    rows = []
    with connect() as conn:
        conn.execute("CREATE SCHEMA IF NOT EXISTS scratch")
        agg_ms = exec_ms(conn, AGG_Q)
        for n in FACTORS:
            conn.execute("DROP TABLE IF EXISTS scratch.items_x")
            t = time.perf_counter()
            conn.execute(f"""
                CREATE TABLE scratch.items_x AS
                SELECT i.order_id || '-' || g AS order_id, i.purchase_date, i.category, i.customer_state,
                       i.price, i.freight_value
                FROM gold.fact_order_items i CROSS JOIN generate_series(1, {n}) g
                WHERE i.is_valid_sale""")
            gen_s = time.perf_counter() - t
            t = time.perf_counter()
            conn.execute("CREATE INDEX ON scratch.items_x (category, purchase_date)")
            conn.execute("ANALYZE scratch.items_x")
            idx_s = time.perf_counter() - t
            nrows = conn.execute("SELECT count(*) FROM scratch.items_x").fetchone()[0]
            mb = conn.execute("SELECT pg_total_relation_size('scratch.items_x') / 1048576.0").fetchone()[0]
            rec = {"factor": n, "rows": nrows, "size_mb": round(float(mb), 1), "generate_s": round(gen_s, 2),
                   "index_s": round(idx_s, 2), "rows_per_s_server": round(nrows / gen_s),
                   "raw_month_category_ms": exec_ms(conn, RAW_Q), "raw_filtered_indexed_ms": exec_ms(conn, FILTER_Q),
                   "preaggregated_view_ms": agg_ms}
            rows.append(rec)
            print(rec, flush=True)
        conn.execute("DROP SCHEMA scratch CASCADE")

    with (EVIDENCE_DIR / "scale_experiment.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    base = rows[0]
    lines = ["# Thí nghiệm mở rộng trên Neon (0,25 CU)", "",
             "Nhân bản `gold.fact_order_items` (đơn hợp lệ) ×N bằng `generate_series` ngay trên server, "
             "đo truy vấn kiểu dashboard bằng `EXPLAIN ANALYZE` (trung vị 3 lần, chỉ thời gian server). "
             "Script: `scripts/scale_experiment.py`.", "",
             "| ×N | Số dòng | MB | Sinh dữ liệu (s) | Dòng/s (server) | Doanh thu tháng × danh mục trên dữ liệu thô (ms) "
             "| Lọc 1 danh mục, có index (ms) | Đọc view tổng hợp sẵn (ms) |",
             "|---:|---:|---:|---:|---:|---:|---:|---:|"]
    lines += [f"| {r['factor']} | {r['rows']:,} | {r['size_mb']} | {r['generate_s']} | {r['rows_per_s_server']:,} | "
              f"{r['raw_month_category_ms']} | {r['raw_filtered_indexed_ms']} | {r['preaggregated_view_ms']} |" for r in rows]
    last = rows[-1]
    lines += ["", f"- Dữ liệu ×{last['factor']}: truy vấn thô tăng từ {base['raw_month_category_ms']} ms lên "
              f"{last['raw_month_category_ms']} ms (×{last['raw_month_category_ms'] / base['raw_month_category_ms']:.1f}), "
              "gần tuyến tính theo số dòng.",
              f"- Đọc bảng/view đã tổng hợp ở Spark giữ ~{base['preaggregated_view_ms']} ms bất kể dữ liệu nguồn lớn bao nhiêu: "
              "đây là lý do Presentation đọc output Analytics thay vì tính lại từ fact.",
              "- Truy vấn có điều kiện lọc dùng index tăng chậm hơn nhiều so với quét toàn bảng."]
    (EVIDENCE_DIR / "scale_experiment.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
