"""Sinh tài liệu hỏi đáp vấn đáp: report/HoiDap_VanDap_DoAn.docx.

    python report/build_qa.py [--out đường_dẫn.docx]

Nội dung nằm trong report/content/qa/*.md (Markdown rút gọn như báo cáo chính). Câu hỏi viết dạng
    Q(Người trả lời): nội dung câu hỏi
    A: gợi ý trả lời
và được đánh số tự động "Câu n".
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
Q_RX = re.compile(r"^Q\(([^)]*)\):\s*(.+)$")


def preprocess(text: str, counter: list[int]) -> str:
    """Q(...)/A: → tiêu đề cấp 3 "Câu n (người)" + đoạn trả lời."""
    out = []
    for ln in text.splitlines():
        m = Q_RX.match(ln.strip())
        if m:
            counter[0] += 1
            out.append(f"### Câu {counter[0]} ({m.group(1)}). {m.group(2)}")
        elif ln.strip().startswith("A:"):
            out.append("**Trả lời:** " + ln.strip()[2:].strip())
        else:
            out.append(ln)
    return "\n".join(out)


def cover(r: BR.Renderer, team: dict) -> None:
    def line(txt, size=14, bold=False, before=0, after=4):
        p = r.doc.add_paragraph(style="CoverText")
        p.paragraph_format.space_before = Pt(before)
        p.paragraph_format.space_after = Pt(after)
        r.inline(p, txt, size=size, bold=bold)

    line(team["school"].upper(), 14, True)
    line(team["faculty"].upper(), 14, True, after=40)
    line("TÀI LIỆU CHUẨN BỊ VẤN ĐÁP", 18, True, before=40)
    line(f"Học phần {team['course']}", 15, False, after=18)
    line("Đồ án: Olist E-commerce · Analytics → Presentation", 14, True)
    line("Neon Serverless Postgres + tầng ngữ nghĩa SQL + Apache Superset", 13, after=24)
    line(f"Lớp: {team['class']}   –   Giảng viên hướng dẫn: {team['instructor']}", 13, after=16)
    rows = [[str(i + 1), m["name"], m["student_id"], m["role"]] for i, m in enumerate(team["members"])]
    r.table(["STT", "Họ và tên", "MSSV", "Vai trò chính"], rows, font_size=12, widths=[1.2, 5.3, 3.3, 6.2])
    line("Tài liệu nội bộ của nhóm: bảng số liệu, đối chiếu yêu cầu, câu hỏi dự kiến và kịch bản demo.", 12, before=24)
    line(f"{team['place']}, {team['date']}", 13, before=40)


def build(out: Path) -> tuple[Path, int]:
    team = json.loads((REPORT_DIR / "content" / "team.json").read_text(encoding="utf-8"))
    doc = BR.new_document()
    r = BR.Renderer(doc, {"vars": {}, "team": team, "captions": {}, "images": []})
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
    BR.add_field(toc, 'TOC \\o "1-2" \\h \\z \\u', "Nhấn Ctrl+A rồi F9 để cập nhật mục lục.")
    r.fresh_page = False

    counter = [0]
    for md in sorted(QA_DIR.glob("*.md")):
        r.render_markdown(preprocess(md.read_text(encoding="utf-8"), counter))

    doc.core_properties.title = "Tài liệu chuẩn bị vấn đáp – Analytics → Presentation"
    doc.core_properties.author = ", ".join(m["name"] for m in team["members"])
    doc.core_properties.language = "vi-VN"
    doc.save(out)
    return out, counter[0]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="đường dẫn docx đầu ra")
    a = ap.parse_args()
    out, n = build(Path(a.out) if a.out else OUT_DOCX)
    d = Document(str(out))
    text = "\n".join(p.text for p in d.paragraphs)
    print(f"Đã sinh: {out}")
    print(f"  câu hỏi: {n}")
    print(f"  đoạn: {len(d.paragraphs)}, bảng: {len(d.tables)}, tiêu đề cấp 1/2/3: "
          + "/".join(str(sum(1 for p in d.paragraphs if p.style.name == f'Heading {k}')) for k in (1, 2, 3)))
    print(f"  số từ (đoạn + bảng): {len(text.split()) + sum(len(c.text.split()) for t in d.tables for row in t.rows for c in row.cells)}")
    left = sorted(set(BR.PH_RX.findall(text)))
    print(f"  placeholder còn lại: {len(left)}")


if __name__ == "__main__":
    main()
