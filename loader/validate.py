"""Kiểm chứng dữ liệu trong Neon:
1. Số dòng Parquet (đọc lại file) vs COUNT(*) trên Postgres cho mọi bảng.
2. Số neo của ANALYTICS_HANDOVER.md (sql/90_anchor_checks.sql).
Kết quả: evidence/validation.md + evidence/validation.json
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime
from decimal import Decimal

import pyarrow.dataset as ds

from common import DATA_DIR, EVIDENCE_DIR, SQL_DIR, connect
from load_to_neon import TABLES

CHECK_RE = re.compile(r"^-- check:\s*(.+?)\s*\|\s*expected:\s*(.+?)\s*\|\s*tol:\s*(\S+)\s*$", re.M)


def parse_checks() -> list[dict]:
    text = (SQL_DIR / "90_anchor_checks.sql").read_text(encoding="utf-8")
    matches = list(CHECK_RE.finditer(text))
    checks = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        checks.append({"name": m[1], "expected": m[2], "tol": float(m[3]), "sql": text[m.end():end].strip()})
    return checks


def judge(got, expected: str, tol: float) -> str:
    if expected == "info":
        return "INFO"
    try:
        return "ĐẠT" if abs(float(got) - float(expected)) <= tol else "LỆCH"
    except (TypeError, ValueError):
        return "ĐẠT" if str(got) == expected else "LỆCH"


def fmt(v):
    if isinstance(v, Decimal):
        return f"{v:,.2f}" if v != v.to_integral() else f"{int(v):,}"
    if isinstance(v, int):
        return f"{v:,}"
    return str(v)


def main() -> None:
    conn = connect()
    counts = []
    for fq in TABLES:
        schema, name = fq.split(".")
        pq_rows = ds.dataset(DATA_DIR / schema / name, format="parquet", partitioning="hive").count_rows()
        pg_rows = conn.execute(f"SELECT COUNT(*) FROM {fq}").fetchone()[0]
        counts.append({"table": fq, "parquet_rows": pq_rows, "postgres_rows": pg_rows, "ok": pq_rows == pg_rows})

    results = []
    for c in parse_checks():
        t = time.perf_counter()
        got = conn.execute(c["sql"]).fetchone()[0]
        ms = (time.perf_counter() - t) * 1000
        results.append({**c, "got": got, "status": judge(got, c["expected"], c["tol"]), "ms": round(ms, 1)})
    conn.close()

    n_ok = sum(r["ok"] for r in counts)
    n_pass = sum(r["status"] == "ĐẠT" for r in results)
    n_judged = sum(r["status"] != "INFO" for r in results)
    lines = [
        "# Kiểm chứng dữ liệu đã nạp vào Neon",
        "",
        f"Thời điểm: {datetime.now():%Y-%m-%d %H:%M:%S} · Script: `loader/validate.py`",
        "",
        f"## 1. Số dòng Parquet vs Postgres — {n_ok}/{len(counts)} khớp",
        "",
        "| Bảng | Parquet | Postgres | Kết quả |",
        "|---|---:|---:|---|",
    ]
    lines += [f"| `{r['table']}` | {r['parquet_rows']:,} | {r['postgres_rows']:,} | {'ĐẠT' if r['ok'] else 'LỆCH'} |" for r in counts]
    lines += [
        "",
        f"Tổng: {sum(r['postgres_rows'] for r in counts):,} dòng.",
        "",
        f"## 2. Số neo bàn giao Analytics — {n_pass}/{n_judged} đạt",
        "",
        "SQL nằm trong `sql/90_anchor_checks.sql`.",
        "",
        "| Kiểm tra | Kỳ vọng | Thực tế (Neon) | Kết quả | Thời gian truy vấn (ms) |",
        "|---|---:|---:|---|---:|",
    ]
    lines += [f"| {r['name']} | {r['expected']} | {fmt(r['got'])} | {r['status']} | {r['ms']} |" for r in results]
    (EVIDENCE_DIR / "validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (EVIDENCE_DIR / "validation.json").write_text(
        json.dumps({"row_counts": counts, "anchors": results}, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print("\n".join(lines))
    if n_ok != len(counts) or n_pass != n_judged:
        raise SystemExit("Có kiểm tra không đạt")


if __name__ == "__main__":
    main()
