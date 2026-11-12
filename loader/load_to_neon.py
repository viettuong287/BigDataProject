"""Nạp toàn bộ output Analytics (Parquet) vào Neon Postgres.

Luồng: Parquet (data/analytics, data/gold) -> pyarrow -> CSV trong bộ nhớ -> COPY FROM STDIN
-> khoá chính / index -> ANALYZE -> ghi analytics.load_log + evidence/load_log.csv
-> áp dụng các view tầng trình bày (sql/*.sql).

Chạy:  docker compose run --rm tools python loader/load_to_neon.py [--only kpi_monthly,...] [--skip-views]
"""
from __future__ import annotations

import argparse
import csv
import io
import time
import uuid
from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pacsv
import pyarrow.dataset as ds
from psycopg import sql

from common import DATA_DIR, EVIDENCE_DIR, SQL_DIR, Tee, connect, mask, neon_url

# Khoá chính + index phụ cho từng bảng. Grain lấy từ ANALYTICS_HANDOVER.md / HANDOVER.md.
TABLES: dict[str, dict] = {
    # ---- Output Analytics (16 bảng) ----
    "analytics.kpi_monthly": {"pk": ["purchase_year", "purchase_month"], "grain": "1 tháng (2017-01→2018-08)"},
    "analytics.category_pareto": {"pk": ["category"], "grain": "1 danh mục"},
    "analytics.category_seasonality": {"pk": ["category", "purchase_month"], "grain": "1 danh mục × 1 tháng năm 2017"},
    "analytics.state_logistics": {"pk": ["customer_state"], "grain": "1 bang khách hàng"},
    "analytics.insight_distance": {"pk": ["distance_band"], "grain": "1 band khoảng cách"},
    "analytics.rfm_scores": {"pk": ["customer_unique_id"], "idx": [["rfm_segment"], ["customer_state"]], "grain": "1 khách thật"},
    "analytics.repeat_profile": {"pk": ["cohort"], "grain": "repeat vs one_shot"},
    "analytics.repeat_categories": {"pk": ["category"], "grain": "1 danh mục của khách lặp"},
    "analytics.repeat_states": {"pk": ["customer_state"], "grain": "1 bang của khách lặp"},
    "analytics.customer_segments": {"pk": ["customer_unique_id"], "idx": [["cluster"], ["rfm_segment"], ["customer_state"]], "grain": "1 khách thật + cụm K-Means"},
    "analytics.cluster_profile": {"pk": ["cluster"], "grain": "1 cụm K-Means"},
    "analytics.seller_pareto": {"pk": ["seller_id"], "idx": [["seller_state"]], "grain": "1 seller"},
    "analytics.seller_watchlist": {"pk": ["seller_id"], "grain": "seller top 10% doanh thu có vận hành kém"},
    "analytics.insight_late_vs_review": {"pk": ["delivery"], "grain": "late vs on_time"},
    "analytics.delay_vs_review": {"pk": ["delay_band"], "grain": "1 band ngày trễ"},
    "analytics.payment_mix": {"pk": ["main_payment_type", "installment_band"], "grain": "PTTT × band trả góp"},
    # ---- Gold (đầu vào của Analytics, dùng cho bộ lọc chi tiết trên dashboard) ----
    "gold.fact_orders": {"pk": ["order_id"], "idx": [["purchase_date"], ["customer_state"], ["main_payment_type"]], "grain": "1 đơn hàng"},
    "gold.fact_order_items": {"pk": ["order_id", "order_item_id"], "idx": [["purchase_date"], ["category"], ["customer_state"], ["seller_id"]], "grain": "1 sản phẩm trong 1 đơn"},
    "gold.agg_sales_monthly": {"pk": ["purchase_year", "purchase_month"], "grain": "1 tháng (gồm 2016, 2018-09)"},
    "gold.agg_category_monthly": {"pk": ["purchase_year", "purchase_month", "category"], "grain": "1 danh mục × 1 tháng"},
    "gold.agg_customer_state": {"pk": ["customer_state"], "grain": "1 bang khách hàng"},
    "gold.agg_seller_performance": {"pk": ["seller_id"], "grain": "1 seller"},
    "gold.agg_customer_rfm": {"pk": ["customer_unique_id"], "grain": "1 khách thật"},
}

LOAD_LOG_DDL = """
CREATE TABLE IF NOT EXISTS analytics.load_log (
    id             bigserial PRIMARY KEY,
    run_id         text        NOT NULL,
    schema_name    text        NOT NULL,
    table_name     text        NOT NULL,
    rows           bigint      NOT NULL,
    parquet_rows   bigint      NOT NULL,
    row_count_ok   boolean     NOT NULL,
    parquet_files  int         NOT NULL,
    parquet_bytes  bigint      NOT NULL,
    csv_bytes      bigint      NOT NULL,
    read_seconds   numeric(10,3),
    copy_seconds   numeric(10,3),
    index_seconds  numeric(10,3),
    seconds        numeric(10,3) NOT NULL,
    rows_per_sec   numeric(14,1),
    source_path    text,
    loaded_at      timestamptz NOT NULL DEFAULT now()
);
"""


def pg_type(t: pa.DataType) -> str:
    if pa.types.is_string(t) or pa.types.is_large_string(t) or pa.types.is_dictionary(t):
        return "text"
    if pa.types.is_boolean(t):
        return "boolean"
    if pa.types.is_int8(t) or pa.types.is_int16(t):
        return "smallint"
    if pa.types.is_int32(t):
        return "integer"
    if pa.types.is_int64(t):
        return "bigint"
    if pa.types.is_float32(t):
        return "real"
    if pa.types.is_float64(t):
        return "double precision"
    if pa.types.is_decimal(t):
        return f"numeric({t.precision},{t.scale})"
    if pa.types.is_date(t):
        return "date"
    if pa.types.is_timestamp(t):
        return "timestamptz" if t.tz else "timestamp"
    raise TypeError(f"Chưa ánh xạ kiểu Arrow {t}")


def read_table(path: Path) -> tuple[pa.Table, int, int]:
    """Đọc 1 thư mục bảng Spark (có thể phân vùng hive year/month). Trả về (table, số file, bytes)."""
    dataset = ds.dataset(path, format="parquet", partitioning="hive")
    files = dataset.files
    nbytes = sum(Path(f).stat().st_size for f in files)
    table = dataset.to_table()
    # Postgres chỉ giữ tới micro giây; đổi timestamp[ns] -> timestamp[us] để CSV hợp lệ.
    cols = []
    for field, col in zip(table.schema, table.columns):
        if pa.types.is_timestamp(field.type) and field.type.unit == "ns":
            col = pc.cast(col, pa.timestamp("us", field.type.tz))
        if pa.types.is_dictionary(field.type):
            col = pc.cast(col, pa.string())
        cols.append(col)
    table = pa.table(cols, names=table.schema.names)
    return table, len(files), nbytes


def to_csv_bytes(table: pa.Table) -> bytes:
    buf = io.BytesIO()
    # all_valid: mọi giá trị được đặt trong "" -> Postgres phân biệt chuỗi rỗng ("") với NULL (trống).
    pacsv.write_csv(table, buf, write_options=pacsv.WriteOptions(include_header=False, quoting_style="all_valid"))
    return buf.getvalue()


def load_one(conn, fq: str, spec: dict, run_id: str, log: Tee) -> dict:
    schema, name = fq.split(".")
    src = DATA_DIR / schema / name
    t0 = time.perf_counter()
    table, nfiles, nbytes = read_table(src)
    t_read = time.perf_counter() - t0

    cols_ddl = ",\n    ".join(f"{f.name} {pg_type(f.type)}" for f in table.schema)
    payload = to_csv_bytes(table)
    collist = ", ".join(table.schema.names)

    t1 = time.perf_counter()
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {fq} CASCADE")
            cur.execute(f"CREATE TABLE {fq} (\n    {cols_ddl}\n)")
            with cur.copy(f"COPY {fq} ({collist}) FROM STDIN WITH (FORMAT csv)") as cp:
                view = memoryview(payload)
                for i in range(0, len(view), 1 << 20):
                    cp.write(view[i : i + (1 << 20)])
            comment = sql.Literal(f"Grain: {spec['grain']}. Nguồn: data/{schema}/{name} (Parquet)")
            cur.execute(sql.SQL("COMMENT ON TABLE {} IS {}").format(sql.SQL(fq), comment))
    t_copy = time.perf_counter() - t1

    t2 = time.perf_counter()
    with conn.cursor() as cur:
        pk = spec.get("pk")
        if pk:
            try:
                with conn.transaction():
                    cur.execute(f"ALTER TABLE {fq} ADD PRIMARY KEY ({', '.join(pk)})")
            except Exception as e:  # dữ liệu có NULL/trùng khoá -> dùng index thường
                log(f"   ! {fq}: không tạo được PK {pk} ({type(e).__name__}); tạo index thường")
                cur.execute(f"CREATE INDEX ON {fq} ({', '.join(pk)})")
        for cols in spec.get("idx", []):
            cur.execute(f"CREATE INDEX ON {fq} ({', '.join(cols)})")
        cur.execute(f"ANALYZE {fq}")
        cur.execute(f"SELECT count(*) FROM {fq}")
        pg_rows = cur.fetchone()[0]
    t_idx = time.perf_counter() - t2

    total = time.perf_counter() - t0
    rec = {
        "run_id": run_id,
        "schema_name": schema,
        "table_name": name,
        "rows": pg_rows,
        "parquet_rows": table.num_rows,
        "row_count_ok": pg_rows == table.num_rows,
        "parquet_files": nfiles,
        "parquet_bytes": nbytes,
        "csv_bytes": len(payload),
        "read_seconds": round(t_read, 3),
        "copy_seconds": round(t_copy, 3),
        "index_seconds": round(t_idx, 3),
        "seconds": round(total, 3),
        "rows_per_sec": round(pg_rows / t_copy, 1) if t_copy > 0 else None,
        "source_path": f"data/{schema}/{name}",
    }
    with conn.cursor() as cur:
        keys = list(rec)
        cur.execute(
            f"INSERT INTO analytics.load_log ({', '.join(keys)}) VALUES ({', '.join(['%s'] * len(keys))})",
            [rec[k] for k in keys],
        )
    flag = "OK " if rec["row_count_ok"] else "SAI"
    log(
        f"{flag} {fq:<34} rows={pg_rows:>7,}  parquet={nbytes/1e6:6.2f}MB/{nfiles:>2}f  "
        f"read={t_read:5.2f}s copy={t_copy:5.2f}s idx={t_idx:5.2f}s  {rec['rows_per_sec'] or 0:>9,.0f} rows/s"
    )
    return rec


def apply_sql_files(conn, log: Tee) -> None:
    for f in sorted(SQL_DIR.glob("[0-8]*.sql")):
        t = time.perf_counter()
        with conn.transaction():
            conn.execute(f.read_text(encoding="utf-8"))
        log(f"SQL {f.name} áp dụng trong {time.perf_counter() - t:.2f}s")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="danh sách bảng (tên ngắn) cách nhau dấu phẩy")
    ap.add_argument("--skip-views", action="store_true")
    args = ap.parse_args()

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
    log = Tee(EVIDENCE_DIR / "load_run.log")
    log(f"Run {run_id} -> {mask(neon_url())}")

    targets = TABLES
    if args.only:
        wanted = {x.strip() for x in args.only.split(",")}
        targets = {k: v for k, v in TABLES.items() if k.split(".")[1] in wanted or k in wanted}

    t_all = time.perf_counter()
    conn = connect(direct=True)
    with conn.cursor() as cur:
        cur.execute("SELECT version()")
        log(cur.fetchone()[0])
        for s in ("analytics", "gold", "presentation"):
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {s}")
        cur.execute(LOAD_LOG_DDL)

    records = [load_one(conn, fq, spec, run_id, log) for fq, spec in targets.items()]
    t_load = time.perf_counter() - t_all

    if not args.skip_views:
        apply_sql_files(conn, log)
    conn.close()

    rows = sum(r["rows"] for r in records)
    pq = sum(r["parquet_bytes"] for r in records)
    copy_s = sum(r["copy_seconds"] for r in records)
    ok = sum(r["row_count_ok"] for r in records)
    log("-" * 100)
    log(f"Tổng: {len(records)} bảng, {rows:,} dòng, Parquet {pq/1e6:.2f} MB")
    log(f"Thời gian nạp (đọc+COPY+index): {t_load:.2f}s; riêng COPY {copy_s:.2f}s -> {rows/copy_s:,.0f} rows/s; "
        f"end-to-end {rows/t_load:,.0f} rows/s")
    log(f"Đối chiếu số dòng Parquet vs Postgres: {ok}/{len(records)} khớp")
    log(f"Tổng thời gian chạy: {time.perf_counter() - t_all:.2f}s")
    log.close()

    out = EVIDENCE_DIR / "load_log.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0]))
        w.writeheader()
        w.writerows(records)
    if ok != len(records):
        raise SystemExit("Có bảng lệch số dòng!")


if __name__ == "__main__":
    main()
