"""Render the Mermaid blocks in docs/deliverables/ERD.md into docs/deliverables/ERD.svg.

ERD.md is the single source. The SVG beside it is a rendering, never edited by hand -
the previous one was a PlantUML export that sat six days behind the schema before anyone
noticed, which is what this script exists to prevent.

    python docs/generate_erd_svg.py

Needs mermaid-cli and a Chrome for it to drive:

    npm install @mermaid-js/mermaid-cli

Chrome is found automatically on Windows, or set PUPPETEER_EXECUTABLE_PATH. If mermaid-cli
brought its own Chromium, that is used instead and nothing needs to be found.

Two rendering choices worth knowing about:

* `htmlLabels` is off. Mermaid's default wraps every label in a <foreignObject> holding
  HTML, which looks right in a browser and disappears in Inkscape, Illustrator, and most
  SVG-to-PDF converters. Off, labels are real <text> and the file survives being printed
  or dropped into a report.
* Section 1 is five diagrams, so the output stitches them into one file under a heading
  each. Each diagram's internal ids are namespaced (erd1..erdN) so that five style blocks
  and five sets of arrow markers do not collide once they share a document.

Every diagram is checked for relationship labels printed over another label or over a table
(pdf_check.label_collisions). Mermaid does not avoid those itself; the order of relationship
lines in ERD.md decides the layout, so reordering them is the fix. The SVG is still written
when a collision is found, but the run exits non-zero.

The footer date comes from the document's own history table rather than from today, so it
does not churn on every render. Mermaid still routes edge curves slightly differently from
run to run, so expect a small diff in the path data even when nothing changed - entity
positions and sizes are stable, only the curves between them wobble.
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import pdf_check

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "deliverables" / "ERD.md"
OUT = ROOT / "deliverables" / "ERD.svg"

MERMAID_CLI = "11.17.0"   # pinned: layout shifts between mermaid versions

PAD = 44            # margin, and the left edge every diagram is aligned to
GAP_TITLE = 26      # section heading baseline -> top of its diagram
GAP_SECTION = 60    # bottom of a diagram -> next heading baseline
HEAD_RULE = 104     # y of the rule under the document title
FONT = "&quot;Trebuchet MS&quot;, Verdana, Arial, sans-serif"

MERMAID_CFG = {
    "theme": "default",
    "htmlLabels": False,
    "er": {"useMaxWidth": False, "htmlLabels": False},
    "flowchart": {"htmlLabels": False},
}

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


def find_mmdc():
    """Local install, then PATH, then npx. Returns an argv prefix."""
    for name in ("mmdc.cmd", "mmdc"):
        local = ROOT.parent / "node_modules" / ".bin" / name
        if local.exists():
            return argv_for(str(local))
    found = shutil.which("mmdc")
    if found:
        return argv_for(found)
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if npx:
        print("  catatan  : mmdc belum terpasang, memakai npx (unduh sekali, lambat).")
        print("             lebih cepat: npm install -g @mermaid-js/mermaid-cli")
        return argv_for(npx) + ["-y", "-p", "@mermaid-js/mermaid-cli@%s" % MERMAID_CLI, "mmdc"]
    sys.exit("mmdc dan npx tidak ditemukan. Jalankan: npm install -g @mermaid-js/mermaid-cli")


def argv_for(path):
    """Windows cannot CreateProcess a .cmd shim directly; go through the shell."""
    if path.lower().endswith((".cmd", ".bat")):
        return [os.environ.get("COMSPEC", "cmd.exe"), "/c", path]
    return [path]


def find_chrome():
    env = os.environ.get("PUPPETEER_EXECUTABLE_PATH")
    if env and pathlib.Path(env).exists():
        return env
    for c in CHROME_CANDIDATES:
        if pathlib.Path(c).exists():
            return c
    for name in ("google-chrome", "chromium", "chrome"):
        found = shutil.which(name)
        if found:
            return found
    return None                      # mermaid-cli's own Chromium, if it has one


def read_source():
    md = SRC.read_text(encoding="utf-8")
    blocks = re.findall(r"```mermaid\r?\n(.*?)```", md, re.S)
    titles = re.findall(r"^### (1\.\d.*)$", md, re.M)
    if not blocks:
        sys.exit("%s tidak memuat blok mermaid." % SRC.name)
    if len(blocks) != len(titles):
        sys.exit("%d blok mermaid tetapi %d judul '### 1.x' - keduanya harus sama."
                 % (len(blocks), len(titles)))
    return md, blocks, titles


def subtitle(md):
    """Facts for the header line, taken from the document so they cannot drift."""
    bits = ["PostgreSQL 16"]
    tables = re.search(r"\*\*(\d+) tabel\*\*", md)
    if tables:
        bits.append("%s tabel" % tables.group(1))
    rev = re.search(r"revisi \*\*`([0-9a-f]+)_", md)
    if rev:
        bits.append("revisi Alembic %s" % rev.group(1))
    bits.append("sumber: docs/deliverables/%s" % SRC.name)
    return " \u00b7 ".join(bits)


def stamp(md):
    """Newest row of the history table - stable across re-renders."""
    row = re.search(r"^\|\s*([\d.]+)\s*\|\s*([^|]+?)\s*\|", md[md.find("## 6."):], re.M)
    return "v%s \u00b7 %s" % (row.group(1), row.group(2)) if row else ""


def render(mmdc, chrome, code, index, tmp):
    src = tmp / ("d%d.mmd" % index)
    dst = tmp / ("d%d.svg" % index)
    src.write_text(code, encoding="utf-8")
    cmd = mmdc + ["-i", str(src), "-o", str(dst), "-b", "white", "-c", str(tmp / "mermaid.json")]
    if chrome:
        cmd += ["-p", str(tmp / "puppeteer.json")]
    done = subprocess.run(cmd, capture_output=True, text=True)
    if done.returncode or not dst.exists():
        sys.exit("mmdc gagal pada diagram %d:\n%s%s" % (index, done.stdout, done.stderr))
    return dst.read_text(encoding="utf-8").strip()


def namespace(svg, index):
    """Make one diagram's ids unique so five can share a document."""
    svg = svg.replace("my-svg", "erd%d" % index)          # style scope + arrow markers
    return svg.replace('id="id_entity', 'id="erd%d_id_entity' % index)


def frame(svg, top):
    """Re-open a rendered diagram as a nested <svg> placed at y=top."""
    head = re.match(r"<svg\s+([^>]*?)>", svg)
    attrs = dict(re.findall(r'([\w:-]+)="([^"]*)"', head.group(1)))
    open_tag = (
        '<svg x="%d" y="%.2f" width="%s" height="%s" viewBox="%s" id="%s" class="erDiagram"'
        ' xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">'
        % (PAD, top, attrs["width"], attrs["height"], attrs["viewBox"], attrs["id"]))
    return float(attrs["width"]), float(attrs["height"]), open_tag + svg[head.end():]


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def compose(parts, titles, md):
    body, y, widest = [], HEAD_RULE + 44, 0
    for (w, h, markup), title in zip(parts, titles):
        body.append('<text class="section" x="%d" y="%.2f">%s</text>' % (PAD, y, esc(title)))
        body.append(markup)
        widest = max(widest, w)
        y += GAP_TITLE + h + GAP_SECTION
    width = widest + 2 * PAD
    height = y - GAP_SECTION + PAD + 34
    when = stamp(md)
    note = "Dihasilkan dari blok Mermaid di docs/deliverables/%s%s. Jangan disunting " \
           "langsung; jalankan docs/generate_erd_svg.py bila dokumen berubah." \
           % (SRC.name, " \u2014 " + when if when else "")
    return width, height, """<svg xmlns="http://www.w3.org/2000/svg" \
xmlns:xlink="http://www.w3.org/1999/xlink" width="%(w).0f" height="%(h).0f" \
viewBox="0 0 %(w).0f %(h).0f" role="img">
<title>Entity Relationship Diagram \u2014 Neonatal Care System</title>
<desc>%(desc)s</desc>
<style>
  .bg { fill: #ffffff; }
  text { font-family: %(font)s; fill: #333333; }
  .h1 { font-size: 25px; font-weight: 700; }
  .sub { font-size: 14px; fill: #666666; }
  .section { font-size: 19px; font-weight: 700; }
  .foot { font-size: 12px; fill: #888888; }
  .rule { stroke: #dddddd; stroke-width: 1; }
</style>
<rect class="bg" x="0" y="0" width="%(w).0f" height="%(h).0f"/>
<text class="h1" x="%(pad)d" y="52">Entity Relationship Diagram \u2014 Neonatal Care System</text>
<text class="sub" x="%(pad)d" y="80">%(sub)s</text>
<line class="rule" x1="%(pad)d" y1="%(rule)d" x2="%(rx).0f" y2="%(rule)d"/>
%(body)s
<text class="foot" x="%(pad)d" y="%(fy).0f">%(note)s</text>
</svg>
""" % dict(w=width, h=height, pad=PAD, rule=HEAD_RULE, rx=width - PAD,
           body="\n".join(body), fy=height - PAD + 6, font=FONT,
           sub=esc(subtitle(md)), note=esc(note),
           desc=esc("Diagram hubungan antar tabel, dipecah menjadi %d bagian." % len(parts)))


def main():
    md, blocks, titles = read_source()
    mmdc, chrome = find_mmdc(), find_chrome()
    print("  sumber   : %s (%d diagram)" % (SRC.name, len(blocks)))
    print("  perender : %s" % (pathlib.Path(chrome).name if chrome
                               else "Chromium bawaan mermaid-cli"))

    with tempfile.TemporaryDirectory() as raw:
        tmp = pathlib.Path(raw)
        (tmp / "mermaid.json").write_text(json.dumps(MERMAID_CFG), encoding="utf-8")
        if chrome:
            (tmp / "puppeteer.json").write_text(
                json.dumps({"executablePath": chrome, "args": ["--no-sandbox"]}), encoding="utf-8")
        parts, y, collisions = [], HEAD_RULE + 44 + GAP_TITLE, []
        for i, code in enumerate(blocks, 1):
            rendered = render(mmdc, chrome, code, i, tmp)
            found = pdf_check.label_collisions(rendered)
            collisions += ["%s: %s" % (titles[i - 1], c) for c in found]
            svg = namespace(rendered, i)
            w, h, markup = frame(svg, y)
            parts.append((w, h, markup))
            y += h + GAP_SECTION + GAP_TITLE
            print("  %-34s %6.0f x %6.0f%s" % (titles[i - 1], w, h,
                                              "  %d label bertumpuk" % len(found) if found else ""))

    width, height, svg = compose(parts, titles, md)
    if "<foreignObject" in svg:
        sys.exit("label masih berupa foreignObject - periksa htmlLabels pada MERMAID_CFG.")
    OUT.write_text(svg, encoding="utf-8")
    print("  %s (%s bytes, %.0f x %.0f)" % (OUT.name, format(len(svg), ","), width, height))
    if collisions:
        # Still written, so it can be inspected - but the run fails until the source is reordered.
        print("  label bertumpuk - ubah urutan baris relasi di ERD.md:")
        for c in collisions:
            print("    - " + c)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
