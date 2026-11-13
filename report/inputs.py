"""Thu thập đầu vào cho báo cáo: Parquet Analytics, số liệu upstream, minh chứng (ảnh, log, latency).

Mọi thứ đều được phát hiện tự động; thiếu file nào thì báo cáo chèn placeholder [[CẬP NHẬT: ...]].
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

REPORT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = REPORT_DIR.parent
UPSTREAM_DIR = Path(os.environ.get("ANALYTICS_REPO", r"D:\Analytics-main"))
EVIDENCE_DIR = PROJECT_DIR / "evidence"
DOCS_DIR = PROJECT_DIR / "docs"
FIG_DIR = REPORT_DIR / "figures"
CONTENT_DIR = REPORT_DIR / "content"
REPO_URL = "https://github.com/viettuong287/BigDataProject"
UPSTREAM_REPO_URL = "https://github.com/NguyenAlpha/big-data"

IMG_EXT = {".png", ".jpg", ".jpeg"}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", "upstream"}


def placeholder(what: str) -> str:
    return f"[[CẬP NHẬT: {what}]]"


# ---------------------------------------------------------------- định dạng số kiểu Việt Nam
def fmt_int(x) -> str:
    return f"{int(round(float(x))):,}".replace(",", ".")


def fmt_num(x, nd: int = 2) -> str:
    s = f"{float(x):,.{nd}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


# ---------------------------------------------------------------- Parquet Analytics
TABLE_META = {
    # tên bảng: (chủ đề, 1 dòng =, khoá/cột định danh, dashboard dùng cho)
    "kpi_monthly": ("1. Xu hướng", "1 tháng (2017-01 → 2018-08)", "purchase_year, purchase_month", "KPI tổng quan, xu hướng"),
    "category_pareto": ("2. Danh mục", "1 danh mục", "category", "Pareto danh mục"),
    "category_seasonality": ("2. Danh mục", "1 danh mục × 1 tháng (2017)", "category, purchase_month", "Heatmap mùa vụ"),
    "state_logistics": ("3. Địa lý", "1 bang của khách", "customer_state", "Bản đồ / bảng bang"),
    "insight_distance": ("3. Địa lý", "1 khoảng cách (band km)", "distance_band (band_order)", "Logistics theo km"),
    "rfm_scores": ("4. Khách hàng", "1 khách thật", "customer_unique_id", "Phân khúc RFM"),
    "customer_segments": ("4. Khách hàng", "1 khách thật (+ cụm K-Means)", "customer_unique_id", "Phân khúc + cụm"),
    "cluster_profile": ("4. Khách hàng", "1 cụm K-Means", "cluster", "Hồ sơ cụm"),
    "repeat_profile": ("4. Khách hàng", "1 cohort (repeat / one_shot)", "cohort", "Thẻ KPI giữ chân"),
    "repeat_categories": ("4. Khách hàng", "1 danh mục của khách mua lại", "category", "Danh mục khách lặp"),
    "repeat_states": ("4. Khách hàng", "1 bang của khách mua lại", "customer_state", "Bang khách lặp"),
    "seller_pareto": ("5. Người bán", "1 người bán", "seller_id", "Pareto người bán"),
    "seller_watchlist": ("5. Người bán", "1 người bán cần theo dõi", "seller_id", "Gợi ý quyết định"),
    "insight_late_vs_review": ("6. Giao hàng & review", "1 nhóm (late / on_time)", "delivery", "So sánh trễ vs đúng hạn"),
    "delay_vs_review": ("6. Giao hàng & review", "1 khoảng ngày trễ", "delay_band (band_order)", "Ngưỡng trễ → review"),
    "payment_mix": ("6. Giao hàng & review", "1 PTTT × 1 nhóm kỳ trả góp", "main_payment_type, installment_band", "Cơ cấu thanh toán"),
}
TABLE_ORDER = list(TABLE_META)


def analytics_dir() -> Path | None:
    for c in (PROJECT_DIR / "data" / "analytics", UPSTREAM_DIR / "data" / "analytics"):
        if c.exists() and any(c.glob("*/*.parquet")):
            return c
    return None


def pg_type(t: pa.DataType) -> str:
    if pa.types.is_decimal(t):
        return f"NUMERIC({t.precision},{t.scale})"
    if pa.types.is_int32(t) or pa.types.is_int16(t):
        return "INTEGER"
    if pa.types.is_int64(t):
        return "BIGINT"
    if pa.types.is_floating(t):
        return "DOUBLE PRECISION"
    if pa.types.is_boolean(t):
        return "BOOLEAN"
    if pa.types.is_date(t):
        return "DATE"
    if pa.types.is_timestamp(t):
        return "TIMESTAMP"
    return "TEXT"


@dataclass
class TableInfo:
    name: str
    rows: int
    bytes: int
    files: int
    schema: pa.Schema
    table: pa.Table


def load_analytics() -> dict[str, TableInfo]:
    root = analytics_dir()
    out: dict[str, TableInfo] = {}
    if root is None:
        return out
    names = [n for n in TABLE_ORDER if (root / n).exists()]
    names += sorted(p.name for p in root.iterdir() if p.is_dir() and p.name not in names)
    for n in names:
        files = sorted((root / n).glob("*.parquet"))
        if not files:
            continue
        t = pq.read_table(root / n)
        out[n] = TableInfo(n, t.num_rows, sum(f.stat().st_size for f in files), len(files), t.schema, t)
    return out


def upstream_summary() -> dict:
    for p in (DOCS_DIR / "upstream" / "analytics_summary.json", UPSTREAM_DIR / "reports" / "analytics_summary.json"):
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return {}


def upstream_manifest() -> dict:
    for p in (DOCS_DIR / "upstream" / "MANIFEST.json", UPSTREAM_DIR / "data" / "MANIFEST.json"):
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return {}


# ---------------------------------------------------------------- ảnh minh chứng
# (khoá, regex trên tên file, chú thích mặc định). Thứ tự quan trọng: file khớp mục đầu tiên.
IMAGE_CATEGORIES = [
    ("architecture", r"arch|kien[-_ ]?truc|data[-_ ]?flow|pipeline|diagram|so[-_ ]?do", "Sơ đồ kiến trúc / luồng dữ liệu của hệ thống"),
    ("neon", r"neon", "Neon Console: project, nhánh và compute của tầng phục vụ"),
    ("load", r"load|copy|ingest", "Log nạp dữ liệu Parquet vào Neon"),
    ("latency", r"latenc|perf|bench|timing", "Kết quả đo độ trễ truy vấn"),
    ("sql", r"sql|view|query|psql|semantic", "Truy vấn semantic view (SQL Lab / psql)"),
    ("superset_setup", r"dataset|database|connection", "Cấu hình kết nối cơ sở dữ liệu và datasets trong Superset"),
    ("filter", r"filter|bo[-_ ]?loc", "Dashboard khi áp dụng bộ lọc native"),
    ("decision", r"watchlist|decision|alert|hint|canh[-_ ]?bao|action", "Khu vực gợi ý quyết định trên dashboard"),
    ("dashboard", r"dashboard|superset|chart|tab|overview", "Dashboard Apache Superset"),
    ("docker", r"docker|container|compose", "Các container Docker của hệ thống"),
]


def _natural_key(p: Path):
    return [int(s) if s.isdigit() else s.lower() for s in re.split(r"(\d+)", p.name)]


def find_images() -> list[Path]:
    imgs: list[Path] = []
    for base in (EVIDENCE_DIR, DOCS_DIR):
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.suffix.lower() in IMG_EXT and not (set(p.relative_to(base).parts[:-1]) & SKIP_DIRS):
                imgs.append(p)
    return sorted(set(imgs), key=lambda p: (0 if EVIDENCE_DIR in p.parents else 1, _natural_key(p)))


def classify_image(p: Path) -> str | None:
    stem = p.stem.lower()
    for key, rx, _ in IMAGE_CATEGORIES:
        if re.search(rx, stem):
            return key
    return None


def load_caption_overrides() -> dict[str, str]:
    p = CONTENT_DIR / "captions.json"
    if p.exists():
        data = json.loads(p.read_text(encoding="utf-8"))
        return {k.lower(): v for k, v in data.items() if not k.startswith("_")}
    return {}


def pretty_stem(p: Path) -> str:
    s = re.sub(r"^\d+[-_ ]*", "", p.stem)
    return re.sub(r"[-_]+", " ", s).strip()


def image_caption(p: Path, overrides: dict[str, str]) -> str:
    for k in (p.name.lower(), p.stem.lower()):
        if k in overrides:
            return overrides[k]
    cat = classify_image(p)
    base = next((c for k, _, c in IMAGE_CATEGORIES if k == cat), "Minh chứng hệ thống")
    return f"{base} – {pretty_stem(p)} (tệp {p.name})"


# ---------------------------------------------------------------- file số liệu (load log, latency, validate)
@dataclass
class DataFile:
    path: Path
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    scalars: dict[str, str] = field(default_factory=dict)
    raw: str = ""

    @property
    def is_table(self) -> bool:
        return bool(self.headers and self.rows)


def _glob_evidence(patterns: list[str]) -> list[Path]:
    if not EVIDENCE_DIR.exists():
        return []
    found: set[Path] = set()
    for pat in patterns:
        found.update(p for p in EVIDENCE_DIR.rglob(pat) if p.is_file())
    return sorted(found, key=_natural_key)


def _md_table(text: str) -> tuple[list[str], list[list[str]]]:
    lines = [ln.strip() for ln in text.splitlines()]
    for i, ln in enumerate(lines):
        if ln.startswith("|") and i + 1 < len(lines) and re.match(r"^\|?\s*:?-{2,}", lines[i + 1]):
            hdr = [c.strip() for c in ln.strip("|").split("|")]
            rows = []
            for r in lines[i + 2:]:
                if not r.startswith("|"):
                    break
                rows.append([c.strip() for c in r.strip("|").split("|")])
            return hdr, rows
    return [], []


def _json_table(obj) -> tuple[list[str], list[list[str]], dict[str, str]]:
    scalars: dict[str, str] = {}
    rows_obj = None
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        rows_obj = obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, list) and v and isinstance(v[0], dict) and rows_obj is None:
                rows_obj = v
            elif isinstance(v, dict) and v and all(isinstance(x, dict) for x in v.values()) and rows_obj is None:
                rows_obj = [{"name": kk, **vv} for kk, vv in v.items()]
            elif not isinstance(v, (list, dict)):
                scalars[k] = str(v)
    if not rows_obj:
        return [], [], scalars
    hdr: list[str] = []
    for r in rows_obj:
        for k in r:
            if k not in hdr and not isinstance(r[k], (list, dict)):
                hdr.append(k)
    return hdr, [[("" if r.get(h) is None else str(r.get(h))) for h in hdr] for r in rows_obj], scalars


def read_data_file(p: Path) -> DataFile:
    text = p.read_text(encoding="utf-8-sig", errors="replace")
    df = DataFile(p, raw=text)
    ext = p.suffix.lower()
    try:
        if ext == ".csv":
            rdr = list(csv.reader(io.StringIO(text)))
            if rdr:
                df.headers, df.rows = rdr[0], [r for r in rdr[1:] if any(c.strip() for c in r)]
        elif ext == ".json":
            df.headers, df.rows, df.scalars = _json_table(json.loads(text))
        elif ext == ".md":
            df.headers, df.rows = _md_table(text)
    except Exception:  # file đang được ghi dở hoặc sai định dạng: chỉ dùng raw
        pass
    return df


def find_data_files(kind: str) -> list[DataFile]:
    pats = {
        "load": ["load_log*.csv", "load_log*.json", "load_log*.md", "load_log*.txt", "load_log*.log"],
        "latency": ["*latency*.csv", "*latency*.md", "*latency*.json"],
        "validate": ["validat*.csv", "validat*.json", "validat*.md", "validat*.txt", "validat*.log",
                     "reconcil*.csv", "reconcil*.json", "reconcil*.md", "row_count*.csv", "row_count*.json"],
        "dashboard": ["build_dashboard*.log", "build_dashboard*.txt", "build_dashboard*.json", "dashboard*.log"],
    }[kind]
    return [read_data_file(p) for p in _glob_evidence(pats)]


def _col(headers: list[str], rx: str) -> int | None:
    for i, h in enumerate(headers):
        if re.search(rx, h.lower()):
            return i
    return None


def _to_float(s: str) -> float | None:
    try:
        return float(str(s).replace(",", "").strip())
    except ValueError:
        return None


def is_loader_csv(f: DataFile) -> bool:
    return f.is_table and {"table_name", "rows", "seconds", "copy_seconds"} <= set(f.headers)


def summarize_load(files: list[DataFile]) -> dict[str, str]:
    """Tìm tổng dòng / tổng giây / throughput từ log nạp (CSV/JSON/MD dạng bảng hoặc TXT)."""
    out: dict[str, str] = {}
    for f in files:
        if is_loader_csv(f):
            H = {h: i for i, h in enumerate(f.headers)}

            def col(name, rows):
                return sum(_to_float(r[H[name]]) or 0 for r in rows)

            rows = f.rows
            ana = [r for r in rows if r[H["schema_name"]] == "analytics"] if "schema_name" in H else rows
            gold = [r for r in rows if "schema_name" in H and r[H["schema_name"]] == "gold"]
            tot_s, copy_s = col("seconds", rows), col("copy_seconds", rows)
            out.update(
                load_tables=str(len(rows)), load_total_rows=fmt_int(col("rows", rows)),
                load_total_seconds=fmt_num(tot_s, 2), load_copy_seconds=fmt_num(copy_s, 2),
                load_throughput=fmt_int(col("rows", rows) / tot_s) if tot_s else "",
                load_copy_throughput=fmt_int(col("rows", rows) / copy_s) if copy_s else "",
                load_ana_tables=str(len(ana)), load_ana_rows=fmt_int(col("rows", ana)),
                load_ana_seconds=fmt_num(col("seconds", ana), 2),
                load_gold_tables=str(len(gold)), load_gold_rows=fmt_int(col("rows", gold)),
                load_gold_seconds=fmt_num(col("seconds", gold), 2),
                load_ok=f"{sum(1 for r in rows if 'row_count_ok' in H and r[H['row_count_ok']].lower() == 'true')}/{len(rows)}",
                load_source=f.path.name,
            )
            if "parquet_bytes" in H:
                out["load_parquet_mb"] = fmt_num(col("parquet_bytes", rows) / 1e6, 2)
            if "csv_bytes" in H:
                csv_b = col("csv_bytes", rows)
                out["load_csv_mb"] = fmt_num(csv_b / 1e6, 2)
                if copy_s:
                    out["load_copy_mbps"] = fmt_num(csv_b / 1e6 / copy_s, 2)
            if gold and tot_s:
                out["load_gold_share"] = fmt_num(col("seconds", gold) / tot_s * 100, 0)
            small = [r for r in rows if (_to_float(r[H["rows"]]) or 0) < 1000]
            if small:
                out["load_small_avg_s"] = fmt_num(col("seconds", small) / len(small), 2)
                out["load_small_tables"] = str(len(small))
            run = f.rows[0][H["run_id"]] if "run_id" in H else ""
            out["load_run_id"] = run
            return out
        if f.is_table:
            ri = _col(f.headers, r"^rows?$|row_?count|rows_?loaded|so_?dong|n_?rows|^rows")
            si = _col(f.headers, r"sec|second|duration|elapsed|time_s|thoi_?gian")
            ti = _col(f.headers, r"^table|table_?name|^name$|bang")
            data = [r for r in f.rows if ti is None or not re.search(r"total|tong", r[ti].lower())]
            if ri is not None:
                vals = [_to_float(r[ri]) for r in data if ri < len(r)]
                out["load_total_rows"] = fmt_int(sum(v for v in vals if v is not None))
                out["load_tables"] = str(len(data))
            if si is not None:
                secs = [_to_float(r[si]) for r in data if si < len(r)]
                tot = sum(v for v in secs if v is not None)
                out["load_total_seconds"] = fmt_num(tot, 2)
                if ri is not None and tot > 0:
                    rows = sum(v for v in vals if v is not None)
                    out["load_throughput"] = fmt_int(rows / tot)
            for k, v in f.scalars.items():
                kl = k.lower()
                if re.search(r"total_?rows", kl):
                    out["load_total_rows"] = fmt_int(_to_float(v) or 0)
                if re.search(r"total_?(sec|time|duration)|elapsed", kl) and _to_float(v) is not None:
                    out["load_total_seconds"] = fmt_num(_to_float(v), 2)
            if out:
                out["load_source"] = f.path.name
                return out
        m = re.search(r"(?i)(?:total|tổng)[^\n]*?([\d.,]+)\s*(?:rows|dòng)[^\n]*?([\d.,]+)\s*s", f.raw)
        if m:
            out.update(load_total_rows=m.group(1), load_total_seconds=m.group(2), load_source=f.path.name)
            return out
    return out


def validation_json(files: list[DataFile]) -> dict | None:
    for f in files:
        if f.path.suffix.lower() == ".json":
            try:
                obj = json.loads(f.raw)
            except ValueError:
                continue
            if isinstance(obj, dict) and ("row_counts" in obj or "anchors" in obj):
                return obj
    return None


def summarize_validation(files: list[DataFile]) -> dict[str, str]:
    obj = validation_json(files)
    if not obj:
        return {}
    out: dict[str, str] = {"validation_source": "validation.json"}
    rc = obj.get("row_counts", [])
    if rc:
        out["val_rows_ok"] = f"{sum(1 for r in rc if r.get('ok'))}/{len(rc)}"
    an = obj.get("anchors", [])
    if an:
        graded = [a for a in an if str(a.get("status", "")).upper() != "INFO"]
        out["val_anchor_ok"] = f"{sum(1 for a in graded if 'ĐẠT' in str(a.get('status', '')))}/{len(graded)}"
        ms = sorted(float(a["ms"]) for a in an if a.get("ms") is not None)
        if ms:
            n = len(ms)
            med = ms[n // 2] if n % 2 else (ms[n // 2 - 1] + ms[n // 2]) / 2
            out.update(anchor_n=str(n), anchor_ms_min=fmt_num(ms[0], 1), anchor_ms_median=fmt_num(med, 1),
                       anchor_ms_max=fmt_num(ms[-1], 1))
    return out


_BAD_STATUS = re.compile(r"http\s*[45]\d\d|error|fail|denied|timeout|exception|lỗi", re.I)


def valid_latency_rows(f: DataFile) -> list[list[str]]:
    """Bỏ các dòng đo thất bại (cột status chứa HTTP 4xx/5xx, error...)."""
    si = _col(f.headers, r"^status$|^result$|^ket_?qua$")
    if si is None:
        return f.rows
    return [r for r in f.rows if si < len(r) and not _BAD_STATUS.search(r[si])]


def latency_col(f: DataFile) -> int | None:
    for rx in (r"median|p50", r"warm", r"latency|_ms$|^ms$"):
        ci = _col(f.headers, rx)
        if ci is not None:
            return ci
    return None


def latency_files(files: list[DataFile]) -> list[DataFile]:
    """Bỏ bản .md/.json nếu đã có .csv cùng tên (cùng dữ liệu, tránh trùng bảng)."""
    csv_stems = {f.path.stem for f in files if f.path.suffix.lower() == ".csv"}
    return [f for f in files if f.path.suffix.lower() == ".csv" or f.path.stem not in csv_stems]


def latency_md_facts(files: list[DataFile]) -> dict[str, str]:
    out: dict[str, str] = {}
    pats = {
        "latency_connect_ms": r"kết nối TLS mới:\s*\*\*([\d.,]+)\s*ms",
        "latency_rtt_ms": r"SELECT 1`?:\s*\*\*([\d.,]+)\s*ms",
        "latency_server_median_md": r"\*\*([\d.,]+)\s*ms\*\*\s*phía server",
        "latency_measured_at": r"Thời điểm đo:\s*([\d\-: ]+)",
        "latency_runs": r"(\d+)\s*lần đo/truy vấn",
    }
    for f in files:
        if f.path.suffix.lower() != ".md":
            continue
        for k, rx in pats.items():
            m = re.search(rx, f.raw)
            if m and k not in out:
                v = m.group(1).strip()
                f_ = _to_float(v)
                out[k] = fmt_num(f_, 2 if f_ is not None and f_ < 10 else 0) if f_ is not None and k != "latency_measured_at" else v
    return out


def summarize_latency(files: list[DataFile]) -> dict[str, str]:
    for f in latency_files(files):
        if not f.is_table:
            continue
        ci = latency_col(f)
        if ci is None:
            continue
        rows = [r for r in valid_latency_rows(f) if not (r and re.match(r"(?i)so sánh|compar|baseline", r[0]))]
        vals = sorted(v for v in (_to_float(r[ci]) for r in rows if ci < len(r)) if v is not None)
        if not vals:
            continue
        n = len(vals)

        def median(xs):
            m = len(xs)
            return xs[m // 2] if m % 2 else (xs[m // 2 - 1] + xs[m // 2]) / 2

        p95 = vals[min(n - 1, int(round(0.95 * (n - 1))))]
        out = {
            "latency_queries": str(n),
            "latency_total": str(len(f.rows)),
            "latency_col": f.headers[ci],
            "latency_min": fmt_num(vals[0], 1),
            "latency_median": fmt_num(median(vals), 1),
            "latency_p95": fmt_num(p95, 1),
            "latency_max": fmt_num(vals[-1], 1),
            "latency_source": f.path.name,
        }
        pi = _col(f.headers, r"p95")
        if pi is not None and pi != ci:
            p95s = [v for v in (_to_float(r[pi]) for r in rows if pi < len(r)) if v is not None]
            if p95s:
                out["latency_p95_max"] = fmt_num(max(p95s), 1)
        si = _col(f.headers, r"server")
        if si is not None:
            sv = sorted(v for v in (_to_float(r[si]) for r in rows if si < len(r)) if v is not None)
            if sv:
                out.update(latency_server_median=fmt_num(median(sv), 2), latency_server_max=fmt_num(sv[-1], 2))
        return out
    return {}


# ---------------------------------------------------------------- mã nguồn dự án
@dataclass
class ViewInfo:
    name: str
    kind: str          # VIEW / MATERIALIZED VIEW / TABLE
    file: str
    comment: str
    sources: list[str]


def detect_views() -> list[ViewInfo]:
    """Quét *.sql trong dự án: view/bảng của tầng trình bày, chú thích ngay phía trên và bảng nguồn."""
    out: list[ViewInfo] = []
    rx = re.compile(r"create\s+(?:or\s+replace\s+)?(materialized\s+view|view|table)\s+(?:if\s+not\s+exists\s+)?([\w\".]+)", re.I)
    for p in sorted(PROJECT_DIR.rglob("*.sql"), key=_natural_key):
        if set(p.relative_to(PROJECT_DIR).parts) & (SKIP_DIRS | {"report"}):
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        hits = [(i, rx.search(ln)) for i, ln in enumerate(lines)]
        hits = [(i, m) for i, m in hits if m and not lines[i].lstrip().startswith("--")]
        for k, (i, m) in enumerate(hits):
            name = m.group(2).replace('"', "")
            if "." not in name or not name.startswith("presentation."):
                continue
            block, j = [], i - 1
            while j >= 0 and lines[j].strip().startswith("--"):
                block.insert(0, lines[j].strip().lstrip("-").strip())
                j -= 1
            meaningful = [b for b in block if b and not re.fullmatch(r"[=\-_*#]+", b)]
            comment = meaningful[0] if meaningful and not meaningful[0].startswith("Chủ đề") else ""
            end = hits[k + 1][0] if k + 1 < len(hits) else len(lines)
            body = "\n".join(lines[i:end])
            srcs = sorted({s for s in re.findall(r"\b((?:analytics|gold|presentation)\.\w+)", body) if s != name})
            out.append(ViewInfo(name, m.group(1).upper(), str(p.relative_to(PROJECT_DIR)).replace("\\", "/"), comment, srcs))
    return out


def load_gold() -> dict[str, tuple[int, int, int, int]]:
    """Bảng gold (đầu vào của Analytics) nếu có trong data/gold: tên -> (dòng, cột, file, bytes)."""
    import pyarrow.dataset as pads

    root = None
    for c in (PROJECT_DIR / "data" / "gold", UPSTREAM_DIR / "data" / "gold"):
        if c.exists() and any(c.iterdir()):
            root = c
            break
    out: dict[str, tuple[int, int, int, int]] = {}
    if root is None:
        return out
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        dset = pads.dataset(d, format="parquet", partitioning="hive")
        files = dset.files
        out[d.name] = (dset.count_rows(), len(dset.schema), len(files), sum(Path(f).stat().st_size for f in files))
    return out


def source_tree(max_depth: int = 2) -> str:
    skip = SKIP_DIRS | {"data", "figures", ".env"}
    lines = [PROJECT_DIR.name + "/"]

    def walk(d: Path, prefix: str, depth: int):
        items = sorted([p for p in d.iterdir() if p.name not in skip and not p.name.startswith(".") or p.name in (".env.example", ".gitignore")],
                       key=lambda p: (p.is_file(), p.name.lower()))
        items = [p for p in items if p.name != ".env"]
        for i, p in enumerate(items):
            last = i == len(items) - 1
            lines.append(f"{prefix}{'└── ' if last else '├── '}{p.name}{'/' if p.is_dir() else ''}")
            if p.is_dir() and depth < max_depth and p.name not in ("evidence", "report", "export"):
                walk(p, prefix + ("    " if last else "│   "), depth + 1)

    walk(PROJECT_DIR, "", 1)
    if (PROJECT_DIR / "data").exists():
        lines.insert(1, "├── data/            (Parquet nhận từ Analytics: analytics/, gold/)")
    return "\n".join(lines)


def evidence_csv(name: str) -> list[dict[str, str]]:
    p = EVIDENCE_DIR / name
    if not p.exists():
        return []
    return list(csv.DictReader(io.StringIO(p.read_text(encoding="utf-8-sig"))))


def evidence_json(name: str) -> dict:
    p = EVIDENCE_DIR / name
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return {}


TAB_LABELS = {"tong_quan_xu_huong": "Tổng quan & xu hướng", "danh_muc_mua_vu": "Danh mục & mùa vụ",
              "dia_ly_logistics": "Địa lý & logistics", "khach_hang_rfm": "Khách hàng & RFM", "nguoi_ban": "Người bán",
              "giao_tre_review_thanh_toan": "Giao trễ, đánh giá & thanh toán",
              "goi_y_quyet_dinh_nguon_du_lieu": "Gợi ý quyết định & nguồn dữ liệu"}


def tab_label(scenario: str) -> str:
    """'5 · nguoi_ban' (dashboard_load_time.csv) -> '5 · Người bán' (tên tab trên dashboard)."""
    num, _, slug = scenario.partition("·")
    slug = slug.strip()
    return f"{num.strip()} · {TAB_LABELS.get(slug, slug.replace('_', ' '))}"


def extra_vars() -> dict[str, str]:
    """Số liệu từ các tệp minh chứng bổ sung: tải dashboard, thí nghiệm scale, project Neon."""
    v: dict[str, str] = {}
    s = evidence_json("dashboard_load_summary.json")
    if s:
        v.update(
            dash_tab_cold_median=fmt_num(s["tab_cold_median_s"], 2), dash_tab_warm_median=fmt_num(s["tab_warm_median_s"], 2),
            dash_tabs_cold_total=fmt_num(s["tabs_cold_total_s"], 2), dash_tabs_warm_total=fmt_num(s["tabs_warm_total_s"], 2),
            dash_shell_cold=fmt_num(s["dashboard_shell_s"]["cold"], 1),
            chart_force_median=fmt_int(s["chart_force_median_ms"]), chart_cache_median=fmt_int(s["chart_cache_median_ms"]),
            charts_ok=f"{s['charts_ok']}/{s['charts_measured']}",
            chart_speedup=fmt_int(s["chart_force_median_ms"] / s["chart_cache_median_ms"]),
        )
    rows = evidence_csv("dashboard_load_time.csv")
    tabs = [r for r in rows if r.get("kind") == "tab"]
    flt = [r for r in rows if r.get("kind") == "filter"]
    if tabs:
        worst = max(tabs, key=lambda r: float(r["cold_s"]))
        v.update(dash_tabs=str(len(tabs)), dash_components=str(sum(int(r["components"]) for r in tabs)),
                 dash_cold_max=fmt_num(float(worst["cold_s"]), 2), dash_errors=str(sum(int(r["errors"] or 0) for r in rows)),
                 dash_cold_max_tab=tab_label(worst["scenario"]).split("·")[-1].strip(),
                 dash_cold_over5=f"{sum(1 for r in tabs if float(r['cold_s']) > 5)}/{len(tabs)}",
                 dash_cold_verdict=("Đạt" if all(float(r["cold_s"]) <= 5 for r in tabs) else
                                    "Đạt một phần" if s and s["tab_cold_median_s"] < 5 else "Chưa đạt"))
    if flt:
        t = [float(r["cold_s"]) for r in flt]
        v.update(filter_n=str(len(flt)), filter_min=fmt_num(min(t), 2), filter_max=fmt_num(max(t), 2),
                 filter_ok=f"{sum(1 for r in flt if (r['errors'] or '0') == '0')}/{len(flt)}")
    sc = evidence_csv("scale_experiment.csv")
    if sc:
        lo, hi = sc[0], sc[-1]
        v.update(scale_max=hi["factor"], scale_rows=fmt_int(hi["rows"]), scale_raw_lo=fmt_num(float(lo["raw_month_category_ms"]), 1),
                 scale_raw_hi=fmt_num(float(hi["raw_month_category_ms"]), 1), scale_view=fmt_num(float(hi["preaggregated_view_ms"]), 1),
                 scale_idx_hi=fmt_num(float(hi["raw_filtered_indexed_ms"]), 1))
    qa = evidence_json("qa_results.json").get("summary")
    if qa:
        total = qa["PASS"] + qa["FAIL"] + qa["KNOWN"]
        v.update(qa_total=str(total), qa_pass=str(qa["PASS"]), qa_fail=str(qa["FAIL"]), qa_known=str(qa["KNOWN"]),
                 qa_verdict="Đạt" if qa["FAIL"] == 0 else "Chưa đạt")
    nj = evidence_json("neon_project.json")
    if nj:
        v.update(neon_cu=nj.get("autoscaling_cu", "").replace(".", ","), neon_plan=nj.get("plan", ""),
                 neon_project_id=nj.get("id", ""), neon_branch_gib=str(nj.get("branch_logical_size_limit_gib", "")),
                 neon_compute_s=fmt_int(nj.get("compute_time_seconds", 0)), neon_active_s=fmt_int(nj.get("active_time_seconds", 0)))
    return v


def read_project_file(rel: str) -> str | None:
    p = PROJECT_DIR / rel
    if not p.exists() or p.name == ".env":
        return None
    return p.read_text(encoding="utf-8", errors="replace")
