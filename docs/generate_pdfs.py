"""Render every document in docs/deliverables/ to PDF, into docs/deliverables/pdf/, and check them.

The Markdown, HTML, and slides stay the sources; the PDFs are for recipients who print, sign,
or archive, and are never edited by hand.

    python docs/generate_pdfs.py              # all six
    python docs/generate_pdfs.py SRS ERD      # only these (matched against file names)

Needs `pip install mistune pypdfium2`, plus the mermaid-cli and Chrome that generate_erd_svg.py
uses. Exits non-zero if any document fails its checks, so a bad layout cannot pass unnoticed.

Each format takes the route that keeps it most faithful:

* Markdown (SRS, UAT_REPORT, ERD) is rendered to HTML in the dashboard's theme and printed by
  headless Chrome. This uses a real Markdown parser rather than generate_manual_html.py's
  hand-rolled subset: three documents with nested lists, code, quotes, and wide tables are past
  the point where a subset stays trustworthy.
* MANUAL.html and api.html are printed from a temporary copy. The manual already carries a
  print stylesheet; the API reference was built for screens, so its copy also hides the sidebar
  and filter box and opens its collapsed notes, which would otherwise print shut. The
  generators that own those files are untouched.
* The presentation is exported by PowerPoint itself over COM - the only renderer that lays a
  .pptx out exactly as designed. Without PowerPoint it falls back to LibreOffice, and without
  either it is skipped with a note rather than failing the rest.

Diagrams are sized for paper, not for the page. Each Mermaid block is drawn as an SVG and
placed at the largest scale that still keeps its text at MIN_TEXT_PT or more:

* one that fits a portrait page at that size stays inline;
* one too wide for portrait gets a landscape page of its own (CSS named page);
* one too tall is cut into page-high slices, each cut placed in a gap between entity boxes so
  no table is split - the lines between them may cross a cut, and each slice says so.

After printing, every PDF goes through pdf_check.py (stranded headings, near-empty pages, text
at the page edge), and every diagram through the text-size floor. Page numbers come from CSS
@page margin boxes, which Chrome prints since version 131.
"""
import html.parser
import json
import math
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import generate_erd_svg as erd
import pdf_check

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "deliverables"
OUT = SRC / "pdf"
SYSTEM = "Neonatal Care System"

# source file, footer label
DOCS = [
    ("SRS.md", "Spesifikasi Kebutuhan Perangkat Lunak"),
    ("UAT_REPORT.md", "Laporan Pengujian Sistem"),
    ("ERD.md", "Entity Relationship Diagram"),
    ("MANUAL.html", "Panduan Pengguna"),
    ("api.html", "Referensi API"),
    ("Presentasi-Neonatal-Care.pptx", None),
]

MERMAID_CFG = dict(erd.MERMAID_CFG,
                   sequence={"useMaxWidth": False},
                   flowchart={"htmlLabels": False, "useMaxWidth": False})

FONT_LINK = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
             'family=Manrope:wght@400;500;600;700;800&display=swap">')

# Diagram sizing, in CSS px (96 per inch). Mermaid draws its text at 16px.
MM = 96 / 25.4
MERMAID_TEXT_PX = 16
MIN_TEXT_PT = 7.0
PORTRAIT_W = (210 - 32) * MM        # A4 minus 16mm side margins
PORTRAIT_H = 226 * MM               # leaves room for the heading and intro kept on the same page
LANDSCAPE_W = (297 - 32) * MM
LANDSCAPE_H = (210 - 12 - 19 - 30) * MM   # its heading and intro move to the landscape page too


def text_pt(scale):
    return MERMAID_TEXT_PX * scale * 0.75


def page_rules(label):
    """A4 with the document name bottom-left and 'n / N' bottom-right on every page."""
    box = "font-family:Manrope,system-ui,sans-serif;font-size:7.5pt;color:#64748B;"
    return """
@page{size:A4;margin:17mm 16mm 19mm;
  @bottom-left{content:"%s \\2014  %s";%s}
  @bottom-right{content:counter(page) " / " counter(pages);%s}}
@page wide{size:A4 landscape;margin:12mm 16mm 19mm}
html{-webkit-print-color-adjust:exact;print-color-adjust:exact}
""" % (SYSTEM, label.replace('"', '\\"'), box, box)


# Applied to every Chrome-printed document. A heading keeps its first block with it, short
# tables never split, and long ones never leave fewer than three rows on either side of a
# break. `.keep` is the wrapper keep_groups() puts around a heading and the unbreakable block
# it introduces - CSS adjacency alone does not hold, because Chrome gives up break-after:avoid
# as soon as the next block cannot be split and does not fit the space left.
KEEP_CSS = """
h1,h2,h3,h4,h5,h6{break-after:avoid;break-inside:avoid}
:is(h1,h2,h3,h4,h5,h6) + :is(p,ul,ol,blockquote,.tagnote,.lead){break-after:avoid}
figure,pre,.shot,tr{break-inside:avoid}
table:not(:has(tr:nth-child(13))){break-inside:avoid}
tbody tr:nth-child(-n+3),tbody tr:nth-last-child(-n+2){break-before:avoid}
p,li{orphans:3;widows:3}
.keep{break-inside:avoid}
.keep>:is(ul,ol):last-child{margin-bottom:0}
:is(ul,ol).cont{margin-top:0}
.wide{page:wide}
"""

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source",
        "track", "wbr"}
HEADINGS = {"h2", "h3", "h4"}
LEAD_IN_MAX = 500           # characters: an intro short enough to travel with what it introduces
TAIL_NOTE_MAX = 250         # characters: a closing note that belongs to the block above it
SPLITTABLE_ROWS = 13        # a table with more rows than this may break across pages


class _Tree(html.parser.HTMLParser):
    """Element spans as (tag, attrs, start, end, parent). Enough structure to find siblings."""

    def __init__(self, markup):
        super().__init__(convert_charrefs=False)
        self.markup = markup
        self.line_starts = [0] + [m.end() for m in re.finditer("\n", markup)]
        self.nodes, self.stack = [], [-1]
        self.feed(markup)
        self.close()

    def _offset(self):
        line, col = self.getpos()
        return self.line_starts[line - 1] + col

    def handle_starttag(self, tag, attrs):
        start = self._offset()
        end = self.markup.index(">", start) + 1
        self.nodes.append([tag, dict(attrs), start, end, self.stack[-1]])
        if tag not in VOID:
            self.stack.append(len(self.nodes) - 1)

    def handle_startendtag(self, tag, attrs):
        start = self._offset()
        self.nodes.append([tag, dict(attrs), start, self.markup.index(">", start) + 1, self.stack[-1]])

    def handle_endtag(self, tag):
        end = self.markup.index(">", self._offset()) + 1
        for depth in range(len(self.stack) - 1, 0, -1):
            if self.nodes[self.stack[depth]][0] == tag:
                for idx in self.stack[depth:]:
                    self.nodes[idx][3] = end
                del self.stack[depth:]
                break


def keep_groups(markup):
    """Wrap each heading, its short intro, and the unbreakable block it introduces in .keep."""
    tree = _Tree(markup)
    nodes = tree.nodes
    children = {}
    for i, node in enumerate(nodes):
        children.setdefault(node[4], []).append(i)

    def text_len(i):
        return len(re.sub(r"<[^>]+>|data:[^\"']+", "", markup[nodes[i][2]:nodes[i][3]]))

    def classes(i):
        return nodes[i][1].get("class", "").split()

    def unbreakable(i):
        tag, cls = nodes[i][0], classes(i)
        body = markup[nodes[i][2]:nodes[i][3]]
        if tag in ("figure", "pre") or "shot" in cls or "ep" in cls:
            return True
        if tag == "table" or "tblwrap" in cls:
            return body.count("<tr") <= SPLITTABLE_ROWS
        return False

    wraps = []
    for parent, kids in children.items():
        for pos, i in enumerate(kids):
            if nodes[i][0] not in HEADINGS:
                continue
            if pos and nodes[kids[pos - 1]][0] == "h1":     # a subtitle: the title page styles it
                continue
            j, group = pos + 1, [i]
            while j < len(kids) and len(group) < 3 and nodes[kids[j]][0] in ("p", "blockquote") \
                    and text_len(kids[j]) <= LEAD_IN_MAX and not unbreakable(kids[j]):
                group.append(kids[j])
                j += 1
            if j < len(kids) and nodes[kids[j]][0] in ("ul", "ol"):
                # A heading over a list: Chrome drops break-after:avoid when the first item
                # cannot split and does not fit, and the heading is left alone at the foot of
                # the page. A wrapper cannot cut a list in half, so the list is split instead:
                # its first item closes the .keep group, the rest continues as a second list.
                lst = kids[j]
                items = [k for k in children.get(lst, []) if nodes[k][0] == "li"]
                if len(items) > 1:
                    tag = nodes[lst][0]
                    start = int(nodes[lst][1].get("start") or 1) + 1 if tag == "ol" else None
                    reopen = '<ol class="cont" start="%d">' % start if start else '<ul class="cont">'
                    wraps.append((nodes[i][2], nodes[items[0]][3], "keep",
                                  "</%s></div>%s" % (tag, reopen)))
                    continue
            if j >= len(kids) or not unbreakable(kids[j]):
                continue
            group.append(kids[j])
            tail = j + 1
            if tail < len(kids) and nodes[kids[tail]][0] == "p" and text_len(kids[tail]) <= TAIL_NOTE_MAX \
                    and (tail + 1 >= len(kids) or nodes[kids[tail + 1]][0] in HEADINGS | {"hr"}):
                group.append(kids[tail])
            wide = any("wide" in classes(k) for k in group)
            wraps.append((nodes[group[0]][2], nodes[group[-1]][3], "keep wide" if wide else "keep",
                          "</div>"))

    # Insert as points from the back, so offsets stay valid when one group sits inside another
    # (an API section around its first card, and a Responses group inside that card). At a shared
    # offset the opening tag goes in first, which leaves the earlier group's </div> before it.
    points = [(s, 1, '<div class="%s">' % c) for s, _, c, _ in wraps] + \
             [(e, 0, close) for _, e, _, close in wraps]
    for offset, _, tag in sorted(points, reverse=True):
        markup = markup[:offset] + tag + markup[offset:]
    return markup, len(wraps)

# Tokens are the dashboard's (web/app/globals.css), as MANUAL.html and api.html use, darkened
# one step for paper the same way MANUAL.html's own print stylesheet does.
MD_CSS = """
:root{--primary:#2563EB;--ink:#0F172A;--ink-muted:#475569;--ink-faint:#64748B;
  --line:#E2E8F0;--line-strong:#CBD5E1;--surface:#F4F7FB;
  --sans:Manrope,ui-sans-serif,system-ui,sans-serif;
  --mono:ui-monospace,SFMono-Regular,Consolas,Menlo,monospace}
body{margin:0;color:var(--ink);font-family:var(--sans);font-size:9.8pt;line-height:1.55}
h1{font-size:22pt;line-height:1.15;margin:0 0 4pt;letter-spacing:-.01em}
h2{break-before:page;font-size:15.5pt;line-height:1.25;margin:0 0 8pt;
  padding-bottom:5pt;border-bottom:1.5pt solid var(--primary)}
h1+h2{break-before:auto;border:0;padding:0;margin:0 0 16pt;font-size:12.5pt;font-weight:600;
  color:var(--ink-muted)}
h3{font-size:11.5pt;margin:15pt 0 5pt}
h4{font-size:10.2pt;margin:11pt 0 4pt}
p{margin:0 0 7pt}
ul,ol{margin:0 0 7pt;padding-left:17pt}
li{margin:1.5pt 0}
a{color:var(--primary);text-decoration:none}
strong{font-weight:700}
code{font-family:var(--mono);font-size:8.6pt;background:var(--surface);padding:.5pt 2.5pt;
  border-radius:2.5pt}
pre{font-family:var(--mono);font-size:8.1pt;line-height:1.45;background:var(--surface);
  border:.75pt solid var(--line-strong);border-radius:4pt;padding:7pt 9pt;margin:6pt 0 9pt;
  white-space:pre-wrap;word-break:break-word}
pre code{background:none;padding:0;font-size:inherit}
table{border-collapse:collapse;width:100%;font-size:8.6pt;line-height:1.4;margin:5pt 0 10pt}
th{text-align:left;font-weight:700;color:var(--ink-muted);background:var(--surface);
  border-bottom:1pt solid var(--line-strong);padding:4pt 6pt;vertical-align:bottom}
td{border-bottom:.5pt solid var(--line);padding:4pt 6pt;vertical-align:top}
blockquote{margin:7pt 0 9pt;padding:6pt 10pt;border-left:2.5pt solid var(--primary);
  background:var(--surface);color:var(--ink-muted)}
blockquote p{margin:2pt 0}
hr{border:0;border-top:.75pt solid var(--line-strong);margin:12pt 0}
hr:has(+ h2){display:none}
img{max-width:100%}
figure{margin:8pt 0 12pt;text-align:center}
figure.wide{page:wide;margin:0}
figcaption{font-size:7.5pt;color:var(--ink-faint);margin-top:3pt}
"""

API_PRINT_CSS = """
.rail,.search,#empty{display:none!important}
.wrap{display:block!important;max-width:none!important;padding:0!important}
main{padding-top:10pt!important}
body{background:#fff!important;font-size:10pt!important}
.ep{box-shadow:none!important;break-inside:avoid-page}
header.masthead{background:#fff!important}
"""


def need(module, pip_name):
    try:
        return __import__(module)
    except ImportError:
        sys.exit("%s tidak ditemukan. Jalankan: pip install %s" % (module, pip_name))


def chrome_pdf(chrome, html_path, pdf_path):
    cmd = [chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
           "--run-all-compositor-stages-before-draw", "--virtual-time-budget=15000",
           "--print-to-pdf=%s" % pdf_path, html_path.as_uri()]
    done = subprocess.run(cmd, capture_output=True, text=True)
    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        sys.exit("Chrome gagal mencetak %s:\n%s" % (html_path.name, done.stderr[-800:]))


def render_mermaid(mmdc, chrome, code, dst, tmp):
    src = dst.with_suffix(".mmd")
    src.write_text(code, encoding="utf-8")
    cmd = mmdc + ["-i", str(src), "-o", str(dst), "-b", "white", "-c", str(tmp / "mermaid.json"),
                  "-p", str(tmp / "puppeteer.json")]
    done = subprocess.run(cmd, capture_output=True, text=True)
    if done.returncode or not dst.exists():
        sys.exit("mmdc gagal pada %s:\n%s%s" % (src.name, done.stdout, done.stderr))


# ---------------------------------------------------------------------------------------------
# Diagram layout


def svg_frame(svg):
    """(root tag, viewBox x, y, width, height)."""
    root = re.match(r"\s*<svg\b[^>]*>", svg).group(0)
    vx, vy, vw, vh = (float(v) for v in re.search(r'viewBox="([^"]+)"', root).group(1).split())
    return root, vx, vy, vw, vh


def box_bands(svg):
    """Vertical extents of every entity box and edge label - the places a cut must not fall.

    Mermaid places each node as a group translated to its centre, drawn by a rect or path whose
    coordinates are relative to that centre."""
    bands = []
    for m in re.finditer(r'<g class="(node|edgeLabel)[^"]*"[^>]*?transform="translate\(\s*'
                         r'([-\d.e]+)[ ,]+([-\d.e]+)\s*\)"', svg):
        cy = float(m.group(3))
        chunk = svg[m.end():m.end() + 1500]
        rect = re.search(r"<rect\b[^>]*>", chunk)
        path = re.search(r'<path\b[^>]*\bd="([^"]+)"', chunk)
        ys = []
        if rect and 'height="' in rect.group(0):
            y = re.search(r'\by="([-\d.e]+)"', rect.group(0))
            h = re.search(r'\bheight="([\d.e]+)"', rect.group(0))
            if y and h:
                ys = [float(y.group(1)), float(y.group(1)) + float(h.group(1))]
        if not ys and path:
            nums = [float(v) for v in re.findall(r"[-\d.]+(?:e-?\d+)?", path.group(1))]
            ys = nums[1::2]
        if ys:
            bands.append((cy + min(ys) - 6, cy + max(ys) + 6))
        elif m.group(1) == "edgeLabel":
            bands.append((cy - 16, cy + 16))
    return bands


def cut_points(vy, vh, max_units, bands):
    """Greedy page-high cuts, each moved up into the nearest gap between boxes."""
    cuts, top, bottom = [], vy, vy + vh
    while bottom - top > max_units:
        limit = top + max_units
        blocked = [(a, b) for a, b in bands if a < limit and b > top]
        y = limit
        for a, b in sorted(blocked, key=lambda ab: -ab[1]):
            if a < y < b:
                y = a
        if y - top < max_units * 0.35:          # no gap in reach: cut straight through
            y = limit
        cuts.append(y)
        top = y
    return cuts


def slice_svg(svg, vx, y0, vw, h):
    root = re.match(r"\s*<svg\b[^>]*>", svg).group(0)
    new_root = re.sub(r'\bviewBox="[^"]+"', 'viewBox="%s %s %s %s"' % (vx, y0, vw, h), root)
    new_root = re.sub(r'\bwidth="[^"]+"', 'width="%s"' % vw, new_root, count=1)
    new_root = re.sub(r'\bheight="[^"]+"', 'height="%s"' % h, new_root, count=1)
    return svg.replace(root, new_root, 1)


def layout_diagram(svg_path, number):
    """HTML for one diagram, and a line describing how it was placed."""
    svg = svg_path.read_text(encoding="utf-8")
    _, vx, vy, vw, vh = svg_frame(svg)
    floor = MIN_TEXT_PT / text_pt(1)
    fit = min(1.0, PORTRAIT_W / vw)

    if vh * fit <= PORTRAIT_H:
        scale = min(fit, PORTRAIT_H / vh)
        wide = min(1.0, LANDSCAPE_W / vw, LANDSCAPE_H / vh)
        if scale < floor and wide > scale:
            html = ('<figure class="wide"><img src="%s" style="width:%.1fpx" alt="Diagram %d">'
                    '</figure>' % (svg_path.as_uri(), vw * wide, number))
            return html, wide, "halaman lanskap"
        return ('<figure><img src="%s" style="width:%.1fpx" alt="Diagram %d"></figure>'
                % (svg_path.as_uri(), vw * scale, number)), scale, "sebaris"

    # Too tall: the fewest page-high slices that keep text at the floor, at the largest scale
    # that still needs no more slices than that.
    bands = box_bands(svg)
    target = max(1, math.ceil(vh * floor / PORTRAIT_H))
    scale, cuts = fit, None
    candidate = min(fit, target * PORTRAIT_H / vh)
    while candidate >= floor * 0.999:
        trial = cut_points(vy, vh, PORTRAIT_H / candidate, bands)
        if len(trial) + 1 <= target:
            scale, cuts = candidate, trial
            break
        candidate *= 0.97
    if cuts is None:                                   # gaps too sparse: accept one more slice
        scale = max(floor, min(fit, target * PORTRAIT_H / vh))
        cuts = cut_points(vy, vh, PORTRAIT_H / scale, bands)

    edges = [vy] + cuts + [vy + vh]
    parts = []
    for i in range(len(edges) - 1):
        piece = svg_path.with_name("%s-%d.svg" % (svg_path.stem, i + 1))
        piece.write_text(slice_svg(svg, vx, edges[i], vw, edges[i + 1] - edges[i]), encoding="utf-8")
        note = ("Diagram %d, bagian %d dari %d%s" % (number, i + 1, len(edges) - 1,
                " - garis relasi berlanjut ke halaman berikutnya" if i < len(edges) - 2 else ""))
        parts.append('<figure><img src="%s" style="width:%.1fpx" alt="Diagram %d bagian %d">'
                     "<figcaption>%s</figcaption></figure>"
                     % (piece.as_uri(), vw * scale, number, i + 1, note))
    return "\n".join(parts), scale, "%d bagian" % (len(edges) - 1)


# ---------------------------------------------------------------------------------------------
# Documents


def markdown_pdf(name, label, tools, tmp):
    mistune = need("mistune", "mistune")
    mmdc, chrome = tools
    text = (SRC / name).read_text(encoding="utf-8")
    stem = pathlib.Path(name).stem
    placed, collisions = [], []

    # Each mermaid block becomes figure HTML before parsing, so the parser only ever sees HTML.
    def figure(match):
        n = len(placed) + 1
        svg = tmp / ("%s-d%d.svg" % (stem, n))
        render_mermaid(mmdc, chrome, match.group(1), svg, tmp)
        collisions.extend("diagram %d: %s" % (n, c)
                          for c in pdf_check.label_collisions(svg.read_text(encoding="utf-8")))
        html, scale, how = layout_diagram(svg, n)
        placed.append((n, scale, how))
        return "\n%s\n" % html

    text = re.sub(r"```mermaid\r?\n(.*?)```", figure, text, flags=re.S)
    body = mistune.create_markdown(escape=False, plugins=["table", "strikethrough", "url"])(text)
    body, kept = keep_groups(body)
    title = re.search(r"^# (.+)$", text, re.M)

    page = """<!doctype html><html lang="id"><head><meta charset="utf-8">
<base href="%s">
<title>%s</title>%s
<style>%s%s%s</style></head><body>%s</body></html>""" % (
        SRC.as_uri() + "/", (title.group(1) if title else stem), FONT_LINK,
        page_rules(label), MD_CSS, KEEP_CSS, body)
    html_path = tmp / (stem + ".html")
    html_path.write_text(page, encoding="utf-8")
    chrome_pdf(chrome, html_path, OUT / (stem + ".pdf"))

    issues = ["diagram %d: teks %.1f pt, di bawah batas %.1f pt" % (n, text_pt(s), MIN_TEXT_PT)
              for n, s, _ in placed if text_pt(s) < MIN_TEXT_PT - 0.05] + collisions
    notes = ["diagram %d %s %.1f pt" % (n, how, text_pt(s)) for n, s, how in placed]
    return body, notes + ["%d grup dijaga utuh" % kept], issues


def html_pdf(name, label, tools, tmp):
    _, chrome = tools
    html = (SRC / name).read_text(encoding="utf-8")
    extra = page_rules(label) + KEEP_CSS + (API_PRINT_CSS if name == "api.html" else "")
    opened = len(re.findall(r"<details(?![^>]*\bopen\b)", html))
    html = re.sub(r"<details(?![^>]*\bopen\b)", "<details open", html)
    html, kept = keep_groups(html)
    # Relative links and images keep resolving against the real folder. After the doctype, not
    # before it - anything ahead of <!doctype> drops the page into quirks mode.
    base = '<base href="%s">' % (SRC.as_uri() + "/")
    doctype = re.match(r"\s*<!doctype[^>]*>", html, re.I)
    html = (html[:doctype.end()] + base + html[doctype.end():]) if doctype else base + "\n" + html
    # Last </style>, so these rules win over the page's own.
    cut = html.rfind("</style>")
    html = html[:cut] + extra + html[cut:] if cut >= 0 else html + "<style>%s</style>" % extra
    html_path = tmp / name
    html_path.write_text(html, encoding="utf-8")
    chrome_pdf(chrome, html_path, OUT / (pathlib.Path(name).stem + ".pdf"))
    return html, (["%d catatan dibuka" % opened] if opened else []) + ["%d grup dijaga utuh" % kept], []


def slides_pdf(name, _label, _tools, _tmp):
    src, dst = SRC / name, OUT / (pathlib.Path(name).stem + ".pdf")
    if sys.platform == "win32":
        # ppSaveAsPDF = 32; Open(file, ReadOnly, Untitled, WithWindow) with msoTrue = -1.
        ps = ("$ErrorActionPreference='Stop';"
              "$app=New-Object -ComObject PowerPoint.Application;"
              "try{$p=$app.Presentations.Open('%s',-1,0,0);$p.SaveAs('%s',32);$p.Close()}"
              "finally{$app.Quit()}") % (str(src).replace("'", "''"), str(dst).replace("'", "''"))
        done = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                              capture_output=True, text=True)
        if done.returncode == 0 and dst.exists():
            return None, ["PowerPoint"], []
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice:
        subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(OUT), str(src)],
                       capture_output=True, text=True)
        if dst.exists():
            return None, ["LibreOffice - periksa tata letaknya"], []
    return None, None, ["dilewati: PowerPoint maupun LibreOffice tidak ada"]


def pdf_pages(path):
    """Page objects when they are plain; otherwise the page tree's /Count."""
    data = path.read_bytes()
    pages = len(re.findall(rb"/Type\s*/Page(?!s)", data))
    counts = [int(c) for c in re.findall(rb"/Count\s+(\d+)", data)]
    return pages or (max(counts) if counts else 0)


def main():
    wanted = [a.lower() for a in sys.argv[1:]]
    docs = [d for d in DOCS if not wanted or any(w in d[0].lower() for w in wanted)]
    if not docs:
        sys.exit("Tidak ada dokumen yang cocok dengan: %s" % " ".join(sys.argv[1:]))
    need("pypdfium2", "pypdfium2")

    chrome = erd.find_chrome()
    if not chrome:
        sys.exit("Chrome atau Edge tidak ditemukan. Setel PUPPETEER_EXECUTABLE_PATH.")
    OUT.mkdir(exist_ok=True)
    needs_mermaid = any("```mermaid" in (SRC / n).read_text(encoding="utf-8")
                        for n, _ in docs if n.endswith(".md"))
    tools = [erd.find_mmdc() if needs_mermaid else None, chrome]

    handlers = {".md": markdown_pdf, ".html": html_pdf, ".pptx": slides_pdf}
    failed = 0
    with tempfile.TemporaryDirectory() as raw:
        tmp = pathlib.Path(raw)
        (tmp / "mermaid.json").write_text(json.dumps(MERMAID_CFG), encoding="utf-8")
        (tmp / "puppeteer.json").write_text(
            json.dumps({"executablePath": chrome, "args": ["--no-sandbox"]}), encoding="utf-8")
        for name, label in docs:
            markup, notes, issues = handlers[pathlib.Path(name).suffix](name, label, tools, tmp)
            pdf = OUT / (pathlib.Path(name).stem + ".pdf")
            if notes is None:
                print("  %-34s %s" % (name, issues[0]))
                failed += 1
                continue
            issues = issues + pdf_check.check(pdf, markup)
            print("  %-34s %3d hlm  %7s KB  %s  %s" % (
                pdf.name, pdf_pages(pdf), format(pdf.stat().st_size // 1024, ","),
                "OK" if not issues else "%d MASALAH" % len(issues), "; ".join(notes)))
            for it in issues:
                print("      - " + it)
            failed += bool(issues)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
