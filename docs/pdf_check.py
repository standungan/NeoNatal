"""Layout checks for the PDFs generate_pdfs.py prints. Run by it after every build.

Reads the text layer of each page and reports what a reader would trip over:

* a heading stranded at the bottom of a page - under ~3 lines of its section below it there,
  while the rest of the section continues on the next;
* a near-empty page in the middle of a document;
* text running into the right edge of the page;
* in a Mermaid ER diagram, a relationship label printed over another label or a table
  (label_collisions, run on the SVG before it is placed).

Headings come from the HTML that was printed, walked in step with the PDF's lines so that a
repeated heading ("Responses", once per endpoint) binds to the right occurrence. Pages that
are mostly heading text - a table of contents - are skipped rather than mistaken for headings.

Needs pypdfium2 (`pip install pypdfium2`).
"""
import html
import re

STRANDED_REACH_PT = 60      # about three lines of body text


def key(text):
    """Whitespace and underscores removed: neither survives PDF text extraction reliably."""
    return re.sub(r"[\s_]+", "", html.unescape(re.sub(r"<[^>]+>", "", text))).lower()


def headings(markup):
    """(level, key) in document order. An API endpoint card counts as a level-3 section."""
    pat = re.compile(r'<h([1-4])[^>]*>(.*?)</h\1>|<div class="epline">(.*?)</div>', re.S)
    out = []
    for m in pat.finditer(markup):
        level, body = (int(m.group(1)), m.group(2)) if m.group(1) else (3, m.group(3))
        if key(body):
            out.append((level, key(body)))
    return out


def lines_of(page):
    """Text lines, top to bottom, built character by character.

    pdfium's segment rectangles are not usable for this: a band sliced across a line drops
    short glyphs (the period in "1. Pendahuluan"), and a segment's box overlaps its kerned
    neighbour, doubling letters ("TeTerintegrasi")."""
    tp = page.get_textpage()
    n = tp.count_chars()
    text = tp.get_text_range(0, n)
    if len(text) != n:                                  # surrogate pairs - align the slow way
        text = [tp.get_text_range(i, 1) or " " for i in range(n)]
    lines, last = [], None
    for i in range(n):
        ch = text[i]
        if ch in ("\r", "\n"):
            continue
        l, b, r, t = tp.get_charbox(i)
        if r - l <= 0.01 or t - b <= 0.01:              # a generated space joins its neighbour
            if last is not None:
                last["chars"].append((last["r"] + 0.01, ch))
            continue
        for ln in lines:
            if min(t, ln["t"]) - max(b, ln["b"]) > 0.35 * min(t - b, ln["t"] - ln["b"]):
                break
        else:
            ln = {"b": b, "t": t, "r": r, "chars": []}
            lines.append(ln)
        ln["b"], ln["t"], ln["r"] = min(ln["b"], b), max(ln["t"], t), max(ln["r"], r)
        ln["chars"].append((l, ch))
        last = ln
    for ln in lines:
        ln["text"] = re.sub(r"\s+", " ", "".join(c for _, c in sorted(ln["chars"],
                                                                     key=lambda c: c[0]))).strip()
    return [ln for ln in sorted(lines, key=lambda ln: -ln["t"]) if ln["text"]]


_NUM = r"([-\d.e]+)"
_LABEL = re.compile(
    r'<g class="edgeLabel" transform="translate\(%s,\s*%s\)"><g class="label"[^>]*transform='
    r'"translate\(%s,\s*%s\)"><g><rect class="background"[^>]*x="%s" y="%s" width="%s" height="%s"[^>]*>'
    % ((_NUM,) * 8))
_NODE = re.compile(r'<g class="node[^"]*" id="[^"]*entity-(\w+?)-\d+"[^>]*transform="translate\(%s,\s*%s\)">'
                   % (_NUM, _NUM))


def label_collisions(svg):
    """Relationship labels in a Mermaid ER diagram that sit on another label or on an entity box.

    Mermaid places labels at edge midpoints without avoiding each other, so a crowded diagram
    can print one label over the next. Reordering the relationship lines in the source changes
    the layout and is the fix."""
    labels, nodes = [], []
    for m in _LABEL.finditer(svg):
        ex, ey, lx, ly, x, y, w, h = map(float, m.groups())
        if w > 1:
            text = re.sub(r"<[^>]+>", " ", svg[m.end():svg.find("</text>", m.end())])
            labels.append((ex + lx + x, ey + ly + y, w, h, " ".join(text.split())))
    for m in _NODE.finditer(svg):
        cx, cy = float(m.group(2)), float(m.group(3))
        chunk = svg[m.end():m.end() + 800]
        rect = re.search(r'<rect class="basic label-container"[^>]*x="%s" y="%s" width="%s" height="%s"'
                         % ((_NUM,) * 4), chunk)
        path = re.search(r'<path d="M%s %s L%s %s L%s %s' % ((_NUM,) * 6), chunk)
        if rect:
            x, y, w, h = map(float, rect.groups())
        elif path:
            x0, y0, x1, _, _, y2 = map(float, path.groups())
            x, y, w, h = x0, y0, x1 - x0, y2 - y0
        else:
            continue
        nodes.append((cx + x, cy + y, w, h, m.group(1)))

    def hit(a, b, pad=1.0):
        return (a[0] < b[0] + b[2] - pad and b[0] < a[0] + a[2] - pad
                and a[1] < b[1] + b[3] - pad and b[1] < a[1] + a[3] - pad)

    found = ['label "%s" menimpa label "%s"' % (a[4], b[4])
             for i, a in enumerate(labels) for b in labels[i + 1:] if hit(a, b)]
    found += ['label "%s" menimpa tabel %s' % (a[4], n[4]) for a in labels for n in nodes if hit(a, n)]
    return found


def check(pdf_path, markup, footer_pt=48):
    """Problems found in pdf_path, as short human-readable strings."""
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(pdf_path))
    heads = headings(markup) if markup else []
    keys = {k for _, k in heads}
    issues, flat, toc, heights = [], [], set(), []
    try:
        for p in range(len(doc)):
            page = doc[p]
            width, height = page.get_size()
            heights.append(height)
            body = [ln for ln in lines_of(page) if ln["b"] > footer_pt]
            kinds = [o.type for o in page.get_objects()]
            # Pictures count as content: raster images, embedded forms, or a real amount of vector
            # drawing (a diagram's boxes) - not just the few paths of a rule or a table border.
            images = (sum(k in (pdfium.raw.FPDF_PAGEOBJ_IMAGE, pdfium.raw.FPDF_PAGEOBJ_FORM) for k in kinds)
                      + (kinds.count(pdfium.raw.FPDF_PAGEOBJ_PATH) > 30))
            # A contents list: mostly heading text, and only near the front. Without the page
            # limit, an API page dense with "Parameters"/"Responses" labels qualifies too, and
            # skipping it throws every later heading onto the wrong occurrence.
            if heads and p < 3 and len(body) >= 6 and sum(key(ln["text"]) in keys for ln in body) >= len(body) / 2:
                toc.add(p)
            flat.extend((p, key(ln["text"]), ln["text"], ln["b"]) for ln in body)
            if p < len(doc) - 1 and len(body) < 3 and images == 0:
                issues.append("hlm %d: hampir kosong (%d baris)" % (p + 1, len(body)))
            edge = [ln for ln in body if ln["r"] > width - 20]
            if edge:
                issues.append("hlm %d: %d baris menyentuh tepi kanan, mis. %r"
                              % (p + 1, len(edge), edge[0]["text"][-40:]))
    finally:
        doc.close()

    # Bind each heading to its line, in order. A heading that never extracts is skipped
    # without moving the cursor, so one miss does not derail the rest.
    pos, cursor = {}, 0
    for hj, (_, hk) in enumerate(heads):
        for g in range(cursor, len(flat)):
            if flat[g][0] in toc:
                continue
            k = flat[g][1]
            wrapped = k + "".join(f[1] for f in flat[g + 1:g + 3])
            if k == hk or (len(k) >= 4 and hk.startswith(k) and wrapped.startswith(hk)):
                pos[hj], cursor = g, g + 1
                break

    # Stranded = near the foot of its page, followed there by little of its section, with the rest
    # continuing overleaf. "Little" is measured as the height the section reaches below the
    # heading, not as a count of text lines: a screenshot has no text, so a heading, a one-line
    # intro, and a captioned screenshot would otherwise look like two lines - and that is fine.
    matched = sorted(pos)
    for n, hj in enumerate(matched):
        g, level = pos[hj], heads[hj][0]
        page, bottom = flat[g][0], flat[g][3]
        end = next((pos[m] for m in matched[n + 1:] if heads[m][0] <= level), len(flat))
        section = flat[g + 1:end]
        below = [f[3] for f in section if f[0] == page]
        reach = bottom - min(below) if below else 0
        low = bottom - footer_pt < 0.3 * (heights[page] - footer_pt)
        if low and reach < STRANDED_REACH_PT and any(f[0] > page for f in section):
            issues.append("hlm %d: judul tertinggal di dasar halaman (%d baris sebelum pindah): %r"
                          % (page + 1, len(below), flat[g][2][:50]))
    unplaced = len(heads) - len(pos)
    if heads and unplaced > len(heads) * 0.1:
        issues.append("%d dari %d judul tidak ditemukan di PDF - pemeriksaan judul tidak lengkap"
                      % (unplaced, len(heads)))
    return issues
