"""Kiểm kê đối tượng trong Neon (schema, bảng/view, số dòng, dung lượng) từ catalog Postgres.

Neon Console cần đăng nhập tương tác nên minh chứng được sinh từ truy vấn catalog trực tiếp
trên database và thông tin project (evidence/neon_project.json, lấy từ Neon API).
Kết quả: evidence/neon_inventory.csv, evidence/neon_inventory.html (chụp thành neon_tables_inventory.png)

Chạy: docker compose run --rm tools python scripts/neon_inventory.py
"""
from __future__ import annotations

import csv
import html
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "loader"))
from common import EVIDENCE_DIR, connect  # noqa: E402

SQL = """
SELECT n.nspname AS schema, c.relname AS name,
       CASE c.relkind WHEN 'r' THEN 'table' WHEN 'v' THEN 'view' WHEN 'm' THEN 'matview' END AS kind,
       CASE WHEN c.relkind = 'r' THEN pg_total_relation_size(c.oid) END AS total_bytes,
       (SELECT count(*) FROM pg_index i WHERE i.indrelid = c.oid) AS indexes,
       obj_description(c.oid) AS comment
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname IN ('analytics', 'gold', 'presentation') AND c.relkind IN ('r', 'v', 'm')
ORDER BY n.nspname, c.relkind, c.relname
"""


def main() -> None:
    with connect() as conn:
        version = conn.execute("SELECT version()").fetchone()[0]
        db, db_bytes = conn.execute("SELECT current_database(), pg_database_size(current_database())").fetchone()
        objs = []
        for schema, name, kind, nbytes, nidx, comment in conn.execute(SQL).fetchall():
            rows = conn.execute(f'SELECT count(*) FROM "{schema}"."{name}"').fetchone()[0]
            objs.append({"schema": schema, "name": name, "kind": kind, "rows": rows,
                         "size_mb": round(nbytes / 1048576, 2) if nbytes else "", "indexes": nidx,
                         "comment": comment or ""})
    proj = json.loads((EVIDENCE_DIR / "neon_project.json").read_text(encoding="utf-8"))

    with (EVIDENCE_DIR / "neon_inventory.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(objs[0]))
        w.writeheader()
        w.writerows(objs)

    summary = {}
    for o in objs:
        s = summary.setdefault((o["schema"], o["kind"]), [0, 0, 0.0])
        s[0] += 1
        s[1] += o["rows"]
        s[2] += o["size_mb"] or 0
    trs = "".join(
        f"<tr class='{o['kind']}'><td>{o['schema']}</td><td><b>{o['name']}</b></td><td>{o['kind']}</td>"
        f"<td class='n'>{o['rows']:,}</td><td class='n'>{o['size_mb']}</td><td class='n'>{o['indexes'] or ''}</td>"
        f"<td class='c'>{html.escape(o['comment'][:70])}</td></tr>" for o in objs)
    sums = "".join(f"<li><b>{s}.*</b> – {n} {k}, {r:,} dòng" + (f", {mb:.1f} MB" if mb else "") + "</li>"
                   for (s, k), (n, r, mb) in summary.items())
    page = f"""<!doctype html><html><head><meta charset="utf-8"><style>
body{{font-family:Inter,Segoe UI,Arial,sans-serif;margin:24px;color:#1a1a1a;width:1180px}}
h1{{font-size:22px;margin:0 0 4px}} .sub{{color:#555;font-size:13px;margin-bottom:14px}}
.cards{{display:flex;gap:10px;margin-bottom:14px}} .card{{border:1px solid #d8e2dc;border-radius:8px;padding:8px 12px;background:#f3fbf7}}
.card b{{display:block;font-size:17px;color:#0b6e4f}} .card span{{font-size:11px;color:#555}}
table{{border-collapse:collapse;width:100%;font-size:12px}} th{{background:#0b6e4f;color:#fff;text-align:left;padding:5px}}
td{{border-bottom:1px solid #e5e5e5;padding:3px 5px}} .n{{text-align:right;font-variant-numeric:tabular-nums}}
.c{{color:#666;font-size:11px}} tr.view td{{background:#fafafa;color:#333}} ul{{font-size:12px;margin:4px 0 12px}}
</style></head><body>
<h1>Neon Postgres · project <code>{proj['name']}</code> ({proj['id']})</h1>
<div class="sub">Sinh bởi scripts/neon_inventory.py lúc {datetime.now():%Y-%m-%d %H:%M} từ catalog của database <b>{db}</b> · {html.escape(version.split(' on ')[0])}</div>
<div class="cards">
<div class="card"><b>{proj['region_id']}</b><span>Region</span></div>
<div class="card"><b>PostgreSQL {proj['pg_version']}</b><span>Phiên bản</span></div>
<div class="card"><b>{proj['autoscaling_cu']} CU</b><span>Compute (autoscaling)</span></div>
<div class="card"><b>{db_bytes / 1048576:.0f} MB</b><span>Dung lượng database</span></div>
<div class="card"><b>{sum(1 for o in objs if o['kind'] == 'table')} bảng · {sum(1 for o in objs if o['kind'] == 'view')} view</b><span>analytics / gold / presentation</span></div>
<div class="card"><b>{proj['plan']}</b><span>Gói Neon</span></div>
</div>
<ul>{sums}</ul>
<table><tr><th>Schema</th><th>Đối tượng</th><th>Loại</th><th>Số dòng</th><th>MB</th><th>Index</th><th>Mô tả (COMMENT)</th></tr>{trs}</table>
</body></html>"""
    (EVIDENCE_DIR / "neon_inventory.html").write_text(page, encoding="utf-8")
    print(f"{len(objs)} đối tượng; database {db_bytes / 1048576:.1f} MB")
    for (s, k), (n, r, mb) in summary.items():
        print(f"  {s}.{k}: {n} đối tượng, {r:,} dòng, {mb:.1f} MB")


if __name__ == "__main__":
    main()
