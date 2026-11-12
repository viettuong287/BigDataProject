"""Sinh biểu đồ cho báo cáo từ các bảng Parquet Analytics (matplotlib, không cần Neon/Superset)."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

from inputs import FIG_DIR, TableInfo  # noqa: E402

plt.rcParams.update({
    "font.family": ["Arial", "DejaVu Sans"],
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "figure.dpi": 100,
})
BLUE, ORANGE, RED, GREEN, GREY = "#2E5A88", "#E07B39", "#C0392B", "#2E8B57", "#7F8C8D"


def _df(tables: dict[str, TableInfo], name: str):
    df = tables[name].table.to_pandas()
    for c in df.columns:
        if df[c].dtype == object and len(df) and type(df[c].iloc[0]).__name__ == "Decimal":
            df[c] = df[c].astype(float)
    return df


def _save(fig, name: str) -> Path:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    p = FIG_DIR / f"{name}.png"
    fig.savefig(p, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return p


# ---------------------------------------------------------------- sơ đồ kiến trúc
def architecture() -> Path:
    fig, ax = plt.subplots(figsize=(13, 6.6))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 6.6)
    ax.axis("off")
    ax.grid(False)

    def box(x, y, w, h, title, body, color, fs=9):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05,rounding_size=0.12",
                                    fc=color, ec="#333333", lw=1.1))
        ax.text(x + w / 2, y + h - 0.22, title, ha="center", va="top", fontsize=fs + 1, weight="bold")
        ax.text(x + w / 2, y + h - 0.6, body, ha="center", va="top", fontsize=fs, linespacing=1.35)

    def arrow(x1, y1, x2, y2, label="", dy=0.15, style="-|>", ls="-"):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=16,
                                     lw=1.6, color="#333333", linestyle=ls))
        if label:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2 + dy, label, ha="center", va="bottom", fontsize=8,
                    style="italic", color="#1F3B57")

    # vùng ranh giới
    ax.add_patch(FancyBboxPatch((0.1, 0.25), 2.75, 6.05, boxstyle="round,pad=0.02", fc="none", ec=GREY, ls="--"))
    ax.text(1.47, 6.38, "UPSTREAM (nhóm Analytics)", ha="center", fontsize=9, color=GREY, weight="bold")
    ax.add_patch(FancyBboxPatch((3.05, 0.25), 7.55, 6.05, boxstyle="round,pad=0.02", fc="none", ec=BLUE, ls="--", lw=1.4))
    ax.text(6.82, 6.38, "PHẠM VI NHÓM: ANALYTICS → PRESENTATION", ha="center", fontsize=9.5, color=BLUE, weight="bold")
    ax.add_patch(FancyBboxPatch((10.8, 0.25), 2.1, 6.05, boxstyle="round,pad=0.02", fc="none", ec=GREY, ls="--"))
    ax.text(11.85, 6.38, "DOWNSTREAM", ha="center", fontsize=9, color=GREY, weight="bold")

    box(0.25, 3.7, 2.45, 2.3, "Spark cluster", "1 master + 2 worker\n(4 core, Spark 3.5.3)\nSpark SQL + MLlib\nK-Means k=4", "#EDEDED")
    box(0.25, 0.55, 2.45, 2.6, "Data Lake (Parquet)", "data/analytics/: 16 bảng\n6 chủ đề nghiệp vụ\ndata/gold/: 7 bảng\n+ ANALYTICS_HANDOVER\n(data contract)", "#FFF4D6")
    arrow(1.47, 3.7, 1.47, 3.15, "ghi Parquet", dy=-0.05)

    box(3.25, 2.0, 2.2, 2.6, "Loader (Python)", "pyarrow đọc schema\n→ DDL tự sinh\n→ COPY (psycopg 3)\n→ kiểm tra số dòng\n→ load_log", "#DCEBF7")
    arrow(2.7, 1.9, 3.25, 2.9, "Parquet\n(cột, nén)", dy=0.05)

    box(5.8, 1.0, 2.6, 4.6, "Neon Serverless\nPostgres 18", "", "#D5F0E3")
    ax.text(7.1, 4.55, "analytics (16 + load_log)\ngold (7 fact/agg)", ha="center", va="top", fontsize=8.5,
            bbox=dict(boxstyle="round", fc="white", ec=GREEN))
    ax.text(7.1, 3.45, "presentation\nviews v_* + dim_state", ha="center", va="top", fontsize=8.5,
            bbox=dict(boxstyle="round", fc="white", ec=GREEN))
    ax.text(7.1, 2.25, "Compute: autoscaling,\nscale-to-zero\nStorage: pageserver +\nsafekeeper + S3", ha="center",
            va="top", fontsize=7.8, color="#145A32")
    arrow(5.45, 3.3, 5.8, 3.3, "")
    ax.text(5.62, 3.85, "COPY\nTLS:5432", ha="center", fontsize=7.5, style="italic", color="#1F3B57")
    arrow(7.1, 3.95, 7.1, 3.55, "", style="-|>")

    box(8.7, 2.0, 1.75, 2.6, "Apache\nSuperset 4.1", "(Docker :8088)\ndatasets\ncharts (ECharts)\nnative filters\ncache 10'", "#F6E0F0", fs=8.5)
    arrow(8.4, 3.3, 8.7, 3.3, "")
    ax.text(8.55, 3.85, "SQL\nSQLAlchemy", ha="center", fontsize=7.5, style="italic", color="#1F3B57")

    box(10.95, 3.7, 1.8, 2.3, "Người dùng\nnghiệp vụ", "Ban điều hành\nCategory, Ops\nCRM, Seller ops", "#FDEBD0", fs=8.5)
    arrow(10.45, 3.9, 10.95, 4.6, "HTTP", dy=0.05)
    box(10.95, 0.55, 1.8, 2.6, "Decision /\nAction", "rule engine,\ncảnh báo seller,\nCSKH đơn trễ", "#FADBD8", fs=8.5)
    arrow(8.4, 1.5, 10.95, 1.5, "views gợi ý quyết định (SQL / CSV / API)", dy=0.08, ls="--")
    return _save(fig, "fig_architecture")


# ---------------------------------------------------------------- quy mô dữ liệu
def table_sizes(tables: dict[str, TableInfo]) -> Path:
    names = list(tables)
    rows = [tables[n].rows for n in names]
    fig, ax = plt.subplots(figsize=(9, 5))
    y = range(len(names))
    ax.barh(y, rows, color=BLUE)
    ax.set_yticks(list(y), names)
    ax.invert_yaxis()
    ax.set_xscale("log")
    ax.set_xlabel("Số dòng (thang log)")
    for i, r in enumerate(rows):
        ax.text(r * 1.1, i, f"{r:,}".replace(",", "."), va="center", fontsize=8)
    ax.set_title("Số dòng của 16 bảng Parquet Analytics (đầu vào của tầng Presentation)")
    return _save(fig, "fig_table_sizes")


# ---------------------------------------------------------------- 1. KPI theo tháng
def kpi_trend(tables) -> Path:
    df = _df(tables, "kpi_monthly").sort_values(["purchase_year", "purchase_month"])
    lbl = [f"{m:02d}/{str(y)[2:]}" for y, m in zip(df.purchase_year, df.purchase_month)]
    x = range(len(df))
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    colors = [ORANGE if b else BLUE for b in df.is_black_friday_month]
    a1.bar(x, df.revenue / 1e3, color=colors)
    a1.set_ylabel("Doanh thu (nghìn BRL)")
    a1b = a1.twinx()
    a1b.plot(x, df.orders, color=GREY, marker="o", ms=3, lw=1.2)
    a1b.set_ylabel("Số đơn")
    a1b.grid(False)
    i_bf = int(df.reset_index(drop=True).revenue.idxmax())
    a1.annotate("11/2017: đỉnh doanh thu\nMoM +52%", (i_bf, df.revenue.iloc[i_bf] / 1e3),
                xytext=(i_bf - 6.5, df.revenue.max() / 1e3 * 0.93), arrowprops=dict(arrowstyle="->"), fontsize=9)
    a1.set_title("(a) Doanh thu và số đơn theo tháng")
    a2.plot(x, df.late_delivery_pct, color=RED, marker="o", ms=3, label="% đơn giao trễ")
    a2.set_ylabel("% đơn giao trễ", color=RED)
    a2b = a2.twinx()
    a2b.plot(x, df.avg_review_score, color=GREEN, marker="s", ms=3, label="Điểm review TB")
    a2b.set_ylabel("Điểm review TB (1–5)", color=GREEN)
    a2b.grid(False)
    a2.set_title("(b) Tỷ lệ giao trễ và điểm review trung bình")
    a2.set_xticks(list(x), lbl, rotation=60)
    fig.tight_layout()
    return _save(fig, "fig_kpi_trend")


# ---------------------------------------------------------------- 2. Danh mục
def category_pareto(tables, top: int = 25) -> Path:
    df = _df(tables, "category_pareto").sort_values("revenue", ascending=False).reset_index(drop=True)
    d = df.head(top)
    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.bar(range(len(d)), d.revenue / 1e3, color=BLUE)
    ax.set_ylabel("Doanh thu (nghìn BRL)")
    ax.set_xticks(range(len(d)), d.category, rotation=70, ha="right", fontsize=8)
    ax2 = ax.twinx()
    ax2.plot(range(len(d)), d.cumulative_share_pct, color=ORANGE, marker="o", ms=3)
    ax2.axhline(80, color=RED, ls="--", lw=1)
    ax2.text(len(d) - 1, 81, "80%", color=RED, ha="right", fontsize=9)
    ax2.set_ylim(0, 100)
    ax2.set_ylabel("% doanh thu cộng dồn")
    ax2.grid(False)
    ax.set_title(f"Pareto doanh thu theo danh mục (top {top}/{len(df)} danh mục)")
    return _save(fig, "fig_category_pareto")


def category_season(tables, top: int = 8) -> Path:
    par = _df(tables, "category_pareto").sort_values("revenue", ascending=False)
    cats = list(par.category.head(top))
    s = _df(tables, "category_seasonality")
    piv = s[s.category.isin(cats)].pivot_table(index="category", columns="purchase_month",
                                                values="pct_of_category_year", aggfunc="sum").reindex(cats)
    fig, ax = plt.subplots(figsize=(10, 4.4))
    im = ax.imshow(piv.values, aspect="auto", cmap="YlOrRd")
    ax.set_xticks(range(piv.shape[1]), [f"T{m}" for m in piv.columns])
    ax.set_yticks(range(len(cats)), cats)
    ax.grid(False)
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = piv.values[i, j]
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=7.5,
                    color="white" if v > piv.values.max() * 0.6 else "black")
    fig.colorbar(im, ax=ax, label="% doanh thu năm 2017 của danh mục")
    ax.set_title("Mùa vụ 2017: tỷ trọng doanh thu từng tháng của 8 danh mục lớn nhất")
    return _save(fig, "fig_category_season")


# ---------------------------------------------------------------- 3. Địa lý
def state_scatter(tables) -> Path:
    df = _df(tables, "state_logistics")
    fig, ax = plt.subplots(figsize=(9.5, 5.6))
    sc = ax.scatter(df.avg_delivery_days, df.avg_review_score, s=df.revenue / df.revenue.max() * 1800 + 25,
                    c=df.late_delivery_pct, cmap="RdYlGn_r", alpha=0.75, edgecolors="#333333", lw=0.6)
    for _, r in df.iterrows():
        ax.text(r.avg_delivery_days, r.avg_review_score, r.customer_state, ha="center", va="center", fontsize=7.5)
    fig.colorbar(sc, ax=ax, label="% đơn giao trễ")
    ax.set_xlabel("Số ngày giao trung bình")
    ax.set_ylabel("Điểm review trung bình")
    ax.set_title("27 bang: thời gian giao vs điểm review (kích thước = doanh thu)")
    return _save(fig, "fig_state_scatter")


def distance(tables) -> Path:
    df = _df(tables, "insight_distance").sort_values("band_order")
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    x = range(len(df))
    ax.bar([i - 0.2 for i in x], df.avg_freight, width=0.4, color=BLUE, label="Phí ship TB (BRL)")
    ax.bar([i + 0.2 for i in x], df.avg_delivery_days, width=0.4, color=GREY, label="Ngày giao TB")
    ax.set_xticks(list(x), df.distance_band)
    ax2 = ax.twinx()
    ax2.plot(list(x), df.late_pct, color=RED, marker="o", label="% món trễ")
    ax2.set_ylabel("% món giao trễ", color=RED)
    ax2.set_ylim(0, max(df.late_pct) * 1.4)
    ax2.grid(False)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=8)
    ax.set_title("Khoảng cách người bán → khách: phí ship, thời gian giao và tỷ lệ trễ")
    return _save(fig, "fig_distance")


# ---------------------------------------------------------------- 4. Khách hàng
def rfm_segments(tables) -> Path:
    df = _df(tables, "rfm_scores")
    cnt = df.rfm_segment.value_counts().sort_values()
    fig, ax = plt.subplots(figsize=(8.5, 4))
    colors = [GREEN if not s.startswith("One-shot") else GREY for s in cnt.index]
    ax.barh(cnt.index, cnt.values, color=colors)
    ax.set_xscale("log")
    for i, v in enumerate(cnt.values):
        ax.text(v * 1.08, i, f"{v:,}".replace(",", "."), va="center", fontsize=8.5)
    ax.set_xlabel("Số khách (thang log)")
    ax.set_title("Phân khúc RFM theo luật: khách mua lại (xanh) vs khách mua một lần (xám)")
    return _save(fig, "fig_rfm_segments")


# ---------------------------------------------------------------- 5. Người bán
def seller_lorenz(tables) -> Path:
    df = _df(tables, "seller_pareto").sort_values("revenue", ascending=False).reset_index(drop=True)
    n = len(df)
    xs = [(i + 1) / n * 100 for i in range(n)]
    cum = df.cumulative_share_pct.tolist()
    n80 = int((df.cumulative_share_pct <= 80).sum())
    x80 = n80 / n * 100
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.plot(xs, cum, color=BLUE, lw=2)
    ax.plot([0, 100], [0, 100], color=GREY, ls=":")
    ax.axhline(80, color=RED, ls="--", lw=1)
    ax.axvline(x80, color=RED, ls="--", lw=1)
    ax.annotate(f"{n80:,} người bán ({x80:.2f}%)\ntạo 80% doanh thu".replace(",", "X").replace(".", ",").replace("X", "."),
                (x80, 80), xytext=(x80 + 12, 55), arrowprops=dict(arrowstyle="->"), fontsize=9)
    ax.set_xlabel("% người bán (sắp theo doanh thu giảm dần)")
    ax.set_ylabel("% doanh thu cộng dồn")
    ax.set_title(f"Đường Pareto doanh thu của {n:,} người bán".replace(",", "."))
    return _save(fig, "fig_seller_pareto")


# ---------------------------------------------------------------- 6. Trễ & review, thanh toán
def delay_review(tables) -> Path:
    df = _df(tables, "delay_vs_review").sort_values("band_order")
    names = {"on_time_or_early": "Đúng hạn/sớm", "late_1_3d": "Trễ 1–3 ngày", "late_4_7d": "Trễ 4–7 ngày",
             "late_8_14d": "Trễ 8–14 ngày", "late_15d_plus": "Trễ ≥15 ngày"}
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    x = range(len(df))
    bars = ax.bar(x, df.avg_review, color=[GREEN] + [ORANGE] * (len(df) - 1))
    ax.set_ylim(0, 5)
    ax.set_ylabel("Điểm review trung bình")
    ax.set_xticks(list(x), [names.get(s, s) for s in df.delay_band])
    for b, v in zip(bars, df.avg_review):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.08, f"{v:.2f}", ha="center", fontsize=9)
    ax2 = ax.twinx()
    ax2.plot(list(x), df.pct_1_star, color=RED, marker="o")
    ax2.set_ylabel("% đơn 1 sao", color=RED)
    ax2.set_ylim(0, 100)
    ax2.grid(False)
    ax.set_title("Số ngày trễ so với hẹn và phản ứng của khách (review)")
    return _save(fig, "fig_delay_review")


def payment(tables) -> Path:
    df = _df(tables, "payment_mix")
    piv = df.pivot_table(index="installment_band", columns="main_payment_type", values="avg_order_value")
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    piv.plot(kind="bar", ax=ax, rot=0, colormap="tab10")
    ax.set_ylabel("Giá trị đơn trung bình (BRL)")
    ax.set_xlabel("Nhóm số kỳ trả góp")
    ax.set_title("Giá trị đơn trung bình theo phương thức thanh toán và số kỳ trả góp")
    ax.legend(fontsize=8)
    return _save(fig, "fig_payment")


ALL = {
    "architecture": lambda t: architecture(),
    "table_sizes": table_sizes,
    "kpi_trend": kpi_trend,
    "category_pareto": category_pareto,
    "category_season": category_season,
    "state_scatter": state_scatter,
    "distance": distance,
    "rfm_segments": rfm_segments,
    "seller_pareto": seller_lorenz,
    "delay_review": delay_review,
}


def build_all(tables) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for key, fn in ALL.items():
        try:
            out[key] = fn(tables)
        except Exception as e:  # thiếu bảng → biểu đồ đó thành placeholder
            print(f"[charts] bỏ qua {key}: {e}")
    return out
