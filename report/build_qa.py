"""Sinh tài liệu vấn đáp: trả lời từng yêu cầu Mục 5 của đề bài → report/HoiDap_VanDap_DoAn.docx.

    python report/build_qa.py [--out đường_dẫn.docx]

Nội dung nằm trong report/content/qa/*.md (Markdown rút gọn như báo cáo chính, dùng chung các directive
{{contract_table}}, {{views}}, {{dashload:tabs}}, {{scale}}, {{shot:...}}, {{image:...}} của build_report.py,
nên bảng số liệu được đọc trực tiếp từ Parquet và evidence/).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_report as BR  # noqa: E402

REPORT_DIR = Path(__file__).resolve().parent
QA_DIR = REPORT_DIR / "content" / "qa"
OUT_DOCX = REPORT_DIR / "HoiDap_VanDap_DoAn.docx"


class QARenderer(BR.Renderer):
    """Đánh số hình/bảng theo mục con của Mục 5 (Bảng 5.3.1, Hình 5.6.1...)."""

    def heading(self, text: str, level: int) -> None:
        super().heading(text, level)
        if level == 1:
            m = re.match(r"^(\d+\.\d+)\.", text)
            if m:
                self.chapter = m.group(1)
            # các mục nối tiếp nhau (kể cả ngay sau mục lục) để tài liệu gọn
            self.doc.paragraphs[-1].paragraph_format.page_break_before = False

    def table(self, header, rows, caption=None, font_size=None, widths=None):
        """Cho phép ghi độ rộng cột ở cuối dòng "Bảng: ... {w=1.5,3,4}" (cm)."""
        if caption:
            m = re.search(r"\s*\{w=([\d.,\s]+)\}\s*$", caption)
            if m:
                widths = [float(x) for x in m.group(1).split(",")]
                caption = caption[: m.start()]
        super().table(header, rows, caption, font_size, widths)


def cover(r: BR.Renderer, team: dict) -> None:
    def line(txt, size=14, bold=False, before=0, after=4):
        p = r.doc.add_paragraph(style="CoverText")
        p.paragraph_format.space_before = Pt(before)
        p.paragraph_format.space_after = Pt(after)
        r.inline(p, txt, size=size, bold=bold)

    line(team["school"].upper(), 14, True)
    line(team["faculty"].upper(), 14, True, after=40)
    line("TÀI LIỆU VẤN ĐÁP", 18, True, before=40)
    line("Trả lời các yêu cầu bắt buộc – Mục 5 của đề bài", 15, False, after=18)
    line(f"Học phần {team['course']}", 14, True)
    line("Đồ án: Olist E-commerce · Analytics → Presentation", 14, True)
    line("Neon Serverless Postgres + tầng ngữ nghĩa SQL + Apache Superset", 13, after=24)
    line(f"Lớp: {team['class']}   –   Giảng viên hướng dẫn: {team['instructor']}", 13, after=16)
    rows = [[str(i + 1), m["name"], m["student_id"], m["role"]] for i, m in enumerate(team["members"])]
    r.table(["STT", "Họ và tên", "MSSV", "Vai trò chính"], rows, font_size=12, widths=[1.2, 5.3, 3.3, 6.2])
    line(f"{team['place']}, {team['date']}", 13, before=40)


def build(out: Path) -> Path:
    ctx = BR.collect_context(make_charts=False)
    team = json.loads((REPORT_DIR / "content" / "team.json").read_text(encoding="utf-8"))
    ctx["team"] = team
    doc = BR.new_document()
    r = QARenderer(doc, ctx)
    cover(r, team)

    sec = doc.add_section(WD_SECTION.NEW_PAGE)
    sec.footer.is_linked_to_previous = False
    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    BR.add_field(fp, "PAGE", "1")
    BR.set_page_numbering(sec, "decimal", 1)

    tp = doc.add_paragraph()
    tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = tp.add_run("MỤC LỤC")
    run.bold = True
    BR.run_font(run, BR.FONT, 16)
    toc = doc.add_paragraph()
    toc.paragraph_format.first_line_indent = Cm(0)
    BR.add_field(toc, 'TOC \\o "1-1" \\h \\z \\u', "Nhấn Ctrl+A rồi F9 để cập nhật mục lục.")
    intro = doc.add_paragraph()
    intro.paragraph_format.space_before = Pt(18)
    r.inline(intro, "Tài liệu này trả lời lần lượt tám yêu cầu bắt buộc tại **Mục 5 – Yêu cầu bắt buộc đối với mỗi nhóm** "
                    "của đề bài. Mỗi mục trích nguyên văn yêu cầu (khung màu), sau đó là câu trả lời của nhóm với số liệu "
                    "lấy trực tiếp từ repo (`data/`, `sql/`, `loader/`, `superset/`, `evidence/`) tại lần nạp ngày 13/11/2026. "
                    "Chi tiết đầy đủ nằm trong báo cáo `report/BaoCao_DoAn_BigData.docx` và README.")
    r.fresh_page = False

    for md in sorted(QA_DIR.glob("*.md")):
        r.render_markdown(md.read_text(encoding="utf-8"))

    doc.core_properties.title = "Tài liệu vấn đáp – trả lời Mục 5 đề bài"
    doc.core_properties.author = ", ".join(m["name"] for m in team["members"])
    doc.core_properties.language = "vi-VN"
    doc.save(out)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="đường dẫn docx đầu ra")
    a = ap.parse_args()
    out = build(Path(a.out) if a.out else OUT_DOCX)
    d = Document(str(out))
    text = "\n".join(p.text for p in d.paragraphs) + "\n" + "\n".join(
        c.text for t in d.tables for row in t.rows for c in row.cells)
    print(f"Đã sinh: {out}")
    print(f"  mục: {[p.text for p in d.paragraphs if p.style.name == 'Heading 1']}")
    print(f"  đoạn: {len(d.paragraphs)}, bảng: {len(d.tables)}, ảnh: {len(d.inline_shapes)}, số từ: {len(text.split())}")
    print(f"  placeholder còn lại: {sorted(set(BR.PH_RX.findall(text)))}")


if __name__ == "__main__":
    main()
