"""Áp dụng lại các file sql/[0-8]*.sql (view tầng trình bày) mà không nạp lại dữ liệu."""
from common import EVIDENCE_DIR, Tee, connect
from load_to_neon import apply_sql_files

if __name__ == "__main__":
    log = Tee(EVIDENCE_DIR / "apply_sql.log")
    with connect() as conn:
        apply_sql_files(conn, log)
        rows = conn.execute(
            "SELECT table_name, table_type FROM information_schema.tables "
            "WHERE table_schema = 'presentation' ORDER BY table_type, table_name"
        ).fetchall()
    for name, kind in rows:
        log(f"  presentation.{name:<26} {kind}")
    log(f"{len(rows)} đối tượng trong schema presentation")
    log.close()
