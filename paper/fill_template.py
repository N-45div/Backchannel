"""Fill Apart's Word template with the report: keeps the template's title block, footnote, author grid, abstract box
and heading styles; replaces the guidance text with paper/sections/*.md; numbers come from figures/stats.json.

  uv run --with python-docx python paper/fill_template.py <template.docx> <out.docx>
"""
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import build  # noqa: E402  (VALUES, TITLE, KEYWORDS: the same numbers and words as the PDF build)

FONT = "Old Standard TT"
BODY, SMALL, TINY = Pt(9.5), Pt(8.5), Pt(7.5)
MARGIN, TEXT_W = 0.85, 8.5 - 2 * 0.85  # inches
ORDER = ["intro_related", "method", "results", "realdata_limits", "conclusion",
         "references", "appendix", "appendix_tables", "appendix_texts", "llm_usage"]
INLINE = re.compile(r"(\*\*.+?\*\*|`[^`]+`|<sup>.*?</sup>|\*[^*\s][^*]*?\*)")


def set_font(run, size=None, bold=None, italic=None, mono=False):
    name = "Consolas" if mono else FONT
    run.font.name = name
    rpr = run._r.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.insert(0, fonts)
    for k in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(k), name)
    if size:
        run.font.size = size
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def fill(text):
    for k, v in build.VALUES.items():
        text = text.replace(k, v)
    return text


def mark_size(par, size):
    """Give the paragraph mark the text's size, so it doesn't pad the line to the template's 11 pt."""
    ppr = par._p.get_or_add_pPr()
    rpr = ppr.find(qn("w:rPr"))
    if rpr is None:
        rpr = OxmlElement("w:rPr")
        ppr.append(rpr)
    for tag in ("w:sz", "w:szCs"):
        for old in rpr.findall(qn(tag)):
            rpr.remove(old)
        el = OxmlElement(tag)
        el.set(qn("w:val"), str(int(size.pt * 2)))
        rpr.append(el)


def visible(text):
    return re.sub(r"\*\*|`|<sup>|</sup>|(?<!\w)\*|\*(?!\w)", "", text)


def add_inline(par, text, size=BODY, bold=False, italic=False):
    """Write text with **bold**, *italic*, `code` and <sup>…</sup> into par as runs."""
    mark_size(par, size)
    for piece in INLINE.split(text):
        if not piece:
            continue
        b, i, mono, sup = bold, italic, False, False
        if piece.startswith("**") and piece.endswith("**") and len(piece) > 4:
            piece, b = piece[2:-2], True
        elif piece.startswith("`") and piece.endswith("`"):
            piece, mono = piece[1:-1], True
        elif piece.startswith("<sup>"):
            piece, sup = piece[5:-6], True
        elif piece.startswith("*") and piece.endswith("*") and len(piece) > 2:
            piece, i = piece[1:-1], not italic
        if "*" in piece and not mono:  # nested markup inside bold, e.g. **text *x***
            add_inline(par, piece, size, b, i)
            continue
        r = par.add_run(piece)
        set_font(r, Pt(size.pt - 1) if mono else size, b, i, mono)
        if sup:
            r.font.superscript = True


def paragraph(doc, text, size=BODY, align=WD_ALIGN_PARAGRAPH.JUSTIFY, after=4, keep=False, indent=None, hang=None):
    p = doc.add_paragraph(style="normal")
    p.alignment = align
    f = p.paragraph_format
    f.space_before, f.space_after, f.line_spacing = Pt(0), Pt(after), 1.0
    f.keep_with_next = keep
    if indent is not None:
        f.left_indent = indent
    if hang is not None:
        f.first_line_indent = -hang
    add_inline(p, text, size)
    return p


def heading(doc, text, level):
    p = doc.add_paragraph(style="Heading 2" if level == 2 else "Heading 3")
    f = p.paragraph_format
    f.space_before, f.space_after, f.keep_with_next = Pt(8 if level == 2 else 5), Pt(2), True
    f.page_break_before = text == "Appendix"
    r = p.add_run(text)
    set_font(r, Pt(13) if level == 2 else Pt(11), True)
    return p


def caption(doc, text):
    """'*Figure N. text*' or '*Table N. text*': bold label, italic body; table captions keep with their table."""
    m = re.match(r"\*((?:Figure|Table) \d+\.)\s*(.*)\*$", text, re.S)
    label, body = m.group(1), m.group(2)
    p = doc.add_paragraph(style="normal")
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    f = p.paragraph_format
    f.space_before, f.space_after, f.line_spacing = Pt(2), Pt(6), 1.0
    f.keep_with_next = label.startswith("Table")
    r = p.add_run(label + " ")
    set_font(r, SMALL, True, False)
    add_inline(p, body, SMALL, italic=True)


def border(el, side, sz):
    b = OxmlElement(f"w:{side}")
    b.set(qn("w:val"), "single")
    b.set(qn("w:sz"), str(sz))
    b.set(qn("w:space"), "0")
    b.set(qn("w:color"), "000000")
    el.append(b)


def table(doc, rows, size):
    """Journal-style table: rules above and below the header and at the end only."""
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    header, body = cells[0], [r for r in cells[2:]]
    ncol = len(header)
    t = doc.add_table(rows=1 + len(body), cols=ncol)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    tblpr = t._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    border(borders, "top", 10)
    border(borders, "bottom", 10)
    tblpr.append(borders)
    widths = [max(len(visible(r[c])) if c < len(r) else 0 for r in cells[:1] + body) for c in range(ncol)]
    longest = [max((len(x) for r in cells[:1] + body if c < len(r) for x in visible(r[c]).split()), default=0)
               for c in range(ncol)]
    widths = [max(min(w, 70), lw * 1.6) + 4 for w, lw in zip(widths, longest)]
    total = sum(widths)
    mar = OxmlElement("w:tblCellMar")  # tight cells: the template's defaults pad every row
    for side, v in (("top", 15), ("left", 70), ("bottom", 15), ("right", 70)):
        e = OxmlElement(f"w:{side}")
        e.set(qn("w:w"), str(v))
        e.set(qn("w:type"), "dxa")
        mar.append(e)
    tblpr.append(mar)
    # fixed layout with explicit grid widths, so Word and Google Docs both honour the column widths
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblpr.append(layout)
    grid = t._tbl.tblGrid
    for gc, wch in zip(grid.findall(qn("w:gridCol")), widths):
        gc.set(qn("w:w"), str(int(TEXT_W * 1440 * wch / total)))
    for ri, rowvals in enumerate([header] + body):
        for ci in range(ncol):
            cell = t.cell(ri, ci)
            cell.width = Inches(TEXT_W * widths[ci] / total)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            add_inline(p, rowvals[ci] if ci < len(rowvals) else "", size, bold=(ri == 0))
            if ri == 0:
                tcpr = cell._tc.get_or_add_tcPr()
                b = OxmlElement("w:tcBorders")
                border(b, "bottom", 6)
                tcpr.append(b)
    for i, r in enumerate(t.rows):  # keep each row, and the whole table, on one page
        trpr = r._tr.get_or_add_trPr()
        cant = OxmlElement("w:cantSplit")
        trpr.append(cant)
        if i < len(t.rows) - 1:
            for c in r.cells:
                for cp in c.paragraphs:
                    cp.paragraph_format.keep_with_next = True
    doc.add_paragraph(style="normal").paragraph_format.space_after = Pt(2)


def picture(doc, path):
    doc.add_picture(str(path), width=Inches(4.7))
    p = doc.paragraphs[-1]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_after = Pt(0)


def blocks(text):
    return [b for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]


# Word moves a figure or table that doesn't fit to the next page and leaves a gap. These are placed
# that many body paragraphs later in the .docx only, so text fills the gap (the PDF build is unaffected).
DEFER = {"Table 1.": 2, "Table 2.": 1, "fig1_payloads_defences.png": 2, "fig3_counterfactuals.png": 2}
PENDING = []


def write_section(doc, name):
    text = fill((HERE / "sections" / f"{name}.md").read_text(encoding="utf-8"))
    in_refs = name == "references"
    in_appendix_tables = name == "appendix_tables"
    bl = blocks(text)
    pending = PENDING  # [paragraphs still to wait, [writers]]; carries across section files

    def tick():
        for item in pending:
            item[0] -= 1
        for item in [x for x in pending if x[0] <= 0]:
            for fn in item[1]:
                fn()
            pending.remove(item)

    i = -1
    while i + 1 < len(bl):
        i += 1
        b = bl[i]
        lines = b.splitlines()
        first = lines[0]
        cap = re.match(r"\*(Table \d+\.)", first)
        if cap and cap.group(1) in DEFER and i + 1 < len(bl):
            ctext, tlines = " ".join(x.strip() for x in lines), bl[i + 1].splitlines()
            pending.append([DEFER[cap.group(1)], [lambda c=ctext: caption(doc, c),
                                                   lambda t=tlines: table(doc, t, SMALL)]])
            i += 1
            continue
        fig = re.match(r"!\[[^\]]*\]\(\.\./figures/([^)]+)\)", first.strip())
        if fig and fig.group(1) in DEFER:
            rest = " ".join(x.strip() for x in lines[1:]).strip()
            pending.append([DEFER[fig.group(1)], [lambda f=fig.group(1): picture(doc, ROOT / "figures" / f),
                                                   lambda r=rest: caption(doc, r) if r else None]])
            continue
        if not (first.startswith("#") or first.startswith("|") or first.startswith("![")):
            write_text_block(doc, b, in_refs)
            tick()
            continue
        if first.startswith("### "):
            heading(doc, first[4:].strip(), 3)
            rest = "\n".join(lines[1:]).strip()
            if rest:
                write_text_block(doc, rest, in_refs)
            continue
        if first.startswith("## "):
            heading(doc, first[3:].strip(), 2)
            rest = "\n".join(lines[1:]).strip()
            if rest:
                write_text_block(doc, rest, in_refs)
            continue
        if all(l.strip().startswith("|") for l in lines):
            table(doc, lines, TINY if (in_appendix_tables or len(lines[0].split("|")) > 7) else SMALL)
            continue
        m = re.match(r"!\[[^\]]*\]\(\.\./figures/([^)]+)\)", first.strip())
        if m:
            picture(doc, ROOT / "figures" / m.group(1))
            rest = "\n".join(lines[1:]).strip()
            if rest:
                caption(doc, " ".join(x.strip() for x in rest.splitlines()))
            continue
        write_text_block(doc, b, in_refs)
    if name == "conclusion":  # anything still waiting goes before the back matter
        for item in pending:
            for fn in item[1]:
                fn()
        pending.clear()


def write_text_block(doc, b, in_refs=False):
    lines = b.splitlines()
    joined = " ".join(x.strip() for x in lines)
    if re.match(r"\*(Figure|Table) \d+\.", joined) and joined.endswith("*"):
        caption(doc, joined)
        return
    if re.match(r"^\d+\. ", lines[0]) or lines[0].startswith("- "):
        items, cur = [], []
        for l in lines:
            if re.match(r"^\d+\. ", l) or l.startswith("- "):
                if cur:
                    items.append(" ".join(cur))
                cur = [l.strip()]
            else:
                cur.append(l.strip())
        items.append(" ".join(cur))
        for it in items:
            mk = re.match(r"^(\d+\.|-)\s+(.*)", it)
            mark = mk.group(1) if mk.group(1) != "-" else "–"
            paragraph(doc, f"{mark}\t{mk.group(2)}", indent=Inches(0.3), hang=Inches(0.22), after=2)
        doc.paragraphs[-1].paragraph_format.space_after = Pt(5)
        return
    if in_refs and joined.startswith("["):
        paragraph(doc, joined, size=SMALL, align=WD_ALIGN_PARAGRAPH.LEFT, after=2, indent=Inches(0.35), hang=Inches(0.35))
        return
    paragraph(doc, joined)


def page_number_footer(doc):
    p = doc.sections[0].footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    for kind, text in (("begin", None), (None, "PAGE"), ("end", None)):
        if kind:
            fc = OxmlElement("w:fldChar")
            fc.set(qn("w:fldCharType"), kind)
            run._r.append(fc)
        else:
            it = OxmlElement("w:instrText")
            it.set(qn("xml:space"), "preserve")
            it.text = text
            run._r.append(it)
    set_font(run, SMALL)


def main(src, out):
    doc = Document(src)
    body = doc.element.body
    outer = doc.tables[0]
    # title (the run holding the text; the footnote reference stays in its own run)
    title_p = [p for p in outer.cell(0, 0).paragraphs if p.style.name == "Title"][0]
    texts = [r for r in title_p.runs if r.text.strip()]
    texts[0].text = build.TITLE
    for r in texts[1:]:
        r.text = ""
    # authors: one author in the middle slot of the first row; the second row removed
    holder = outer.cell(1, 0).tables[0].cell(0, 0)
    grid = holder.tables[0]
    line = holder.add_paragraph(style="normal")
    line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = line.add_run("N. Divij")
    set_font(r, Pt(11), True)
    line.add_run().add_break()
    r = line.add_run("Independent AI researcher")
    set_font(r, Pt(10), False, True)
    grid._tbl.addnext(line._p)
    grid._tbl.getparent().remove(grid._tbl)
    # abstract box: our abstract, then keywords
    box = [t for t in outer.cell(1, 0).tables if len(t.rows) == 1 and len(t.columns) == 1][0]
    ap = box.cell(0, 0).paragraphs[0]
    for r in list(ap.runs):
        r._r.getparent().remove(r._r)
    add_inline(ap, fill(" ".join((HERE / "sections" / "abstract.md").read_text(encoding="utf-8").split())), BODY)
    kw = box.cell(0, 0).add_paragraph(style="normal")
    kw.paragraph_format.space_before = Pt(4)
    r = kw.add_run("Keywords: ")
    set_font(r, SMALL, True)
    add_inline(kw, build.KEYWORDS, SMALL)
    # drop the info box and all guidance text after the title block
    children = list(body.iterchildren())
    start = children.index(outer._tbl) + 1
    for el in children[start:]:
        if el.tag != qn("w:sectPr"):
            body.remove(el)
    for name in ORDER:
        write_section(doc, name)
    page_number_footer(doc)
    for s in doc.sections:
        s.left_margin = s.right_margin = Inches(MARGIN)
    doc.save(out)
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
