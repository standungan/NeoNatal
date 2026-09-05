"""Render docs/MANUAL.md into docs/MANUAL.html.

MANUAL.md is the single source. This script exists so the two cannot drift: the HTML
is never edited by hand, it is regenerated.

    python docs/generate_manual_html.py

Handles only the Markdown subset MANUAL.md actually uses - headings, paragraphs,
tables, ordered and unordered lists, blockquotes, bold, inline code, and the
[Gambar: ...] figure placeholders. Deliberately not a general Markdown parser: a
known-small subset is easier to trust than a dependency.
"""
import html
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "MANUAL.md"
OUT = ROOT / "MANUAL.html"

e = html.escape


def inline(t):
    """Bold, inline code and the figure placeholder. Escape first, then re-introduce tags."""
    t = e(t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    return t


def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def convert(md):
    lines = md.split("\n")
    out, toc = [], []
    i, n = 0, len(lines)
    # Drop the editing note aimed at whoever maintains the Markdown.
    while i < n:
        raw = lines[i]
        s = raw.strip()

        if not s:
            i += 1
            continue

        # figure placeholder -> a labelled slot, so a missing screenshot is visible
        m = re.match(r"^\[Gambar:\s*(.+?)\]$", s)
        if m:
            out.append('<figure class="shot"><div class="slot">'
                       '<span class="slot-tag">Gambar</span>'
                       '<span class="slot-txt">%s</span></div></figure>' % e(m.group(1)))
            i += 1
            continue

        if s.startswith("---") and set(s) == {"-"}:
            out.append('<hr>')
            i += 1
            continue

        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            lvl, txt = len(m.group(1)), m.group(2)
            sid = slug(txt)
            if lvl == 2:
                toc.append((sid, txt, []))
            elif lvl == 3 and toc:
                toc[-1][2].append((sid, txt))
            out.append('<h%d id="%s">%s</h%d>' % (lvl, sid, inline(txt), lvl))
            i += 1
            continue

        # blockquote (may span several lines)
        if s.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            body = " ".join(x for x in buf if x)
            out.append('<blockquote><p>%s</p></blockquote>' % inline(body))
            continue

        # table
        if s.startswith("|"):
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            if len(rows) >= 2 and all(set(c) <= set("-: ") for c in rows[1]):
                head, body = rows[0], rows[2:]
            else:
                head, body = None, rows
            t = ['<div class="tblwrap"><table>']
            if head:
                t.append("<thead><tr>" + "".join("<th>%s</th>" % inline(c) for c in head) + "</tr></thead>")
            t.append("<tbody>")
            for r in body:
                t.append("<tr>" + "".join("<td>%s</td>" % inline(c) for c in r) + "</tr>")
            t.append("</tbody></table></div>")
            out.append("".join(t))
            continue

        # ordered list
        if re.match(r"^\d+\.\s", s):
            items = []
            while i < n and re.match(r"^\d+\.\s", lines[i].strip()):
                items.append(re.sub(r"^\d+\.\s+", "", lines[i].strip()))
                i += 1
                # continuation lines belong to the item above
                while i < n and lines[i].startswith("   ") and lines[i].strip() \
                        and not re.match(r"^\d+\.\s", lines[i].strip()):
                    items[-1] += " " + lines[i].strip()
                    i += 1
            out.append("<ol>" + "".join("<li>%s</li>" % inline(x) for x in items) + "</ol>")
            continue

        # bullet list
        if s.startswith("- "):
            items = []
            while i < n and lines[i].strip().startswith("- "):
                items.append(lines[i].strip()[2:])
                i += 1
                while i < n and lines[i].startswith("  ") and lines[i].strip() \
                        and not lines[i].strip().startswith("- "):
                    items[-1] += " " + lines[i].strip()
                    i += 1
            out.append("<ul>" + "".join("<li>%s</li>" % inline(x) for x in items) + "</ul>")
            continue

        # paragraph
        buf = []
        while i < n and lines[i].strip() and not re.match(
                r"^(#{1,4}\s|\||>|-\s|\d+\.\s|---|\[Gambar:)", lines[i].strip()):
            buf.append(lines[i].strip())
            i += 1
        if buf:
            out.append("<p>%s</p>" % inline(" ".join(buf)))
    return "\n".join(out), toc


CSS = """
:root{
  --ink:#0F172A; --ink-muted:#55637A; --ink-faint:#94A3B8;
  --surface:#F4F7FB; --card:#FFFFFF; --line:#E9EEF5; --line-strong:#D7E0EC;
  --primary:#2563EB; --accent:#0EA5E9; --ok:#10B981; --warn:#F59E0B; --bad:#EF4444;
  --sans:"IBM Plex Sans",ui-sans-serif,system-ui,sans-serif;
  --serif:"IBM Plex Serif",Georgia,"Times New Roman",serif;
  --mono:"IBM Plex Mono",ui-monospace,Consolas,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --ink:#E8EEF7; --ink-muted:#9DAABF; --ink-faint:#6B7C93;
  --surface:#0B1220; --card:#111A2B; --line:#1E2A3E; --line-strong:#2B3A52;
  --primary:#5B9BFF; --accent:#38BDF8; --ok:#34D399; --warn:#FBBF24; --bad:#F87171;
}}
:root[data-theme="dark"]{
  --ink:#E8EEF7; --ink-muted:#9DAABF; --ink-faint:#6B7C93;
  --surface:#0B1220; --card:#111A2B; --line:#1E2A3E; --line-strong:#2B3A52;
  --primary:#5B9BFF; --accent:#38BDF8; --ok:#34D399; --warn:#FBBF24; --bad:#F87171;
}
*{box-sizing:border-box}
body{margin:0;background:var(--surface);color:var(--ink);font-family:var(--sans);
  font-size:16px;line-height:1.68;-webkit-font-smoothing:antialiased}
header.mast{background:var(--card);border-bottom:1px solid var(--line)}
.mast-in{max-width:1120px;margin:0 auto;padding:34px 28px 26px}
.eyebrow{font-family:var(--mono);font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;
  color:var(--ink-faint);margin:0 0 10px}
.mast-in h1{font-family:var(--serif);font-size:33px;line-height:1.14;margin:0 0 10px;
  letter-spacing:-.01em;text-wrap:balance}
.mast-in p.lede{margin:0;color:var(--ink-muted);max-width:62ch}
.wrap{display:grid;grid-template-columns:236px minmax(0,1fr);gap:44px;
  max-width:1120px;margin:0 auto;padding:0 28px 90px}
nav.toc{position:sticky;top:0;align-self:start;height:100vh;overflow-y:auto;padding-top:32px}
nav.toc a{display:block;text-decoration:none;color:var(--ink-muted);font-size:13.5px;
  padding:4px 9px;border-radius:6px;line-height:1.35}
nav.toc a:hover,nav.toc a:focus-visible{background:var(--card);color:var(--ink)}
nav.toc a.sub{padding-left:20px;font-size:12.5px;color:var(--ink-faint)}
main{padding-top:32px;max-width:74ch}
h2{font-family:var(--serif);font-size:25px;margin:44px 0 10px;padding-bottom:10px;
  border-bottom:2px solid var(--line-strong);scroll-margin-top:14px;text-wrap:balance}
h2:first-child{margin-top:0}
h3{font-family:var(--sans);font-weight:600;font-size:17.5px;margin:30px 0 8px;
  scroll-margin-top:14px;color:var(--ink)}
h4{font-family:var(--mono);font-size:12px;letter-spacing:.09em;text-transform:uppercase;
  color:var(--ink-faint);margin:22px 0 6px}
p{margin:0 0 14px}
ul,ol{margin:0 0 15px;padding-left:22px}
li{margin:0 0 6px}
code{font-family:var(--mono);font-size:13.5px;background:var(--line);padding:1.5px 5px;
  border-radius:4px}
strong{font-weight:600}
hr{border:0;border-top:1px solid var(--line);margin:34px 0}
blockquote{margin:0 0 16px;padding:13px 17px;background:var(--card);
  border:1px solid var(--line);border-left:3px solid var(--warn);border-radius:0 8px 8px 0}
blockquote p{margin:0;color:var(--ink-muted);font-size:15px}
.tblwrap{overflow-x:auto;border:1px solid var(--line);border-radius:9px;margin:0 0 18px;
  background:var(--card)}
table{border-collapse:collapse;width:100%;font-size:14.5px}
th{text-align:left;font-weight:600;font-size:11.5px;letter-spacing:.06em;text-transform:uppercase;
  color:var(--ink-faint);padding:9px 13px;background:var(--surface);
  border-bottom:1px solid var(--line)}
td{padding:9px 13px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:0}
figure.shot{margin:0 0 18px}
.slot{border:1.5px dashed var(--line-strong);border-radius:9px;background:var(--card);
  padding:26px 20px;display:flex;flex-direction:column;align-items:center;gap:7px;
  text-align:center}
.slot-tag{font-family:var(--mono);font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;
  color:var(--accent)}
.slot-txt{color:var(--ink-muted);font-size:14px;max-width:46ch}
@media(max-width:900px){
  .wrap{grid-template-columns:1fr;gap:0}
  nav.toc{position:static;height:auto;padding-top:12px;margin-bottom:20px}
  main{max-width:none}
}
@media print{
  :root{--ink:#000;--ink-muted:#333;--ink-faint:#666;--surface:#fff;--card:#fff;
        --line:#ccc;--line-strong:#999}
  body{font-size:10.5pt;line-height:1.5;background:#fff}
  header.mast{border-bottom:2px solid #000}
  .mast-in{padding:0 0 14pt}
  nav.toc{display:none}
  .wrap{display:block;max-width:none;padding:0}
  main{max-width:none;padding-top:12pt}
  h2{page-break-before:always;page-break-after:avoid;font-size:16pt}
  h2:first-of-type{page-break-before:avoid}
  h3{page-break-after:avoid;font-size:12pt}
  table,figure,blockquote,.tblwrap{page-break-inside:avoid}
  .slot{border:1pt dashed #999}
  a{color:#000;text-decoration:none}
  @page{margin:16mm 14mm}
}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""


def main():
    md = SRC.read_text(encoding="utf-8")
    # strip the H1 and the maintainer note; the masthead carries them
    md = re.sub(r"\A# .*?\n", "", md, count=1)
    md = re.sub(r"\A\s*>.*?(?=\n\n)", "", md, count=1, flags=re.S)
    body, toc = convert(md)

    nav = []
    for sid, txt, subs in toc:
        nav.append('<a href="#%s">%s</a>' % (sid, e(txt)))
        for ssid, stxt in subs:
            nav.append('<a class="sub" href="#%s">%s</a>' % (ssid, e(stxt)))

    page = """<title>Panduan Neonatal Care</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Serif:wght@600;700&display=swap">
<style>%s</style>
<header class="mast"><div class="mast-in">
  <p class="eyebrow">Sistem Monitoring Bayi pada Inkubator</p>
  <h1>Panduan Pengguna</h1>
  <p class="lede">Untuk perawat, dokter, dan admin. Disusun per peran &mdash; cari bagian
  Anda, lewati sisanya. Pemasangan server dan pemrograman alat ada di
  <code>DEPLOYMENT.md</code>, bukan di sini.</p>
</div></header>
<div class="wrap">
  <nav class="toc">%s</nav>
  <main>%s</main>
</div>
""" % (CSS, "".join(nav), body)

    OUT.write_text(page, encoding="utf-8")
    figs = page.count('class="slot"')
    print("  %s (%s bytes, %d bagian, %d slot gambar)"
          % (OUT.name, format(len(page), ","), len(toc), figs))


if __name__ == "__main__":
    sys.exit(main())
