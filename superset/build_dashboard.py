"""Dựng dashboard Superset từ code (idempotent): database Neon -> dataset (view presentation.*)
-> chart -> dashboard 7 tab + native filter -> export ZIP vào superset/export/.

Chạy: docker compose run --rm tools python superset/build_dashboard.py
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import sys
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from superset_client import Superset  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = ROOT / "superset" / "export"
DB_NAME = "Neon · olist_analytics"
SCHEMA = "presentation"
DASH_SLUG = "olist-presentation"
DASH_TITLE = "Thương mại điện tử Olist · Phân tích → Trình bày"

# ---------------------------------------------------------------------------------------------
# Nhãn tiếng Việt cho cột (verbose_name) – hiển thị ở header bảng, trục, chú giải, tooltip, bộ lọc.
# Giá trị dữ liệu (tên phân khúc RFM, danh mục, PTTT...) giữ nguyên như bàn giao từ Analytics.
# ---------------------------------------------------------------------------------------------
VERBOSE = {
    "month_date": "Tháng", "month_label": "Tháng", "purchase_month": "Tháng (2017)", "orders": "Số đơn",
    "customers": "Số khách", "items": "Số món", "revenue": "Doanh thu (BRL)", "freight": "Phí vận chuyển (BRL)",
    "gmv": "Giá trị hàng hoá – GMV (BRL)", "avg_order_value": "Giá trị TB/đơn (BRL)",
    "avg_review_score": "Điểm đánh giá TB", "avg_delivery_days": "Ngày giao TB", "late_delivery_pct": "% giao trễ",
    "revenue_mom_pct": "Doanh thu so với tháng trước (%)", "orders_mom_pct": "Số đơn so với tháng trước (%)",
    "revenue_yoy_pct": "Doanh thu so với cùng kỳ năm trước (%)", "revenue_rank": "Hạng doanh thu",
    "category": "Danh mục", "avg_price": "Giá TB (BRL)", "freight_to_revenue_pct": "Phí vận chuyển/doanh thu (%)",
    "revenue_share_pct": "Tỷ trọng doanh thu (%)", "cumulative_share_pct": "Cộng dồn (%)",
    "pareto_class": "Nhóm Pareto", "category_label": "Danh mục (hạng)", "band_label": "Khoảng cách",
    "watchlist_label": "Danh sách theo dõi", "customer_state": "Bang khách hàng", "state_name": "Tên bang",
    "region": "Vùng", "avg_freight": "Phí vận chuyển TB (BRL)", "freight_pct_of_revenue": "Phí vận chuyển/doanh thu (%)",
    "distance_band": "Khoảng cách", "late_pct": "% trễ", "avg_delay_days": "Lệch hẹn TB (ngày)",
    "rfm_segment": "Phân khúc RFM", "cluster_name": "Cụm K-Means", "recency_days": "Số ngày từ lần mua cuối",
    "frequency": "Số lần mua", "monetary": "Tổng chi tiêu (BRL)", "pct_customers": "% khách",
    "avg_recency_days": "Số ngày từ lần mua cuối (TB)", "avg_frequency": "Số lần mua TB",
    "avg_monetary": "Chi tiêu TB (BRL)", "crm_action": "Hành động CRM", "avg_recency": "Số ngày từ lần mua cuối (TB)",
    "champions": "Số khách Champions", "loyal": "Số khách Loyal", "at_risk": "Số khách At Risk",
    "cohort_label": "Nhóm", "pct": "%", "avg_aov": "Giá trị TB/đơn (BRL)",
    "repeat_customers": "Khách mua lại", "seller_short": "Người bán", "seller_state": "Bang người bán",
    "avg_distance_km": "Khoảng cách TB (km)", "active_months": "Số tháng hoạt động",
    "pareto_group": "Nhóm Pareto", "is_watchlist": "Trong danh sách theo dõi", "violations": "Số vi phạm",
    "reasons": "Lý do", "alert_level": "Mức cảnh báo", "recommended_action": "Hành động đề xuất",
    "revenue_pctile": "Phân vị doanh thu", "delivery_label": "Giao hàng", "avg_review": "Điểm đánh giá TB",
    "pct_score_1_2": "% 1–2 sao", "pct_has_comment": "% có bình luận", "delay_label": "Mức trễ",
    "pct_1_star": "% 1 sao", "main_payment_type": "Phương thức thanh toán", "installment_label": "Kỳ trả góp",
    "pct_orders": "% đơn", "priority": "Ưu tiên", "severity": "Mức độ", "topic": "Chủ đề",
    "signal": "Tín hiệu", "metric_value": "Giá trị", "detail": "Chi tiết", "threshold": "Ngưỡng",
    "action": "Hành động gợi ý", "source": "Nguồn", "table_fq": "Bảng", "rows": "Số dòng",
    "parquet_rows": "Dòng Parquet", "row_count_ok": "Khớp", "parquet_files": "Số file",
    "parquet_mb": "Parquet (MB)", "seconds": "Thời gian (s)", "rows_per_sec": "Dòng/giây",
    "source_path": "Đường dẫn nguồn", "loaded_at": "Thời điểm nạp", "review_score": "Điểm đánh giá",
    "order_value": "Giá trị đơn (BRL)", "late_flag": "Trễ (0/1)",
    "band_order": "Thứ tự khoảng", "cluster": "Mã cụm", "cohort": "Nhóm khách",
    "customer_unique_id": "Mã khách (duy nhất)", "delay_band": "Khoảng trễ", "delivery": "Giao hàng",
    "delivery_days": "Số ngày giao", "delivery_delay_days": "Số ngày lệch hẹn", "distance_km": "Khoảng cách (km)",
    "r_score": "Điểm R", "f_score": "Điểm F", "m_score": "Điểm M",
    "gold_revenue_total": "Tổng doanh thu gold (BRL)", "gold_valid_orders": "Số đơn hợp lệ (gold)",
    "installment_band": "Nhóm kỳ trả góp", "is_black_friday_month": "Tháng Black Friday", "iso_code": "Mã ISO bang",
    "kpi_months": "Số tháng KPI", "kpi_window_revenue": "Doanh thu khung KPI (BRL)",
    "late_review": "Đánh giá TB đơn trễ", "on_time_review": "Đánh giá TB đơn đúng hạn",
    "max_installments": "Số kỳ trả góp", "order_id": "Mã đơn", "order_item_id": "STT dòng sản phẩm",
    "order_status": "Trạng thái đơn", "pct_of_category_year": "% doanh thu năm của danh mục",
    "peak_mom_pct": "Tăng trưởng đỉnh so với tháng trước (%)", "peak_month": "Tháng đỉnh",
    "purchase_date": "Ngày mua", "purchase_year": "Năm", "repeat_pct": "% khách mua lại", "run_id": "Mã lần nạp",
    "schema_name": "Schema", "segment_order": "Thứ tự phân khúc", "seller_id": "Mã người bán",
    "sellers": "Số người bán", "sellers_80pct_revenue": "Người bán tạo 80% doanh thu", "table_name": "Tên bảng",
    "watchlist_sellers": "Người bán cần theo dõi",
}
# Nhãn cho metric mặc định của dataset (Superset tự tạo "count" với nhãn COUNT(*)).
METRIC_VERBOSE = {"count": "Số dòng"}

DATASETS = [
    "v_kpi_monthly", "v_orders", "v_category_pareto", "v_category_seasonality", "v_category_monthly",
    "v_sales_items", "v_state_logistics", "v_insight_distance", "v_rfm_customers", "v_rfm_segments",
    "v_cluster_profile", "v_repeat_profile", "v_repeat_categories", "v_repeat_states", "v_seller_pareto",
    "v_seller_watchlist", "v_late_vs_review", "v_delay_vs_review", "v_payment_mix", "v_decision_hints",
    "v_load_log", "v_kpi_overview",
]


# ---------------------------------------------------------------------------------------------
# Tiện ích dựng params
# ---------------------------------------------------------------------------------------------
def M(label: str, sql: str) -> dict:
    """Adhoc SQL metric."""
    return {"expressionType": "SQL", "sqlExpression": sql, "label": label, "hasCustomLabel": True,
            "optionName": "metric_" + re.sub(r"\W+", "_", label.lower())}


def TF(col: str = "month_date") -> dict:
    """Bộ lọc thời gian rỗng để native filter 'Khoảng thời gian' ghi đè."""
    return {"clause": "WHERE", "subject": col, "operator": "TEMPORAL_RANGE", "comparator": "No filter",
            "expressionType": "SIMPLE"}


def SQLF(sql: str) -> dict:
    return {"clause": "WHERE", "expressionType": "SQL", "sqlExpression": sql}


# Bảng màu "Olist Insight" khai báo trong superset_config.py (EXTRA_*_COLOR_SCHEMES), đồng bộ với landing page.
COLOR_SCHEME = "olistInsight"
SEQ_SCHEME = "olistInsightSeq"
GREEN, YELLOW, RED = "#34d399", "#fbbf24", "#f87171"
DASH_CSS = (ROOT / "superset" / "dashboard.css").read_text(encoding="utf-8")


def big(metric, fmt=",.0f", sub="", filters=None):
    return {"viz_type": "big_number_total", "metric": metric, "adhoc_filters": filters or [],
            "y_axis_format": fmt, "header_font_size": 0.3, "subheader_font_size": 0.125, "subheader": sub}


def big_trend(metric, fmt=",.0f"):
    return {"viz_type": "big_number", "x_axis": "month_date", "time_grain_sqla": "P1M", "metric": metric,
            "adhoc_filters": [TF()], "show_trend_line": True, "start_y_axis_at_zero": True,
            "compare_lag": 1, "compare_suffix": "so với tháng trước", "y_axis_format": fmt,
            "header_font_size": 0.3, "subheader_font_size": 0.125, "rolling_type": "None",
            "time_format": "%Y-%m", "color_picker": {"r": 52, "g": 211, "b": 153, "a": 1}}


def ts(viz, metrics, x="month_date", groupby=None, filters=None, fmt=",.0f", **extra):
    p = {"viz_type": viz, "x_axis": x, "metrics": metrics, "groupby": groupby or [],
         "adhoc_filters": filters if filters is not None else ([TF()] if x == "month_date" else []),
         "row_limit": 10000, "truncate_metric": True, "show_legend": True, "legendOrientation": "top",
         "rich_tooltip": True, "y_axis_format": fmt, "x_axis_time_format": "%Y-%m", "markerEnabled": True,
         "zoomable": False, "color_scheme": COLOR_SCHEME, "only_total": True, "order_desc": True}
    if x == "month_date":
        p["time_grain_sqla"] = "P1M"
    p.update(extra)
    return p


def cat_bar(metric, x, limit=15, fmt=",.0f", horizontal=False, filters=None, groupby=None, **extra):
    p = ts("echarts_timeseries_bar", [metric], x=x, groupby=groupby, filters=filters or [], fmt=fmt,
           row_limit=limit, x_axis_sort=metric["label"], x_axis_sort_asc=horizontal,
           orientation="horizontal" if horizontal else "vertical", show_value=True,
           show_legend=bool(groupby), xAxisLabelRotation=0 if horizontal else 45)
    p.update(extra)
    return p


def mixed(a, b, x="month_date", type_a="bar", type_b="line", fmt_a=",.0f", fmt_b=",.2f", filters=None, **extra):
    f = filters if filters is not None else ([TF()] if x == "month_date" else [])
    p = {"viz_type": "mixed_timeseries", "x_axis": x, "metrics": [a], "metrics_b": [b], "groupby": [],
         "groupby_b": [], "adhoc_filters": f, "adhoc_filters_b": f, "seriesType": type_a, "seriesTypeB": type_b,
         "yAxisIndex": 0, "yAxisIndexB": 1, "y_axis_format": fmt_a, "y_axis_format_secondary": fmt_b,
         "show_legend": True, "legendOrientation": "top", "rich_tooltip": True, "markerEnabled": True,
         "row_limit": 10000, "row_limit_b": 10000, "truncate_metric": True, "zoomable": False,
         "x_axis_time_format": "%Y-%m", "color_scheme": COLOR_SCHEME, "show_value": False,
         "show_valueB": True, "order_desc": True, "order_desc_b": True}
    if x == "month_date":
        p["time_grain_sqla"] = "P1M"
    p.update(extra)
    return p


def table(columns, order=None, limit=1000, page=10, fmt=None, cond=None, filters=None, **extra):
    return {"viz_type": "table", "query_mode": "raw", "all_columns": columns,
            "order_by_cols": [json.dumps(o) for o in (order or [])], "row_limit": limit,
            "server_page_length": page, "include_search": True, "show_cell_bars": True,
            "allow_rearrange_columns": True, "table_timestamp_format": "%Y-%m",
            # Cột số không khai báo định dạng vẫn đi qua D3 để dùng dấu thập phân "," (D3_FORMAT tiếng Việt).
            "column_config": {c: {"d3NumberFormat": (fmt or {}).get(c, ",.2~f")} for c in columns},
            "conditional_formatting": cond or [], "adhoc_filters": filters or [], **extra}


def agg_table(groupby, metrics, sort=None, limit=1000, filters=None, **extra):
    return {"viz_type": "table", "query_mode": "aggregate", "groupby": groupby, "metrics": metrics,
            "timeseries_limit_metric": sort or metrics[0], "order_desc": True, "row_limit": limit,
            "show_cell_bars": True, "include_search": False, "adhoc_filters": filters or [], **extra}


def pie(metric, groupby, **extra):
    p = {"viz_type": "pie", "groupby": [groupby], "metric": metric, "adhoc_filters": [], "row_limit": 100,
         "sort_by_metric": True, "show_labels": True, "label_type": "key_percent", "labels_outside": True,
         "label_line": True, "donut": True, "innerRadius": 35, "outerRadius": 70, "show_legend": True,
         "legendOrientation": "right", "number_format": ",.0f", "color_scheme": COLOR_SCHEME,
         "show_total": True}
    p.update(extra)
    return p


def cond(col, op, val, color):
    return {"column": col, "operator": op, "targetValue": val, "colorScheme": color}


# ---------------------------------------------------------------------------------------------
# Đặc tả dashboard: tab -> hàng -> (key, dataset, tên chart, params, width, height)
# ---------------------------------------------------------------------------------------------
REV = M("Doanh thu (BRL)", "SUM(revenue)")
ORDERS_CNT = M("Số đơn", "COUNT(*)")

TABS = [
    ("Tổng quan & xu hướng", [
        [
            # Tiêu đề thẻ KPI phải ngắn: thẻ rộng 2/12 cột, khi có bộ lọc Superset chèn thêm biểu tượng phễu vào tiêu đề.
            ("kpi_rev", "v_orders", "Doanh thu", big(REV, sub="BRL, tổng giá sản phẩm đơn hợp lệ", filters=[TF()]), 2, 22),
            ("kpi_orders", "v_orders", "Đơn hàng", big(ORDERS_CNT, sub="đơn hợp lệ (is_valid_sale)", filters=[TF()]), 2, 22),
            ("kpi_cust", "v_orders", "Khách hàng", big(M("Khách", "COUNT(DISTINCT customer_unique_id)"), sub="không trùng (customer_unique_id)", filters=[TF()]), 2, 22),
            ("kpi_aov", "v_orders", "Giá trị TB/đơn", big(M("Giá trị TB/đơn", "AVG(order_value)"), fmt=",.2f", sub="AOV, BRL mỗi đơn", filters=[TF()]), 2, 22),
            ("kpi_late", "v_orders", "Tỷ lệ giao trễ", big(M("% trễ", "AVG(late_flag)"), fmt=".2%", sub="trên đơn đã giao", filters=[TF()]), 2, 22),
            ("kpi_review", "v_orders", "Đánh giá TB", big(M("Đánh giá TB", "AVG(review_score)"), fmt=".2f", sub="sao, cấp đơn hàng", filters=[TF()]), 2, 22),
        ],
        [
            ("trend_big", "v_kpi_monthly", "Doanh thu tháng gần nhất & xu hướng", big_trend(REV), 4, 50),
            ("trend_rev_orders", "v_kpi_monthly", "Doanh thu (cột) và số đơn (đường) theo tháng",
             mixed(REV, M("Số đơn", "SUM(orders)"), fmt_b=",.0f"), 8, 50),
        ],
        [
            ("trend_late_review", "v_kpi_monthly", "Tỷ lệ giao trễ (%) và điểm đánh giá TB theo tháng",
             mixed(M("% giao trễ", "MAX(late_delivery_pct)"), M("Đánh giá TB", "MAX(avg_review_score)"), fmt_a=",.1f"), 6, 50),
            ("trend_mom", "v_kpi_monthly", "Tăng trưởng doanh thu so với tháng trước (%)",
             ts("echarts_timeseries_bar", [M("So với tháng trước (%)", "MAX(revenue_mom_pct)")], fmt=",.1f", show_value=True, show_legend=False), 6, 50),
        ],
        [
            ("kpi_table", "v_kpi_monthly", "Bảng KPI theo tháng (2017-01 → 2018-08)",
             table(["month_label", "orders", "customers", "revenue", "avg_order_value", "late_delivery_pct",
                    "avg_review_score", "revenue_mom_pct", "revenue_yoy_pct", "revenue_rank"],
                   order=[["month_date", True]], page=20, filters=[TF()],
                   fmt={"revenue": ",.0f", "avg_order_value": ",.2f"},
                   cond=[cond("late_delivery_pct", ">", 15, RED), cond("avg_review_score", "<", 4, YELLOW),
                         cond("revenue_rank", "<=", 3, GREEN)]), 12, 60),
        ],
    ]),
    ("Danh mục & mùa vụ", [
        [
            ("cat_pareto", "v_category_pareto", "Pareto danh mục: doanh thu (cột) & tỷ trọng cộng dồn % (đường) – top 25",
             mixed(REV, M("Cộng dồn (%)", "MAX(cumulative_share_pct)"), x="category_label", fmt_b=",.1f",
                   filters=[SQLF("revenue_rank <= 25")], x_axis_sort="category_label", x_axis_sort_asc=True,
                   xAxisLabelRotation=45), 12, 60),
        ],
        [
            ("cat_season", "v_category_seasonality", "Mùa vụ 2017: % doanh thu năm theo tháng (top 12 danh mục)",
             {"viz_type": "heatmap_v2", "x_axis": "purchase_month", "groupby": "category",
              "metric": M("% doanh thu năm", "SUM(pct_of_category_year)"),
              "adhoc_filters": [SQLF("revenue_rank <= 12")],
              "row_limit": 10000, "sort_x_axis": "alpha_asc", "sort_y_axis": "alpha_asc", "normalize_across": "heatmap",
              "legend_type": "continuous", "linear_color_scheme": SEQ_SCHEME, "xscale_interval": -1,
              "yscale_interval": -1, "left_margin": "auto", "bottom_margin": "auto", "value_bounds": [None, None],
              "y_axis_format": ",.1f", "show_legend": True, "show_percentage": False, "show_values": True}, 7, 60),
            ("cat_freight", "v_category_pareto", "Phí vận chuyển / doanh thu (%) – 15 danh mục lớn nhất",
             cat_bar(M("Phí vận chuyển/doanh thu (%)", "MAX(freight_to_revenue_pct)"), "category", limit=15, fmt=",.1f",
                     horizontal=True, filters=[SQLF("revenue_rank <= 15")]), 5, 60),
        ],
        [
            ("cat_trend", "v_category_monthly", "Doanh thu theo tháng của 6 danh mục lớn nhất (lọc được theo danh mục)",
             ts("echarts_timeseries_line", [REV], groupby=["category"], series_limit=6, series_limit_metric=REV), 12, 50),
        ],
    ]),
    ("Địa lý & logistics", [
        [
            ("geo_map", "v_state_logistics", "Bản đồ doanh thu theo bang (Brazil)",
             {"viz_type": "country_map", "select_country": "brazil", "entity": "iso_code", "metric": REV,
              "adhoc_filters": [], "linear_color_scheme": SEQ_SCHEME, "number_format": ",.0f"}, 6, 70),
            ("geo_bubble", "v_state_logistics", "Ngày giao TB và điểm đánh giá TB theo bang (kích thước = doanh thu)",
             {"viz_type": "bubble_v2", "entity": "customer_state", "series": "region",
              "x": M("Ngày giao TB", "MAX(avg_delivery_days)"), "y": M("Đánh giá TB", "MAX(avg_review_score)"),
              "size": REV, "adhoc_filters": [], "row_limit": 100, "max_bubble_size": "40",
              "x_axis_label": "Ngày giao trung bình", "y_axis_label": "Điểm đánh giá trung bình", "xAxisFormat": ",.1f",
              "y_axis_format": ",.2f", "truncateYAxis": True, "y_axis_bounds": [3.6, 4.4], "opacity": 0.7,
              "show_legend": True, "color_scheme": COLOR_SCHEME, "tooltipSizeFormat": ",.0f"}, 6, 70),
        ],
        [
            ("geo_late", "v_state_logistics", "% giao trễ theo bang",
             cat_bar(M("% giao trễ", "MAX(late_delivery_pct)"), "customer_state", limit=27, fmt=",.1f"), 6, 50),
            ("geo_distance", "v_insight_distance", "Khoảng cách người bán → khách: phí vận chuyển TB (cột) & % trễ (đường)",
             mixed(M("Phí vận chuyển TB (BRL)", "MAX(avg_freight)"), M("% trễ", "MAX(late_pct)"), x="band_label",
                   fmt_a=",.2f", fmt_b=",.2f", x_axis_sort="band_label", x_axis_sort_asc=True, show_value=True), 6, 50),
        ],
        [
            ("geo_table", "v_state_logistics", "Bảng logistics theo bang",
             table(["customer_state", "state_name", "region", "orders", "revenue", "revenue_share_pct",
                    "avg_order_value", "freight_pct_of_revenue", "avg_delivery_days", "late_delivery_pct",
                    "avg_review_score"], order=[["revenue", False]], page=27,
                   fmt={"revenue": ",.0f"},
                   cond=[cond("late_delivery_pct", ">", 10, RED), cond("avg_review_score", "<", 4, YELLOW),
                         cond("avg_delivery_days", "<", 10, GREEN)]), 12, 60),
        ],
    ]),
    ("Khách hàng & RFM", [
        [
            ("rfm_total", "v_rfm_customers", "Khách hàng (RFM)", big(M("Khách", "COUNT(*)"), sub="customer_unique_id"), 3, 22),
            ("rfm_repeat", "v_rfm_customers", "Khách mua lại", big(M("Khách mua lại", "SUM(CASE WHEN frequency >= 2 THEN 1 ELSE 0 END)"), sub="≥ 2 đơn (frequency ≥ 2)"), 3, 22),
            ("rfm_rate", "v_rfm_customers", "Tỷ lệ mua lại", big(M("Tỷ lệ mua lại", "AVG(CASE WHEN frequency >= 2 THEN 1.0 ELSE 0 END)"), fmt=".2%", sub="~97% khách chỉ mua 1 lần"), 3, 22),
            ("rfm_monetary", "v_rfm_customers", "Chi tiêu TB/khách", big(M("Chi tiêu TB", "AVG(monetary)"), fmt=",.2f", sub="BRL, giá trị mua trọn đời"), 3, 22),
        ],
        [
            ("rfm_pie", "v_rfm_customers", "Phân bố khách theo phân khúc RFM (luật)", pie(M("Số khách", "COUNT(*)"), "rfm_segment"), 6, 55),
            ("rfm_cluster", "v_rfm_customers", "Số khách theo cụm K-Means (k=4)",
             cat_bar(M("Số khách", "COUNT(*)"), "cluster_name", limit=10, horizontal=True), 6, 55),
        ],
        [
            ("rep_cat", "v_repeat_categories", "Danh mục khách mua lại ưa chuộng (top 10)",
             cat_bar(M("Khách mua lại", "SUM(repeat_customers)"), "category", limit=10, horizontal=True), 6, 50),
            ("rep_state", "v_repeat_states", "Khách mua lại theo bang (top 10)",
             cat_bar(M("Khách mua lại", "SUM(repeat_customers)"), "customer_state", limit=10), 6, 50),
        ],
        [
            ("rfm_seg_table", "v_rfm_segments", "Phân khúc RFM & hành động CRM",
             table(["rfm_segment", "customers", "pct_customers", "avg_recency_days", "avg_frequency", "avg_monetary", "crm_action"],
                   order=[["segment_order", True]], fmt={"customers": ",.0f"}), 7, 45),
            ("cluster_table", "v_cluster_profile", "Hồ sơ cụm K-Means",
             table(["cluster_name", "customers", "avg_recency", "avg_frequency", "avg_monetary", "champions", "loyal", "at_risk"],
                   order=[["cluster", True]], fmt={"customers": ",.0f"}), 5, 45),
        ],
    ]),
    ("Người bán", [
        [
            ("sel_total", "v_seller_pareto", "Số người bán", big(M("Người bán", "COUNT(*)"), sub="toàn bộ người bán (Pareto)"), 3, 22),
            ("sel_top", "v_seller_pareto", "Người bán nhóm A", big(M("Người bán nhóm A", "SUM(CASE WHEN cumulative_share_pct <= 80 THEN 1 ELSE 0 END)"), sub="tạo 80% doanh thu (Pareto)"), 3, 22),
            ("sel_top_pct", "v_seller_pareto", "% người bán nhóm A", big(M("% người bán nhóm A", "AVG(CASE WHEN cumulative_share_pct <= 80 THEN 1.0 ELSE 0 END)"), fmt=".2%", sub="tập trung hơn quy tắc 20/80"), 3, 22),
            ("sel_watch", "v_seller_pareto", "Cần theo dõi", big(M("Cần theo dõi", "SUM(CASE WHEN is_watchlist THEN 1 ELSE 0 END)"), sub="top 10% doanh thu, vận hành kém"), 3, 22),
        ],
        [
            ("sel_pareto", "v_seller_pareto", "Pareto người bán: số người bán (cột) & % doanh thu (đường) theo nhóm",
             mixed(M("Số người bán", "COUNT(*)"), M("% doanh thu", "SUM(revenue_share_pct)"), x="pareto_group",
                   fmt_b=",.1f", x_axis_sort="pareto_group", x_axis_sort_asc=True, show_value=True), 5, 60),
            ("sel_bubble", "v_seller_pareto", "Top 300 người bán: ngày giao và điểm đánh giá (kích thước = doanh thu, màu = danh sách theo dõi)",
             {"viz_type": "bubble_v2", "entity": "seller_short", "series": "watchlist_label",
              "x": M("Ngày giao TB", "MAX(avg_delivery_days)"), "y": M("Đánh giá TB", "MAX(avg_review_score)"),
              "size": REV, "adhoc_filters": [SQLF("revenue_rank <= 300")], "row_limit": 300, "max_bubble_size": "25",
              "x_axis_label": "Ngày giao trung bình", "y_axis_label": "Điểm đánh giá trung bình", "xAxisFormat": ",.1f",
              "y_axis_format": ",.2f", "opacity": 0.6, "show_legend": True, "color_scheme": COLOR_SCHEME,
              "tooltipSizeFormat": ",.0f"}, 7, 60),
        ],
        [
            ("sel_watch_table", "v_seller_watchlist", "Người bán cần theo dõi (watchlist) – cảnh báo vận hành (153 người bán)",
             table(["seller_short", "seller_state", "alert_level", "violations", "reasons", "orders", "revenue",
                    "avg_review_score", "avg_delivery_days", "late_delivery_pct", "active_months", "recommended_action"],
                   order=[["violations", False], ["revenue", False]], page=15, fmt={"revenue": ",.0f"},
                   cond=[cond("avg_review_score", "<", 4, RED), cond("avg_delivery_days", ">", 15, YELLOW),
                         cond("late_delivery_pct", ">", 10, RED), cond("violations", ">=", 2, RED)]), 12, 70),
        ],
    ]),
    ("Giao trễ, đánh giá & thanh toán", [
        [
            ("rev_late", "v_late_vs_review", "Điểm đánh giá TB: giao trễ và đúng hạn",
             cat_bar(M("Đánh giá TB", "MAX(avg_review)"), "delivery_label", limit=5, fmt=",.2f"), 4, 50),
            ("rev_delay", "v_delay_vs_review", "Ngưỡng ngày trễ: điểm đánh giá TB (cột) & % 1 sao (đường)",
             mixed(M("Đánh giá TB", "MAX(avg_review)"), M("% 1 sao", "MAX(pct_1_star)"), x="delay_label",
                   fmt_a=",.2f", fmt_b=",.1f", x_axis_sort="delay_label", x_axis_sort_asc=True, show_value=True), 8, 50),
        ],
        [
            ("pay_mix", "v_payment_mix", "Số đơn theo phương thức thanh toán × kỳ trả góp",
             cat_bar(M("Số đơn", "SUM(orders)"), "main_payment_type", limit=100, groupby=["installment_label"],
                     stack="Stack", show_value=False), 6, 50),
            ("pay_aov", "v_payment_mix", "Giá trị TB mỗi đơn theo số kỳ trả góp (BRL)",
             cat_bar(M("Giá trị TB/đơn (BRL)", "SUM(gmv) / NULLIF(SUM(orders), 0)"), "installment_label", limit=10, fmt=",.2f",
                     x_axis_sort="installment_label", x_axis_sort_asc=True), 6, 50),
        ],
        [
            ("pay_pie", "v_orders", "Cơ cấu đơn theo phương thức thanh toán (lọc được theo tháng/bang)",
             pie(ORDERS_CNT, "main_payment_type", adhoc_filters=[TF()]), 6, 50),
            ("pay_table", "v_payment_mix", "Bảng cơ cấu thanh toán",
             table(["main_payment_type", "installment_label", "orders", "pct_orders", "gmv", "avg_order_value"],
                   order=[["orders", False]], fmt={"gmv": ",.0f", "orders": ",.0f"}), 6, 50),
        ],
    ]),
    ("Gợi ý quyết định & nguồn dữ liệu", [
        [
            ("md_hints", None, """### Gợi ý quyết định
Bảng bên phải là **luật có ngưỡng** tính trực tiếp từ dữ liệu (view `presentation.v_decision_hints`).
Giai đoạn kế tiếp (**Presentation → Decision/Action**) có thể đọc view này bằng SQL/API để:

- gửi **cảnh báo người bán** trong danh sách theo dõi (mức ĐỎ = vi phạm ≥ 2 tiêu chí);
- **cảnh báo sớm** đơn trễ 1–3 ngày, trước mốc 4–7 ngày khi điểm đánh giá rơi xuống ~2,1 sao;
- lên kế hoạch **năng lực vận chuyển** trước tháng cao điểm (T11, T2–T3);
- chạy chiến dịch **kéo khách quay lại** cho nhóm *At Risk* thay vì 65 nghìn khách *One-shot Lost*.
""", 4, 60),
            ("hints", "v_decision_hints", "Gợi ý quyết định (luật + ngưỡng + hành động)",
             table(["priority", "severity", "topic", "signal", "metric_value", "detail", "threshold", "action"],
                   order=[["priority", True]], page=10, fmt={"metric_value": ",.2f"}), 8, 60),
        ],
        [
            ("md_lineage", None, """### Nguồn dữ liệu
**Luồng:** Spark (nhóm Phân tích – Analytics) → Parquet `data/analytics`, `data/gold` → `loader/load_to_neon.py` (COPY) →
Neon Postgres (`analytics.*`, `gold.*`) → view `presentation.*` → Superset.

- Khung thời gian KPI: **2017-01 → 2018-08** (đã bỏ 2016 và 2018-09).
- Khách = `customer_unique_id`; điểm đánh giá tính ở cấp đơn.
- Tổng doanh thu gold (mọi tháng): **13.494.400,74 BRL** — kiểm chứng trong `evidence/validation.md`.
- Bảng bên phải: lần nạp gần nhất (`analytics.load_log`).
""", 4, 60),
            ("load_log", "v_load_log", "Nhật ký nạp dữ liệu (analytics.load_log)",
             table(["table_fq", "rows", "parquet_rows", "row_count_ok", "parquet_files", "parquet_mb", "seconds",
                    "rows_per_sec", "loaded_at"], order=[["rows", False]], page=25,
                   fmt={"rows": ",.0f", "parquet_rows": ",.0f"}, table_timestamp_format="%Y-%m-%d %H:%M"), 8, 60),
        ],
    ]),
]

# Native filter: (tên, loại, dataset nguồn, cột, mô tả)
FILTERS = [
    ("Khoảng thời gian", "filter_time", None, "month_date", "Áp dụng cho biểu đồ có cột month_date (2017-01 → 2018-08)"),
    ("Bang khách hàng", "filter_select", "v_state_logistics", "customer_state", "Mã bang 2 ký tự (SP, RJ, ...)"),
    ("Vùng", "filter_select", "v_state_logistics", "region", "5 vùng Brazil"),
    ("Danh mục", "filter_select", "v_category_pareto", "category", "Danh mục sản phẩm (tiếng Anh)"),
    ("Phân khúc RFM", "filter_select", "v_rfm_segments", "rfm_segment", "Nhãn CRM theo luật"),
    ("Phương thức thanh toán", "filter_select", "v_payment_mix", "main_payment_type", "Phương thức thanh toán chính của đơn"),
    ("Bang người bán", "filter_select", "v_seller_pareto", "seller_state", "Bang của người bán"),
]
TIME_SCOPE = {"v_kpi_monthly", "v_orders", "v_category_monthly", "v_sales_items"}


# ---------------------------------------------------------------------------------------------
def sqlalchemy_uri() -> str:
    url = os.environ["NEON_DATABASE_URL"]
    return re.sub(r"^postgres(ql)?://", "postgresql+psycopg2://", url)


def ensure_database(api: Superset) -> int:
    existing = {d["database_name"]: d["id"] for d in api.list_all("database")}
    payload = {"database_name": DB_NAME, "sqlalchemy_uri": sqlalchemy_uri(), "expose_in_sqllab": True,
               "allow_ctas": False, "allow_cvas": False, "allow_dml": False, "cache_timeout": 600,
               "extra": api.dumps({"metadata_params": {}, "engine_params": {"pool_pre_ping": True},
                                   "schemas_allowed_for_file_upload": []})}
    if DB_NAME in existing:
        api.put(f"/api/v1/database/{existing[DB_NAME]}", payload)
        return existing[DB_NAME]
    return api.post("/api/v1/database/", payload)["id"]


def ensure_datasets(api: Superset, db_id: int, refresh: set[str] | None = None) -> dict[str, dict]:
    """refresh=None: làm mới cột của mọi dataset; set(): chỉ làm mới các dataset có tên trong set."""
    existing = {(d["schema"], d["table_name"]): d["id"] for d in api.list_all("dataset")}
    created = set()
    for name in DATASETS:  # tạo tuần tự: Superset trả 422 khi tạo dataset song song
        if (SCHEMA, name) not in existing:
            existing[(SCHEMA, name)] = api.post("/api/v1/dataset/", {"database": db_id, "schema": SCHEMA, "table_name": name})["id"]
            created.add(name)

    def one(name: str) -> tuple[str, dict]:
        ds_id = existing[(SCHEMA, name)]
        if refresh is not None and name not in refresh and name not in created:
            info = api.get(f"/api/v1/dataset/{ds_id}")["result"]
            return name, {"id": ds_id, "columns": {c["column_name"] for c in info["columns"]}}
        api.put(f"/api/v1/dataset/{ds_id}/refresh", {})
        info = api.get(f"/api/v1/dataset/{ds_id}")["result"]
        keep = {"id", "column_name", "type", "verbose_name", "description", "expression", "filterable",
                "groupby", "is_active", "is_dttm", "python_date_format", "advanced_data_type", "extra"}
        cols = []
        for c in info["columns"]:
            c = {k: v for k, v in c.items() if k in keep}
            if c["column_name"] in VERBOSE:
                c["verbose_name"] = VERBOSE[c["column_name"]]
            if c["column_name"] == "month_date":
                c["is_dttm"] = True
            cols.append(c)
        keep_m = {"id", "metric_name", "expression", "verbose_name", "metric_type", "d3format", "description",
                  "warning_text", "extra", "currency"}
        metrics = []
        for m in info["metrics"]:
            m = {k: v for k, v in m.items() if k in keep_m and v is not None}
            if m["metric_name"] in METRIC_VERBOSE:
                m["verbose_name"] = METRIC_VERBOSE[m["metric_name"]]
            metrics.append(m)
        payload = {"columns": cols, "metrics": metrics,
                   "description": f"View {SCHEMA}.{name} trên Neon (tầng ngữ nghĩa)", "cache_timeout": 600}
        if any(c["column_name"] == "month_date" for c in cols):
            payload["main_dttm_col"] = "month_date"
        api.put(f"/api/v1/dataset/{ds_id}", payload, override_columns="false")
        print(f"  dataset {SCHEMA}.{name:<24} id={ds_id:<3} cột={len(cols)}", flush=True)
        return name, {"id": ds_id, "columns": {c["column_name"] for c in cols}}

    with ThreadPoolExecutor(max_workers=6) as pool:
        return dict(pool.map(one, DATASETS))


def ensure_dashboard(api: Superset) -> int:
    for d in api.list_all("dashboard"):
        if d.get("slug") == DASH_SLUG:
            return d["id"]
    return api.post("/api/v1/dashboard/", {"dashboard_title": DASH_TITLE, "slug": DASH_SLUG, "published": True})["id"]


def ensure_charts(api: Superset, datasets: dict, dash_id: int) -> dict[str, dict]:
    existing = {c["slice_name"]: c["id"] for c in api.list_all("chart")}
    charts = {}
    for _, rows in TABS:
        for row in rows:
            for key, ds_name, name, params, *_ in row:
                if ds_name is None:
                    continue
                ds = datasets[ds_name]
                params = {**params, "datasource": f"{ds['id']}__table"}
                payload = {"slice_name": name, "viz_type": params["viz_type"], "datasource_id": ds["id"],
                           "datasource_type": "table", "params": api.dumps(params), "dashboards": [dash_id],
                           "description": f"Nguồn: {SCHEMA}.{ds_name}", "cache_timeout": 600}
                if name in existing:
                    api.put(f"/api/v1/chart/{existing[name]}", payload)
                    cid = existing[name]
                else:
                    cid = api.post("/api/v1/chart/", payload)["id"]
                charts[key] = {"id": cid, "name": name, "dataset": ds_name}
                print(f"  chart {cid:>3} [{params['viz_type']:<22}] {name}")
    return charts


def build_layout(charts: dict) -> tuple[dict, dict[str, str]]:
    pos = {"DASHBOARD_VERSION_KEY": "v2",
           "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["TABS-main"]},
           "HEADER_ID": {"type": "HEADER", "id": "HEADER_ID", "meta": {"text": DASH_TITLE}},
           "TABS-main": {"type": "TABS", "id": "TABS-main", "children": [], "parents": ["ROOT_ID"], "meta": {}}}
    chart_tab = {}
    for ti, (tab_name, rows) in enumerate(TABS, 1):
        tab_id = f"TAB-t{ti}"
        pos["TABS-main"]["children"].append(tab_id)
        tab_parents = ["ROOT_ID", "TABS-main"]
        pos[tab_id] = {"type": "TAB", "id": tab_id, "children": [], "parents": tab_parents,
                       "meta": {"text": f"{ti} · {tab_name}", "defaultText": "Tab title", "placeholder": "Tab title"}}
        for ri, row in enumerate(rows, 1):
            row_id = f"ROW-t{ti}r{ri}"
            pos[tab_id]["children"].append(row_id)
            row_parents = tab_parents + [tab_id]
            pos[row_id] = {"type": "ROW", "id": row_id, "children": [], "parents": row_parents,
                           "meta": {"background": "BACKGROUND_TRANSPARENT"}}
            for item in row:
                key, ds_name, width, height = item[0], item[1], item[-2], item[-1]
                parents = row_parents + [row_id]
                if ds_name is None:
                    el_id = f"MARKDOWN-{key}"
                    pos[el_id] = {"type": "MARKDOWN", "id": el_id, "children": [], "parents": parents,
                                  "meta": {"width": width, "height": height, "code": item[2]}}
                else:
                    c = charts[key]
                    el_id = f"CHART-{key}"
                    pos[el_id] = {"type": "CHART", "id": el_id, "children": [], "parents": parents,
                                  "meta": {"width": width, "height": height, "chartId": c["id"],
                                           "sliceName": c["name"], "uuid": str(uuid.uuid5(uuid.NAMESPACE_URL, el_id))}}
                    chart_tab[key] = tab_id
                pos[row_id]["children"].append(el_id)
    return pos, chart_tab


def build_filters(datasets: dict, charts: dict, chart_tab: dict) -> list[dict]:
    all_ids = [c["id"] for c in charts.values()]
    out = []
    for i, (name, ftype, ds_name, col, desc) in enumerate(FILTERS, 1):
        if ftype == "filter_time":
            in_scope = [c["id"] for c in charts.values() if c["dataset"] in TIME_SCOPE]
        else:
            in_scope = [c["id"] for c in charts.values() if col in datasets[c["dataset"]]["columns"]]
        tabs = sorted({chart_tab[k] for k, c in charts.items() if c["id"] in in_scope})
        f = {"id": f"NATIVE_FILTER-{i:02d}{re.sub(r'[^a-z]', '', col)[:10]}", "name": name, "filterType": ftype,
             "type": "NATIVE_FILTER", "description": desc, "cascadeParentIds": [],
             "defaultDataMask": {"extraFormData": {}, "filterState": {}, "ownState": {}},
             "scope": {"rootPath": ["ROOT_ID"], "excluded": [x for x in all_ids if x not in in_scope]},
             "chartsInScope": in_scope, "tabsInScope": tabs}
        if ftype == "filter_time":
            f.update({"targets": [{}], "controlValues": {}})
        else:
            f.update({"targets": [{"datasetId": datasets[ds_name]["id"], "column": {"name": col}}],
                      "controlValues": {"enableEmptyFilter": False, "defaultToFirstItem": False, "multiSelect": True,
                                        "searchAllOptions": False, "inverseSelection": False, "sortAscending": True}})
        out.append(f)
        print(f"  filter {name:<24} áp dụng cho {len(in_scope):>2} chart / {len(tabs)} tab")
    return out


def export_dashboard(api: Superset, dash_id: int) -> Path:
    r = api.s.get(f"{api.url}/api/v1/dashboard/export/", params={"q": f"!({dash_id})"})
    r.raise_for_status()
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    zin = zipfile.ZipFile(io.BytesIO(r.content))
    out = EXPORT_DIR / "dashboard_olist_presentation.zip"
    yaml_dir = EXPORT_DIR / "yaml"
    shutil.rmtree(yaml_dir, ignore_errors=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if "/databases/" in item.filename:
                # Không commit host/user Neon: thay bằng placeholder, import_dashboard.py điền lại từ .env
                text = re.sub(r"sqlalchemy_uri: .*", "sqlalchemy_uri: postgresql+psycopg2://NEON_USER:XXXXXXXXXX@NEON_HOST/olist_analytics?sslmode=require",
                              data.decode("utf-8"))
                data = text.encode("utf-8")
            zout.writestr(item.filename, data)
            rel = Path(*Path(item.filename).parts[1:])
            dest = yaml_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
    return out


def main() -> None:
    api = Superset()
    print(f"Superset: {api.url}")
    db_id = ensure_database(api)
    print(f"database id={db_id} ({DB_NAME})")
    refresh = None
    for arg in sys.argv[1:]:
        if arg == "--no-refresh":
            refresh = set()
        elif arg.startswith("--refresh="):
            refresh = set(arg.split("=", 1)[1].split(","))
    datasets = ensure_datasets(api, db_id, refresh)
    dash_id = ensure_dashboard(api)
    charts = ensure_charts(api, datasets, dash_id)
    positions, chart_tab = build_layout(charts)
    filters = build_filters(datasets, charts, chart_tab)
    # Không đặt color_scheme cấp dashboard: nó ghi đè Country Map sang màu phân loại thay vì thang liên tục.
    metadata = {"native_filter_configuration": filters, "positions": positions,
                "cross_filters_enabled": True, "refresh_frequency": 0, "expanded_slices": {},
                "timed_refresh_immune_slices": [], "label_colors": {}, "shared_label_colors": {},
                "chart_configuration": {}, "default_filters": "{}"}
    api.put(f"/api/v1/dashboard/{dash_id}", {"dashboard_title": DASH_TITLE, "slug": DASH_SLUG, "published": True,
                                             "position_json": api.dumps(positions), "json_metadata": api.dumps(metadata),
                                             "css": DASH_CSS})
    # Xoá chart mồ côi (đổi tên chart trong spec) để export sạch.
    names = {c["name"] for c in charts.values()}
    for c in api.list_all("chart"):
        if c["slice_name"] not in names:
            api.delete(f"/api/v1/chart/{c['id']}")
            print(f"  xoá chart cũ {c['id']} {c['slice_name']}")
    out = export_dashboard(api, dash_id)
    info = {"dashboard_id": dash_id, "url": f"http://localhost:8088/superset/dashboard/{DASH_SLUG}/",
            "charts": {k: v["id"] for k, v in charts.items()}, "datasets": {k: v["id"] for k, v in datasets.items()},
            "filters": [f["id"] for f in filters], "tabs": [f"TAB-t{i}" for i in range(1, len(TABS) + 1)]}
    (EXPORT_DIR / "build_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Dashboard id={dash_id}: {info['url']}")
    print(f"{len(charts)} chart, {len(datasets)} dataset, {len(filters)} native filter; export -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
