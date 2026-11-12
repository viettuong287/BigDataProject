"""Sinh báo cáo Word cho đồ án Big Data (Analytics → Presentation).

    python report/build_report.py            # sinh report/BaoCao_DoAn_BigData.docx
    python report/build_report.py --no-charts  # dùng lại ảnh trong report/figures/

Nội dung chữ nằm trong report/content/*.md (Markdown rút gọn + directive {{...}}),
thông tin nhóm trong report/content/team.json. Script tự phát hiện ảnh/log/latency
trong evidence/ và docs/; thiếu thì chèn placeholder [[CẬP NHẬT: ...]].
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import charts  # noqa: E402
import inputs as I  # noqa: E402

OUT_DOCX = I.REPORT_DIR / "BaoCao_DoAn_BigData.docx"
FONT = "Times New Roman"
MONO = "Consolas"
CONTENT_W_CM = 16.0
PH_RX = re.compile(r"\[\[CẬP NHẬT:[^\]]*\]\]")


# =============================================================== tiện ích OOXML
def _set_rfonts(rpr, name: str) -> None:
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.insert(0, rf)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        rf.attrib.pop(qn(a), None)
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(a), name)


def run_font(run, name: str = FONT, size: float | None = None) -> None:
    run.font.name = name
    _set_rfonts(run._element.get_or_add_rPr(), name)
    if size:
        run.font.size = Pt(size)


def style_font(style, name: str, size: float, bold=None, italic=None, color=RGBColor(0, 0, 0)) -> None:
    style.font.name = name
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.italic = italic
    if color is not None:
        style.font.color.rgb = color
    _set_rfonts(style.element.get_or_add_rPr(), name)


def add_field(par, instr: str, placeholder: str = "") -> None:
    def fld(kind):
        r = par.add_run()
        e = OxmlElement("w:fldChar")
        e.set(qn("w:fldCharType"), kind)
        r._r.append(e)
        return r

    fld("begin")
    r = par.add_run()
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = f" {instr} "
    r._r.append(it)
    fld("separate")
    if placeholder:
        run_font(par.add_run(placeholder))
    fld("end")


def shade(par_or_cell, fill: str) -> None:
    el = par_or_cell._p if hasattr(par_or_cell, "_p") else par_or_cell._tc
    pr = el.get_or_add_pPr() if hasattr(par_or_cell, "_p") else el.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    pr.append(shd)


def para_border(par, color: str = "999999") -> None:
    ppr = par._p.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    for side in ("top", "left", "bottom", "right"):
        b = OxmlElement(f"w:{side}")
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), "6")
        b.set(qn("w:space"), "4")
        b.set(qn("w:color"), color)
        bdr.append(b)
    ppr.append(bdr)


_SECT_AFTER_PGNUM = ("w:cols", "w:formProt", "w:vAlign", "w:noEndnote", "w:titlePg", "w:textDirection",
                     "w:bidi", "w:rtlGutter", "w:docGrid", "w:printerSettings")


def set_page_numbering(section, fmt: str, start: int = 1) -> None:
    sp = section._sectPr
    old = sp.find(qn("w:pgNumType"))
    if old is not None:
        sp.remove(old)
    pg = OxmlElement("w:pgNumType")
    pg.set(qn("w:fmt"), fmt)
    pg.set(qn("w:start"), str(start))
    for tag in _SECT_AFTER_PGNUM:
        nxt = sp.find(qn(tag))
        if nxt is not None:
            nxt.addprevious(pg)
            return
    sp.append(pg)


def repeat_header(row) -> None:
    trpr = row._tr.get_or_add_trPr()
    h = OxmlElement("w:tblHeader")
    h.set(qn("w:val"), "true")
    trpr.append(h)


# =============================================================== tài liệu & style
def new_document():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin, sec.right_margin = Cm(3), Cm(2)
    sec.top_margin, sec.bottom_margin = Cm(2), Cm(2)
    sec.footer_distance = Cm(1)

    st = doc.styles
    normal = st["Normal"]
    style_font(normal, FONT, 13)
    pf = normal.paragraph_format
    pf.line_spacing = 1.5
    pf.space_after = Pt(4)
    pf.space_before = Pt(0)
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for lvl, size, italic in ((1, 16, False), (2, 14, False), (3, 13, True)):
        h = st[f"Heading {lvl}"]
        style_font(h, FONT, size, bold=True, italic=italic)
        h.paragraph_format.space_before = Pt(18 if lvl == 1 else 12)
        h.paragraph_format.space_after = Pt(8 if lvl == 1 else 6)
        h.paragraph_format.line_spacing = 1.15
        h.paragraph_format.keep_with_next = True
        h.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER if lvl == 1 else WD_ALIGN_PARAGRAPH.LEFT
    for name in ("Title", "Subtitle", "List Bullet", "List Bullet 2", "Caption"):
        if name in [s.name for s in st]:
            style_font(st[name], FONT, 13, color=RGBColor(0, 0, 0))

    from docx.enum.style import WD_STYLE_TYPE as T

    def pstyle(name, size, font=FONT, align=None, spacing=1.0, after=0, bold=None, italic=None):
        s = st.add_style(name, T.PARAGRAPH)
        s.base_style = normal
        style_font(s, font, size, bold=bold, italic=italic)
        s.paragraph_format.line_spacing = spacing
        s.paragraph_format.space_after = Pt(after)
        s.paragraph_format.first_line_indent = Cm(0)
        if align is not None:
            s.paragraph_format.alignment = align
        return s

    pstyle("TableText", 11, align=WD_ALIGN_PARAGRAPH.LEFT)
    pstyle("CodeBlock", 9.5, font=MONO, align=WD_ALIGN_PARAGRAPH.LEFT, after=8)
    fc = pstyle("FigureCaption", 12, align=WD_ALIGN_PARAGRAPH.CENTER, spacing=1.15, after=10, italic=True)
    fc.paragraph_format.space_before = Pt(4)
    tc = pstyle("TableCaption", 12, align=WD_ALIGN_PARAGRAPH.CENTER, spacing=1.15, after=4)
    tc.paragraph_format.space_before = Pt(8)
    tc.paragraph_format.keep_with_next = True
    pstyle("CoverText", 14, align=WD_ALIGN_PARAGRAPH.CENTER, spacing=1.2, after=4)

    s = doc.settings.element
    uf = OxmlElement("w:updateFields")
    uf.set(qn("w:val"), "true")
    s.append(uf)
    lang = st["Normal"].element.get_or_add_rPr()
    lg = OxmlElement("w:lang")
    lg.set(qn("w:val"), "vi-VN")
    lang.append(lg)
    return doc


# =============================================================== renderer
class Renderer:
    INLINE_RX = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\[\[[^\]]+\]\]|(?<![\w*])\*[^*\s][^*]*?\*(?![\w*]))")

    def __init__(self, doc, ctx: dict):
        self.doc = doc
        self.ctx = ctx
        self.chapter: str | None = None
        self.fig_n = 0
        self.tab_n = 0
        self.fresh_page = True
        self.used_images: set[Path] = set()
        self.figures: list[str] = []
        self.tables: list[str] = []

    # ---------------------------------------------------- inline & đoạn văn
    def inline(self, par, text: str, size: float | None = None, bold: bool | None = None) -> None:
        for tok in self.INLINE_RX.split(text):
            if not tok:
                continue
            if tok.startswith("**") and tok.endswith("**") and len(tok) > 4:
                r = par.add_run(tok[2:-2])
                r.bold = True
                run_font(r, FONT, size)
            elif tok.startswith("`") and tok.endswith("`") and len(tok) > 2:
                r = par.add_run(tok[1:-1])
                run_font(r, MONO, (size or 13) - 2)
            elif tok.startswith("[[") and tok.endswith("]]"):
                r = par.add_run(tok)
                r.bold = True
                r.font.highlight_color = WD_COLOR_INDEX.YELLOW
                run_font(r, FONT, size)
            elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
                r = par.add_run(tok[1:-1])
                r.italic = True
                run_font(r, FONT, size)
            else:
                r = par.add_run(tok)
                run_font(r, FONT, size)
            if bold:
                r.bold = True

    def paragraph(self, text: str, indent: bool = True):
        p = self.doc.add_paragraph()
        if indent:
            p.paragraph_format.first_line_indent = Cm(1)
        self.inline(p, text)
        self.fresh_page = False
        return p

    def bullet(self, text: str, level: int = 1) -> None:
        p = self.doc.add_paragraph(style="List Bullet" if level == 1 else "List Bullet 2")
        p.paragraph_format.space_after = Pt(3)
        self.inline(p, text)
        self.fresh_page = False

    def numbered(self, num: str, text: str) -> None:
        p = self.doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(1)
        p.paragraph_format.first_line_indent = Cm(-0.6)
        p.paragraph_format.space_after = Pt(3)
        self.inline(p, f"{num} {text}")
        self.fresh_page = False

    def note(self, text: str) -> None:
        p = self.doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.8)
        p.paragraph_format.right_indent = Cm(0.5)
        shade(p, "EEF3F8")
        para_border(p, "9DB4CC")
        self.inline(p, text, size=12)
        self.fresh_page = False

    def heading(self, text: str, level: int) -> None:
        if level == 1:
            m = re.match(r"^(\d+)\.", text) or re.match(r"^Phụ lục ([A-Z])", text)
            self.chapter = m.group(1) if m else None
            self.fig_n = self.tab_n = 0
        h = self.doc.add_heading(text, level=level)
        if level == 1:
            h.paragraph_format.page_break_before = not self.fresh_page
        for r in h.runs:
            run_font(r, FONT)
        self.fresh_page = False

    def code(self, text: str) -> None:
        p = self.doc.add_paragraph(style="CodeBlock")
        shade(p, "F2F2F2")
        para_border(p, "BFBFBF")
        lines = text.rstrip("\n").split("\n")
        for i, ln in enumerate(lines):
            r = p.add_run(ln)
            run_font(r, MONO, 9.5)
            if i < len(lines) - 1:
                r.add_break()
        self.fresh_page = False

    def page_break(self) -> None:
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        self.fresh_page = True

    # ---------------------------------------------------- chú thích
    def _label(self, kind: str) -> str:
        if kind == "Hình":
            self.fig_n += 1
            n = self.fig_n
        else:
            self.tab_n += 1
            n = self.tab_n
        return f"{kind} {self.chapter}.{n}." if self.chapter else f"{kind} {n}."

    def caption(self, kind: str, text: str) -> None:
        label = self._label(kind)
        p = self.doc.add_paragraph(style="FigureCaption" if kind == "Hình" else "TableCaption")
        r = p.add_run(label + " ")
        r.bold = True
        r.italic = False
        run_font(r, FONT, 12)
        self.inline(p, text, size=12)
        (self.figures if kind == "Hình" else self.tables).append(f"{label} {text}")

    # ---------------------------------------------------- bảng
    def table(self, header: list[str], rows: list[list[str]], caption: str | None = None,
              font_size: float | None = None, widths: list[float] | None = None) -> None:
        if caption:
            self.caption("Bảng", caption)
        ncol = len(header)
        size = font_size or (10.5 if ncol <= 4 else 10 if ncol <= 8 else 9)
        t = self.doc.add_table(rows=1, cols=ncol)
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        num_rx = re.compile(r"^[-+−]?[\d.,]+\s*%?$")
        for j, h in enumerate(header):
            c = t.rows[0].cells[j]
            shade(c, "D9E2F3")
            p = c.paragraphs[0]
            p.style = "TableText"
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            self.inline(p, h, size=size, bold=True)
        repeat_header(t.rows[0])
        for row in rows:
            cells = t.add_row().cells
            for j in range(ncol):
                val = row[j] if j < len(row) else ""
                p = cells[j].paragraphs[0]
                p.style = "TableText"
                if num_rx.match(val.strip()):
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                self.inline(p, val, size=size)
        if not widths:
            widths = self._auto_widths(header, rows)
        t.autofit = False
        tblpr = t._tbl.tblPr
        tw = tblpr.find(qn("w:tblW"))
        if tw is None:
            tw = OxmlElement("w:tblW")
            tblpr.append(tw)
        tw.set(qn("w:type"), "dxa")
        tw.set(qn("w:w"), str(int(sum(widths) * 567)))
        for j, w in enumerate(widths[:ncol]):
            t.columns[j].width = Cm(w)
        for row in t.rows:
            cs = OxmlElement("w:cantSplit")
            cs.set(qn("w:val"), "true")
            row._tr.get_or_add_trPr().append(cs)
            for j, w in enumerate(widths[:ncol]):
                row.cells[j].width = Cm(w)
        sp = self.doc.add_paragraph()
        sp.paragraph_format.space_after = Pt(2)
        sp.paragraph_format.line_spacing = 1.0
        self.fresh_page = False

    @staticmethod
    def _auto_widths(header: list[str], rows: list[list[str]], total: float = CONTENT_W_CM) -> list[float]:
        """Độ rộng cột tỷ lệ với lượng chữ (căn bậc hai để cột dài không lấn át), tối thiểu đủ chứa từ dài nhất."""
        def clean(s: str) -> str:
            return re.sub(r"[`*]|\[\[|\]\]", "", s)

        n = len(header)
        weights, mins = [], []
        for j in range(n):
            col = [clean(header[j])] + [clean(r[j]) if j < len(r) else "" for r in rows]
            avg = sum(len(c) for c in col) / len(col)
            longest_word = max((len(w) for c in col for w in c.split()), default=4)
            weights.append(max(avg, 3) ** 0.75)
            mins.append(min(max(longest_word * 0.21 + 0.55, 1.2), 4.5))
        w = [total * x / sum(weights) for x in weights]
        for _ in range(3):
            short = [j for j in range(n) if w[j] < mins[j]]
            if not short:
                break
            for j in short:
                w[j] = mins[j]
            free = total - sum(w[j] for j in short)
            rest = [j for j in range(n) if j not in short]
            if not rest or free <= 0:
                break
            s = sum(weights[j] for j in rest)
            for j in rest:
                w[j] = free * weights[j] / s
        scale = total / sum(w)
        return [x * scale for x in w]

    # ---------------------------------------------------- hình
    def image(self, path: Path, caption: str, max_w: float = 15.0, max_h: float = 7.5) -> None:
        w_px, h_px = Image.open(path).size
        w = min(max_w, CONTENT_W_CM)
        h = w * h_px / w_px
        if h > max_h:
            w = max_h * w_px / h_px
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.line_spacing = 1.0
        p.add_run().add_picture(str(path), width=Cm(w))
        self.caption("Hình", caption)
        self.used_images.add(path.resolve())
        self.fresh_page = False

    def image_placeholder(self, what: str, caption: str) -> None:
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.space_before = Pt(6)
        shade(p, "FFF8DC")
        para_border(p, "C9A227")
        for _ in range(2):
            p.add_run().add_break()
        self.inline(p, I.placeholder(what), size=12)
        for _ in range(2):
            p.add_run().add_break()
        self.caption("Hình", caption + " *(chưa có ảnh)*")
        self.fresh_page = False

    # ---------------------------------------------------- markdown
    def render_markdown(self, text: str) -> None:
        text = re.sub(r"\{\{var:([\w]+)\}\}", lambda m: str(self.ctx["vars"].get(m.group(1), I.placeholder(m.group(1)))), text)
        lines = text.splitlines()
        buf: list[str] = []
        pending_caption: str | None = None
        i = 0

        def flush():
            if buf:
                self.paragraph(" ".join(s.strip() for s in buf))
                buf.clear()

        while i < len(lines):
            ln = lines[i]
            s = ln.strip()
            if s.startswith("<!--"):
                while i < len(lines) and "-->" not in lines[i]:
                    i += 1
                i += 1
                continue
            if not s:
                flush()
                i += 1
                continue
            if s.startswith("```"):
                flush()
                j = i + 1
                block = []
                while j < len(lines) and not lines[j].strip().startswith("```"):
                    block.append(lines[j])
                    j += 1
                self.code("\n".join(block))
                i = j + 1
                continue
            m = re.match(r"^(#{1,3})\s+(.*)$", s)
            if m:
                flush()
                self.heading(m.group(2).strip(), len(m.group(1)))
                i += 1
                continue
            if re.match(r"^\{\{[^}]+\}\}$", s):
                flush()
                self.directive(s[2:-2].strip())
                i += 1
                continue
            if s.startswith("Bảng:") and i + 1 < len(lines) and lines[i + 1].strip().startswith("|"):
                flush()
                pending_caption = s[len("Bảng:"):].strip()
                i += 1
                continue
            if s.startswith("|"):
                flush()
                tbl = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    tbl.append(lines[i].strip())
                    i += 1
                def cells(r: str) -> list[str]:
                    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", r.strip()[1:-1] if r.strip().endswith("|") else r.strip()[1:])]

                hdr = cells(tbl[0])
                body = [cells(r) for r in tbl[2:]]
                self.table(hdr, body, pending_caption)
                pending_caption = None
                continue
            m = re.match(r"^(\s*)[-*]\s+(.*)$", ln)
            if m:
                flush()
                self.bullet(m.group(2), 2 if len(m.group(1)) >= 2 else 1)
                i += 1
                continue
            m = re.match(r"^(\d+[.)])\s+(.*)$", s) or re.match(r"^(\[\d+\])\s+(.*)$", s)
            if m:
                flush()
                self.numbered(m.group(1), m.group(2))
                i += 1
                continue
            if s.startswith(">"):
                flush()
                note = [s.lstrip("> ").strip()]
                i += 1
                while i < len(lines) and lines[i].strip().startswith(">"):
                    note.append(lines[i].strip().lstrip("> ").strip())
                    i += 1
                self.note(" ".join(note))
                continue
            buf.append(s)
            i += 1
        flush()

    # ---------------------------------------------------- directive
    def directive(self, d: str) -> None:
        name, _, arg = d.partition(":")
        h = getattr(self, f"d_{name.strip()}", None)
        if h is None:
            self.paragraph(I.placeholder(f"directive lạ {{{{{d}}}}}"))
            return
        h(arg.strip())

    def d_pagebreak(self, _):
        self.page_break()

    def d_section(self, arg):
        sec = self.doc.add_section(WD_SECTION.NEW_PAGE)
        if arg == "front":
            sec.footer.is_linked_to_previous = False
            fp = sec.footer.paragraphs[0]
            fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_field(fp, "PAGE", "i")
            set_page_numbering(sec, "lowerRoman", 1)
        else:
            set_page_numbering(sec, "decimal", 1)
        self.fresh_page = True

    def _toc_like(self, title: str, instr: str, hint: str) -> None:
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if not self.fresh_page:
            p.paragraph_format.page_break_before = True
        r = p.add_run(title)
        r.bold = True
        run_font(r, FONT, 16)
        tp = self.doc.add_paragraph()
        tp.paragraph_format.first_line_indent = Cm(0)
        add_field(tp, instr, hint)
        self.fresh_page = False

    def d_toc(self, _):
        self._toc_like("MỤC LỤC", 'TOC \\o "1-3" \\h \\z \\u',
                       "Mục lục được tạo bằng trường TOC: trong Word nhấn Ctrl+A rồi F9 (hoặc chuột phải → Update Field) để cập nhật.")

    def d_list_figures(self, _):
        self._toc_like("DANH MỤC HÌNH", 'TOC \\h \\z \\t "FigureCaption,1"', "Nhấn F9 để cập nhật danh mục hình.")

    def d_list_tables(self, _):
        self._toc_like("DANH MỤC BẢNG", 'TOC \\h \\z \\t "TableCaption,1"', "Nhấn F9 để cập nhật danh mục bảng.")

    # cover & nhóm
    def d_cover(self, _):
        t = self.ctx["team"]

        def line(txt, size=14, bold=False, before=0, after=4):
            p = self.doc.add_paragraph(style="CoverText")
            p.paragraph_format.space_before = Pt(before)
            p.paragraph_format.space_after = Pt(after)
            self.inline(p, txt, size=size, bold=bold)

        def up(s: str) -> str:
            return s if "[[" in s else s.upper()

        line(up(t["school"]), 14, True)
        line(up(t["faculty"]), 14, True, after=30)
        line("ĐỒ ÁN HỌC PHẦN", 16, True, before=40)
        line(t["course"].upper(), 18, True, after=24)
        line("ĐỀ TÀI", 14, False, before=24)
        line(t["title"], 17, True, after=6)
        line(t["subtitle"], 13, False, after=24)
        line(f"Quy trình phụ trách: **{t['process']}**", 13)
        line(f"Lớp: {t['class']}   –   Nhóm: {t['group']}", 13)
        line(f"Giảng viên hướng dẫn: {t['instructor']}", 13, after=16)
        rows = [[str(i + 1), m["name"], m["student_id"], m["role"]] for i, m in enumerate(t["members"])]
        self.table(["STT", "Họ và tên", "MSSV", "Vai trò chính"], rows, font_size=12, widths=[1.2, 5.5, 3.3, 6.0])
        line(f"{t['place']}, {t['date']}", 13, False, before=40)
        self.fresh_page = False

    def d_team_table(self, _):
        t = self.ctx["team"]
        rows = [[str(i + 1), m["name"], m["student_id"], m["role"], "; ".join(m["tasks"]), m["contribution"]]
                for i, m in enumerate(t["members"])]
        self.table(["STT", "Họ và tên", "MSSV", "Vai trò", "Nhiệm vụ thực tế", "Đóng góp"], rows,
                   "Bảng phân công nhiệm vụ và mức đóng góp của các thành viên", font_size=10,
                   widths=[1.0, 3.2, 2.2, 2.6, 5.4, 1.6])

    # dữ liệu Analytics
    def d_contract_table(self, _):
        tb = self.ctx["tables"]
        rows = []
        for n, ti in tb.items():
            topic, grain, key, use = I.TABLE_META.get(n, ("–", "–", "–", "–"))
            rows.append([f"`{n}`", topic, grain, key, I.fmt_int(ti.rows), str(len(ti.schema)), use])
        rows.append(["**Tổng**", "", "", "", f"**{I.fmt_int(sum(t.rows for t in tb.values()))}**",
                     str(sum(len(t.schema) for t in tb.values())), ""])
        self.table(["Bảng (analytics.*)", "Chủ đề", "1 dòng =", "Khoá / cột định danh", "Số dòng", "Số cột",
                    "Dùng trên dashboard"], rows, "Data contract Analytics → Presentation: danh sách bảng, grain và khoá",
                   font_size=9)

    def d_size_table(self, _):
        tb = self.ctx["tables"]
        rows = [[f"`{n}`", I.fmt_int(t.rows), str(t.files), I.fmt_num(t.bytes / 1024, 1)] for n, t in tb.items()]
        rows.append(["**Tổng**", f"**{I.fmt_int(sum(t.rows for t in tb.values()))}**",
                     str(sum(t.files for t in tb.values())), f"**{I.fmt_num(sum(t.bytes for t in tb.values()) / 1024, 1)}**"])
        self.table(["Bảng", "Số dòng", "Số file Parquet", "Dung lượng (KB, snappy)"], rows,
                   "Quy mô thực tế của các bảng Parquet Analytics (đọc trực tiếp bằng pyarrow khi sinh báo cáo)")

    def d_schema_appendix(self, _):
        for n, ti in self.ctx["tables"].items():
            rows = [[f"`{f.name}`", str(f.type), I.pg_type(f.type)] for f in ti.schema]
            self.table(["Cột", "Kiểu Parquet (Arrow)", "Kiểu PostgreSQL"], rows,
                       f"Schema bảng `{n}` ({I.fmt_int(ti.rows)} dòng; 1 dòng = {I.TABLE_META.get(n, ('', '–'))[1]})",
                       font_size=10, widths=[5.5, 5.0, 5.0])

    def d_type_mapping(self, _):
        seen: dict[str, tuple[str, set]] = {}
        for n, ti in self.ctx["tables"].items():
            for f in ti.schema:
                k = re.sub(r"\(\d+, ?\d+\)", "(p, s)", str(f.type))
                pgt = re.sub(r"\(\d+,\d+\)", "(p,s)", I.pg_type(f.type))
                seen.setdefault(k, (pgt, set()))[1].add(n)
        reason = {"string": "Chuỗi định danh/nhãn, không giới hạn độ dài",
                  "int32": "Số nguyên 4 byte (tháng, điểm, rank)", "int64": "Đếm số lượng lớn (đơn, khách, món)",
                  "double": "Giá trị trung bình/tỷ lệ đã làm tròn", "bool": "Cờ (vd. tháng Black Friday)",
                  "date32[day]": "Ngày mua đầu/cuối", "decimal128(p, s)": "Tiền BRL: giữ chính xác 2 chữ số thập phân, không sai số dấu phẩy động"}
        rows = [[f"`{k}`", f"`{v[0]}`", reason.get(k, ""), str(len(v[1]))] for k, v in seen.items()]
        self.table(["Kiểu Arrow/Parquet", "Kiểu PostgreSQL", "Lý do", "Số bảng dùng"], rows,
                   "Ánh xạ kiểu dữ liệu Parquet → PostgreSQL do loader áp dụng")

    def d_sample_records(self, _):
        tb = self.ctx["tables"]
        out = []
        for n in ("kpi_monthly", "customer_segments", "seller_watchlist"):
            if n in tb:
                rec = tb[n].table.slice(0, 1).to_pylist()[0]
                rec = {k: (str(v) if not isinstance(v, (int, float, bool)) or isinstance(v, bool) else v)
                       for k, v in rec.items()}
                out.append(f"-- {n} (1 dòng mẫu)\n" + json.dumps(rec, ensure_ascii=False, indent=2))
        self.code("\n\n".join(out))

    def d_expected_checks(self, _):
        tb = self.ctx["tables"]
        rows = []
        for n, t in tb.items():
            rows.append([f"COUNT(*) `analytics.{n}`", I.fmt_int(t.rows), "Số dòng Parquet = số dòng bảng Neon"])
        def ssum(n, col):
            return sum(float(v) for v in tb[n].table.column(col).to_pylist() if v is not None)
        extra = []
        if "kpi_monthly" in tb:
            extra.append(["SUM(revenue) `kpi_monthly` (20 tháng)", I.fmt_num(ssum("kpi_monthly", "revenue")),
                          "Nhỏ hơn 13.494.400,74 vì đã cắt tháng 2016 và 09/2018"])
        if "state_logistics" in tb:
            extra.append(["SUM(revenue) `state_logistics`", I.fmt_num(ssum("state_logistics", "revenue")),
                          "Số neo gold toàn kỳ"])
        if "seller_pareto" in tb:
            extra.append(["SUM(revenue) `seller_pareto`", I.fmt_num(ssum("seller_pareto", "revenue")), "Tổng theo người bán"])
        if "category_pareto" in tb:
            extra.append(["SUM(revenue) `category_pareto`", I.fmt_num(ssum("category_pareto", "revenue")), "Tổng theo danh mục"])
        if "repeat_profile" in tb:
            extra.append(["SUM(customers) `repeat_profile`", I.fmt_int(ssum("repeat_profile", "customers")),
                          "= số khách thật (customer_unique_id)"])
        self.table(["Kiểm tra", "Giá trị kỳ vọng (từ Parquet)", "Ghi chú"], extra + rows,
                   "Bộ kiểm tra đối chiếu Parquet ↔ Neon và giá trị kỳ vọng", font_size=10, widths=[6.3, 4.0, 5.7])

    # hình
    def d_chart(self, arg):
        key, _, cap = arg.partition("|")
        p = self.ctx["charts"].get(key.strip())
        if p and Path(p).exists():
            self.image(Path(p), cap.strip())
        else:
            self.image_placeholder(f"biểu đồ {key} chưa sinh được", cap.strip())

    def d_image(self, arg):
        path, _, cap = arg.partition("|")
        path = path.strip().replace("UPSTREAM:", str(I.UPSTREAM_DIR) + "/").replace("PROJECT:", str(I.PROJECT_DIR) + "/")
        p = Path(path)
        if p.exists():
            self.image(p, cap.strip(), max_h=9)
        else:
            self.image_placeholder(f"không tìm thấy ảnh {path}", cap.strip())

    def d_evidence(self, arg):
        parts = arg.split("|")
        cat = parts[0].strip()
        optional = cat.endswith("?")
        cat = cat.rstrip("?")
        hint = parts[1].strip() if len(parts) > 1 else ""
        imgs = self.ctx["images"]
        ov = self.ctx["captions"]
        if cat == "remaining":
            rest = [p for p in imgs if p.resolve() not in self.used_images]
            if not rest:
                self.paragraph("Không có ảnh minh chứng bổ sung nào khác trong `evidence/` và `docs/` tại thời điểm sinh báo cáo.")
            for p in rest:
                self.image(p, I.image_caption(p, ov), max_h=11)
            return
        sel = [p for p in imgs if I.classify_image(p) == cat and p.resolve() not in self.used_images]
        for p in sel:
            self.image(p, I.image_caption(p, ov), max_h=11)
        if not sel and not optional:
            label = next((c for k, _, c in I.IMAGE_CATEGORIES if k == cat), cat)
            rx = next((r for k, r, _ in I.IMAGE_CATEGORIES if k == cat), "")
            self.image_placeholder(f"chụp ảnh '{hint or label}', lưu vào evidence/ với tên khớp /{rx.split('|')[0]}/ rồi chạy lại build_report.py", label)

    # số liệu thực nghiệm
    def _datafile_block(self, files: list, caption: str, what: str, max_rows: int = 30) -> None:
        if not files:
            self.paragraph(I.placeholder(what), indent=False)
            return
        for f in files:
            rel = str(f.path.relative_to(I.PROJECT_DIR)).replace("\\", "/")
            if f.is_table:
                hdr = f.headers[:9]
                rows = [r[:9] for r in f.rows[:max_rows]]
                self.table(hdr, rows, f"{caption} (tệp `{rel}`)", font_size=9 if len(hdr) > 6 else 10)
                if len(f.rows) > max_rows:
                    self.paragraph(f"*(Hiển thị {max_rows}/{len(f.rows)} dòng; xem đầy đủ trong `{rel}`.)*", indent=False)
                if f.scalars:
                    self.table(["Thuộc tính", "Giá trị"], [[k, v] for k, v in list(f.scalars.items())[:15]])
            else:
                lines = f.raw.strip().splitlines()
                tail = lines[-45:]
                self.paragraph(f"Trích {len(tail)}/{len(lines)} dòng cuối của `{rel}`:", indent=False)
                self.code("\n".join(tail))

    def d_load_log(self, _):
        files = self.ctx["files"]["load"]
        lf = next((f for f in files if I.is_loader_csv(f)), None)
        if lf is None:
            self._datafile_block(files, "Log nạp dữ liệu Parquet → Neon",
                                 "chưa có evidence/load_log*.csv|json|txt – chạy loader để sinh log nạp (bảng, số dòng, thời gian)")
            return
        H = {h: i for i, h in enumerate(lf.headers)}

        def g(r, k, conv=float):
            try:
                return conv(r[H[k]]) if k in H and r[H[k]] != "" else None
            except ValueError:
                return None

        rows, tot = [], dict(rows=0, pq=0.0, csv=0.0, copy=0.0, idx=0.0, sec=0.0)
        for r in lf.rows:
            n = g(r, "rows", lambda x: int(float(x))) or 0
            pqb, csvb = g(r, "parquet_bytes") or 0, g(r, "csv_bytes") or 0
            cp, ix, sec = g(r, "copy_seconds") or 0, g(r, "index_seconds") or 0, g(r, "seconds") or 0
            for k, v in (("rows", n), ("pq", pqb), ("csv", csvb), ("copy", cp), ("idx", ix), ("sec", sec)):
                tot[k] += v
            ok = ("✓" if r[H["row_count_ok"]].lower() == "true" else "✗") if "row_count_ok" in H else ""
            name = f"{r[H['schema_name']]}.{r[H['table_name']]}" if "schema_name" in H else r[H["table_name"]]
            rows.append([f"`{name}`", I.fmt_int(n), I.fmt_num(pqb / 1e6, 2), I.fmt_num(csvb / 1e6, 2),
                         I.fmt_num(cp, 2), I.fmt_num(ix, 2), I.fmt_num(sec, 2),
                         I.fmt_num(csvb / 1e6 / cp, 2) if cp else "", ok])
        rows.append(["**Tổng**", f"**{I.fmt_int(tot['rows'])}**", I.fmt_num(tot["pq"] / 1e6, 2), I.fmt_num(tot["csv"] / 1e6, 2),
                     I.fmt_num(tot["copy"], 2), I.fmt_num(tot["idx"], 2), f"**{I.fmt_num(tot['sec'], 2)}**",
                     I.fmt_num(tot["csv"] / 1e6 / tot["copy"], 2) if tot["copy"] else "", ""])
        rel = str(lf.path.relative_to(I.PROJECT_DIR)).replace("\\", "/")
        self.table(["Bảng", "Số dòng", "Parquet (MB)", "CSV truyền (MB)", "COPY (s)", "PK/index + ANALYZE (s)",
                    "Tổng (s)", "MB/s COPY", "Khớp"], rows,
                   f"Kết quả nạp từng bảng, lần chạy `{lf.rows[0][H['run_id']] if 'run_id' in H else '?'}` (tệp `{rel}`)",
                   font_size=9, widths=[4.6, 1.6, 1.4, 1.5, 1.3, 1.6, 1.3, 1.3, 0.9])

    LAT_LABELS = {"tab": "Tab", "query": "Truy vấn", "rows_returned": "Số dòng", "client_median_ms": "Client trung vị (ms)",
                  "client_p95_ms": "Client p95 (ms)", "server_exec_ms": "Server thực thi (ms)", "slice_name": "Chart",
                  "viz_type": "Loại", "median_ms": "Trung vị (ms)", "min_ms": "Nhỏ nhất (ms)", "rows": "Số dòng"}

    def d_latency(self, _):
        files = [f for f in I.latency_files(self.ctx["files"]["latency"]) if f.is_table]
        if not files:
            self._datafile_block(self.ctx["files"]["latency"], "Độ trễ truy vấn",
                                 "chưa có evidence/*latency*.csv|md – chạy script đo latency (cold/warm, p50/p95) rồi chạy lại build_report.py")
            return
        for f in files:
            rel = str(f.path.relative_to(I.PROJECT_DIR)).replace("\\", "/")
            good = I.valid_latency_rows(f)
            if not good:
                self.paragraph(I.placeholder(f"tệp {rel} hiện chỉ chứa phép đo lỗi ({len(f.rows)}/{len(f.rows)} dòng thất bại) – "
                                             "chạy lại phép đo sau khi dashboard hoạt động"), indent=False)
                continue
            keep = [i for i, h in enumerate(f.headers) if not re.search(r"^(key|chart_id|status)$", h)] or list(range(len(f.headers)))
            hdr = [self.LAT_LABELS.get(f.headers[i], f.headers[i]) for i in keep][:7]
            rows = [[r[i] if i < len(r) else "" for i in keep][:7] for r in good[:40]]
            cap = "Độ trễ truy vấn đo qua Superset" if "superset" in f.path.name.lower() else "Độ trễ truy vấn các view trên Neon"
            self.table(hdr, rows, f"{cap} ({len(good)}/{len(f.rows)} phép đo thành công; tệp `{rel}`)", font_size=9)

    def d_validation(self, arg):
        part = arg or "all"
        files = self.ctx["files"]["validate"]
        obj = I.validation_json(files)
        if not obj:
            if part != "rows":
                self._datafile_block(files, "Kết quả đối chiếu Parquet ↔ Neon",
                                     "chưa có evidence/validat*|reconcil*|row_count* – chạy script kiểm tra đối chiếu")
            return
        rc = obj.get("row_counts", []) if part in ("all", "rows") else []
        if rc:
            rows = [[f"`{r['table']}`", I.fmt_int(r["parquet_rows"]), I.fmt_int(r["postgres_rows"]),
                     "ĐẠT" if r.get("ok") else "LỆCH"] for r in rc]
            self.table(["Bảng trên Neon", "Dòng Parquet", "Dòng Postgres", "Kết quả"], rows,
                       f"Đối chiếu số dòng Parquet ↔ Neon: {sum(1 for r in rc if r.get('ok'))}/{len(rc)} bảng khớp (tệp `evidence/validation.json`)",
                       font_size=10, widths=[6.5, 3.0, 3.0, 2.0])
        an = obj.get("anchors", []) if part in ("all", "anchors") else []
        if an:
            def fmt(v):
                f = I._to_float(str(v))
                if f is None:
                    return str(v)
                return I.fmt_num(f, 2) if abs(f - round(f)) > 1e-9 else I.fmt_int(f)

            rows = [[a["name"], fmt(a.get("expected", "")), fmt(a.get("got", "")), str(a.get("status", "")),
                     I.fmt_num(a["ms"], 1) if a.get("ms") is not None else ""] for a in an]
            self.table(["Kiểm tra (sql/90_anchor_checks.sql)", "Kỳ vọng", "Thực tế trên Neon", "Kết quả", "ms"], rows,
                       "Đối chiếu số neo bàn giao của Analytics và tính nhất quán giữa các view trên Neon",
                       font_size=9.5, widths=[7.6, 2.4, 2.6, 1.4, 1.2])

    def d_dashboard_log(self, _):
        files = self.ctx["files"]["dashboard"]
        if files:
            self._datafile_block(files, "Log dựng dashboard qua Superset REST API", "")

    def d_views(self, arg):
        views = self.ctx["views"]
        if views:
            rows = []
            for v in views:
                short = v.name.split(".", 1)[1]
                desc = VIEW_DESC.get(short) or v.comment or ""
                srcs = ", ".join(f"`{s}`" for s in v.sources) or "–"
                kind = "bảng" if v.kind == "TABLE" else "view"
                rows.append([f"`{short}`", kind, srcs, desc])
            nview = sum(1 for v in views if v.kind != "TABLE")
            files = sorted({v.file for v in views})
            self.table(["Đối tượng (schema presentation)", "Loại", "Nguồn", "Mục đích"], rows,
                       f"Các đối tượng của tầng ngữ nghĩa: {nview} view và {len(views) - nview} bảng dimension "
                       f"(quét tự động từ {', '.join(f'`{f}`' for f in files)})", font_size=9, widths=[4.0, 1.2, 5.0, 5.8])
        else:
            rows = [[f"`presentation.{v}`", src, desc] for v, src, desc in PLANNED_VIEWS]
            self.table(["View (dự kiến)", "Bảng nguồn", "Mục đích"], rows,
                       "Thiết kế semantic view của schema presentation", font_size=10)
            self.paragraph(I.placeholder("chưa tìm thấy file sql/*.sql có CREATE VIEW – kiểm tra lại tên view thực tế"), indent=False)

    def d_gold_table(self, _):
        gold = self.ctx["gold"]
        if not gold:
            self.paragraph(I.placeholder("không tìm thấy data/gold"), indent=False)
            return
        meta = I.upstream_manifest().get("tables", {})
        rows = [[f"`gold.{n}`", meta.get(n, {}).get("grain", ""), I.fmt_int(r), str(c), str(f), I.fmt_num(b / 1e6, 2)]
                for n, (r, c, f, b) in gold.items()]
        rows.append(["**Tổng**", "", f"**{I.fmt_int(sum(v[0] for v in gold.values()))}**", "",
                     str(sum(v[2] for v in gold.values())), I.fmt_num(sum(v[3] for v in gold.values()) / 1e6, 2)])
        self.table(["Bảng", "1 dòng =", "Số dòng", "Số cột", "Số file", "MB"], rows,
                   "Các bảng gold được nạp bổ sung vào schema gold (đầu vào chi tiết cho bộ lọc chéo)", font_size=10)

    def d_source_tree(self, _):
        self.code(I.source_tree())

    def d_run_commands(self, _):
        order = [r"load", r"view|sql|semantic", r"validat|check|reconcil", r"dashboard", r"latenc|bench", r"screenshot"]
        found = []
        for sub in ("loader", "sql", "superset", "scripts"):
            d = I.PROJECT_DIR / sub
            if not d.exists():
                continue
            for p in sorted(d.glob("*.py")):
                if p.name in ("common.py", "superset_config.py", "__init__.py", "inspect_parquet.py") or p.stem.endswith("client"):
                    continue
                rel = f"{sub}/{p.name}"
                rank = next((i for i, rx in enumerate(order) if re.search(rx, p.stem.lower())), len(order))
                doc = re.search(r'^\s*(?:"""|\'\'\')(.*?)(?:\n|"""|\'\'\')', p.read_text(encoding="utf-8", errors="replace"), re.S)
                found.append((rank, rel, (doc.group(1).strip() if doc else "")))
        if not found:
            self.paragraph(I.placeholder("chưa có script Python trong loader/, superset/, scripts/ – bổ sung lệnh chạy"), indent=False)
            return
        lines = []
        for n, (rank, rel, doc) in enumerate(sorted(found), start=3):
            lines.append(f"# {n}. {rel}" + (f" – {doc}" if doc else ""))
            if "screenshot" in rel:
                lines.append("docker compose --profile screenshots run --rm screenshots")
            else:
                lines.append(f"docker compose run --rm tools python {rel}")
            lines.append("")
        self.code("\n".join(lines).rstrip())

    def d_sql_files(self, _):
        files = sorted((I.PROJECT_DIR / "sql").glob("*.sql")) if (I.PROJECT_DIR / "sql").exists() else []
        if not files:
            self.paragraph(I.placeholder("chưa có tệp sql/*.sql – mã SQL các view sẽ được trích tự động khi có"), indent=False)
            return
        for p in files:
            txt = p.read_text(encoding="utf-8", errors="replace").rstrip().splitlines()
            if len(txt) > 150:
                txt = txt[:150] + [f"-- ... (cắt, tổng {len(txt)} dòng)"]
            self.paragraph(f"Tệp `sql/{p.name}`:", indent=False)
            self.code("\n".join(txt))

    def d_evidence_files(self, _):
        if not I.EVIDENCE_DIR.exists() or not any(I.EVIDENCE_DIR.rglob("*")):
            self.paragraph(I.placeholder("thư mục evidence/ chưa có tệp minh chứng"), indent=False)
            return
        rows = []
        for p in sorted((p for p in I.EVIDENCE_DIR.rglob("*") if p.is_file()), key=I._natural_key):
            rel = str(p.relative_to(I.PROJECT_DIR)).replace("\\", "/")
            kind = "Ảnh" if p.suffix.lower() in I.IMG_EXT else p.suffix.lstrip(".").upper() or "Tệp"
            rows.append([f"`{rel}`", kind, I.fmt_num(p.stat().st_size / 1024, 1)])
        self.table(["Tệp", "Loại", "KB"], rows, "Danh sách tệp minh chứng trong evidence/", font_size=10)

    def d_file(self, arg):
        parts = [x.strip() for x in arg.split("|")]
        rel = parts[0]
        maxl = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 60
        txt = I.read_project_file(rel)
        if txt is None:
            self.paragraph(I.placeholder(f"tệp {rel} chưa tồn tại"), indent=False)
            return
        lines = txt.rstrip().splitlines()
        if len(lines) > maxl:
            lines = lines[:maxl] + [f"... (cắt, tổng {len(txt.splitlines())} dòng – xem {rel})"]
        self.paragraph(f"Tệp `{rel}`:", indent=False)
        self.code("\n".join(lines))


VIEW_DESC = {
    "dim_state": "Dimension 27 bang: tên, vùng, mã ISO `BR-xx` cho Country Map",
    "v_kpi_monthly": "Chuỗi KPI tháng; thêm `month_date` (DATE) và `month_label` cho bộ lọc thời gian",
    "v_orders": "Đơn hợp lệ cấp đơn 2017-01→2018-08: thẻ KPI lọc được theo tháng/bang/PTTT; `late_flag` cho % trễ chính xác",
    "v_kpi_overview": "1 dòng số neo toàn kỳ (doanh thu gold, tháng đỉnh, review trễ/đúng hạn, % khách lặp, watchlist)",
    "v_category_pareto": "Pareto danh mục + hạng + nhóm A/B/C",
    "v_category_seasonality": "Heatmap danh mục × tháng năm 2017",
    "v_category_monthly": "Doanh thu danh mục theo tháng (từ gold) cho xu hướng có lọc danh mục",
    "v_sales_items": "Dòng sản phẩm hợp lệ: doanh thu/ship theo danh mục × bang × tháng (không chứa review)",
    "v_state_logistics": "Logistics theo bang, kèm tên bang, vùng, mã ISO",
    "v_insight_distance": "Phí ship, ngày giao, % trễ theo band khoảng cách",
    "v_rfm_customers": "1 khách: điểm RFM, phân khúc, cohort, cụm K-Means có tên nghiệp vụ",
    "v_rfm_segments": "Tổng hợp theo phân khúc RFM + hành động CRM gợi ý",
    "v_cluster_profile": "Hồ sơ 4 cụm K-Means với tên nghiệp vụ",
    "v_repeat_profile": "Khách mua lại vs mua một lần",
    "v_repeat_categories": "Danh mục ưa thích của khách mua lại",
    "v_repeat_states": "Bang của khách mua lại",
    "v_seller_pareto": "Pareto người bán, nhóm A/B/C, cờ thuộc watchlist",
    "v_seller_watchlist": "Người bán cần theo dõi: số vi phạm, lý do, mức cảnh báo ĐỎ/VÀNG, hành động khuyến nghị",
    "v_late_vs_review": "Review đơn trễ vs đúng hạn (nhãn tiếng Việt)",
    "v_delay_vs_review": "Review và % 1 sao theo số ngày trễ",
    "v_payment_mix": "Cơ cấu PTTT × kỳ trả góp, % đơn",
    "v_decision_hints": "7 luật gợi ý quyết định có ngưỡng, giá trị, hành động, nguồn – giao diện cho Decision/Action",
    "v_load_log": "Lần nạp gần nhất của mỗi bảng (lineage, độ tươi dữ liệu trên dashboard)",
}

PLANNED_VIEWS = [
    ("v_kpi_overview", "kpi_monthly, repeat_profile", "Thẻ KPI tổng: doanh thu, đơn, AOV, % trễ, review, % khách lặp"),
    ("v_kpi_monthly", "kpi_monthly", "Chuỗi thời gian có cột month_start (DATE) để lọc khoảng tháng"),
    ("v_category_pareto", "category_pareto", "Pareto danh mục, cờ nhóm A (≤80% cộng dồn)"),
    ("v_category_seasonality", "category_seasonality", "Heatmap danh mục × tháng 2017"),
    ("v_state_logistics", "state_logistics", "Thêm iso_code 'BR-xx' cho Country Map Brazil"),
    ("v_distance_logistics", "insight_distance", "Phí ship, ngày giao, % trễ theo band km"),
    ("v_rfm_segment_summary", "rfm_scores", "Đếm khách, monetary TB theo rfm_segment × bang"),
    ("v_cluster_profile", "cluster_profile", "Hồ sơ cụm K-Means kèm tên cụm nghiệp vụ"),
    ("v_seller_pareto", "seller_pareto", "Pareto người bán, xếp hạng"),
    ("v_seller_watchlist", "seller_watchlist", "Gợi ý quyết định: lý do cảnh báo (review/ngày giao/% trễ)"),
    ("v_late_vs_review", "insight_late_vs_review, delay_vs_review", "Tác động giao trễ lên review"),
    ("v_payment_mix", "payment_mix", "Cơ cấu thanh toán × kỳ trả góp"),
]


# =============================================================== điều phối
def collect_context(make_charts: bool) -> dict:
    tables = I.load_analytics()
    if not tables:
        sys.exit("Không tìm thấy Parquet Analytics (data/analytics hoặc D:\\Analytics-main\\data\\analytics)")
    team = json.loads((I.CONTENT_DIR / "team.json").read_text(encoding="utf-8"))
    if make_charts:
        ch = charts.build_all(tables)
    else:
        ch = {k: I.FIG_DIR / f"fig_{k}.png" for k in charts.ALL}
    files = {k: I.find_data_files(k) for k in ("load", "latency", "validate", "dashboard")}
    up = I.upstream_summary()
    v: dict[str, str] = {
        "n_tables": str(len(tables)),
        "total_rows": I.fmt_int(sum(t.rows for t in tables.values())),
        "total_kb": I.fmt_num(sum(t.bytes for t in tables.values()) / 1024, 1),
        "total_mb": I.fmt_num(sum(t.bytes for t in tables.values()) / 1024 / 1024, 2),
        "total_cols": str(sum(len(t.schema) for t in tables.values())),
        "build_date": dt.date.today().strftime("%d/%m/%Y"),
        "repo_url": I.REPO_URL,
        "analytics_dir": str(I.analytics_dir()).replace("\\", "/"),
    }
    if up.get("run"):
        v.update(spark_total_s=I.fmt_num(up["run"]["total_seconds"], 2), spark_sql_s=I.fmt_num(up["run"]["sql_seconds"], 2),
                 spark_kmeans_s=I.fmt_num(up["run"]["kmeans_seconds"], 2))
    v.update(I.summarize_load(files["load"]))
    v.update(I.summarize_latency(files["latency"]))
    v.update(I.latency_md_facts(files["latency"]))
    v.update(I.summarize_validation(files["validate"]))
    views = I.detect_views()
    v["n_views"] = str(sum(1 for x in views if x.kind != "TABLE")) if views else str(len(PLANNED_VIEWS))
    gold = I.load_gold()
    if gold:
        v["n_gold"] = str(len(gold))
        v["gold_rows"] = I.fmt_int(sum(g[0] for g in gold.values()))
        v["serving_tables"] = str(len(tables) + len(gold))
        v["serving_rows"] = I.fmt_int(sum(t.rows for t in tables.values()) + sum(g[0] for g in gold.values()))
    return dict(tables=tables, team=team, charts=ch, files=files, vars=v, views=views, gold=gold,
                images=I.find_images(), captions=I.load_caption_overrides())


def build(make_charts: bool = True) -> Path:
    ctx = collect_context(make_charts)
    doc = new_document()
    r = Renderer(doc, ctx)
    for md in sorted(I.CONTENT_DIR.glob("*.md")):
        r.render_markdown(md.read_text(encoding="utf-8"))
    doc.core_properties.title = ctx["team"]["title"]
    doc.core_properties.subject = ctx["team"]["course"]
    doc.core_properties.author = ctx["team"]["group"]
    doc.core_properties.language = "vi-VN"
    doc.save(OUT_DOCX)
    return OUT_DOCX


def verify(path: Path) -> dict:
    d = Document(str(path))
    heads = {lvl: sum(1 for p in d.paragraphs if p.style.name == f"Heading {lvl}") for lvl in (1, 2, 3)}
    words_body = sum(len(p.text.split()) for p in d.paragraphs)
    words_tables = sum(len(c.text.split()) for t in d.tables for row in t.rows for c in row.cells)
    all_text = "\n".join(p.text for p in d.paragraphs) + "\n" + "\n".join(
        c.text for t in d.tables for row in t.rows for c in row.cells)
    phs = sorted(set(PH_RX.findall(all_text)))
    stats = {
        "paragraphs": len(d.paragraphs), "headings": heads, "tables": len(d.tables),
        "images": len(d.inline_shapes), "words_paragraphs": words_body, "words_tables": words_tables,
        "sections": len(d.sections),
        "fig_captions": sum(1 for p in d.paragraphs if p.style.name == "FigureCaption"),
        "table_captions": sum(1 for p in d.paragraphs if p.style.name == "TableCaption"),
        "placeholders": phs,
    }
    # ước lượng trang: ~520 từ chữ/trang (TNR 13, giãn dòng 1,5, lề 3-2-2-2), ảnh ~0,45 trang, bảng ~ theo số dòng
    rows = sum(len(t.rows) for t in d.tables)
    stats["est_pages"] = round(words_body / 520 + len(d.inline_shapes) * 0.45 + rows * 0.032 + heads[1] * 0.3, 1)
    return stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-charts", action="store_true", help="không vẽ lại biểu đồ matplotlib")
    a = ap.parse_args()
    out = build(make_charts=not a.no_charts)
    st = verify(out)
    print(f"Đã sinh: {out}")
    for k, v in st.items():
        if k != "placeholders":
            print(f"  {k}: {v}")
    print(f"  placeholders còn lại: {len(st['placeholders'])}")
    (I.REPORT_DIR / "placeholders.txt").write_text("\n".join(st["placeholders"]) + "\n", encoding="utf-8")
    for p in st["placeholders"]:
        print("   -", p)


if __name__ == "__main__":
    main()
